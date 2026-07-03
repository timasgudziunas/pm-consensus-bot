"""Phase 1: trader discovery + vetting — cohort edition (2026-07-03).

Per category: pull MONTH and ALL leaderboards, intersect, vet the top
candidates by trade history. Candidates passing the hard filters are then
selected under THREE cohorts — competing definitions of "efficient profitable
trader" — and the union becomes the watchlist:

  A: raw month PnL (the original method, kept as the control)
  B: PnL per dollar of volume (leaderboard pnl / vol)
  C: stake-weighted entry edge — mean (resolution payout − entry price)
     weighted by stake across the wallet's resolved sample buys; the metric
     most aligned with copy-trading (we copy entries, not exits)

Every candidate also gets a consistency score (fraction of sampled positions
with a positive PnL proxy) used as a tie-breaker within cohorts.

Run: python src/discover.py
"""
import json
import logging
import os
import time
from collections import Counter, defaultdict
from typing import Optional

from tabulate import tabulate

import db
from data_api import ApiError, DataApi, load_config
from gamma_api import GammaApi

log = logging.getLogger(__name__)

REPORTS_DIR = os.path.join(db.REPO_ROOT, "reports")

COHORT_TAGS = ("A", "B", "C")


def pull_leaderboard(api: DataApi, category: str, time_period: str) -> dict:
    """Return {wallet: {user_name, pnl, vol}} across all leaderboard pages."""
    cfg = load_config()["discovery"]
    limit = cfg["leaderboard_page_limit"]
    out: dict = {}
    offset = 0
    while offset <= cfg["leaderboard_max_offset"]:
        try:
            rows = api.get_leaderboard(category, time_period, "PNL", limit=limit, offset=offset)
        except ApiError as e:
            log.warning("leaderboard %s/%s offset=%d failed: %s", category, time_period, offset, e)
            break
        if not rows:
            break
        for r in rows:
            w = r.get("proxy_wallet")
            if w and w not in out:
                out[w] = {"user_name": r.get("user_name") or "",
                          "pnl": float(r.get("pnl") or 0),
                          "vol": float(r.get("vol") or 0)}
        if len(rows) < limit:
            break
        offset += limit
    return out


def pull_trade_sample(api: DataApi, wallet: str) -> Optional[list]:
    """Pull up to vetting_trade_limit trades for a wallet (paginated).

    The API silently caps limit at 1000 per page, so limits above that need
    explicit pagination. None on API failure."""
    dcfg = load_config()["discovery"]
    page_cap = load_config()["ingest"]["page_size"]
    want = dcfg["vetting_trade_limit"]
    trades: list = []
    offset = 0
    while len(trades) < want:
        ask = min(page_cap, want - len(trades))
        try:
            page = api.get_trades(user=wallet, limit=ask, offset=offset)
        except ApiError as e:
            log.warning("vetting pull failed for %s: %s", wallet, e)
            return None
        trades.extend(page)
        if len(page) < ask:
            break
        offset += len(page)
    return trades


def vet_wallet(api: DataApi, wallet: str) -> Optional[tuple]:
    """Vetting stats plus per-position sample data. None on API failure.

    Returns (stats, positions) where positions maps (condition_id,
    outcome_index) -> {buys: [(price, usd)], buy_usd, sell_usd, net_shares}.
    PnL-concentration uses a cash-flow proxy per market (sell USD − buy USD);
    it ignores unredeemed winnings, which is acceptable for ranking purposes —
    profitability itself is already established by the leaderboard."""
    cfg = load_config()["discovery"]
    sample = pull_trade_sample(api, wallet)
    if sample is None:
        return None

    by_market: dict = defaultdict(list)
    positions: dict = {}
    for t in sample:
        row = db.trade_row_from_api(t)
        if not row:
            continue
        by_market[row["condition_id"]].append(row)
        if row["outcome_index"] < 0 or row["price"] <= 0:
            continue
        p = positions.setdefault((row["condition_id"], row["outcome_index"]),
                                 {"buys": [], "buy_usd": 0.0, "sell_usd": 0.0, "net_shares": 0.0})
        shares = row["size_usd"] / row["price"]
        if row["side"] == "BUY":
            p["buys"].append((row["price"], row["size_usd"]))
            p["buy_usd"] += row["size_usd"]
            p["net_shares"] += shares
        else:
            p["sell_usd"] += row["size_usd"]
            p["net_shares"] -= shares

    n_markets = len(by_market)
    n_trades = sum(len(v) for v in by_market.values())

    # Market-maker heuristic: same-day BUY+SELL round trip on the same market.
    rt_window = cfg["mm_roundtrip_window_seconds"]
    roundtrip_markets = 0
    pnl_by_market = {}
    for cond, rows in by_market.items():
        buys = [r["timestamp"] for r in rows if r["side"] == "BUY"]
        sells = [r["timestamp"] for r in rows if r["side"] == "SELL"]
        found = False
        for bt in buys:
            if found:
                break
            for st in sells:
                if abs(st - bt) <= rt_window:
                    found = True
                    break
        if found:
            roundtrip_markets += 1
        pnl_by_market[cond] = (sum(r["size_usd"] for r in rows if r["side"] == "SELL")
                               - sum(r["size_usd"] for r in rows if r["side"] == "BUY"))

    mm_ratio = roundtrip_markets / n_markets if n_markets else 0.0
    abs_pnls = sorted((abs(v) for v in pnl_by_market.values()), reverse=True)
    total_abs = sum(abs_pnls)
    concentration = sum(abs_pnls[:2]) / total_abs if total_abs > 0 else 0.0

    stats = {
        "markets_traded": n_markets,
        "total_trades": n_trades,
        "mm_ratio": mm_ratio,
        "concentration": concentration,
    }
    return stats, positions


def fetch_resolutions(conn, cond_ids: set) -> dict:
    """Payout lists for resolved sample markets, fetching what the DB lacks.

    Fetched metadata is cached in the markets table (category left NULL —
    ingest.py backfills categories for signal-candidate markets). Returns
    {condition_id: [payout per outcome]} for closed markets only."""
    gamma = GammaApi()
    batch = load_config()["ingest"]["gamma_batch_size"]
    payouts: dict = {}
    have: set = set()
    for r in conn.execute("SELECT condition_id, closed, outcome_prices FROM markets"):
        have.add(r["condition_id"])
        if r["closed"] and r["outcome_prices"]:
            try:
                payouts[r["condition_id"]] = [float(x) for x in json.loads(r["outcome_prices"])]
            except (TypeError, ValueError):
                pass
    missing = sorted(cond_ids - have)
    log.info("resolution lookups: %d sample markets, %d already cached, fetching %d ...",
             len(cond_ids), len(cond_ids) - len(missing), len(missing))
    for i in range(0, len(missing), batch):
        chunk = missing[i:i + batch]
        markets: list = []
        try:
            # two passes: Gamma hides closed markets unless closed=true
            markets = gamma.get_markets(condition_ids=chunk, limit=batch)
            markets += gamma.get_markets(condition_ids=chunk, limit=batch, closed=True)
        except ApiError as e:
            log.warning("gamma batch failed (%s) — chunk skipped, edge sample shrinks", e)
        for m in markets:
            row = db.market_row_from_gamma(m)
            if not row["condition_id"]:
                continue
            db.upsert_market(conn, row)
            if row["closed"] and row["outcome_prices"]:
                try:
                    payouts[row["condition_id"]] = [float(x) for x in json.loads(row["outcome_prices"])]
                except (TypeError, ValueError):
                    pass
        if (i // batch) % 50 == 0:
            log.info("resolutions %d/%d", min(i + batch, len(missing)), len(missing))
    return payouts


def entry_edge(positions: dict, payouts: dict) -> tuple:
    """Cohort C metric: stake-weighted (payout − entry price) over resolved buys.

    Returns (edge or None, resolved_buy_count)."""
    stake = weighted = 0.0
    n = 0
    for (cond, idx), p in positions.items():
        pay = payouts.get(cond)
        if pay is None or idx >= len(pay):
            continue
        for price, usd in p["buys"]:
            weighted += (pay[idx] - price) * usd
            stake += usd
            n += 1
    return (weighted / stake if stake > 0 else None), n


def consistency_score(positions: dict, payouts: dict) -> Optional[float]:
    """Fraction of sampled positions with positive PnL proxy.

    Proxy = sell USD − buy USD + net shares × payout for resolved markets;
    unresolved positions count only if effectively round-tripped flat."""
    wins = counted = 0
    for (cond, idx), p in positions.items():
        pnl = p["sell_usd"] - p["buy_usd"]
        pay = payouts.get(cond)
        if pay is not None and idx < len(pay):
            pnl += p["net_shares"] * pay[idx]
        elif abs(p["net_shares"]) > 1e-6:
            continue  # open position, value unknown
        counted += 1
        wins += 1 if pnl > 0 else 0
    return wins / counted if counted else None


def select_cohorts(passing: list, dcfg: dict) -> tuple:
    """Rank passing wallets under each cohort and build the capped union.

    Returns (cohort_tags {wallet: set}, selected_set, per_cat Counter)."""
    metric = {
        "A": lambda r: r["pnl_month"],
        "B": lambda r: r["pnl_per_vol"],
        "C": lambda r: r["entry_edge"],
    }
    eligible = {
        "A": passing,
        "B": [r for r in passing if r["pnl_per_vol"] is not None],
        "C": [r for r in passing if r["entry_edge"] is not None
              and r["resolved_buys"] >= dcfg["cohort_c_min_resolved_buys"]],
    }
    cohort_tags: dict = defaultdict(set)
    best_rank: dict = {}
    for tag in COHORT_TAGS:
        ranked = sorted(eligible[tag],
                        key=lambda r: (r["concentrated"], -metric[tag](r), -(r["consistency"] or 0)))
        log.info("cohort %s: %d eligible, selecting top %d",
                 tag, len(ranked), min(dcfg["cohort_size"], len(ranked)))
        for rank, r in enumerate(ranked[: dcfg["cohort_size"]]):
            cohort_tags[r["wallet"]].add(tag)
            best_rank[r["wallet"]] = min(best_rank.get(r["wallet"], 1 << 30), rank)

    by_wallet = {r["wallet"]: r for r in passing}
    priority = sorted(cohort_tags,
                      key=lambda w: (best_rank[w], -(by_wallet[w]["consistency"] or 0)))
    selected_set: set = set()
    per_cat: Counter = Counter()
    for w in priority:
        if len(selected_set) >= dcfg["max_watchlist"]:
            break
        cats = by_wallet[w]["categories"]
        if all(per_cat[c] >= dcfg["max_per_category"] for c in cats):
            continue
        selected_set.add(w)
        for c in cats:
            per_cat[c] += 1
    return cohort_tags, selected_set, per_cat


def main() -> None:
    """Run cohort discovery across all configured categories and write the watchlist."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg = load_config()
    dcfg = cfg["discovery"]
    api = DataApi()
    conn = db.connect()

    # 1. Leaderboards + intersection per category
    candidates: dict = {}   # wallet -> {user_name, pnl_month, pnl_all, vol_month, categories}
    for category in cfg["categories"]:
        log.info("leaderboards for %s ...", category)
        month = pull_leaderboard(api, category, "MONTH")
        allw = pull_leaderboard(api, category, "ALL")
        both = set(month) & set(allw)
        ranked = sorted(both, key=lambda w: -month[w]["pnl"])[: dcfg["max_candidates_per_category"]]
        log.info("%s: %d month / %d all / %d intersect -> %d candidates",
                 category, len(month), len(allw), len(both), len(ranked))
        for w in ranked:
            c = candidates.setdefault(w, {
                "user_name": month[w]["user_name"], "pnl_month": month[w]["pnl"],
                "pnl_all": allw[w]["pnl"], "vol_month": month[w]["vol"], "categories": set(),
            })
            c["categories"].add(category)

    log.info("vetting %d unique candidates ...", len(candidates))

    # 2. Vetting (trade samples; positions kept for cohort C / consistency)
    results = []
    samples: dict = {}
    for i, (wallet, c) in enumerate(sorted(candidates.items(), key=lambda kv: -kv[1]["pnl_month"]), 1):
        vetted = vet_wallet(api, wallet)
        if vetted is None:
            continue
        stats, positions = vetted
        samples[wallet] = positions
        is_mm = stats["mm_ratio"] > dcfg["mm_roundtrip_threshold"]
        concentrated = stats["concentration"] > dcfg["max_pnl_concentration"]
        passes = (stats["markets_traded"] >= dcfg["min_markets"]
                  and stats["total_trades"] >= dcfg["min_trades"]
                  and not is_mm)
        vol = c["vol_month"]
        results.append({**c, "wallet": wallet, **stats, "is_mm": is_mm,
                        "concentrated": concentrated, "passes": passes,
                        "pnl_per_vol": (c["pnl_month"] / vol) if vol and vol > 0 else None})
        log.info("[%d/%d] %s (%s) mkts=%d trades=%d mm=%.0f%% conc=%.0f%% -> %s",
                 i, len(candidates), c["user_name"] or wallet[:10], "/".join(sorted(c["categories"])),
                 stats["markets_traded"], stats["total_trades"], stats["mm_ratio"] * 100,
                 stats["concentration"] * 100, "PASS" if passes else "reject")

    # 3. Resolution lookups for cohort C + consistency (batched, cached)
    sample_conds = {cond for pos in samples.values() for (cond, _idx) in pos}
    payouts = fetch_resolutions(conn, sample_conds)
    for r in results:
        pos = samples[r["wallet"]]
        r["entry_edge"], r["resolved_buys"] = entry_edge(pos, payouts)
        r["consistency"] = consistency_score(pos, payouts)

    # 4. Hard filters with per-filter rejection accounting
    rejects = Counter()
    for r in results:
        if r["markets_traded"] < dcfg["min_markets"]:
            rejects["min_markets"] += 1
        if r["total_trades"] < dcfg["min_trades"]:
            rejects["min_trades"] += 1
        if r["is_mm"]:
            rejects["market_maker"] += 1
    passing = [r for r in results if r["passes"]]
    log.info("filters: %d vetted -> %d passing; rejections (overlapping): %s",
             len(results), len(passing), dict(rejects))

    # 5. Cohort selection + capped union
    cohort_tags, selected_set, per_cat = select_cohorts(passing, dcfg)

    # 6. Persist (wipe stale selection state first — re-runs must not leak
    #    previously selected wallets that this round didn't pick)
    conn.execute("UPDATE wallets SET selected = 0, cohorts = NULL")
    conn.commit()
    now = int(time.time())
    for r in results:
        tags = cohort_tags.get(r["wallet"])
        db.upsert_wallet(conn, {
            "address": r["wallet"], "username": r["user_name"],
            "category": ",".join(sorted(r["categories"])),
            "pnl_month": r["pnl_month"], "pnl_all": r["pnl_all"],
            "markets_traded": r["markets_traded"], "total_trades": r["total_trades"],
            "is_mm": 1 if r["is_mm"] else 0, "concentrated": 1 if r["concentrated"] else 0,
            "selected": 1 if r["wallet"] in selected_set else 0,
            "discovered_at": now,
            "cohorts": ",".join(sorted(tags)) if tags else None,
            "vol_month": r["vol_month"], "pnl_per_vol": r["pnl_per_vol"],
            "entry_edge": r["entry_edge"], "resolved_buys": r["resolved_buys"],
            "consistency": r["consistency"],
        })

    # 7. Human-readable preview (stdout + reports/watchlist_preview.txt)
    def n2(v):
        return "" if v is None else f"{v:.2f}"

    results.sort(key=lambda r: (",".join(sorted(r["categories"])), -r["pnl_month"]))
    table = [[r["wallet"][:10] + "…", (r["user_name"] or "")[:20], ",".join(sorted(r["categories"])),
              f"{r['pnl_month']:,.0f}", n2(r["pnl_per_vol"]), n2(r["entry_edge"]),
              r["resolved_buys"], n2(r["consistency"]), r["markets_traded"], r["total_trades"],
              "Y" if r["is_mm"] else "", "Y" if r["concentrated"] else "",
              "".join(sorted(cohort_tags.get(r["wallet"], []))),
              "Y" if r["wallet"] in selected_set else ""] for r in results]
    headers = ["wallet", "username", "categories", "pnl_month", "pnl/vol", "edge",
               "rbuys", "consist", "markets", "trades", "MM", "conc", "cohorts", "sel"]
    preview = tabulate(table, headers=headers, tablefmt="github")

    tag_counts = Counter(t for w in selected_set for t in cohort_tags.get(w, []))
    overlap = Counter(frozenset(cohort_tags[w]) for w in selected_set)
    counts = "\n".join(f"  {cat}: {n}" for cat, n in sorted(per_cat.items()))
    footer = (f"\n\nFilter rejections (of {len(results)} vetted, overlapping): {dict(rejects)}"
              f"\nCohort membership within the selected union: "
              + ", ".join(f"{t}={tag_counts[t]}" for t in COHORT_TAGS)
              + "\nCohort overlap: "
              + ", ".join(f"{'+'.join(sorted(k))}: {v}" for k, v in sorted(overlap.items(), key=lambda kv: -kv[1]))
              + f"\n\nSelected per category (wallets may count in several):\n{counts}"
              f"\nTotal selected: {len(selected_set)} of {len(results)} vetted candidates\n")
    print(preview + footer)
    os.makedirs(REPORTS_DIR, exist_ok=True)
    with open(os.path.join(REPORTS_DIR, "watchlist_preview.txt"), "w", encoding="utf-8") as f:
        f.write(preview + footer)
    log.info("watchlist written: %d selected (cohorts A=%d B=%d C=%d)",
             len(selected_set), tag_counts["A"], tag_counts["B"], tag_counts["C"])


if __name__ == "__main__":
    main()
