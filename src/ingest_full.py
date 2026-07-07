"""Offline deep-history ingestion for the cohort-B watchlist (2026-07-06).

The /trades endpoint hard-caps offset at 3000 (max ~4000 trades/wallet), which
truncated active wallets' history to recent weeks and made pre-April sports
data unusable (see reports/category_analysis.md §5). The UNDOCUMENTED `end`
param (verified live 2026-07-06, see data_api.get_trades) filters to
timestamp < end and composes with offset, so full history is reachable by
walking windows backwards: end = oldest_seen + 1 after each window.

Safety with the live paper loop (running while this ingests):
- only trades older than now - analysis.full_pull.recent_guard_seconds are
  inserted (the live detector reads at most the last 24h of trades);
- same (tx_hash, condition_id, wallet) dedupe as every other inserter;
- short per-page transactions on a WAL database with 15s busy timeout.

Resumable: progress checkpoints per wallet in full_history_progress (created
here, read by nothing live). Kill and rerun freely; wallets are processed
least-active-first so the long tail completes early and only whale wallets
remain at the end.

Run: python src/ingest_full.py
"""
import logging
import sys
import time
from datetime import datetime, timezone

import db
from data_api import ApiError, DataApi, load_config

log = logging.getLogger("ingest_full")

PROGRESS_SCHEMA = """
CREATE TABLE IF NOT EXISTS full_history_progress (
    wallet      TEXT PRIMARY KEY,
    next_end    INTEGER,            -- walk cursor: fetch trades with ts < this
    pages_done  INTEGER DEFAULT 0,
    trades_added INTEGER DEFAULT 0,
    done        INTEGER DEFAULT 0,  -- 1 = reached history_start or wallet start
    truncated   INTEGER DEFAULT 0,  -- 1 = stopped by max_pages_per_wallet
    updated_at  INTEGER
);
"""


def pull_wallet(api: DataApi, conn, wallet: str, fp_cfg: dict,
                history_start: int, recent_cutoff: int) -> tuple:
    """Walk one wallet's history backwards to history_start. Returns
    (done, truncated, pages, added) with progress checkpointed per window."""
    row = conn.execute("SELECT * FROM full_history_progress WHERE wallet = ?",
                       (wallet,)).fetchone()
    if row and row["done"]:
        return True, bool(row["truncated"]), row["pages_done"], row["trades_added"]
    next_end = row["next_end"] if row else recent_cutoff
    pages = row["pages_done"] if row else 0
    added = row["trades_added"] if row else 0
    page_size = fp_cfg["page_size"]
    offset_max = fp_cfg["window_offset_max"]
    max_pages = fp_cfg["max_pages_per_wallet"]

    done = truncated = False
    while not done and not truncated:
        # one end-window: offset 0..offset_max
        oldest = None
        window_exhausted = False
        for offset in range(0, offset_max + 1, page_size):
            try:
                page = api.get_trades(user=wallet, limit=page_size, offset=offset,
                                      end=next_end)
            except ApiError as e:
                log.warning("%s: page failed (%s) — checkpointing and moving on", wallet[:10], e)
                conn.execute(
                    """INSERT OR REPLACE INTO full_history_progress
                       (wallet, next_end, pages_done, trades_added, done, truncated, updated_at)
                       VALUES (?,?,?,?,0,0,?)""",
                    (wallet, next_end, pages, added, int(time.time())))
                conn.commit()
                return False, False, pages, added
            pages += 1
            rows = []
            for t in page:
                r = db.trade_row_from_api(t)
                if r and r["timestamp"] < recent_cutoff and r["timestamp"] >= history_start \
                        and r["outcome_index"] >= 0 and t.get("side") in ("BUY", "SELL"):
                    rows.append(r)
            if rows:
                added += db.insert_trades(conn, rows)
            if page:
                oldest = int(page[-1]["timestamp"])
            if len(page) < page_size:
                window_exhausted = True
                break
            if pages >= max_pages:
                truncated = True
                break
        if oldest is None or window_exhausted and (oldest is None or len(page) == 0):
            done = True          # nothing at all below next_end -> wallet start reached
        elif oldest < history_start:
            done = True          # walked past the analysis window
        elif window_exhausted:
            done = True          # fewer than a full window remained; all fetched
        elif oldest + 1 == next_end:
            # a full window of same-second trades (bot burst): +1 would refetch
            # it forever. Step past the tied second; the dropped remainder of
            # that second is logged, not silently lost.
            log.warning("%s: >%d trades share ts=%d — skipping past that second",
                        wallet[:10], offset_max + page_size, oldest)
            next_end = oldest
        else:
            next_end = oldest + 1   # +1 re-fetches ties at the boundary; dedupe eats them
        conn.execute(
            """INSERT OR REPLACE INTO full_history_progress
               (wallet, next_end, pages_done, trades_added, done, truncated, updated_at)
               VALUES (?,?,?,?,?,?,?)""",
            (wallet, next_end, pages, added, int(done or truncated), int(truncated),
             int(time.time())))
        conn.commit()
    return done, truncated, pages, added


def main() -> None:
    """Pull deep history for every cohort wallet, least-active first."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cfg = load_config()
    fp_cfg = cfg["analysis"]["full_pull"]
    history_start = int(datetime.fromisoformat(
        fp_cfg["history_start_utc"].replace("Z", "+00:00")).timestamp())
    recent_cutoff = int(time.time()) - fp_cfg["recent_guard_seconds"]
    conn = db.connect()
    conn.executescript(PROGRESS_SCHEMA)
    api = DataApi()

    cohort = cfg["paper"]["watchlist_cohort"]
    wallets = sorted(db.get_cohort_wallets(conn, cohort))
    counts = {r["wallet"]: r["n"] for r in conn.execute(
        "SELECT wallet, COUNT(*) n FROM trades GROUP BY wallet")}
    wallets.sort(key=lambda w: counts.get(w, 0))   # least active first
    log.info("deep pull: %d cohort-%s wallets, window %s -> now-24h",
             len(wallets), cohort, fp_cfg["history_start_utc"])

    t0 = time.time()
    n_done = n_trunc = n_fail = 0
    total_added = 0
    for i, w in enumerate(wallets, 1):
        done, truncated, pages, added = pull_wallet(
            api, conn, w, fp_cfg, history_start, recent_cutoff)
        total_added += added
        n_done += done and not truncated
        n_trunc += truncated
        n_fail += not done and not truncated
        log.info("[%d/%d] %s: done=%s trunc=%s pages=%d added=%d (total added %d, %.0fs)",
                 i, len(wallets), w[:10], done, truncated, pages, added,
                 total_added, time.time() - t0)
    log.info("PULL COMPLETE: %d full, %d truncated-by-budget, %d failed/partial; "
             "%d trades added in %.0fs", n_done, n_trunc, n_fail, total_added,
             time.time() - t0)
    log.info("rerun this script to retry failed/partial wallets (resumes from checkpoints)")


if __name__ == "__main__":
    main()
