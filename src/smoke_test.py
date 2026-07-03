"""Phase 0 smoke tests: prove every endpoint works through the real clients,
print raw response keys, and verify the DB schema creates cleanly.

Run: python src/smoke_test.py
"""
import json
import logging
import time

import db
from clob_api import ClobApi
from data_api import DataApi
from gamma_api import GammaApi

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


def show_keys(label: str, rows: list) -> None:
    """Print the raw (normalized) keys of the first row so casing is auditable."""
    print(f"\n--- {label} ---")
    if not rows:
        print("  EMPTY RESPONSE")
        return
    print("  keys:", sorted(rows[0].keys()))
    for r in rows[:3]:
        compact = {k: r[k] for k in list(r)[:8]}
        print("  row:", json.dumps(compact, default=str)[:220])


def main() -> None:
    """Run all smoke tests; raises on any failure."""
    data, gamma, clob = DataApi(), GammaApi(), ClobApi()

    # 1. DB creates cleanly
    conn = db.connect()
    tables = [r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    print("DB tables:", sorted(tables))

    # 2. Leaderboard (both time periods used by discovery)
    lb_month = data.get_leaderboard("OVERALL", "MONTH", "PNL", limit=5)
    show_keys("leaderboard OVERALL/MONTH", lb_month)
    lb_all = data.get_leaderboard("OVERALL", "ALL", "PNL", limit=5)
    show_keys("leaderboard OVERALL/ALL", lb_all)
    wallet = lb_month[0]["proxy_wallet"]

    # 3. Trades for a known top wallet
    trades = data.get_trades(user=wallet, limit=3)
    show_keys(f"trades user={wallet[:10]}…", trades)
    row = db.trade_row_from_api(trades[0])
    assert row and row["size_usd"] > 0, "trade normalization failed"
    print("  normalized trade row:", row)
    cond_id = row["condition_id"]

    # 4. Global feed (paper-mode dependency)
    feed = data.get_trades(limit=3)
    show_keys("trades global feed", feed)
    print("  NOTE: global feed outcome_index =", [t.get("outcome_index") for t in feed],
          "(999 = unreliable; paper maps via asset/clobTokenIds)")

    # 5. Positions + activity
    show_keys("positions", data.get_positions(wallet))
    show_keys("activity", data.get_activity(wallet, limit=3))

    # 6. Gamma market by conditionId (single + batch)
    mkts = gamma.get_markets(condition_ids=[cond_id])
    show_keys("gamma market", mkts)
    m = mkts[0]
    token_ids = json.loads(m["clob_token_ids"])
    print("  outcome_prices:", m["outcome_prices"], "| closed:", m["closed"], "| tokens:", len(token_ids))
    mrow = db.market_row_from_gamma(m)
    print("  normalized market row event_slug:", mrow["event_slug"])
    batch = gamma.get_markets(condition_ids=[cond_id, feed[0]["condition_id"]])
    print("  batch condition_ids lookup returned", len(batch), "markets")

    # 7. Category resolution via event tags
    cat, labels = gamma.resolve_category(mrow["event_slug"]) if mrow["event_slug"] else ("", [])
    print("  event tags:", labels, "-> category:", repr(cat))

    # 8. CLOB price history + book + midpoint
    now = int(time.time())
    hist = clob.get_price_history(token_ids[0], now - 5 * 86400, now, fidelity=60)
    print(f"\n--- clob price history --- {len(hist)} points; first 5: {hist[:5]}")
    assert hist, "empty price history"
    book = clob.get_book(token_ids[0])
    print("--- clob book --- best bid:", book["bids"][:1], "best ask:", book["asks"][:1])
    mid = clob.get_midpoint(token_ids[0])
    print("--- clob midpoint ---", mid)

    print("\nALL SMOKE TESTS PASSED")


if __name__ == "__main__":
    main()
