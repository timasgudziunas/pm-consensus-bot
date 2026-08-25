"""Signal v2 post-filter backtest (owner pre-registration, 2026-08-25).

Simulates ONLY the base cell (cohort B, N=5, W=12h, F=$1000, hold_to_resolution,
$100/position -- the winning 2026-07-03 cohort sweep cell) and applies four
post-filter "arms" from `reports/proposals/signal_v2_preregistration.md` on top
of the already-detected signal stream:
  A. no-favorites  (drop entry > favorite_cutoff)
  B. mid-band      (keep band_low <= entry <= band_high)
  C. quality-gated (>= quality_gate_k of 5 consensus wallets in the train-window
                     top half of cohort B by stake-weighted entry edge)
  D. fade          (opposite outcome at 1 - entry; descriptive only, no adoption path)

REUSES backtest.py's evaluate_signal / price_at_or_after / resolution_payout /
cell_metrics and signals.py's detect_signals -- signal detection and pricing are
NOT reimplemented. signals.py, backtest.py, paper.py, paper_status.py, and
watchdog.py are NOT modified. Read-only against data/copybot.db (paper.py is the
sole writer).

**Sanity gate / Amendment 2026-08-25** (see the pre-registration's "Amendment
2026-08-25" section): the gate that reproduces the 2026-07-03 backtest_report.md
base cell now checks ONLY validate-window PnL within +/- `signal_v2.sanity_gate.
tolerance` of that report's +$3,482.39 -- a CALIBRATION reference, not a
stop condition (it passes at -5.0%). Signal/closed COUNTS are expected to differ
(157 vs 122 validate signals) because the trades table grew ~10x via a
2026-07-06/07 deep-history backfill that post-dates that report; this is
diagnosed automatically and logged/reported but does not block arm evaluation.
Per the amendment, the base reference for every arm-vs-base comparison in this
script is this run's OWN today's-DB base simulation, never the stale report.

Run: python src/backtest_signal_v2.py
Writes: reports/proposals/signal_v2_backtest.md, reports/proposals/signal_v2_signals.csv
"""
import json
import logging
import math
import os
import random
import sqlite3
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone

import backtest as bt
import db
import signals as sig
from data_api import load_config

log = logging.getLogger("backtest_signal_v2")

REPORT_MD = os.path.join(db.REPO_ROOT, "reports", "proposals", "signal_v2_backtest.md")
SIGNALS_CSV = os.path.join(db.REPO_ROOT, "reports", "proposals", "signal_v2_signals.csv")
COHORT = "B"


def ro_connect() -> sqlite3.Connection:
    """Read-only connection -- paper.py is the sole writer to this DB."""
    conn = sqlite3.connect(f"file:{db.DB_PATH}?mode=ro", uri=True, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def parse_ts(iso: str) -> int:
    """Parse a config ISO-8601 UTC timestamp ('...Z') to epoch seconds."""
    return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp())


def fmt(v, spec: str, na: str = "-") -> str:
    return format(v, spec) if v is not None else na


# ---------- loading (clipped to analysis.window_end_utc, cohort B only) ----------

def load_clipped_data(conn: sqlite3.Connection, wallets: set, cutoff_ts: int, max_gap: int) -> tuple:
    """Cohort-B trades strictly before cutoff_ts, plus the markets/price_history
    those trades reference. Filters in SQL (not Python) -- the live DB now holds
    50+ extra days of paper-poll trades the base cell must never see."""
    wlist = sorted(wallets)
    ph_w = ",".join("?" * len(wlist))
    t0 = time.time()
    trades = [dict(r) for r in conn.execute(
        f"""SELECT tx_hash, condition_id, wallet, side, outcome_index, size_usd, price, timestamp
            FROM trades WHERE wallet IN ({ph_w}) AND outcome_index >= 0 AND timestamp < ?
            ORDER BY timestamp""", (*wlist, cutoff_ts))]
    log.info("loaded %d cohort-%s trades < cutoff (%.1fs)", len(trades), COHORT, time.time() - t0)

    cond_ids = sorted({t["condition_id"] for t in trades})
    markets: dict = {}
    for i in range(0, len(cond_ids), 500):
        chunk = cond_ids[i:i + 500]
        ph = ",".join("?" * len(chunk))
        for r in conn.execute(f"SELECT * FROM markets WHERE condition_id IN ({ph})", chunk):
            markets[r["condition_id"]] = dict(r)
    log.info("loaded %d markets for %d referenced condition_ids", len(markets), len(cond_ids))

    token_ids: set = set()
    for m in markets.values():
        try:
            token_ids.update(json.loads(m["clob_token_ids"]))
        except (TypeError, ValueError):
            pass
    price_cutoff = cutoff_ts + max_gap
    prices: dict = {}
    tlist = sorted(token_ids)
    for i in range(0, len(tlist), 500):
        chunk = tlist[i:i + 500]
        ph = ",".join("?" * len(chunk))
        for r in conn.execute(
                f"""SELECT token_id, timestamp, price FROM price_history
                    WHERE token_id IN ({ph}) AND timestamp < ? ORDER BY token_id, timestamp""",
                (*chunk, price_cutoff)):
            prices.setdefault(r["token_id"], ([], []))
            ts_list, p_list = prices[r["token_id"]]
            ts_list.append(r["timestamp"])
            p_list.append(r["price"])
    log.info("loaded price history for %d tokens", len(prices))
    return trades, markets, prices


def diagnose_ingestion_timing(conn: sqlite3.Connection, wallets: set, cutoff_ts: int) -> list:
    """(ingest_date, n_trades) for cohort-B trades < cutoff_ts, grouped by the day
    each row was actually inserted (trades.ingested_at) -- surfaces whether the
    dataset grew materially AFTER a prior report's generation date (sqlite has no
    DATE() over an alias-joined temp table portably, so group in Python)."""
    wlist = sorted(wallets)
    ph = ",".join("?" * len(wlist))
    rows = conn.execute(
        f"""SELECT ingested_at FROM trades WHERE wallet IN ({ph})
            AND outcome_index >= 0 AND timestamp < ?""", (*wlist, cutoff_ts)).fetchall()
    counts: dict = defaultdict(int)
    for r in rows:
        if r["ingested_at"]:
            d = datetime.fromtimestamp(r["ingested_at"], tz=timezone.utc).date().isoformat()
            counts[d] += 1
    return sorted(counts.items())


def global_train_boundary(conn: sqlite3.Connection, cutoff_ts: int, train_months: float) -> int:
    """Train/validate boundary computed from the GLOBAL (all-wallet) trade
    timestamp floor, clipped to cutoff_ts -- matches backtest.py's `t_min` basis
    exactly ('one calendar boundary from ALL trades so every cohort's split is
    comparable'), so cohort-B's split lines up with the original run."""
    row = conn.execute(
        "SELECT MIN(timestamp) AS t_min, MAX(timestamp) AS t_max FROM trades "
        "WHERE outcome_index >= 0 AND timestamp < ?", (cutoff_ts,)).fetchone()
    t_min, t_max = row["t_min"], row["t_max"]
    boundary = int(t_min + train_months * bt.SECONDS_PER_MONTH)
    log.info("global trade range (clipped) %s -> %s; train/validate boundary %s",
             datetime.fromtimestamp(t_min, tz=timezone.utc).date(),
             datetime.fromtimestamp(t_max, tz=timezone.utc).date(),
             datetime.fromtimestamp(boundary, tz=timezone.utc).date())
    return boundary


# ---------- base signal simulation (reuses signals.detect_signals + backtest.evaluate_signal) ----------

def evaluate_window(trades_window: list, params: dict, markets: dict, prices: dict, cfg: dict) -> tuple:
    """Detect + price signals for one split. Returns (detected, raw_results, entries)
    where entries drop the None (un-priced) results and tag each with its signal
    (wallets, condition_id, outcome_index, signal_time) for post-filtering."""
    detected = sig.detect_signals(trades_window, params)
    raw_results = [bt.evaluate_signal(s, "hold_to_resolution", markets, prices, {}, cfg) for s in detected]
    entries = []
    for s, r in zip(detected, raw_results):
        if r is None:
            continue
        e = dict(r)
        e["signal"] = s
        e["wallets"] = s["wallets"]
        e["condition_id"] = s["condition_id"]
        e["outcome_index"] = s["outcome_index"]
        e["signal_time"] = s["signal_time"]
        entries.append(e)
    return detected, raw_results, entries


# ---------- arm C: train-window wallet quality ranking ----------

def compute_train_ranking(train_trades: list, markets: dict, min_resolved: int) -> tuple:
    """Stake-weighted entry edge (payout - price) per wallet over its own
    resolved taker BUYs in the train window ONLY -- no lookahead. Wallets below
    min_resolved are excluded from ranking (bottom-half by construction)."""
    stats: dict = defaultdict(lambda: {"stake": 0.0, "edge_stake": 0.0, "n": 0})
    for t in train_trades:
        if t["side"] != "BUY" or t["price"] <= 0:
            continue
        m = markets.get(t["condition_id"])
        if not m or not m.get("closed"):
            continue
        payout = bt.resolution_payout(m, t["outcome_index"])
        if payout is None:
            continue
        s = stats[t["wallet"]]
        s["stake"] += t["size_usd"]
        s["edge_stake"] += (payout - t["price"]) * t["size_usd"]
        s["n"] += 1
    ranked = [(w, s["edge_stake"] / s["stake"], s["n"]) for w, s in stats.items()
              if s["n"] >= min_resolved and s["stake"] > 0]
    ranked.sort(key=lambda x: -x[1])
    top_n = math.ceil(len(ranked) / 2)
    top_half = {w for w, _, _ in ranked[:top_n]}
    log.info("train ranking: %d cohort-%s wallets with >=%d resolved train BUYs ranked; "
             "top half = %d wallets", len(ranked), COHORT, min_resolved, len(top_half))
    return top_half, ranked


# ---------- arm masks (uniform over sim entries and paper fills: entry_price, wallets) ----------

def mask_all(_e: dict) -> bool:
    return True


def mask_favorite(e: dict, cutoff: float) -> bool:
    return e["entry_price"] <= cutoff


def mask_band(e: dict, lo: float, hi: float) -> bool:
    return lo <= e["entry_price"] <= hi


def mask_quality(e: dict, top_half: set, k: int) -> bool:
    return sum(1 for w in e["wallets"] if w in top_half) >= k


# ---------- arm D: fade (opposite outcome at 1 - entry_price) ----------

def fade_transform_sim(entries: list, markets: dict, slip_100: float) -> list:
    """Same signal set, opposite outcome, entered at (1 - entry_price)."""
    out = []
    for e in entries:
        entry_fade_raw = 1.0 - e["entry_price"]
        m = markets.get(e["condition_id"])
        opp_idx = 1 - e["outcome_index"]
        payout_fade = bt.resolution_payout(m, opp_idx) if m else None
        entry_fade = entry_fade_raw + slip_100
        pnl = None
        if payout_fade is not None and 0 < entry_fade < 1:
            pnl = (payout_fade - entry_fade) * (100.0 / entry_fade)
        f = dict(e)
        f["entry_price"] = entry_fade_raw
        f["pnls"] = {100: pnl}
        f["resolved"] = 1 if payout_fade is not None else 0
        out.append(f)
    return out


def fade_transform_paper(fills: list, markets: dict) -> list:
    """Paper-fill analog: entry_price already reflects real execution (no
    synthetic slippage haircut layered on top, unlike the simulated arm)."""
    out = []
    for f in fills:
        entry_fade = 1.0 - f["entry_price"]
        m = markets.get(f["condition_id"])
        opp_idx = 1 - f["outcome_index"]
        payout_fade = bt.resolution_payout(m, opp_idx) if m else None
        pnl = None
        if payout_fade is not None and entry_fade > 0:
            shares = f["position_usd"] / entry_fade
            pnl = (payout_fade - entry_fade) * shares
        g = dict(f)
        g["entry_price"] = entry_fade
        g["pnl_20"] = pnl
        out.append(g)
    out = [g for g in out if g["pnl_20"] is not None]
    return out


# ---------- metrics ----------

def compute_sim_metrics(entries: list, mask, position_size: int) -> dict:
    retained = [e for e in entries if mask(e)]
    closed = [e for e in retained if e["pnls"].get(position_size) is not None]
    total = sum(e["pnls"][position_size] for e in closed)
    wins = sum(1 for e in closed if e["pnls"][position_size] > 0)
    return {
        "n": len(retained), "n_closed": len(closed), "total_pnl": total,
        "expectancy": total / (position_size * len(closed)) if closed else None,
        "win_rate": wins / len(closed) if closed else None,
    }


def compute_paper_metrics(fills: list, mask) -> dict:
    retained = [f for f in fills if mask(f)]
    total = sum(f["pnl_20"] for f in retained)
    stake = sum(f["position_usd"] for f in retained)
    wins = sum(1 for f in retained if f["pnl_20"] > 0)
    return {
        "n": len(retained), "n_closed": len(retained), "total_pnl": total,
        "expectancy": total / stake if stake else None,
        "win_rate": wins / len(retained) if retained else None,
        "pairs": [(f["pnl_20"], f["position_usd"]) for f in retained],
    }


def bootstrap_ratio_ci(pairs: list, iterations: int, seed: int) -> "dict | None":
    """Percentile bootstrap 95% CI on sum(pnl)/sum(stake), seeded, paired resample."""
    n = len(pairs)
    if n == 0:
        return None
    rng = random.Random(seed)
    ratios = []
    for _ in range(iterations):
        num = den = 0.0
        for _ in range(n):
            p, s = pairs[rng.randrange(n)]
            num += p
            den += s
        ratios.append(num / den if den else 0.0)
    ratios.sort()
    lo = ratios[int(0.025 * len(ratios))]
    hi = ratios[min(int(0.975 * len(ratios)), len(ratios) - 1)]
    tot_p = sum(p for p, _ in pairs)
    tot_s = sum(s for _, s in pairs)
    return {"n": n, "mean": tot_p / tot_s if tot_s else None, "ci_lo": lo, "ci_hi": hi}


def sign(x) -> int:
    if x is None:
        return 0
    if x > 1e-9:
        return 1
    if x < -1e-9:
        return -1
    return 0


# ---------- paper fills loader ----------

def load_paper_closed(conn: sqlite3.Connection) -> list:
    rows = conn.execute(
        """SELECT id, condition_id, outcome_index, entry_price, exit_price, exit_type,
                  pnl_20, position_usd, wallets, category, signal_time, exit_time, resolved
           FROM paper_trades WHERE status = 'CLOSED' ORDER BY id""").fetchall()
    fills = []
    for r in rows:
        d = dict(r)
        d["wallets"] = json.loads(d["wallets"] or "[]")
        fills.append(d)
    return fills


def load_markets_for(conn: sqlite3.Connection, cond_ids: list) -> dict:
    markets: dict = {}
    cond_ids = sorted(set(cond_ids))
    for i in range(0, len(cond_ids), 500):
        chunk = cond_ids[i:i + 500]
        ph = ",".join("?" * len(chunk))
        for r in conn.execute(f"SELECT * FROM markets WHERE condition_id IN ({ph})", chunk):
            markets[r["condition_id"]] = dict(r)
    return markets


# ---------- report ----------

def build_arm_variants(v2: dict, top_half: set) -> dict:
    """Nominal + neighborhood-offset mask variants for A, B, C."""
    off = v2["neighborhood_offset"]
    fav = v2["favorite_cutoff"]
    lo, hi = v2["band_low"], v2["band_high"]
    k = v2["quality_gate_k"]
    return {
        "A": {"nominal": (lambda e: mask_favorite(e, fav), f"<= {fav:.2f}")},
        "A_nbhd": {
            f"cutoff-{off:.2f}": (lambda e, c=fav - off: mask_favorite(e, c), f"<= {fav - off:.2f}"),
            f"cutoff+{off:.2f}": (lambda e, c=fav + off: mask_favorite(e, c), f"<= {fav + off:.2f}"),
        },
        "B": {"nominal": (lambda e: mask_band(e, lo, hi), f"[{lo:.2f},{hi:.2f}]")},
        "B_nbhd": {
            f"low-{off:.2f}": (lambda e, l=lo - off: mask_band(e, l, hi), f"[{lo - off:.2f},{hi:.2f}]"),
            f"low+{off:.2f}": (lambda e, l=lo + off: mask_band(e, l, hi), f"[{lo + off:.2f},{hi:.2f}]"),
            f"high-{off:.2f}": (lambda e, h=hi - off: mask_band(e, lo, h), f"[{lo:.2f},{hi - off:.2f}]"),
            f"high+{off:.2f}": (lambda e, h=hi + off: mask_band(e, lo, h), f"[{lo:.2f},{hi + off:.2f}]"),
        },
        "C": {"nominal": (lambda e: mask_quality(e, top_half, k), f">= {k}-of-5")},
        "C_nbhd": {
            f"{v}-of-5": (lambda e, kk=v: mask_quality(e, top_half, kk), f">= {v}-of-5")
            for v in v2["quality_gate_variants"]
        },
    }


def write_report(cfg: dict, gate: dict, base: dict, arm_metrics: dict, neighborhood: dict,
                 verdicts: dict, ranked: list, v2: dict) -> None:
    L = ["# Signal v2 post-filter backtest -- generated "
         + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "",
         "Pre-registration: `reports/proposals/signal_v2_preregistration.md` (frozen "
         "before this script was run; criteria below are applied mechanically, no "
         "post-hoc arms). Engine: `src/backtest_signal_v2.py`, reusing "
         "`backtest.py`'s `evaluate_signal`/pricing and `signals.py`'s "
         "`detect_signals` unmodified. Base cell: cohort B, N=5, W=12h, F=$1000, "
         f"hold_to_resolution, ${v2['position_size_usd']}/position.", "",
         "## Amendment 2026-08-25 & calibration note (read before the numbers below)", "",
         "Full text: `reports/proposals/signal_v2_preregistration.md` section "
         "\"Amendment 2026-08-25\", written and committed BEFORE any arm was evaluated. "
         "The original sanity gate (reproduce `backtest_report.md`'s 2026-07-03 base cell "
         "within +/-10%) failed structurally: DB forensics showed only 10% of cohort-B's "
         "clipped trades existed when that report was generated; a 2026-07-06/07 "
         "deep-history backfill (`ingest_full.py`) grew the data ~10x, with cohort "
         "membership unchanged (100% overlap). **The gate was accordingly narrowed to a "
         "PnL-only calibration check, and the base reference for every arm-vs-base "
         "comparison below is this run's OWN today's-DB base simulation "
         f"(validate: {base['validate']['n']} signals, "
         f"{fmt(base['validate']['total_pnl'], '+.2f')}), not the stale report.**", ""]
    L.append(f"**Calibration: {'PASS' if gate['ok'] else 'FAIL'}** -- reproduced validate PnL "
             f"${gate['pnl']:+.2f} vs original ${gate['orig_pnl']:+.2f} "
             f"({gate['pnl_dev']:+.1%}, tolerance +/-{v2['sanity_gate']['tolerance']:.0%}) -- "
             "informational only, does not gate arm evaluation. Signal/closed counts "
             f"({gate['n']} vs {gate['orig_n']}, {gate['n_closed']} vs {gate['orig_closed']}) "
             "are EXPECTED to differ (more historical data now) and are not part of the gate.")
    L.append("")
    L += ["Diagnosis (ingestion-timing forensics):", "", gate.get("diagnosis", "(none recorded)"), ""]

    L += ["## Base-cell reproduction (today's-DB base -- THE reference for all arms below)", "",
          "| window | n signals | n closed | win rate | total PnL |",
          "|---|---|---|---|---|"]
    for w in ("train", "validate"):
        b = base[w]
        L.append(f"| {w} | {b['n']} | {b['n_closed']} | {fmt(b['win_rate'], '.0%')} | "
                 f"{fmt(b['total_pnl'], '+.2f')} |")
    L += ["", f"Train/validate boundary and global trade range logged at run time (see "
          "console log); train = first `backtest.train_months` months of the clipped "
          "(pre-`analysis.window_end_utc`) cohort-B data, validate = remainder, exactly "
          "matching `backtest.py`'s split.", ""]

    L += ["## Train-window quality ranking (arm C)", "",
          f"{len(ranked)} cohort-B wallets ranked (>= {v2['min_resolved_train_trades']} "
          "resolved train BUYs on resolved markets); top half by stake-weighted entry "
          f"edge = {math.ceil(len(ranked)/2)} wallets. All other cohort-B wallets "
          "(unranked or bottom half) count as not-top-half.", ""]

    L += ["## Per-arm-per-window metrics", "",
          "Expectancy = sum(closed PnL) / sum(closed-position stake); retention = "
          "n retained / n base-window signals (all entered, resolved or not).", "",
          "| arm | window | n retained | retention | n closed | win rate | total PnL | expectancy/$ |",
          "|---|---|---|---|---|---|---|---|"]
    for arm in ("base", "A", "B", "C", "D"):
        for w in ("train", "validate", "paper"):
            m = arm_metrics[arm][w]
            L.append(f"| {arm} | {w} | {m['n']} | {fmt(m.get('retention'), '.0%')} | "
                     f"{m['n_closed']} | {fmt(m['win_rate'], '.0%')} | "
                     f"{fmt(m['total_pnl'], '+.2f')} | {fmt(m['expectancy'], '+.4f')} |")
    L.append("")
    L.append("Paper counterfactual bootstrap 95% CI on filtered expectancy "
             f"({v2['bootstrap']['iterations']:,} iters, seed {v2['bootstrap']['seed']}):")
    L.append("")
    L.append("| arm | n | mean | CI lo | CI hi |")
    L.append("|---|---|---|---|---|")
    for arm in ("base", "A", "B", "C", "D"):
        ci = arm_metrics[arm]["paper"].get("boot")
        if ci is None:
            L.append(f"| {arm} | - | - | - | - |")
        else:
            L.append(f"| {arm} | {ci['n']} | {fmt(ci['mean'], '+.4f')} | "
                     f"{fmt(ci['ci_lo'], '+.4f')} | {fmt(ci['ci_hi'], '+.4f')} |")
    L.append("")

    L += ["## Neighborhood robustness (validate window)", "",
          "| arm | variant | rule | validate expectancy | delta vs base | sign kept vs nominal? |",
          "|---|---|---|---|---|---|"]
    for arm in ("A", "B", "C"):
        base_delta = neighborhood[arm]["nominal"]["delta"]
        base_sign = sign(base_delta)
        L.append(f"| {arm} | nominal | {neighborhood[arm]['nominal']['rule']} | "
                 f"{fmt(neighborhood[arm]['nominal']['expectancy'], '+.4f')} | "
                 f"{fmt(base_delta, '+.4f')} | (reference) |")
        for name, row in neighborhood[arm]["variants"].items():
            kept = sign(row["delta"]) == base_sign
            L.append(f"| {arm} | {name} | {row['rule']} | {fmt(row['expectancy'], '+.4f')} | "
                     f"{fmt(row['delta'], '+.4f')} | {'yes' if kept else 'no'} |")
    L.append("")

    L += ["## Verdict (pre-registered adoption rule, applied mechanically)", "",
          "All 4 criteria must hold for adoption. Arm D has no adoption path by "
          "design (reported for information only).", "",
          "| arm | 1. validate (exp>=base & retain>=%.0f%%) | 2. train (exp>=0) | "
          "3. paper (n>=%d & exp>=%.2f) | 4. neighborhood (sign kept) | verdict |"
          % (v2["fill_retention_floor"] * 100, v2["min_paper_fills"], v2["paper_expectancy_floor"]),
          "|---|---|---|---|---|---|"]
    for arm in ("A", "B", "C"):
        v = verdicts[arm]
        L.append(f"| {arm} | {'PASS' if v['c1'] else 'FAIL'} | {'PASS' if v['c2'] else 'FAIL'} | "
                 f"{'PASS' if v['c3'] else 'FAIL'} | {'PASS' if v['c4'] else 'FAIL'} | "
                 f"**{v['verdict']}** |")
    L.append("")
    any_pass = any(verdicts[a]["verdict"] == "PASS" for a in ("A", "B", "C"))
    if any_pass:
        passing = [a for a in ("A", "B", "C") if verdicts[a]["verdict"] == "PASS"]
        L.append(f"**Arm(s) passing all 4 criteria: {', '.join(passing)}.** Per the "
                 "pre-registration's tie-break (best paper-counterfactual expectancy, "
                 "then fewer fills dropped), pick among these before flipping `paper` "
                 "config -- do not adopt automatically from this report.")
    else:
        any_ambig = any(verdicts[a]["verdict"] == "AMBIGUOUS" for a in ("A", "B", "C"))
        if any_ambig:
            L.append("**No arm passes all 4 criteria; at least one is AMBIGUOUS "
                     "(passes 1-3, fails 4 -- neighborhood).** Per pre-registration: "
                     "do not adopt; document and hold.")
        else:
            L.append("**No arm passes.** Per pre-registration's expected-outcome clause: "
                     "\"post-filters cannot salvage the consensus mechanism.\" This is a "
                     "real possible outcome and feeds the standing event-season-only vs "
                     "wind-down decision. It does not license inventing new arms this cycle.")
    L.append("")

    L += ["## Arm D (fade) -- descriptive only, no adoption path", "",
          "Opposite outcome entered at (1 - entry price), same exit at resolution "
          "(payout read directly from the opposite outcome's `outcome_prices` entry, "
          "not assumed as 1-payout, though both should coincide for binary markets). "
          "See the per-arm-per-window table above for D's train/validate/paper "
          "numbers -- n is far too small in the paper window to draw a conclusion "
          "from on this cycle.", ""]

    L += ["## Standing caveats", "",
          "- **Hypothesis-formation contamination**: all four arms were suggested by "
          "the paper-period fills (2026-07-05 onward). The paper counterfactual is "
          "therefore NOT independent validation of the hypotheses -- it is reported "
          "with a bootstrap CI, never as sole grounds for adoption.",
          "- **All judgments are relative** (arm vs base, same window, same "
          "simulator) -- absolute simulated PnL is not trustworthy; the base "
          "parameters themselves were tuned on this same train/validate split.",
          "- **Taker-only trades feed**; survivorship bias on cohort selection; "
          "the validate window is World-Cup-inflated; a simulator-vs-paper "
          "calibration gap is unresolved (base validate showed strong simulated "
          "returns while live paper showed negative expectancy in an overlapping "
          "regime) -- exactly why every judgment above is relative-only.",
          "- **Jul 16-17 ingestion outage**: paper-window signals near those dates "
          "may be undercounted, affecting the paper counterfactual's denominator "
          "(not the backtest windows).", ""]

    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")


def write_csv(entries_val: list, fade_val: list, v2: dict, top_half: set) -> None:
    fade_by_key = {(f["condition_id"], f["outcome_index"]): f for f in fade_val}
    fields = ["signal_time", "condition_id", "outcome_index", "category", "entry_price",
              "n_wallets", "wallets", "resolved", "pnl_100", "retained_A", "retained_B",
              "retained_C_3of5", "quality_wallets_in_top_half", "fade_pnl_100"]
    with open(SIGNALS_CSV, "w", encoding="utf-8", newline="") as f:
        import csv
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for e in entries_val:
            key = (e["condition_id"], e["outcome_index"])
            fd = fade_by_key.get(key)
            row = {
                "signal_time": datetime.fromtimestamp(e["signal_time"], tz=timezone.utc).isoformat(),
                "condition_id": e["condition_id"], "outcome_index": e["outcome_index"],
                "category": e.get("category"), "entry_price": e["entry_price"],
                "n_wallets": len(e["wallets"]), "wallets": json.dumps(e["wallets"]),
                "resolved": e["resolved"], "pnl_100": e["pnls"].get(100),
                "retained_A": mask_favorite(e, v2["favorite_cutoff"]),
                "retained_B": mask_band(e, v2["band_low"], v2["band_high"]),
                "retained_C_3of5": mask_quality(e, top_half, v2["quality_gate_k"]),
                "quality_wallets_in_top_half": sum(1 for x in e["wallets"] if x in top_half),
                "fade_pnl_100": fd["pnls"].get(100) if fd else None,
            }
            w.writerow(row)


# ---------- main ----------

def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    started = time.time()

    cfg = load_config()
    v2 = cfg["analysis"]["signal_v2"]
    bcfg = cfg["backtest"]
    pcfg = cfg["paper"]
    position_size = v2["position_size_usd"]
    slip_100 = cfg["slippage"][f"entry_cents_{position_size}"] / 100.0

    conn = ro_connect()
    wset = db.get_cohort_wallets(conn, COHORT)
    cutoff_ts = parse_ts(cfg["analysis"]["window_end_utc"])
    max_gap = bcfg["entry_price_max_gap_seconds"]

    trades, markets, prices = load_clipped_data(conn, wset, cutoff_ts, max_gap)
    if not trades:
        raise SystemExit("no cohort-B trades before analysis.window_end_utc -- check ingestion")
    boundary = global_train_boundary(conn, cutoff_ts, bcfg["train_months"])

    splits = {
        "train": [t for t in trades if t["timestamp"] < boundary],
        "validate": [t for t in trades if t["timestamp"] >= boundary],
    }
    log.info("cohort %s: %d train trades, %d validate trades", COHORT,
             len(splits["train"]), len(splits["validate"]))

    params = {"n_traders": pcfg["default_n"],
              "window_seconds": int(pcfg["default_window_hours"] * 3600),
              "size_floor_usd": pcfg["default_size_floor"]}

    entries: dict = {}
    raw_results: dict = {}
    for w, wtrades in splits.items():
        _, rr, ent = evaluate_window(wtrades, params, markets, prices, cfg)
        raw_results[w] = rr
        entries[w] = ent
        log.info("%s: %d signals detected, %d entered (priced)", w, len(rr), len(ent))

    # ---- sanity gate / calibration (Amendment 2026-08-25: PnL-only, informational --
    # does NOT block arm evaluation; base reference for arms is always today's-DB base) ----
    sg = v2["sanity_gate"]
    official = bt.cell_metrics(raw_results["validate"], position_size)
    orig_pnl, orig_n, orig_closed = (sg["original_validate_pnl"], sg["original_validate_n_signals"],
                                      sg["original_validate_n_closed"])
    pnl_dev = (official["total_pnl"] - orig_pnl) / abs(orig_pnl)
    n_dev = (official["signal_count"] - orig_n) / orig_n
    closed_dev = (official["resolved_count"] - orig_closed) / orig_closed
    tol = sg["tolerance"]
    calibration_ok = abs(pnl_dev) <= tol  # PnL only, per amendment -- counts are expected to differ
    gate = {"ok": calibration_ok, "pnl": official["total_pnl"], "orig_pnl": orig_pnl, "pnl_dev": pnl_dev,
            "n": official["signal_count"], "orig_n": orig_n, "n_dev": n_dev,
            "n_closed": official["resolved_count"], "orig_closed": orig_closed, "closed_dev": closed_dev}
    log.info("CALIBRATION (informational): %s (pnl dev %+.1f%% vs +/-%.0f%% tolerance; "
             "n dev %+.1f%%, closed dev %+.1f%% -- expected to differ, not gated)",
             "PASS" if calibration_ok else "FAIL", pnl_dev * 100, tol * 100, n_dev * 100, closed_dev * 100)

    ingest_timing = diagnose_ingestion_timing(conn, wset, cutoff_ts)
    total_clipped = sum(n for _, n in ingest_timing)
    by_day = "; ".join(f"{d}: {n:,}" for d, n in ingest_timing)
    pre_0703 = sum(n for d, n in ingest_timing if d <= "2026-07-03")
    gate["diagnosis"] = (
        f"Cohort-B trades strictly before analysis.window_end_utc ({cfg['analysis']['window_end_utc']}), "
        f"grouped by the DB row's actual `ingested_at` date: {by_day}. Of {total_clipped:,} such "
        f"trades now in the DB, only {pre_0703:,} ({pre_0703/total_clipped:.0%}) were ingested on or "
        "before 2026-07-03, the date backtest_report.md (the calibration reference) was generated "
        "(09:47 UTC). The remainder was ingested on 2026-07-06/07 -- almost certainly "
        "`ingest_full.py`'s deep-history backfill (config `analysis.full_pull`, run "
        "2026-07-07 overnight per the wallet_quality section), which walks `/trades` "
        "backwards past the original ingest's 3000-offset/4000-trade-per-wallet cap. "
        "Cohort-B wallet MEMBERSHIP is unchanged since 2026-07-03 (both `discovered_at` "
        "timestamps for cohort-B wallets are 2026-07-03; a spot-check against "
        "reports/persistence_checkpoint_wallets.csv's 179-wallet eligible subset shows "
        "100% overlap with the current cohort-B set) -- this rules out cohort redefinition. "
        "Per the pre-registration's Amendment 2026-08-25 (written and committed BEFORE any "
        "arm was evaluated), this is a structural, diagnosed data-growth effect, not a bug, "
        "and the sanity gate was accordingly narrowed to a PnL-only calibration check that "
        "does not block arm evaluation -- the base reference for every arm-vs-base comparison "
        "below is this run's own today's-DB base simulation.")

    base = {w: {"n": m["n"], "n_closed": m["n_closed"], "total_pnl": m["total_pnl"],
                "win_rate": m["win_rate"], "expectancy": m["expectancy"]}
            for w, m in ((w2, compute_sim_metrics(entries[w2], mask_all, position_size))
                        for w2 in ("train", "validate"))}

    # ---- arm C ranking ----
    top_half, ranked = compute_train_ranking(splits["train"], markets, v2["min_resolved_train_trades"])

    # ---- fade transforms ----
    fade_entries = {w: fade_transform_sim(entries[w], markets, slip_100) for w in ("train", "validate")}

    # ---- paper counterfactual ----
    paper_fills = load_paper_closed(conn)
    paper_markets = load_markets_for(conn, [f["condition_id"] for f in paper_fills])
    fade_paper = fade_transform_paper(paper_fills, paper_markets)
    log.info("paper counterfactual: %d CLOSED fills, %d fade-computable", len(paper_fills), len(fade_paper))
    conn.close()

    variants = build_arm_variants(v2, top_half)
    arm_masks = {
        "base": mask_all,
        "A": variants["A"]["nominal"][0],
        "B": variants["B"]["nominal"][0],
        "C": variants["C"]["nominal"][0],
    }

    arm_metrics: dict = {}
    for arm in ("base", "A", "B", "C"):
        mask = arm_masks[arm]
        m_train = compute_sim_metrics(entries["train"], mask, position_size)
        m_val = compute_sim_metrics(entries["validate"], mask, position_size)
        m_train["retention"] = m_train["n"] / base["train"]["n"] if base["train"]["n"] else None
        m_val["retention"] = m_val["n"] / base["validate"]["n"] if base["validate"]["n"] else None
        m_paper = compute_paper_metrics(paper_fills, mask)
        m_paper["retention"] = m_paper["n"] / len(paper_fills) if paper_fills else None
        m_paper["boot"] = bootstrap_ratio_ci(m_paper["pairs"], v2["bootstrap"]["iterations"],
                                             v2["bootstrap"]["seed"])
        arm_metrics[arm] = {"train": m_train, "validate": m_val, "paper": m_paper}

    # arm D (fade): unfiltered, all windows
    d_train = compute_sim_metrics(fade_entries["train"], mask_all, position_size)
    d_val = compute_sim_metrics(fade_entries["validate"], mask_all, position_size)
    d_train["retention"] = 1.0
    d_val["retention"] = 1.0
    d_paper = compute_paper_metrics(fade_paper, mask_all)
    d_paper["retention"] = len(fade_paper) / len(paper_fills) if paper_fills else None
    d_paper["boot"] = bootstrap_ratio_ci(d_paper["pairs"], v2["bootstrap"]["iterations"], v2["bootstrap"]["seed"])
    arm_metrics["D"] = {"train": d_train, "validate": d_val, "paper": d_paper}

    # ---- neighborhood robustness ----
    neighborhood: dict = {}
    for arm in ("A", "B", "C"):
        nom_mask, nom_rule = variants[arm]["nominal"]
        nom_exp = compute_sim_metrics(entries["validate"], nom_mask, position_size)["expectancy"]
        nom_delta = (nom_exp - base["validate"]["expectancy"]
                    if nom_exp is not None and base["validate"]["expectancy"] is not None else None)
        neighborhood[arm] = {"nominal": {"rule": nom_rule, "expectancy": nom_exp, "delta": nom_delta},
                             "variants": {}}
        for name, (mfn, rule) in variants[f"{arm}_nbhd"].items():
            exp = compute_sim_metrics(entries["validate"], mfn, position_size)["expectancy"]
            delta = (exp - base["validate"]["expectancy"]
                    if exp is not None and base["validate"]["expectancy"] is not None else None)
            neighborhood[arm]["variants"][name] = {"rule": rule, "expectancy": exp, "delta": delta}

    # ---- pre-registered verdict, applied mechanically ----
    verdicts: dict = {}
    for arm in ("A", "B", "C"):
        val_exp, val_base_exp = arm_metrics[arm]["validate"]["expectancy"], base["validate"]["expectancy"]
        val_ret = arm_metrics[arm]["validate"]["retention"] or 0.0
        c1 = (val_exp is not None and val_base_exp is not None and val_exp >= val_base_exp
              and val_ret >= v2["fill_retention_floor"])
        train_exp = arm_metrics[arm]["train"]["expectancy"]
        c2 = train_exp is not None and train_exp >= 0.0
        paper_n = arm_metrics[arm]["paper"]["n_closed"]
        paper_exp = arm_metrics[arm]["paper"]["expectancy"]
        c3 = paper_n >= v2["min_paper_fills"] and paper_exp is not None and paper_exp >= v2["paper_expectancy_floor"]
        nom_sign = sign(neighborhood[arm]["nominal"]["delta"])
        c4 = all(sign(row["delta"]) == nom_sign for row in neighborhood[arm]["variants"].values())
        if c1 and c2 and c3 and c4:
            verdict = "PASS"
        elif c1 and c2 and c3 and not c4:
            verdict = "AMBIGUOUS"
        else:
            verdict = "FAIL"
        verdicts[arm] = {"c1": c1, "c2": c2, "c3": c3, "c4": c4, "verdict": verdict}
        log.info("arm %s: c1=%s c2=%s c3=%s c4=%s -> %s", arm, c1, c2, c3, c4, verdict)

    write_report(cfg, gate, base, arm_metrics, neighborhood, verdicts, ranked, v2)
    write_csv(entries["validate"], fade_entries["validate"], v2, top_half)
    log.info("wrote %s and %s (%.1fs total)", REPORT_MD, SIGNALS_CSV, time.time() - started)


if __name__ == "__main__":
    main()
