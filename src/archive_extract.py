"""Archive extract: copy the small tables that back every report out of data/copybot.db.

Written for the 2026-10-25 wind-down. The 6 GB copybot.db (5.9M taker-only
trades, 5.7M price_history rows, 2.2M signals) was deleted on archive; this
script preserves everything the reports and the final write-up cite:

  paper_trades            every paper position (the single source of truth)
  wallets                 cohort B and the rest of the vetted universe
  backtest_results        the parameter sweep behind reports/backtest_report.md
  ingest_progress         per-wallet ingestion checkpoints (provenance only)
  full_history_progress   deep-backfill checkpoints (provenance only)
  event_categories        category labels used by the dashboard
  markets                 ONLY rows referenced by paper_trades

Dropped on purpose: trades, price_history, signals (bulk, irreproducible
because of the /trades 4k-per-wallet cap; see HANDOFF.md).

Output: data/archive_extract.db (schema copied from sqlite_master) and
reports/paper_trades_final.csv. Read-only against the source. Rerunnable.

Run: python src/archive_extract.py
"""
import csv
import os
import sqlite3
from pathlib import Path

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DB = os.path.join(REPO_ROOT, "data", "copybot.db")
OUT_DB = os.path.join(REPO_ROOT, "data", "archive_extract.db")
OUT_CSV = os.path.join(REPO_ROOT, "reports", "paper_trades_final.csv")

FULL_TABLES = [
    "paper_trades",
    "wallets",
    "backtest_results",
    "ingest_progress",
    "full_history_progress",
    "event_categories",
]
SUBSET_TABLES = {
    "markets": "SELECT * FROM src.markets WHERE condition_id IN (SELECT condition_id FROM src.paper_trades)",
}


def main() -> None:
    """Build data/archive_extract.db and reports/paper_trades_final.csv from copybot.db."""
    if os.path.exists(OUT_DB):
        os.remove(OUT_DB)
    out = sqlite3.connect(f"file:{Path(OUT_DB).as_posix()}", uri=True)
    # as_uri() percent-encodes the space in the user profile path; ATTACH only
    # honours ?mode=ro when the main connection was opened with uri=True.
    out.execute(f"ATTACH DATABASE '{Path(SRC_DB).as_uri()}?mode=ro' AS src")
    schema = {
        name: sql
        for name, sql in out.execute(
            "SELECT name, sql FROM src.sqlite_master WHERE type='table' AND sql IS NOT NULL"
        )
    }
    for table in FULL_TABLES + list(SUBSET_TABLES):
        if table not in schema:
            raise SystemExit(f"table {table} missing from source DB")
        out.execute(schema[table])
        select = SUBSET_TABLES.get(table, f"SELECT * FROM src.{table}")
        out.execute(f"INSERT INTO main.{table} {select}")
        n = out.execute(f"SELECT COUNT(*) FROM main.{table}").fetchone()[0]
        print(f"{table:24s} {n:>8,} rows")
    out.commit()

    cur = out.execute("SELECT * FROM main.paper_trades ORDER BY id")
    cols = [d[0] for d in cur.description]
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(cur.fetchall())
    out.execute("DETACH DATABASE src")
    out.close()
    print(f"wrote {OUT_DB} ({os.path.getsize(OUT_DB)/1024/1024:.1f} MB) and {OUT_CSV}")


if __name__ == "__main__":
    main()
