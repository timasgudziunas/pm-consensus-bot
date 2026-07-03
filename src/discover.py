"""Phase 1: trader discovery + vetting.

Per category: pull MONTH and ALL leaderboards, intersect, vet the top
candidates by trade history, and write the watchlist to the wallets table
plus a human-readable preview in reports/watchlist_preview.txt.

Run: python src/discover.py
"""
import logging
import os
import time
from collections import defaultdict
from typing import Optional

from tabulate import tabulate

import db
from data_api import ApiError, DataApi, load_config

log = logging.getLogger(__name__)

REPORTS_DIR = os.path.join(db.REPO_ROOT, "reports")


def pull_leaderboard(api: DataApi, category: str, time_period: str) -> dict:
    """Return {wallet: {user_name, pnl}} across all leaderboard pages."""
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
                out[w] = {"user_name": r.get("user_name") or "", "pnl": float(r.get("pnl") or 0)}
        if len(rows) < limit:
            break
        offset += limit
    return out


def vet_wallet(api: DataApi, wallet: str) -> Optional[dict]:
    """Pull a trade sample and compute vetting stats. None on API failure.

    PnL-concentration uses a cash-flow proxy per market (sell USD − buy USD);
    it ignores unredeemed winnings, which is acceptable for ranking purposes —
    profitability itself is already established by the leaderboard."""
    cfg = load_config()["discovery"]
    try:
        trades = api.get_trades(user=wallet, limit=cfg["vetting_trade_limit"])
    except ApiError as e:
        log.warning("vetting pull failed for %s: %s", wallet, e)
        return None

    by_market: dict = defaultdict(list)
    for t in trades:
        row = db.trade_row_from_api(t)
        if row:
            by_market[row["condition_id"]].append(row)

    n_markets = len(by_market)
    n_trades = sum(len(v) for v in by_market.values())

    # Market-maker heuristic: same-day BUY+SELL round trip on the same outcome.
    rt_window = cfg["mm_roundtrip_window_seconds"]
    roundtrip_markets = 0
    pnl_by_market = {}
    for cond, rows in by_market.items():
        buys = [(r["timestamp"]) for r in rows if r["side"] == "BUY"]
        sells = [(r["timestamp"]) for r in rows if r["side"] == "SELL"]
        # round trip if any buy and sell on this market land within the window
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

    return {
        "markets_traded": n_markets,
        "total_trades": n_trades,
        "mm_ratio": mm_ratio,
        "concentration": concentration,
    }


def main() -> None:
    """Run discovery across all configured categories and write the watchlist."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg = load_config()
    dcfg = cfg["discovery"]
    api = DataApi()
    conn = db.connect()

    # 1. Leaderboards + intersection per category
    candidates: dict = {}   # wallet -> {user_name, pnl_month, pnl_all, categories: set}
    for category in cfg["categories"]:
        log.info("leaderboards for %s ...", category)
        month = pull_leaderboard(api, category, "MONTH")
        allw = pull_leaderboard(api, category, "ALL")
        both = set(month) & set(allw)
        # rank intersection by MONTH pnl, cap vetting work per category
        ranked = sorted(both, key=lambda w: -month[w]["pnl"])[: dcfg["max_candidates_per_category"]]
        log.info("%s: %d month / %d all / %d intersect -> %d candidates",
                 category, len(month), len(allw), len(both), len(ranked))
        for w in ranked:
            c = candidates.setdefault(w, {
                "user_name": month[w]["user_name"], "pnl_month": month[w]["pnl"],
                "pnl_all": allw[w]["pnl"], "categories": set(),
            })
            c["categories"].add(category)

    log.info("vetting %d unique candidates ...", len(candidates))

    # 2. Vetting
    results = []
    for i, (wallet, c) in enumerate(sorted(candidates.items(), key=lambda kv: -kv[1]["pnl_month"]), 1):
        stats = vet_wallet(api, wallet)
        if stats is None:
            continue
        is_mm = stats["mm_ratio"] > dcfg["mm_roundtrip_threshold"]
        concentrated = stats["concentration"] > dcfg["max_pnl_concentration"]
        passes = (stats["markets_traded"] >= dcfg["min_markets"]
                  and stats["total_trades"] >= dcfg["min_trades"]
                  and not is_mm)
        results.append({**c, "wallet": wallet, **stats, "is_mm": is_mm,
                        "concentrated": concentrated, "passes": passes})
        log.info("[%d/%d] %s (%s) mkts=%d trades=%d mm=%.0f%% conc=%.0f%% -> %s",
                 i, len(candidates), c["user_name"] or wallet[:10], "/".join(sorted(c["categories"])),
                 stats["markets_traded"], stats["total_trades"], stats["mm_ratio"] * 100,
                 stats["concentration"] * 100, "PASS" if passes else "reject")

    # 3. Selection: passing wallets, concentrated ones deprioritized, capped
    #    per category and overall.
    passing = [r for r in results if r["passes"]]
    passing.sort(key=lambda r: (r["concentrated"], -r["pnl_month"]))
    per_cat: dict = defaultdict(int)
    selected_set = set()
    for r in passing:
        if len(selected_set) >= dcfg["max_watchlist"]:
            break
        if all(per_cat[cat] >= dcfg["max_per_category"] for cat in r["categories"]):
            continue
        selected_set.add(r["wallet"])
        for cat in r["categories"]:
            per_cat[cat] += 1

    # 4. Persist
    now = int(time.time())
    for r in results:
        db.upsert_wallet(conn, {
            "address": r["wallet"], "username": r["user_name"],
            "category": ",".join(sorted(r["categories"])),
            "pnl_month": r["pnl_month"], "pnl_all": r["pnl_all"],
            "markets_traded": r["markets_traded"], "total_trades": r["total_trades"],
            "is_mm": 1 if r["is_mm"] else 0, "concentrated": 1 if r["concentrated"] else 0,
            "selected": 1 if r["wallet"] in selected_set else 0,
            "discovered_at": now,
        })

    # 5. Human-readable preview (stdout + reports/watchlist_preview.txt)
    results.sort(key=lambda r: (",".join(sorted(r["categories"])), -r["pnl_month"]))
    table = [[r["wallet"][:10] + "…", (r["user_name"] or "")[:20], ",".join(sorted(r["categories"])),
              f"{r['pnl_month']:,.0f}", f"{r['pnl_all']:,.0f}", r["markets_traded"], r["total_trades"],
              "Y" if r["is_mm"] else "", "Y" if r["concentrated"] else "",
              "Y" if r["wallet"] in selected_set else ""] for r in results]
    headers = ["wallet", "username", "categories", "pnl_month", "pnl_all",
               "markets", "trades", "MM", "conc", "sel"]
    preview = tabulate(table, headers=headers, tablefmt="github")
    counts = "\n".join(f"  {cat}: {n}" for cat, n in sorted(per_cat.items()))
    footer = (f"\n\nSelected per category (wallets may count in several):\n{counts}"
              f"\nTotal selected: {len(selected_set)} of {len(results)} vetted candidates\n")
    print(preview + footer)
    os.makedirs(REPORTS_DIR, exist_ok=True)
    with open(os.path.join(REPORTS_DIR, "watchlist_preview.txt"), "w", encoding="utf-8") as f:
        f.write(preview + footer)
    log.info("watchlist written: %d selected", len(selected_set))


if __name__ == "__main__":
    main()
