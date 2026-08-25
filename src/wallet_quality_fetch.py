"""Fetch/refresh resolution metadata for markets traded by cohort-B wallets
(wallet-quality analysis prerequisite, 2026-07-07; extended 2026-08-17 for the
pre-registered persistence checkpoint).

Only signal/vetting markets were ever fetched, so per-wallet PnL computed on
the existing markets table would be selection-biased toward consensus-relevant
markets. This pulls the rest, ordered by descending cohort stake so partial
completion still maximizes stake coverage. Two categories of work, unioned
into one stake-ordered queue:
  MISSING  — cohort-B trades any time up to
             analysis.persistence_checkpoint.window_end_utc with no markets
             row at all (supersedes the original analysis.window_end_utc
             scope, which is an earlier, smaller cutoff).
  REFRESH  — cohort-B trades since analysis.persistence_checkpoint
             .forward_start_utc whose markets row IS present but still looks
             unresolved (closed IS NULL/0 or empty outcome_prices) — these
             may have resolved since first fetch and need re-pulling so the
             persistence checkpoint's forward-window positions aren't
             misclassified UNRESOLVED.

Resumable: the markets table itself is the checkpoint for MISSING rows
(shrinks on restart); REFRESH rows re-queue every run until they resolve
(cheap — restricted to the forward window) or land in the misses file.
condition_ids Gamma returns nothing for are recorded in a misses file and
skipped on restart. Safe to kill any time.

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


def _ts(iso: str) -> int:
    """Parse a config ISO-8601 UTC timestamp ('...Z') to epoch seconds."""
    return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp())


def missing_condition_ids(conn, cfg: dict) -> list:
    """Condition_ids to fetch or refresh, ordered by descending combined
    cohort stake: MISSING (no markets row) up to the persistence-checkpoint
    window end, unioned with REFRESH (present but unresolved-looking) since
    the forward-window start. See module docstring."""
    pc = cfg["analysis"]["persistence_checkpoint"]
    window_end = _ts(pc["window_end_utc"])
    forward_start = _ts(pc["forward_start_utc"])
    wset = sorted(db.get_cohort_wallets(conn, cfg["paper"]["watchlist_cohort"]))
    ph = ",".join("?" * len(wset))

    missing = conn.execute(
        f"""SELECT t.condition_id, SUM(t.size_usd) usd
            FROM trades t
            WHERE t.wallet IN ({ph}) AND t.timestamp < ?
              AND t.condition_id IS NOT NULL AND t.condition_id != ''
              AND NOT EXISTS (SELECT 1 FROM markets m WHERE m.condition_id = t.condition_id)
            GROUP BY t.condition_id""",
        [*wset, window_end]).fetchall()
    refresh = conn.execute(
        f"""SELECT t.condition_id, SUM(t.size_usd) usd
            FROM trades t
            JOIN markets m ON m.condition_id = t.condition_id
            WHERE t.wallet IN ({ph}) AND t.timestamp >= ? AND t.timestamp < ?
              AND (m.closed IS NULL OR m.closed = 0 OR m.outcome_prices IS NULL
                   OR m.outcome_prices = '' OR m.outcome_prices = '[]')
            GROUP BY t.condition_id""",
        [*wset, forward_start, window_end]).fetchall()

    stake: dict = {}
    n_missing = n_refresh = 0
    for r in missing:
        stake[r["condition_id"]] = stake.get(r["condition_id"], 0.0) + (r["usd"] or 0.0)
        n_missing += 1
    for r in refresh:
        if r["condition_id"] not in stake:
            n_refresh += 1
        stake[r["condition_id"]] = stake.get(r["condition_id"], 0.0) + (r["usd"] or 0.0)
    log.info("queue built: %d missing + %d refresh-only = %d condition_ids (stake-ordered)",
             n_missing, n_refresh, len(stake))
    return [cid for cid, _ in sorted(stake.items(), key=lambda kv: -kv[1])]


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
