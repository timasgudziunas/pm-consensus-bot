"""SQLite schema and helpers. Single DB file in data/, WAL mode for concurrent
readers/writers (paper.py and ingest.py run at the same time)."""
import json
import logging
import os
import sqlite3
import time
from typing import Any, Iterable, Optional

log = logging.getLogger(__name__)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(REPO_ROOT, "data", "copybot.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS wallets (
    address         TEXT PRIMARY KEY,
    username        TEXT,
    category        TEXT,       -- comma-separated if discovered in several
    pnl_month       REAL,
    pnl_all         REAL,
    markets_traded  INTEGER,
    total_trades    INTEGER,
    is_mm           INTEGER DEFAULT 0,
    concentrated    INTEGER DEFAULT 0,
    selected        INTEGER DEFAULT 0,
    discovered_at   INTEGER,
    -- cohort-selection extension (2026-07-03): which "efficiency" definitions
    -- picked this wallet, plus the per-cohort ranking metrics
    cohorts         TEXT,       -- comma-separated subset of A,B,C (union members only)
    vol_month       REAL,       -- leaderboard MONTH volume
    pnl_per_vol     REAL,       -- cohort B metric: pnl_month / vol_month
    entry_edge      REAL,       -- cohort C metric: stake-weighted (payout - entry) over resolved buys
    resolved_buys   INTEGER,    -- sample size behind entry_edge
    consistency     REAL        -- tie-breaker: fraction of sampled markets with positive PnL proxy
);

CREATE TABLE IF NOT EXISTS trades (
    tx_hash        TEXT,
    condition_id   TEXT,
    wallet         TEXT,
    side           TEXT,
    outcome_index  INTEGER,
    size_usd       REAL,       -- API 'size' is SHARES; usd = size * price (verified Phase 0)
    price          REAL,
    timestamp      INTEGER,
    ingested_at    INTEGER,
    PRIMARY KEY (tx_hash, condition_id, wallet)
);
CREATE INDEX IF NOT EXISTS idx_trades_cond   ON trades (condition_id, outcome_index, timestamp);
CREATE INDEX IF NOT EXISTS idx_trades_wallet ON trades (wallet, timestamp);
CREATE INDEX IF NOT EXISTS idx_trades_ts     ON trades (timestamp);

CREATE TABLE IF NOT EXISTS markets (
    condition_id    TEXT PRIMARY KEY,
    question        TEXT,
    slug            TEXT,
    category        TEXT,
    end_date        TEXT,
    closed          INTEGER,
    outcome_prices  TEXT,      -- JSON string, e.g. '["1","0"]' when resolved
    clob_token_ids  TEXT,      -- JSON string list, index = outcomeIndex
    volume          REAL,
    liquidity       REAL,
    event_slug      TEXT
);

CREATE TABLE IF NOT EXISTS price_history (
    token_id   TEXT,
    timestamp  INTEGER,
    price      REAL,
    PRIMARY KEY (token_id, timestamp)
);

CREATE TABLE IF NOT EXISTS signals (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    condition_id   TEXT,
    outcome_index  INTEGER,
    side           TEXT,
    signal_time    INTEGER,
    n_traders      INTEGER,
    wallets        TEXT,       -- JSON list of contributing wallets
    entry_price    REAL,
    exit_price     REAL,
    exit_time      INTEGER,
    exit_type      TEXT,
    pnl_20         REAL,
    pnl_50         REAL,
    pnl_100        REAL,
    resolved       INTEGER,
    category       TEXT,
    -- sweep-cell identifiers (extension to PLAN.md schema so one table holds
    -- results for every grid cell, split, and wallet cohort):
    window_hours   REAL,
    size_floor     REAL,
    split          TEXT,
    cohort         TEXT
);
CREATE INDEX IF NOT EXISTS idx_signals_cell ON signals (cohort, n_traders, window_hours, size_floor, exit_type, split);

CREATE TABLE IF NOT EXISTS paper_trades (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    condition_id       TEXT,
    outcome_index      INTEGER,
    side               TEXT,
    signal_time        INTEGER,
    n_traders          INTEGER,
    wallets            TEXT,
    entry_price        REAL,
    exit_price         REAL,
    exit_time          INTEGER,
    exit_type          TEXT,
    pnl_20             REAL,   -- realized PnL at position_usd (legacy name, kept for continuity)
    pnl_50             REAL,   -- unused by paper.py
    resolved           INTEGER,
    category           TEXT,
    token_id           TEXT,
    book_entry_price   REAL,
    midpoint_at_signal REAL,
    avg_trader_price   REAL,
    alpha_decay        REAL,
    status             TEXT,   -- OPEN / CLOSED / SKIPPED (book too thin) / STALE (detected too late)
    tx_hashes          TEXT,   -- JSON list of trades that formed the signal
    position_usd       REAL    -- stake at open; config changes must not reprice old rows
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_paper_dedupe ON paper_trades (condition_id, outcome_index);

-- resumable ingestion bookkeeping (PLAN.md: per-wallet high-water mark)
CREATE TABLE IF NOT EXISTS ingest_progress (
    wallet      TEXT PRIMARY KEY,
    next_offset INTEGER DEFAULT 0,
    done        INTEGER DEFAULT 0,
    updated_at  INTEGER
);

-- cache: event slug -> category (Gamma /events lookups are expensive to repeat)
CREATE TABLE IF NOT EXISTS event_categories (
    slug     TEXT PRIMARY KEY,
    category TEXT,
    tags     TEXT
);

-- per-cell sweep metrics, written by backtest.py, read by report.py
CREATE TABLE IF NOT EXISTS backtest_results (
    cohort             TEXT,   -- wallet set the sweep ran over: A / B / C / union
    n_traders          INTEGER,
    window_hours       REAL,
    size_floor         REAL,
    exit_strategy      TEXT,
    position_size      REAL,
    split              TEXT,
    signal_count       INTEGER,
    resolved_count     INTEGER,
    unresolved_count   INTEGER,
    win_rate           REAL,
    avg_pnl            REAL,
    total_pnl          REAL,
    return_on_capital  REAL,
    max_drawdown       REAL,
    category_breakdown TEXT,   -- JSON {category: {signals, win_rate, total_pnl}}
    PRIMARY KEY (cohort, n_traders, window_hours, size_floor, exit_strategy, position_size, split)
);
"""


def _migrate(conn: sqlite3.Connection) -> None:
    """Additive migrations for DBs created before the cohort build (2026-07-03)."""
    def cols(table: str) -> set:
        return {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}

    for col, decl in [("cohorts", "TEXT"), ("vol_month", "REAL"), ("pnl_per_vol", "REAL"),
                      ("entry_edge", "REAL"), ("resolved_buys", "INTEGER"), ("consistency", "REAL")]:
        if col not in cols("wallets"):
            conn.execute(f"ALTER TABLE wallets ADD COLUMN {col} {decl}")
    sig_cols = cols("signals")
    for col, decl in [("pnl_100", "REAL"), ("cohort", "TEXT")]:
        if col not in sig_cols:
            conn.execute(f"ALTER TABLE signals ADD COLUMN {col} {decl}")
    if "cohort" not in sig_cols:
        conn.execute("DROP INDEX IF EXISTS idx_signals_cell")  # recreated by SCHEMA with cohort
    if "position_usd" not in cols("paper_trades"):
        conn.execute("ALTER TABLE paper_trades ADD COLUMN position_usd REAL")
        # every row opened before this column existed was a $20 position
        # (config paper.position_size_usd until 2026-07-03) — frozen history
        conn.execute("UPDATE paper_trades SET position_usd = 20")
    if "cohort" not in cols("backtest_results"):
        # cohort belongs in the PK, which SQLite can't ALTER; contents are fully
        # regenerated by every backtest.py run, so drop and let SCHEMA recreate
        conn.execute("DROP TABLE backtest_results")
    conn.commit()


def connect(db_path: str = DB_PATH) -> sqlite3.Connection:
    """Open the DB (creating schema if needed) with WAL + generous busy timeout."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=15000")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.executescript(SCHEMA)
    _migrate(conn)
    conn.executescript(SCHEMA)  # recreate anything _migrate dropped (idempotent)
    conn.commit()
    return conn


def insert_trades(conn: sqlite3.Connection, rows: Iterable[dict]) -> int:
    """Bulk-insert trade dicts, deduping on (tx_hash, condition_id, wallet).

    Returns the number of rows actually inserted."""
    now = int(time.time())
    cur = conn.executemany(
        """INSERT OR IGNORE INTO trades
           (tx_hash, condition_id, wallet, side, outcome_index, size_usd, price, timestamp, ingested_at)
           VALUES (:tx_hash, :condition_id, :wallet, :side, :outcome_index, :size_usd, :price, :timestamp, %d)"""
        % now,
        list(rows),
    )
    conn.commit()
    return cur.rowcount


def trade_row_from_api(t: dict) -> Optional[dict]:
    """Normalize a Data-API trade dict (already snake_cased by the client) to a trades row.

    Returns None if required fields are missing. size_usd = shares * price —
    the API 'size' field is in shares, not USD (verified against /activity usdcSize)."""
    try:
        size = float(t["size"])
        price = float(t["price"])
        return {
            "tx_hash": t["transaction_hash"],
            "condition_id": t["condition_id"],
            "wallet": t["proxy_wallet"],
            "side": t["side"],
            "outcome_index": int(t.get("outcome_index", -1)),
            "size_usd": size * price,
            "price": price,
            "timestamp": int(t["timestamp"]),
        }
    except (KeyError, TypeError, ValueError):
        return None


def upsert_wallet(conn: sqlite3.Connection, w: dict) -> None:
    """Insert or replace a wallet row (cohort metric fields optional)."""
    row = {"cohorts": None, "vol_month": None, "pnl_per_vol": None,
           "entry_edge": None, "resolved_buys": None, "consistency": None, **w}
    conn.execute(
        """INSERT INTO wallets (address, username, category, pnl_month, pnl_all,
                                markets_traded, total_trades, is_mm, concentrated, selected, discovered_at,
                                cohorts, vol_month, pnl_per_vol, entry_edge, resolved_buys, consistency)
           VALUES (:address, :username, :category, :pnl_month, :pnl_all,
                   :markets_traded, :total_trades, :is_mm, :concentrated, :selected, :discovered_at,
                   :cohorts, :vol_month, :pnl_per_vol, :entry_edge, :resolved_buys, :consistency)
           ON CONFLICT(address) DO UPDATE SET
               username=excluded.username, category=excluded.category,
               pnl_month=excluded.pnl_month, pnl_all=excluded.pnl_all,
               markets_traded=excluded.markets_traded, total_trades=excluded.total_trades,
               is_mm=excluded.is_mm, concentrated=excluded.concentrated,
               selected=excluded.selected, discovered_at=excluded.discovered_at,
               cohorts=excluded.cohorts, vol_month=excluded.vol_month,
               pnl_per_vol=excluded.pnl_per_vol, entry_edge=excluded.entry_edge,
               resolved_buys=excluded.resolved_buys, consistency=excluded.consistency""",
        row,
    )
    conn.commit()


def upsert_market(conn: sqlite3.Connection, m: dict) -> None:
    """Insert or replace a market row keyed by condition_id."""
    conn.execute(
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
        m,
    )
    conn.commit()


def market_row_from_gamma(m: dict, category: Optional[str] = None) -> dict:
    """Normalize a Gamma market dict (snake_cased) to a markets row."""
    events = m.get("events") or []
    event_slug = events[0].get("slug") if events and isinstance(events[0], dict) else None

    def _num(v: Any) -> Optional[float]:
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    return {
        "condition_id": m.get("condition_id"),
        "question": m.get("question"),
        "slug": m.get("slug"),
        "category": category,
        "end_date": m.get("end_date"),
        "closed": 1 if m.get("closed") else 0,
        "outcome_prices": m.get("outcome_prices"),   # JSON string as returned
        "clob_token_ids": m.get("clob_token_ids"),   # JSON string as returned
        "volume": _num(m.get("volume")),
        "liquidity": _num(m.get("liquidity")),
        "event_slug": event_slug,
    }


def insert_price_history(conn: sqlite3.Connection, token_id: str, points: Iterable[tuple]) -> int:
    """Bulk-insert (timestamp, price) points for a token. Deduped by PK."""
    cur = conn.executemany(
        "INSERT OR IGNORE INTO price_history (token_id, timestamp, price) VALUES (?, ?, ?)",
        [(token_id, int(ts), float(p)) for ts, p in points],
    )
    conn.commit()
    return cur.rowcount


def get_selected_wallets(conn: sqlite3.Connection) -> list:
    """Return wallet rows where selected = 1."""
    return conn.execute("SELECT * FROM wallets WHERE selected = 1 ORDER BY address").fetchall()


def get_cohort_wallets(conn: sqlite3.Connection, cohort: str) -> set:
    """Selected wallet addresses for a cohort tag, or all selected for 'union'."""
    if cohort == "union":
        return {r["address"] for r in get_selected_wallets(conn)}
    return {r["address"] for r in conn.execute(
        "SELECT address FROM wallets WHERE selected = 1 AND (',' || cohorts || ',') LIKE ?",
        (f"%,{cohort},%",))}


def get_ingest_progress(conn: sqlite3.Connection, wallet: str) -> tuple:
    """Return (next_offset, done) for a wallet, defaulting to (0, False)."""
    row = conn.execute("SELECT next_offset, done FROM ingest_progress WHERE wallet = ?", (wallet,)).fetchone()
    return (row["next_offset"], bool(row["done"])) if row else (0, False)


def set_ingest_progress(conn: sqlite3.Connection, wallet: str, next_offset: int, done: bool) -> None:
    """Record the ingestion high-water mark for a wallet."""
    conn.execute(
        """INSERT INTO ingest_progress (wallet, next_offset, done, updated_at)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(wallet) DO UPDATE SET
               next_offset=excluded.next_offset, done=excluded.done, updated_at=excluded.updated_at""",
        (wallet, next_offset, 1 if done else 0, int(time.time())),
    )
    conn.commit()


def get_event_category(conn: sqlite3.Connection, slug: str) -> Optional[str]:
    """Cached event-slug -> category lookup ('' means known-but-unmapped)."""
    row = conn.execute("SELECT category FROM event_categories WHERE slug = ?", (slug,)).fetchone()
    return row["category"] if row else None


def set_event_category(conn: sqlite3.Connection, slug: str, category: str, tags: list) -> None:
    """Cache an event's resolved category and raw tag labels."""
    conn.execute(
        "INSERT OR REPLACE INTO event_categories (slug, category, tags) VALUES (?, ?, ?)",
        (slug, category, json.dumps(tags)),
    )
    conn.commit()
