"""Signal replay: strict-45 consistency cohort vs full cohort B (250).

Produced the frequency tables in
reports/proposals/persistence_power_and_strict45_analysis.md (2026-07-07).
Analysis-only and read-only; runs historical trades through the shared
signals.detect_signals (the exact live detector). The parameter grid below is
frozen documentation of the published analysis, not tunables.

Run: python src/replay_strict45.py
"""
import csv
import os
import sqlite3
from collections import Counter
from datetime import datetime, timezone

from signals import detect_signals

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCORES_CSV = os.path.join(REPO_ROOT, "reports", "wallet_quality_scores.csv")
DB = os.path.join(REPO_ROOT, "data", "copybot.db")

WINDOWS = (("May (pre-WC)", "2026-05-01", "2026-06-01"),
           ("June (WC era)", "2026-06-01", "2026-07-02"),
           ("Jul 5-7 (live gate, paper-poll data)", "2026-07-05T13:00:00", "2026-07-07T17:00:00"))
# (n_traders, size_floor_usd, window_hours); (5, 1000, 12) = live params
GRID = ((5, 1000, 12), (4, 1000, 12), (3, 1000, 12), (3, 500, 12), (3, 250, 12),
        (2, 1000, 12), (2, 500, 12), (3, 500, 24), (2, 1000, 24))


def _ts(s: str) -> int:
    return int(datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp())


def main() -> None:
    """Replay each window x cohort x grid cell and print signal frequencies."""
    rows = list(csv.DictReader(open(SCORES_CSV, encoding="utf-8")))
    all250 = {r["wallet"] for r in rows}
    strict45 = {r["wallet"] for r in rows if r["verdict"] in ("CONSISTENT", "CONSISTENT_YOUNG")}
    print(f"cohorts: 250={len(all250)}, strict={len(strict45)}")

    conn = sqlite3.connect(f"file:{DB.replace(os.sep, '/')}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cat = dict(conn.execute("SELECT condition_id, category FROM markets"))

    for label, lo_s, hi_s in WINDOWS:
        lo, hi = _ts(lo_s), _ts(hi_s)
        days = (hi - lo) / 86400
        trades = [dict(r) for r in conn.execute(
            "SELECT wallet, condition_id, outcome_index, side, size_usd, price, timestamp "
            "FROM trades WHERE timestamp>=? AND timestamp<?", (lo, hi))
            if r["wallet"] in all250]
        print(f"\n=== {label}: {len(trades):,} cohort-B trades over {days:.1f}d ===")
        for name, wset in (("250 (cohort B)", all250), ("45 (strict)", strict45)):
            sub = trades if wset is all250 else [t for t in trades if t["wallet"] in wset]
            for n, floor, w_h in GRID:
                sigs = detect_signals(sub, {"n_traders": n, "window_seconds": w_h * 3600,
                                            "size_floor_usd": floor})
                cc = Counter((cat.get(s["condition_id"]) or "UNMAPPED") for s in sigs)
                top = ", ".join(f"{k}:{v}" for k, v in cc.most_common(4))
                print(f"  {name:>14} N={n} F=${floor} W={w_h}h: {len(sigs):3d} "
                      f"({len(sigs) / days:.1f}/day)  [{top}]")
    conn.close()


if __name__ == "__main__":
    main()
