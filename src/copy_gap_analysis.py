"""Copy-gap diagnosis (2026-08-17, owner-directed): why paper copying lost
money while the copied wallets' own entry edge on the same trades was
positive. Read-only against the live DB (paper.py holds the writer).

Answers, in order: (1) per-share decomposition of the gap into wallet
counterfactual edge, pre-signal decay, and spread/slippage, per CLOSED fill,
overall and by category; (2) whether the signal-forming trades' own edge
matches the cohort-B SPORTS baseline (selection effect) or not (mechanism);
(3) favorite/longshot anatomy of realized losses; (4) a BOUNDED-ESTIMATE
copy-exit counterfactual against the actual hold_to_resolution outcome; (5)
whether the SKIPPED/STALE filters saved or cost money, where a price proxy
exists to judge.

Run: python src/copy_gap_analysis.py -> reports/copy_gap_analysis.md +
     reports/copy_gap_fills.csv
"""
import csv
import json
import logging
import os
import random
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional

import db
import signals as sig
from data_api import load_config

log = logging.getLogger("copy_gap_analysis")

REPORT_MD = os.path.join(db.REPO_ROOT, "reports", "copy_gap_analysis.md")
FILLS_CSV = os.path.join(db.REPO_ROOT, "reports", "copy_gap_fills.csv")


def ro_connect() -> sqlite3.Connection:
    """Read-only connection — paper.py is the sole writer to this DB."""
    conn = sqlite3.connect(f"file:{db.DB_PATH}?mode=ro", uri=True, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


# ---------- loading ----------

def load_closed_fills(conn: sqlite3.Connection) -> list[dict]:
    """All CLOSED paper_trades rows with category backfilled from markets."""
    rows = conn.execute(
        """SELECT pt.*, COALESCE(pt.category, m.category, 'UNMAPPED') AS category_final
           FROM paper_trades pt LEFT JOIN markets m ON m.condition_id = pt.condition_id
           WHERE pt.status = 'CLOSED' ORDER BY pt.id""").fetchall()
    return [dict(r) for r in rows]


def load_filtered(conn: sqlite3.Connection, status: str) -> list[dict]:
    """SKIPPED or STALE rows with category backfilled and market resolution joined."""
    rows = conn.execute(
        """SELECT pt.*, COALESCE(pt.category, m.category, 'UNMAPPED') AS category_final,
                  m.closed AS m_closed, m.outcome_prices AS m_outcome_prices
           FROM paper_trades pt LEFT JOIN markets m ON m.condition_id = pt.condition_id
           WHERE pt.status = ? ORDER BY pt.id""", (status,)).fetchall()
    return [dict(r) for r in rows]


# ---------- 1. per-share decomposition ----------

def decompose(fills: list[dict], tol: float = 1e-6) -> list[dict]:
    """Per-fill decomposition: wallet counterfactual edge, decay, spread, our edge.

    Only rows exited via 'resolution' have a payout (exit_price = the
    resolution price); rows exited via 'copy_exits' are excluded from the
    decomposition (payout is undefined for an early sale) and flagged.
    """
    rows = []
    for f in fills:
        if f["exit_type"] != "resolution":
            log.warning("fill id=%s exit_type=%s excluded from decomposition "
                        "(payout undefined for a non-resolution exit)", f["id"], f["exit_type"])
            continue
        entry, mid, avg_tr, payout = (f["entry_price"], f["midpoint_at_signal"],
                                       f["avg_trader_price"], f["exit_price"])
        if None in (entry, mid, avg_tr, payout) or entry <= 0:
            log.warning("fill id=%s missing a required price field — excluded", f["id"])
            continue
        shares = f["position_usd"] / entry
        wallet_cf = payout - avg_tr           # wallets' own counterfactual edge/share
        decay = mid - avg_tr                  # pre-signal price drift/share
        spread = entry - mid                  # book-crossing cost/share
        our = payout - entry                  # our realized edge/share
        identity_diff = our - (wallet_cf - decay - spread)
        if abs(identity_diff) > tol:
            raise AssertionError(
                f"identity check failed for fill id={f['id']}: our={our:.6f} vs "
                f"wallet_cf-decay-spread={(wallet_cf - decay - spread):.6f} (diff {identity_diff:.2e})")
        rows.append({
            "id": f["id"], "condition_id": f["condition_id"], "outcome_index": f["outcome_index"],
            "category": f["category_final"], "signal_time": f["signal_time"],
            "exit_time": f["exit_time"], "position_usd": f["position_usd"],
            "entry_price": entry, "midpoint_at_signal": mid, "avg_trader_price": avg_tr,
            "payout": payout, "shares": shares,
            "wallet_cf_edge_per_share": wallet_cf, "decay_per_share": decay,
            "spread_per_share": spread, "our_edge_per_share": our,
            "identity_diff": identity_diff,
            "wallet_cf_dollars": wallet_cf * shares, "decay_dollars": decay * shares,
            "spread_dollars": spread * shares, "our_dollars": our * shares,
            "pnl_20_actual": f["pnl_20"], "wallets": json.loads(f["wallets"] or "[]"),
            "tx_hashes": json.loads(f["tx_hashes"] or "[]"),
        })
    return rows


def stake_weighted_mean(rows: list[dict], key: str) -> Optional[float]:
    """sum(value_i * stake_i) / sum(stake_i) — cents/share convention weighted by $ stake."""
    stake = sum(r["position_usd"] for r in rows)
    return sum(r[key] * r["position_usd"] for r in rows) / stake if stake else None


def simple_mean(rows: list[dict], key: str) -> Optional[float]:
    return sum(r[key] for r in rows) / len(rows) if rows else None


def dollar_concentration(rows: list[dict], key: str) -> Optional[dict]:
    """Flags whether a single fill's $ component dominates the aggregate.

    $ components scale with shares = stake/entry_price, so a fill with a very
    low entry_price (large implied share count) can dwarf every other fill's
    $ contribution even though its per-share value is unremarkable — the
    stake-weighted c/share aggregate is not affected by this (it weights by
    stake, not shares), but the $ totals can be. Surfaced so the report can
    warn when the $ column is not representative."""
    if not rows:
        return None
    total = sum(r[key] for r in rows)
    top = max(rows, key=lambda r: abs(r[key]))
    share = abs(top[key]) / abs(total) if total else None
    return {"top_id": top["id"], "top_entry_price": top["entry_price"],
            "top_value": top[key], "total": total, "share_of_total": share}


def aggregate_decomposition(rows: list[dict]) -> dict:
    """$ totals and both mean conventions (stake-weighted, simple unweighted) per component."""
    dollar_keys = ["wallet_cf_dollars", "decay_dollars", "spread_dollars", "our_dollars"]
    share_keys = ["wallet_cf_edge_per_share", "decay_per_share", "spread_per_share", "our_edge_per_share"]
    out = {"n": len(rows), "total_stake": sum(r["position_usd"] for r in rows)}
    for k in dollar_keys:
        out[k] = sum(r[k] for r in rows)
    for k in share_keys:
        out[k + "_stakewtd"] = stake_weighted_mean(rows, k)
        out[k + "_simple"] = simple_mean(rows, k)
    return out


# ---------- 2. selection effect vs cohort baseline ----------

def signal_trade_cross_check(conn: sqlite3.Connection, rows: list[dict]) -> dict:
    """Per-trade edge on the exact signal-forming trades (tx_hashes -> trades),
    stake-weighted: mean((payout - price) weighted by size_usd). Cross-checks
    avg_trader_price and gives a unit-matched per-$-of-stake selection figure."""
    all_tx = {tx for r in rows for tx in r["tx_hashes"]}
    payout_by_fill = {r["condition_id"]: r["payout"] for r in rows}
    tx_by_fill_cond = {}
    for r in rows:
        for tx in r["tx_hashes"]:
            tx_by_fill_cond[tx] = r["condition_id"]
    trades_rows = []
    ph = ",".join("?" * len(all_tx))
    if all_tx:
        trades_rows = conn.execute(
            f"SELECT tx_hash, condition_id, wallet, side, outcome_index, size_usd, price "
            f"FROM trades WHERE tx_hash IN ({ph})", list(all_tx)).fetchall()
    trades_by_hash: dict = defaultdict(list)
    for t in trades_rows:
        trades_by_hash[t["tx_hash"]].append(dict(t))

    per_share_diffs, per_dollar_diffs, stakes = [], [], []
    matched, missing = 0, 0
    for r in rows:
        payout = r["payout"]
        for tx in r["tx_hashes"]:
            cand = [t for t in trades_by_hash.get(tx, [])
                    if t["condition_id"] == r["condition_id"] and t["outcome_index"] == r["outcome_index"]]
            if not cand:
                missing += 1
                continue
            for t in cand:
                matched += 1
                stake = t["size_usd"]
                per_share = payout - t["price"]                # payout - price, stake-weighted (task spec)
                per_dollar = per_share / t["price"] if t["price"] else None
                per_share_diffs.append(per_share * stake)
                if per_dollar is not None:
                    per_dollar_diffs.append(per_dollar * stake)
                stakes.append(stake)
    total_stake = sum(stakes)
    return {
        "n_trades_matched": matched, "n_trades_missing": missing,
        "per_share_edge_stakewtd": (sum(per_share_diffs) / total_stake) if total_stake else None,
        "per_dollar_edge_stakewtd": (sum(per_dollar_diffs) / total_stake) if total_stake else None,
    }


def avg_trader_price_reconciliation(rows: list[dict], cross: dict) -> dict:
    """How avg_trader_price (payout-avg_tr) compares to the direct trades-table
    cross-check, both stake-weighted, both restricted to the same fills."""
    return {
        "from_avg_trader_price_stakewtd": stake_weighted_mean(rows, "wallet_cf_edge_per_share"),
        "from_trades_table_stakewtd": cross["per_share_edge_stakewtd"],
    }


# ---------- 3. favorite-longshot anatomy ----------

def bucket_of(price: float, buckets: list[float]) -> str:
    for i in range(len(buckets) - 1):
        lo, hi = buckets[i], buckets[i + 1]
        if (price < hi) or (i == len(buckets) - 2 and price <= hi):
            return f"{lo:.1f}-{hi:.1f}"
    return f">{buckets[-1]:.1f}"


def favorite_longshot(rows: list[dict], buckets: list[float]) -> list[dict]:
    by_bucket: dict = defaultdict(list)
    for r in rows:
        by_bucket[bucket_of(r["entry_price"], buckets)].append(r)
    out = []
    order = [f"{buckets[i]:.1f}-{buckets[i+1]:.1f}" for i in range(len(buckets) - 1)]
    for b in order:
        rs = by_bucket.get(b, [])
        if not rs:
            out.append({"bucket": b, "n": 0})
            continue
        wins = [r for r in rs if r["pnl_20_actual"] > 0]
        losses = [r for r in rs if r["pnl_20_actual"] <= 0]
        avg_win = (sum(r["pnl_20_actual"] for r in wins) / len(wins)) if wins else None
        avg_stake = sum(r["position_usd"] for r in rs) / len(rs)
        # win rate needed to break even given this bucket's realized avg win vs
        # a full-stake loss (payout=0 always costs exactly -stake, regardless
        # of entry price, since pnl=(payout-entry)*shares=payout*shares-stake)
        breakeven = avg_stake / (avg_win + avg_stake) if avg_win is not None and avg_win + avg_stake > 0 else None
        out.append({
            "bucket": b, "n": len(rs),
            "win_rate": len(wins) / len(rs),
            "avg_win": avg_win,
            "avg_loss": (sum(r["pnl_20_actual"] for r in losses) / len(losses)) if losses else None,
            "breakeven_win_rate": breakeven,
            "total_pnl": sum(r["pnl_20_actual"] for r in rs),
            "our_edge_per_share_simple": simple_mean(rs, "our_edge_per_share"),
            "our_edge_per_share_stakewtd": stake_weighted_mean(rs, "our_edge_per_share"),
        })
    return out


# ---------- 4. exit-policy counterfactual ----------

def load_condition_trades(conn: sqlite3.Connection, condition_id: str) -> list[dict]:
    return [dict(r) for r in conn.execute(
        """SELECT tx_hash, condition_id, wallet, side, outcome_index, size_usd, price, timestamp
           FROM trades WHERE condition_id = ?""", (condition_id,))]


def copy_exit_price(all_trades: list[dict], wallets: list[str], condition_id: str,
                    outcome_index: int, t0: int, exit_ts: int) -> Optional[float]:
    """Stake-weighted price over signal wallets' SELLs in (t0, exit_ts], mirroring
    how avg_trader_price is computed for entries."""
    wset = set(wallets)
    sells = [t for t in all_trades
             if t["side"] == "SELL" and t["condition_id"] == condition_id
             and t.get("outcome_index") == outcome_index and t["wallet"] in wset
             and t0 < t["timestamp"] <= exit_ts and t["price"] > 0]
    total_usd = sum(t["size_usd"] for t in sells)
    return (sum(t["price"] * t["size_usd"] for t in sells) / total_usd) if total_usd else None


def exit_counterfactual(conn: sqlite3.Connection, rows: list[dict], wallet_fraction: float,
                        sold_fraction: float) -> list[dict]:
    """Per-fill copy-exit counterfactual vs the realized hold outcome."""
    out = []
    for r in rows:
        all_trades = load_condition_trades(conn, r["condition_id"])
        s = {"condition_id": r["condition_id"], "outcome_index": r["outcome_index"],
             "signal_time": r["signal_time"], "wallets": r["wallets"]}
        exit_ts = sig.compute_copy_exit(s, all_trades, wallet_fraction, sold_fraction)
        row = {"id": r["id"], "condition_id": r["condition_id"], "category": r["category"],
               "hold_pnl": r["pnl_20_actual"], "shares": r["shares"],
               "copy_exit_ts": exit_ts, "triggered_before_resolution": False,
               "copy_exit_price": None, "copy_exit_pnl": r["pnl_20_actual"]}
        if exit_ts is not None and r["exit_time"] and exit_ts < r["exit_time"]:
            px = copy_exit_price(all_trades, r["wallets"], r["condition_id"], r["outcome_index"],
                                 r["signal_time"], exit_ts)
            if px is not None:
                row["triggered_before_resolution"] = True
                row["copy_exit_price"] = px
                row["copy_exit_pnl"] = (px - r["entry_price"]) * r["shares"]
        out.append(row)
    return out


# ---------- 5. SKIPPED / STALE counterfactual ----------

def filtered_counterfactual(rows: list[dict]) -> dict:
    """Hypothetical PnL at position stake, priced at midpoint_at_signal (fall
    back to entry_price, which is always NULL for SKIPPED/STALE in practice
    since these rows never got a filled book walk — kept for spec fidelity
    and future rows), using markets.outcome_prices for the payout. Skips (and
    counts) rows with neither a price proxy nor a resolved market on file."""
    computed, no_price, not_resolved, no_price_and_not_resolved = [], 0, 0, 0
    for r in rows:
        proxy = r["midpoint_at_signal"] if r["midpoint_at_signal"] is not None else r["entry_price"]
        resolved = bool(r["m_closed"])
        if proxy is None and not resolved:
            no_price_and_not_resolved += 1
            continue
        if proxy is None:
            no_price += 1
            continue
        if not resolved:
            not_resolved += 1
            continue
        try:
            payout = float(json.loads(r["m_outcome_prices"])[r["outcome_index"]])
        except (TypeError, ValueError, IndexError, json.JSONDecodeError):
            no_price_and_not_resolved += 1
            continue
        stake = r["position_usd"] or 0.0
        shares = stake / proxy if proxy else 0.0
        pnl = (payout - proxy) * shares
        computed.append({"id": r["id"], "condition_id": r["condition_id"],
                         "category": r["category_final"], "proxy_price": proxy,
                         "payout": payout, "hypothetical_pnl": pnl})
    return {
        "total": len(rows), "computed": computed,
        "n_computed": len(computed), "n_no_price": no_price,
        "n_not_resolved": not_resolved, "n_neither": no_price_and_not_resolved,
        "hypothetical_pnl_sum": sum(c["hypothetical_pnl"] for c in computed),
    }


# ---------- bootstrap ----------

def bootstrap_mean_ci(values: list[float], bcfg: dict) -> Optional[dict]:
    """Percentile bootstrap 95% CI on the mean, seeded for reproducibility."""
    n = len(values)
    if n < bcfg["min_n_report"]:
        return None
    rng = random.Random(bcfg["seed"])
    means = []
    for _ in range(bcfg["iterations"]):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    lo, hi = int(0.025 * len(means)), int(0.975 * len(means)) - 1
    return {"n": n, "mean": sum(values) / n, "ci_lo": means[lo], "ci_hi": means[hi]}


# ---------- report ----------

def fmt(v, spec: str, na: str = "-") -> str:
    return format(v, spec) if v is not None else na


def write_report(cfg: dict, all_rows: list[dict], sports_rows: list[dict],
                 by_cat_agg: dict, overall_agg: dict, cross: dict, recon: dict,
                 fl_table: list[dict], exit_cf: list[dict], skipped_cf: dict,
                 stale_cf: dict, boot: Optional[dict], sports_concentration: dict) -> None:
    acfg = cfg["analysis"]["copy_gap"]
    ctx_edge = acfg["sports_wallet_entry_edge_context"]
    n_sports = len(sports_rows)
    L = [
        "# Copy-gap diagnosis — generated " + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "",
        f"**Question**: paper trading shows net realized ${recon['total']:+.2f} over "
        f"{recon['n']} CLOSED fills, while the copied wallets' own measured entry edge on "
        "SPORTS is positive (+0.072 PnL/$). Where does the copy gap come from — "
        "selection (consensus fires on the wallets' bad trades), timing/decay "
        "(price moves before our entry), spread cost (we cross the book), or "
        "exit policy (hold_to_resolution vs the wallets' own exits)?",
        "",
        "## Executive summary",
        "",
    ]
    wcf = overall_agg["wallet_cf_edge_per_share_stakewtd"]
    dec = overall_agg["decay_per_share_stakewtd"]
    spr = overall_agg["spread_per_share_stakewtd"]
    our = overall_agg["our_edge_per_share_stakewtd"]
    sports_agg = by_cat_agg.get("SPORTS", {})
    swcf = sports_agg.get("wallet_cf_edge_per_share_stakewtd")
    sdec = sports_agg.get("decay_per_share_stakewtd")
    sspr = sports_agg.get("spread_per_share_stakewtd")
    L += [
        f"- **Headline (SPORTS, n={n_sports} CLOSED fills, stake-weighted ¢/share):** "
        f"wallet counterfactual edge {fmt(swcf*100 if swcf is not None else None, '+.2f')}c, "
        f"minus pre-signal decay {fmt(sdec*100 if sdec is not None else None, '+.2f')}c, "
        f"minus spread/slippage {fmt(sspr*100 if sspr is not None else None, '+.2f')}c, "
        f"= our realized edge {fmt(sports_agg.get('our_edge_per_share_stakewtd')*100 if sports_agg.get('our_edge_per_share_stakewtd') is not None else None, '+.2f')}c/share.",
    ]
    if swcf is not None:
        if swcf > 0:
            verdict = ("the copied trades themselves were profitable -> the gap is pure "
                       "**MECHANISM** (we pay more than the wallets did)")
        else:
            verdict = ("**SELECTION kills the premise** (the copied trades lose even at the "
                       "wallets' own prices, before any copying cost); decay adds a "
                       "comparable-size cost on top, spread is negligible — see the component "
                       "magnitudes in the headline line above")
        L.append(f"- mean(payout − avg_trader_price) over SPORTS closed fills is "
                 f"**{fmt(swcf*100, '+.2f')}c/share ({'positive' if swcf > 0 else 'negative'})** -> {verdict}.")
    if boot:
        L.append(f"- Bootstrap 95% CI on the SPORTS mean our-edge/share (simple, unweighted; "
                 f"n={boot['n']}, seed {cfg['analysis']['copy_gap']['bootstrap']['seed']}, "
                 f"{cfg['analysis']['copy_gap']['bootstrap']['iterations']} iters): "
                 f"mean {fmt(boot['mean']*100, '+.2f')}c/share, CI "
                 f"[{fmt(boot['ci_lo']*100, '+.2f')}c, {fmt(boot['ci_hi']*100, '+.2f')}c].")
    L += [
        f"- Overall (all categories, n={overall_agg['n']}, stake-weighted): wallet CF "
        f"{fmt(wcf*100 if wcf is not None else None, '+.2f')}c, decay {fmt(dec*100 if dec is not None else None, '+.2f')}c, "
        f"spread {fmt(spr*100 if spr is not None else None, '+.2f')}c, our edge {fmt(our*100 if our is not None else None, '+.2f')}c/share.",
        f"- Reconciliation: sum(pnl_20) over all {recon['n']} CLOSED fills = "
        f"${recon['total']:+.2f}; decomposition components re-sum to the DB's own pnl_20 "
        f"over the {recon['decomposed_n']} decomposed fills — **{'MATCH' if recon['ok'] else 'MISMATCH'}**.",
        "",
        "## 1. Per-share decomposition (identity: our = wallet_cf − decay − spread, verified on every row)",
        "",
        "$ totals additive to realized PnL; ¢/share is the $-stake-weighted mean "
        "of the per-share component (bigger positions weight the average more; "
        "'simple' is the plain unweighted mean, the convention used elsewhere in "
        "this repo's dashboard/decay figures, shown for comparability).",
        "",
        "| slice | n | wallet CF $ | decay $ | spread $ | our $ | wallet CF c/sh (wtd/simple) | decay c/sh (wtd/simple) | spread c/sh (wtd/simple) | our c/sh (wtd/simple) |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    def agg_row(name: str, a: dict) -> str:
        def pair(key):
            w, s = a.get(key + "_stakewtd"), a.get(key + "_simple")
            return f"{fmt(w*100 if w is not None else None, '+.2f')} / {fmt(s*100 if s is not None else None, '+.2f')}"
        return (f"| {name} | {a['n']} | {fmt(a['wallet_cf_dollars'], '+.2f')} | {fmt(a['decay_dollars'], '+.2f')} | "
                f"{fmt(a['spread_dollars'], '+.2f')} | {fmt(a['our_dollars'], '+.2f')} | "
                f"{pair('wallet_cf_edge_per_share')} | {pair('decay_per_share')} | "
                f"{pair('spread_per_share')} | {pair('our_edge_per_share')} |")
    L.append(agg_row("ALL", overall_agg))
    for cat in sorted(by_cat_agg):
        L.append(agg_row(cat, by_cat_agg[cat]))
    wc_conc, dec_conc = sports_concentration.get("wallet_cf_dollars"), sports_concentration.get("decay_dollars")
    excl_agg = sports_concentration.get("excl_top_agg")
    if wc_conc and wc_conc["share_of_total"] is not None and wc_conc["share_of_total"] > 0.5 and excl_agg:
        excl_swcf = excl_agg["wallet_cf_edge_per_share_stakewtd"]
        L += [
            "",
            f"**$ column caveat (SPORTS):** a single fill (id={wc_conc['top_id']}, "
            f"entry_price=${wc_conc['top_entry_price']:.3f}) contributes "
            f"{wc_conc['share_of_total']:.0%} of the SPORTS wallet-CF $ total and "
            f"{fmt(dec_conc['share_of_total'], '.0%') if dec_conc else '-'} of the decay $ total. "
            "$ components scale with shares = stake/entry_price, so a very low "
            "entry_price inflates the implied share count and swamps the $ sum even "
            "though the per-share value is unremarkable. The stake-weighted c/share "
            "aggregate above is NOT affected by this (weighted by $ stake, not "
            "shares) — recomputed excluding this one fill "
            f"(n={excl_agg['n']}): wallet-CF {fmt(excl_swcf*100 if excl_swcf is not None else None, '+.2f')}c/share "
            f"vs {fmt(swcf*100 if swcf is not None else None, '+.2f')}c/share including it — "
            "materially unchanged. **Read the $ columns in this table as directional "
            "only; the c/share columns are the reliable read.**",
        ]
    L += [
        "",
        "Component share of the gap in cents/share terms (SPORTS, stake-weighted — "
        "the reliable metric per the caveat above, NOT the $ columns):",
        "",
    ]
    if n_sports and sdec is not None and sspr is not None:
        denom = abs(sdec) + abs(sspr) if (abs(sdec) + abs(sspr)) else 1.0
        L += [
            f"- wallet counterfactual: {fmt(swcf*100, '+.2f')}c/share",
            f"- minus decay: {fmt(sdec*100, '+.2f')}c/share ({abs(sdec)/denom:.0%} of |decay|+|spread|)",
            f"- minus spread/slippage: {fmt(sspr*100, '+.2f')}c/share ({abs(sspr)/denom:.0%} of |decay|+|spread|)",
            f"- = our realized edge: {fmt(sports_agg['our_edge_per_share_stakewtd']*100, '+.2f')}c/share "
            f"({fmt(sports_agg['our_dollars'], '+.2f')} total realized $ on these {n_sports} fills)",
        ]
    L += [
        "",
        "## 2. Selection effect vs cohort baseline (SPORTS)",
        "",
        f"- Cohort-B SPORTS wallets' overall entry edge (context, quoted not recomputed, "
        f"see config `analysis.copy_gap.sports_wallet_entry_edge_context`): "
        f"**{ctx_edge:+.3f} PnL/$ of stake**.",
        f"- Signal-subset wallet edge from avg_trader_price (this analysis, SPORTS, "
        f"stake-weighted c/share): {fmt(swcf*100 if swcf is not None else None, '+.2f')}c/share.",
        f"- Signal-subset wallet edge from the exact signal-forming trades (tx_hashes "
        f"-> trades cross-check, SPORTS, stake-weighted, {cross['n_trades_matched']} trades matched, "
        f"{cross['n_trades_missing']} missing): "
        f"{fmt(cross['per_share_edge_stakewtd']*100 if cross['per_share_edge_stakewtd'] is not None else None, '+.2f')}c/share "
        f"= {fmt(cross['per_dollar_edge_stakewtd'], '+.3f')} PnL/$ of stake (unit-matched to the +0.072 context number above).",
        "",
        "Units note: the +0.072 context figure and the per-dollar cross-check above "
        "are both PnL per dollar of stake; the c/share figures are price-unit edges "
        "per share and are not directly comparable to +0.072 without dividing by "
        "entry price — both are shown so the comparison is auditable either way.",
        "",
        "## 3. Favorite-longshot anatomy (SPORTS CLOSED fills, by entry_price bucket)",
        "",
        "| bucket | n | win% | avg win $ | avg loss $ | breakeven win% | total $ | our edge/share (wtd/simple, c) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for b in fl_table:
        if b["n"] == 0:
            L.append(f"| {b['bucket']} | 0 | - | - | - | - | - | - |")
            continue
        w, s = b["our_edge_per_share_stakewtd"], b["our_edge_per_share_simple"]
        L.append(f"| {b['bucket']} | {b['n']} | {fmt(b['win_rate'], '.0%')} | "
                 f"{fmt(b['avg_win'], '+.2f')} | {fmt(b['avg_loss'], '+.2f')} | "
                 f"{fmt(b['breakeven_win_rate'], '.0%')} | "
                 f"{fmt(b['total_pnl'], '+.2f')} | "
                 f"{fmt(w*100 if w is not None else None, '+.2f')} / {fmt(s*100 if s is not None else None, '+.2f')} |")
    hi_buckets = [b for b in fl_table if b["n"] and float(b["bucket"].split("-")[0]) >= 0.6]
    hi_loss = sum(b["total_pnl"] for b in hi_buckets if b["total_pnl"] < 0)
    all_loss = sum(b["total_pnl"] for b in fl_table if b["total_pnl"] and b["total_pnl"] < 0)
    L += [
        "",
        f"Losses in the >=0.6 (favorite) buckets: ${hi_loss:+.2f} of ${all_loss:+.2f} total "
        f"realized losses across all buckets "
        f"({(hi_loss/all_loss):.0%} of total losses concentrate at favorite prices)." if all_loss else "",
        "**Every loss costs exactly the full stake** ($50, or $20 for older rows) "
        "regardless of entry price — a binary market resolving to 0 wipes out "
        "(payout-entry)*shares = 0*shares - stake = -stake exactly, so avg loss $ "
        "is flat across buckets by construction. The real favorite/longshot "
        "asymmetry is on the WIN side: avg win shrinks in the two highest buckets "
        f"({fl_table[-2]['bucket']}: {fmt(fl_table[-2]['avg_win'], '+.2f')}, "
        f"{fl_table[-1]['bucket']}: {fmt(fl_table[-1]['avg_win'], '+.2f')}) since a "
        "favorite payout of 1.0 is only a small markup over an entry already near "
        "1.0, which raises the win rate needed just to break even (breakeven win% "
        f"column). The {fl_table[-1]['bucket']} bucket wins "
        f"{fmt(fl_table[-1]['win_rate'], '.0%')} of the time but needed "
        f"{fmt(fl_table[-1]['breakeven_win_rate'], '.0%')} to break even, so it "
        f"still lost ${abs(fl_table[-1]['total_pnl']):.2f} net despite winning most bets.",
        "",
        "## 4. Exit-policy counterfactual — BOUNDED ESTIMATE, not a measurement",
        "",
        "**Caveat (applies to every number in this section):** the `trades` feed is "
        "TAKER-ONLY and the median watchlist wallet does ~84% of its volume as "
        "invisible maker fills, so observed exits are ~16% of real exits. Fills "
        "below where no exit was ever observed are scored as hold (same as "
        "realized) by construction — this systematically understates how often "
        "and how early a copy-exit strategy would actually have triggered. "
        "Treat this as a **lower bound on exit-following opportunity**, not a "
        "measurement of it.",
        "",
    ]
    n_triggered = sum(1 for e in exit_cf if e["triggered_before_resolution"])
    hold_total = sum(e["hold_pnl"] for e in exit_cf)
    copyexit_total = sum(e["copy_exit_pnl"] for e in exit_cf)
    L += [
        f"- {n_triggered}/{len(exit_cf)} CLOSED fills had an observed copy-exit trigger "
        f"(>= `backtest.copy_exit_wallet_fraction`={cfg['backtest']['copy_exit_wallet_fraction']} "
        f"of signal wallets selling >= `backtest.copy_exit_sold_fraction`="
        f"{cfg['backtest']['copy_exit_sold_fraction']} of their signal-time position) "
        f"strictly before the actual resolution close.",
        f"- Realized hold_to_resolution total: ${hold_total:+.2f}.",
        f"- Copy-exit counterfactual total (same fills, exit priced at the signal "
        f"wallets' own stake-weighted sell price where triggered, else = hold): "
        f"${copyexit_total:+.2f}.",
        f"- Difference: ${copyexit_total - hold_total:+.2f} "
        f"({'copy-exits would have helped' if copyexit_total > hold_total else 'copy-exits would have hurt or been neutral'}, "
        f"on the ~16%-visible sample that triggered at all).",
        "",
    ]
    if n_triggered == 0:
        L.append(
            f"No per-fill table shown: 0/{len(exit_cf)} fills ever had >= "
            f"{cfg['backtest']['copy_exit_wallet_fraction']:.0%} of signal wallets' "
            "visible SELLs cross the sold-fraction threshold before resolution — "
            "every row is identical (copy-exit PnL = hold PnL, diff $0.00). Full "
            "per-fill detail (including copy_exit_ts for fills where a partial "
            "sell was observed but never crossed threshold) is in "
            "`reports/copy_gap_fills.csv`.")
    else:
        L += ["| id | condition | category | triggered | hold PnL $ | copy-exit PnL $ | diff $ |",
              "|---|---|---|---|---|---|---|"]
        for e in sorted(exit_cf, key=lambda e: -abs(e["copy_exit_pnl"] - e["hold_pnl"])):
            L.append(f"| {e['id']} | {e['condition_id'][:12]}… | {e['category']} | "
                     f"{'yes' if e['triggered_before_resolution'] else 'no'} | "
                     f"{e['hold_pnl']:+.2f} | {e['copy_exit_pnl']:+.2f} | "
                     f"{e['copy_exit_pnl'] - e['hold_pnl']:+.2f} |")
    L += [
        "",
        "## 5. SKIPPED / STALE counterfactual",
        "",
        "Hypothetical PnL at the signal's stake, priced at midpoint_at_signal "
        "(fall back to entry_price; skipped and counted where neither exists), "
        "against markets.outcome_prices where the market has since resolved.",
        "",
    ]
    for name, cf in (("SKIPPED (book too thin/gone)", skipped_cf), ("STALE (detected >30min late)", stale_cf)):
        L += [
            f"### {name}: {cf['total']} rows",
            f"- computable (has a price proxy AND a resolved market on file): {cf['n_computed']}",
            f"- has price proxy but market not yet resolved in our DB: {cf['n_not_resolved']}",
            f"- no price proxy recorded (book/market fetch never happened or failed at signal time): {cf['n_no_price']}",
            f"- neither price proxy nor resolved market: {cf['n_neither']}",
            f"- hypothetical PnL sum over computable rows: ${cf['hypothetical_pnl_sum']:+.2f}",
            "",
        ]
    total_hyp = skipped_cf["hypothetical_pnl_sum"] + stale_cf["hypothetical_pnl_sum"]
    total_computed = skipped_cf["n_computed"] + stale_cf["n_computed"]
    if total_computed:
        verdict = "COST money (forgone profit)" if total_hyp > 0 else "SAVED money (avoided a loss)"
        L.append(f"**Combined, over the {total_computed} computable rows out of "
                 f"{skipped_cf['total'] + stale_cf['total']} SKIPPED+STALE: the filters "
                 f"{verdict} of ${abs(total_hyp):.2f}.** This is a small, likely "
                 f"non-representative slice — most SKIPPED/STALE rows have no price "
                 f"proxy on file (paper.py never recorded one when the book/market "
                 f"fetch itself failed), so this verdict should not be generalized to "
                 f"the full 30 SKIPPED + 11 STALE population.")
    else:
        L.append("**No SKIPPED or STALE row has both a price proxy and a resolved "
                 "market on file — the counterfactual is not computable from data "
                 "already in the DB for this run.** Every SKIPPED row where the "
                 "market has since resolved (24/30) never got a book/midpoint fetch "
                 "recorded at signal time (the fetch itself failed, per paper.py's "
                 "`open_position`); the 2/30 SKIPPED rows with a recorded midpoint "
                 "have not resolved in the local `markets` cache yet. All 11 STALE "
                 "rows skip market/book lookups entirely by design (late-detected "
                 "signals are recorded and never entered), so none have a price proxy.")
    L += [
        "",
        "## Standing caveats (apply to every number above)",
        "",
        "- **Taker-only feed**: `trades` only sees taker fills; the median watchlist "
        "wallet does ~84% of its volume as invisible maker fills. `avg_trader_price` "
        "and the tx_hashes cross-check in §2 are computed over VISIBLE taker BUYs "
        "only — if maker buys are priced differently, the true wallet counterfactual "
        "edge could differ from what's shown here. Section 4's exit counterfactual "
        "is a stated lower bound for the same reason (repeated there).",
        "- **Survivorship bias**: cohort B was selected on its own trailing PnL/vol "
        "window; the +0.072 context edge and all per-wallet figures inherit that bias "
        "(see `reports/wallet_quality_analysis.md` §0).",
        f"- **Small n**: {n_sports} SPORTS CLOSED fills. The bootstrap CI above "
        "quantifies this for the headline mean; bucket-level and per-category splits "
        "in §1/§3 have even smaller n and should be read as directional, not precise.",
        "- avg_trader_price and the §2 cross-check price only the signal-forming "
        "trades that were visible taker buys; wallets with a mostly-maker style are "
        "underrepresented in whatever edge they contributed to a signal.",
        "",
    ]
    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")


def write_csv(rows: list[dict], exit_cf: list[dict], buckets: list[float]) -> None:
    exit_by_id = {e["id"]: e for e in exit_cf}
    fields = ["id", "condition_id", "outcome_index", "category", "signal_time", "exit_time",
              "position_usd", "entry_price", "midpoint_at_signal", "avg_trader_price", "payout",
              "shares", "wallet_cf_edge_per_share", "decay_per_share", "spread_per_share",
              "our_edge_per_share", "identity_diff", "wallet_cf_dollars", "decay_dollars",
              "spread_dollars", "our_dollars", "pnl_20_actual", "price_bucket",
              "copy_exit_ts", "copy_exit_price", "copy_exit_pnl", "copy_exit_triggered"]
    with open(FILLS_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            out = dict(r)
            out["price_bucket"] = bucket_of(r["entry_price"], buckets)
            e = exit_by_id.get(r["id"], {})
            out["copy_exit_ts"] = e.get("copy_exit_ts")
            out["copy_exit_price"] = e.get("copy_exit_price")
            out["copy_exit_pnl"] = e.get("copy_exit_pnl")
            out["copy_exit_triggered"] = e.get("triggered_before_resolution")
            w.writerow(out)


# ---------- main ----------

def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cfg = load_config()
    acfg = cfg["analysis"]["copy_gap"]
    bcfg = cfg["backtest"]
    conn = ro_connect()

    fills = load_closed_fills(conn)
    reconcile_total = sum(f["pnl_20"] for f in fills)
    rows = decompose(fills)
    log.info("decomposed %d/%d CLOSED fills (excluded non-resolution/missing-field rows)",
             len(rows), len(fills))

    # internal identity: decomposition components must re-sum to the DB's own
    # pnl_20 over the decomposed fills (no frozen snapshot constants — rerunnable)
    decomposed_total = sum(r["our_dollars"] for r in rows)
    decomposed_pnl = sum(r["pnl_20_actual"] for r in rows)
    recon = {"n": len(fills), "total": reconcile_total, "decomposed_n": len(rows),
             "ok": abs(decomposed_total - decomposed_pnl) <= 0.005}
    if not recon["ok"]:
        raise AssertionError(
            f"reconciliation failed: sum(our_dollars)={decomposed_total:.4f} vs "
            f"sum(pnl_20)={decomposed_pnl:.4f} over {len(rows)} decomposed fills")
    log.info("reconciliation OK: sum(pnl_20) over %d CLOSED = %.2f (%d decomposed)",
             recon["n"], recon["total"], recon["decomposed_n"])

    overall_agg = aggregate_decomposition(rows)
    by_cat_agg = {}
    for cat in sorted({r["category"] for r in rows}):
        by_cat_agg[cat] = aggregate_decomposition([r for r in rows if r["category"] == cat])
    sports_rows = [r for r in rows if r["category"] == "SPORTS"]
    log.info("sports closed fills in decomposition: %d", len(sports_rows))

    cross = signal_trade_cross_check(conn, sports_rows)
    log.info("tx_hashes cross-check: %d trades matched, %d missing", cross["n_trades_matched"], cross["n_trades_missing"])

    fl_table = favorite_longshot(sports_rows, acfg["price_buckets"])

    exit_cf = exit_counterfactual(conn, rows, bcfg["copy_exit_wallet_fraction"], bcfg["copy_exit_sold_fraction"])
    log.info("exit counterfactual computed for %d fills", len(exit_cf))

    skipped = load_filtered(conn, "SKIPPED")
    stale = load_filtered(conn, "STALE")
    skipped_cf = filtered_counterfactual(skipped)
    stale_cf = filtered_counterfactual(stale)
    log.info("SKIPPED counterfactual: %d/%d computable; STALE: %d/%d computable",
             skipped_cf["n_computed"], skipped_cf["total"], stale_cf["n_computed"], stale_cf["total"])

    sports_our_edges = [r["our_edge_per_share"] for r in sports_rows]
    boot = bootstrap_mean_ci(sports_our_edges, acfg["bootstrap"])

    sports_concentration = {
        "wallet_cf_dollars": dollar_concentration(sports_rows, "wallet_cf_dollars"),
        "decay_dollars": dollar_concentration(sports_rows, "decay_dollars"),
    }
    wc = sports_concentration["wallet_cf_dollars"]
    if wc and wc["share_of_total"] is not None and wc["share_of_total"] > 0.5:
        excl = [r for r in sports_rows if r["id"] != wc["top_id"]]
        sports_concentration["excl_top_agg"] = aggregate_decomposition(excl)
        log.info("SPORTS wallet-CF $ dominated by fill id=%s (%.0f%% of total), "
                 "c/share aggregate recomputed excluding it for the report",
                 wc["top_id"], wc["share_of_total"] * 100)

    write_report(cfg, rows, sports_rows, by_cat_agg, overall_agg, cross, recon,
                fl_table, exit_cf, skipped_cf, stale_cf, boot, sports_concentration)
    write_csv(rows, exit_cf, acfg["price_buckets"])
    log.info("wrote %s and %s", REPORT_MD, FILLS_CSV)


if __name__ == "__main__":
    main()
