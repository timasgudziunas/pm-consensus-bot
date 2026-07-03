"""Phase 2: historical trade ingestion for the selected watchlist.

Resumable: per-wallet progress lives in ingest_progress; kill and restart at
any time and it picks up where it left off. Never re-fetches finished wallets.

Run: python src/ingest.py
"""
import json
import logging
import time
from collections import Counter
from datetime import datetime, timezone

import db
import signals
from clob_api import ClobApi
from data_api import ApiError, DataApi, load_config
from gamma_api import GammaApi

log = logging.getLogger(__name__)

SECONDS_PER_MONTH = 30.44 * 86400


def lookback_cutoff() -> int:
    """Unix timestamp of the start of the lookback window."""
    months = load_config()["lookback_months"]
    return int(time.time() - months * SECONDS_PER_MONTH)


def ingest_wallet_trades(api: DataApi, conn, wallet: str, username: str,
                         index: int, total: int) -> None:
    """Pull a wallet's trade history back to the lookback cutoff.

    API DISCREPANCY (verified 2026-07-02, contra OVERVIEW.md): /trades caps
    limit at 1000 (silently) and offset at 3000 (HTTP 400 beyond), and ignores
    every time-filter param tried (before/endTs/to/maxTimestamp). Deepest
    reachable history = the 4000 most recent trades per wallet. For hyperactive
    wallets that is less than the lookback window — we take what exists and
    flag the truncation.

    Offset-based resume: if new trades arrive between runs the offsets shift
    slightly; dedupe absorbs the overlap and the miss risk is a few trades at
    a page boundary — acceptable for a one-shot historical pull."""
    cfg = load_config()["ingest"]
    page_size = cfg["page_size"]
    max_offset = cfg["max_offset"]
    cutoff = lookback_cutoff()
    offset, done = db.get_ingest_progress(conn, wallet)
    if done:
        log.info("[%d/%d] @%s — already ingested, skipping", index, total, username)
        return

    inserted_total = 0
    truncated = False
    while True:
        if offset > max_offset:
            truncated = True
            break
        try:
            page = api.get_trades(user=wallet, limit=page_size, offset=offset)
        except ApiError as e:
            log.warning("[%d/%d] @%s offset=%d failed (%s) — will resume here next run",
                        index, total, username, offset, e)
            db.set_ingest_progress(conn, wallet, offset, done=False)
            return
        rows = [r for r in (db.trade_row_from_api(t) for t in page) if r]
        in_window = [r for r in rows if r["timestamp"] >= cutoff]
        if in_window:
            inserted_total += db.insert_trades(conn, in_window)
        offset += len(page)
        db.set_ingest_progress(conn, wallet, offset, done=False)
        # trades come newest-first: stop once the page dips below the cutoff
        if len(page) < page_size or (rows and min(r["timestamp"] for r in rows) < cutoff):
            break
    db.set_ingest_progress(conn, wallet, offset, done=True)
    if truncated:
        log.warning("[%d/%d] @%s — hit the 4000-trade API cap; history TRUNCATED "
                    "(coverage shorter than the lookback window)", index, total, username)
    log.info("[%d/%d] @%s — %d trades ingested", index, total, username, inserted_total)


def candidate_condition_ids(conn) -> set:
    """Markets that can produce a signal under the LOOSEST sweep cell.

    Runs the shared detector with min N, max window, min floor from the sweep
    grid; every sweep cell's signals are a subset of these markets, so
    metadata/category/price-history fetching can be restricted to them
    (32k+ markets touched vs. the small set that can actually signal)."""
    sweep = load_config()["sweep"]
    params = {
        "n_traders": min(sweep["n_traders"]),
        "window_seconds": int(max(sweep["window_hours"]) * 3600),
        "size_floor_usd": min(sweep["size_floor_usd"]),
    }
    floor = params["size_floor_usd"]
    trades = [dict(r) for r in conn.execute(
        """SELECT tx_hash, condition_id, wallet, side, outcome_index, size_usd, price, timestamp
           FROM trades WHERE side = 'BUY' AND size_usd >= ? AND outcome_index >= 0""", (floor,))]
    found = signals.detect_signals(trades, params)
    return {s["condition_id"] for s in found}


def ingest_markets(conn, candidates: set) -> None:
    """Fetch Gamma metadata for signal-candidate markets; resolve categories."""
    gamma = GammaApi()
    cfg = load_config()["ingest"]
    have = {r["condition_id"] for r in conn.execute(
        "SELECT condition_id FROM markets WHERE clob_token_ids IS NOT NULL")}
    cond_ids = sorted(candidates - have)
    log.info("fetching metadata for %d new candidate markets ...", len(cond_ids))

    batch = cfg["gamma_batch_size"]
    for i in range(0, len(cond_ids), batch):
        chunk = cond_ids[i:i + batch]
        # two passes: Gamma hides closed markets unless closed=true (see module docstring)
        try:
            markets = gamma.get_markets(condition_ids=chunk, limit=batch)
            markets += gamma.get_markets(condition_ids=chunk, limit=batch, closed=True)
        except ApiError as e:
            log.warning("gamma batch failed (%s); retrying one by one", e)
            markets = []
            for cid in chunk:
                for closed in (None, True):
                    try:
                        markets.extend(gamma.get_markets(condition_ids=[cid], closed=closed))
                    except ApiError as e2:
                        log.warning("gamma lookup failed for %s: %s", cid, e2)
        for m in markets:
            row = db.market_row_from_gamma(m)
            slug = row["event_slug"]
            if slug:
                cat = db.get_event_category(conn, slug)
                if cat is None:
                    cat, labels = gamma.resolve_category(slug)
                    db.set_event_category(conn, slug, cat, labels)
                row["category"] = cat or None
            db.upsert_market(conn, row)
        if (i // batch) % 10 == 0:
            log.info("markets %d/%d", min(i + batch, len(cond_ids)), len(cond_ids))

    # discover.py caches sample-market metadata with category left NULL — the
    # metadata-skip above would otherwise leave those candidates UNMAPPED forever
    uncat = [r for r in conn.execute(
        """SELECT condition_id, event_slug FROM markets
           WHERE category IS NULL AND event_slug IS NOT NULL AND clob_token_ids IS NOT NULL""")
        if r["condition_id"] in candidates]
    if uncat:
        log.info("backfilling categories for %d candidate markets ...", len(uncat))
        for r in uncat:
            cat = db.get_event_category(conn, r["event_slug"])
            if cat is None:
                cat, labels = gamma.resolve_category(r["event_slug"])
                db.set_event_category(conn, r["event_slug"], cat, labels)
            if cat:
                conn.execute("UPDATE markets SET category = ? WHERE condition_id = ?",
                             (cat, r["condition_id"]))
        conn.commit()


def ingest_price_history(conn, candidates: set) -> None:
    """Fetch hourly price history for both outcome tokens of candidate markets.

    API DISCREPANCY: /prices-history rejects intervals somewhere above 15 days
    at fidelity=60 ("interval is too long", HTTP 400) — hence the 14-day chunk
    size in config. Each market is only scanned over [first watchlist trade,
    market end] — fetching the whole lookback for a market that lived 2 days
    would waste dozens of requests. Skips ranges already present (resumable)."""
    clob = ClobApi()
    cfg = load_config()["ingest"]
    fidelity = cfg["price_history_fidelity_minutes"]
    chunk_secs = cfg["price_history_chunk_days"] * 86400
    start_all = lookback_cutoff()
    now = int(time.time())
    buffer = 86400  # a day of slack on both ends of the market's trade range

    trade_range = {r["condition_id"]: (r["mn"], r["mx"]) for r in conn.execute(
        "SELECT condition_id, MIN(timestamp) mn, MAX(timestamp) mx FROM trades GROUP BY condition_id")}
    markets = [m for m in conn.execute(
        "SELECT condition_id, clob_token_ids, closed, end_date FROM markets WHERE clob_token_ids IS NOT NULL"
    ).fetchall() if m["condition_id"] in candidates]
    log.info("price history for %d candidate markets (2 tokens each) ...", len(markets))

    for i, m in enumerate(markets, 1):
        try:
            token_ids = json.loads(m["clob_token_ids"])
        except (TypeError, ValueError):
            continue
        mn, mx = trade_range.get(m["condition_id"], (None, None))
        if mn is None:
            continue
        end_ts = None
        if m["end_date"]:
            try:
                end_ts = int(datetime.fromisoformat(m["end_date"].replace("Z", "+00:00")).timestamp())
            except ValueError:
                pass
        range_start = max(start_all, mn - buffer)
        range_end = min(now, (end_ts + buffer) if end_ts else now)
        # exits can land between last trade and resolution; keep through range_end
        if range_end <= range_start:
            range_end = min(now, mx + buffer)
        for token in token_ids:
            last = conn.execute(
                "SELECT MAX(timestamp) mx FROM price_history WHERE token_id = ?", (token,)
            ).fetchone()["mx"]
            ts = max(range_start, (last + 1) if last else range_start)
            while ts < range_end:
                end = min(ts + chunk_secs, range_end)
                try:
                    pts = clob.get_price_history(token, ts, end, fidelity=fidelity)
                except ApiError as e:
                    log.debug("price history failed token=%s… (%s)", token[:16], e)
                    pts = []
                if pts:
                    db.insert_price_history(conn, token, pts)
                ts = end
        if i % 50 == 0:
            log.info("price history %d/%d markets", i, len(markets))


def summarize(conn) -> None:
    """Print the ingestion summary and sanity-check warnings."""
    n_trades = conn.execute("SELECT COUNT(*) c FROM trades").fetchone()["c"]
    n_markets = conn.execute("SELECT COUNT(*) c FROM markets").fetchone()["c"]
    resolved = conn.execute("SELECT COUNT(*) c FROM markets WHERE closed = 1").fetchone()["c"]
    span = conn.execute("SELECT MIN(timestamp) a, MAX(timestamp) b FROM trades").fetchone()
    cats = Counter(r["category"] or "UNMAPPED" for r in conn.execute("SELECT category FROM markets"))

    def d(ts):
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d") if ts else "?"

    # wallets whose oldest reachable trade is well inside the lookback window:
    # their history hit the 4000-trade API cap and is truncated
    trunc = conn.execute(
        """SELECT COUNT(*) c FROM (SELECT wallet, MIN(timestamp) mn FROM trades GROUP BY wallet)
           WHERE mn > ?""", (lookback_cutoff() + 7 * 86400,)).fetchone()["c"]

    print("\n===== INGESTION SUMMARY =====")
    print(f"trades:           {n_trades:,}")
    print(f"unique markets:   {n_markets:,} ({resolved} resolved, {n_markets - resolved} open)")
    print(f"date range:       {d(span['a'])} -> {d(span['b'])}")
    print(f"truncated wallets: {trunc} (history shorter than lookback due to 4000-trade API cap)")
    print("category distribution:", dict(cats.most_common()))

    orphan = conn.execute(
        """SELECT COUNT(DISTINCT t.condition_id) c FROM trades t
           LEFT JOIN markets m ON m.condition_id = t.condition_id
           WHERE m.condition_id IS NULL""").fetchone()["c"]
    no_price = conn.execute(
        """SELECT COUNT(*) c FROM markets m WHERE NOT EXISTS (
               SELECT 1 FROM price_history p
               WHERE p.token_id IN (SELECT value FROM json_each(m.clob_token_ids)))""").fetchone()["c"]
    if orphan:
        log.warning("%d markets have trades but no Gamma metadata — excluded from backtest", orphan)
    if no_price:
        log.warning("%d markets have no price history — their signals will be skipped", no_price)


def main() -> None:
    """Ingest trades, then market metadata, then price history; print summary."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    conn = db.connect()
    api = DataApi()
    wallets = db.get_selected_wallets(conn)
    if not wallets:
        raise SystemExit("no selected wallets — run discover.py first")
    log.info("ingesting %d wallets, lookback to %s",
             len(wallets), datetime.fromtimestamp(lookback_cutoff(), tz=timezone.utc).date())
    for i, w in enumerate(wallets, 1):
        ingest_wallet_trades(api, conn, w["address"], w["username"] or w["address"][:10], i, len(wallets))
    candidates = candidate_condition_ids(conn)
    log.info("%d signal-candidate markets (loosest sweep cell) out of %d touched",
             len(candidates),
             conn.execute("SELECT COUNT(DISTINCT condition_id) c FROM trades").fetchone()["c"])
    ingest_markets(conn, candidates)
    ingest_price_history(conn, candidates)
    summarize(conn)


if __name__ == "__main__":
    main()
