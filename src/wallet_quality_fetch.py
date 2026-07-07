"""Fetch resolution metadata for markets traded by cohort-B wallets but absent
from the markets table (wallet-quality analysis prerequisite, 2026-07-07).

Only signal/vetting markets were ever fetched, so per-wallet PnL computed on
the existing markets table would be selection-biased toward consensus-relevant
markets. This pulls the rest, ordered by descending cohort stake so partial
completion still maximizes stake coverage.

Resumable: the markets table itself is the checkpoint (missing set shrinks on
restart); condition_ids Gamma returns nothing for are recorded in a misses
file and skipped on restart. Safe to kill any time.

Writes: markets upserts (category left NULL — COALESCE in upsert preserves any
existing category) + the misses file. Nothing else.

Run: python src/wallet_quality_fetch.py
"""
import json
import logging
import os
import sys
from datetime import datetime, timezone

import db
from data_api import load_config, ApiError
from gamma_api import GammaApi

log = logging.getLogger("wq_fetch")


def missing_condition_ids(conn, cfg: dict) -> list:
    """Condition_ids traded by cohort-B wallets pre-cutoff with no markets row,
    ordered by descending total cohort stake."""
    cutoff = int(datetime.fromisoformat(
        cfg["analysis"]["window_end_utc"].replace("Z", "+00:00")).timestamp())
    wset = sorted(db.get_cohort_wallets(conn, cfg["paper"]["watchlist_cohort"]))
    ph = ",".join("?" * len(wset))
    rows = conn.execute(
        f"""SELECT t.condition_id, SUM(t.size_usd) usd
            FROM trades t
            WHERE t.wallet IN ({ph}) AND t.timestamp < ?
              AND t.condition_id IS NOT NULL AND t.condition_id != ''
              AND NOT EXISTS (SELECT 1 FROM markets m WHERE m.condition_id = t.condition_id)
            GROUP BY t.condition_id ORDER BY usd DESC""",
        [*wset, cutoff]).fetchall()
    return [r["condition_id"] for r in rows]


def bulk_upsert_markets(conn, rows: list) -> None:
    """Batched market upsert with a single commit (upsert_market commits per
    row — too much writer contention against the live paper loop)."""
    conn.executemany(
        """INSERT INTO markets (condition_id, question, slug, category, end_date, closed,
                                outcome_prices, clob_token_ids, volume, liquidity, event_slug)
           VALUES (:condition_id, :question, :slug, :category, :end_date, :closed,
                   :outcome_prices, :clob_token_ids, :volume, :liquidity, :event_slug)
           ON CONFLICT(condition_id) DO UPDATE SET
               question=excluded.question, slug=excluded.slug,
               category=COALESCE(excluded.category, markets.category),
               end_date=excluded.end_date, closed=excluded.closed,
               outcome_prices=excluded.outcome_prices, clob_token_ids=excluded.clob_token_ids,
               volume=excluded.volume, liquidity=excluded.liquidity,
               event_slug=COALESCE(excluded.event_slug, markets.event_slug)""",
        rows)
    conn.commit()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cfg = load_config()
    fcfg = cfg["analysis"]["wallet_quality"]["fetch"]
    misses_path = os.path.join(db.REPO_ROOT, *fcfg["misses_file"].split("/"))

    conn = db.connect()
    todo = missing_condition_ids(conn, cfg)
    misses: set = set()
    if os.path.exists(misses_path):
        with open(misses_path, encoding="utf-8") as f:
            misses = set(json.load(f))
    todo = [c for c in todo if c not in misses]
    log.info("missing markets to fetch: %d (%d known misses skipped)", len(todo), len(misses))

    gamma = GammaApi()
    batch_size = int(fcfg["batch_size"])
    pending: list = []
    fetched = failed = 0
    new_misses: list = []

    def flush() -> None:
        nonlocal pending
        if pending:
            bulk_upsert_markets(conn, pending)
            pending = []

    for i in range(0, len(todo), batch_size):
        chunk = todo[i:i + batch_size]
        got: dict = {}
        try:
            # DISCREPANCY note (gamma_api.py header): /markets hides closed
            # markets unless closed=true. Most of these are old -> closed
            # first, then one retry for the remainder with no closed param.
            for m in gamma.get_markets(condition_ids=chunk, closed=True, limit=len(chunk)):
                got[m.get("condition_id")] = m
            left = [c for c in chunk if c not in got]
            if left:
                for m in gamma.get_markets(condition_ids=left, limit=len(left)):
                    got[m.get("condition_id")] = m
        except ApiError as e:
            log.warning("batch at offset %d failed, skipping: %s", i, e)
            failed += len(chunk)
            continue
        for cid in chunk:
            if cid in got:
                pending.append(db.market_row_from_gamma(got[cid]))
                fetched += 1
            else:
                new_misses.append(cid)
        if len(pending) >= int(fcfg["commit_every_markets"]):
            flush()
        if (i // batch_size) % 100 == 0:
            log.info("progress %d/%d ids | fetched %d | misses %d | failed %d",
                     i + len(chunk), len(todo), fetched, len(new_misses), failed)
            # persist misses as we go so restarts never refetch them
            with open(misses_path, "w", encoding="utf-8") as f:
                json.dump(sorted(misses | set(new_misses)), f)
    flush()
    with open(misses_path, "w", encoding="utf-8") as f:
        json.dump(sorted(misses | set(new_misses)), f)
    log.info("DONE: fetched %d, misses %d, failed-batch ids %d (rerun to retry those)",
             fetched, len(new_misses), failed)


if __name__ == "__main__":
    main()
