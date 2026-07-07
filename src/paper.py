"""Phase 5: live paper trading. Same signal engine as the backtest
(signals.detect_signals), fed by the global trades feed, fills simulated
against the real order book. No orders are ever placed.

Run: python src/paper.py   (Ctrl+C to stop; state is in SQLite, restart-safe)
"""
import json
import logging
import os
import signal as os_signal
import sys
import time
from datetime import datetime, timezone

import category_stats
import db
import signals as sig
from clob_api import ClobApi
from data_api import ApiError, DataApi, load_config
from gamma_api import GammaApi

log = logging.getLogger("paper")

LOG_FILE = os.path.join(db.REPO_ROOT, "data", "paper.log")
PID_FILE = os.path.join(db.REPO_ROOT, "data", "logs", "paper.pid")  # read by watchdog.py

_shutdown = False


def _handle_sigterm(_signum, _frame) -> None:
    global _shutdown
    _shutdown = True


def setup_logging() -> None:
    """INFO to stdout, DEBUG to data/paper.log (per CLAUDE.md logging rule)."""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    out = logging.StreamHandler(sys.stdout)
    out.setLevel(logging.INFO)
    out.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    root.addHandler(out)
    root.addHandler(fh)


def ensure_market(conn, gamma: GammaApi, condition_id: str) -> dict:
    """Return the markets row for condition_id, fetching from Gamma if missing."""
    row = conn.execute("SELECT * FROM markets WHERE condition_id = ?", (condition_id,)).fetchone()
    if row and row["clob_token_ids"]:
        return dict(row)
    markets = gamma.get_markets(condition_ids=[condition_id])
    if not markets:  # Gamma hides closed markets unless closed=true
        markets = gamma.get_markets(condition_ids=[condition_id], closed=True)
    if not markets:
        return {}
    mrow = db.market_row_from_gamma(markets[0])
    slug = mrow["event_slug"]
    if slug:
        cat = db.get_event_category(conn, slug)
        if cat is None:
            cat, labels = gamma.resolve_category(slug)
            db.set_event_category(conn, slug, cat, labels)
        mrow["category"] = cat or None
    db.upsert_market(conn, mrow)
    return mrow


# (the asset->outcome_index mapper that lived here is gone with the global
# feed: user-filtered /trades returns correct outcome_index — Phase 0 finding)


class PaperTrader:
    """Polling loop state: watchlist, dedupe sets, poll timers."""

    def __init__(self) -> None:
        self.cfg = load_config()
        self.pcfg = self.cfg["paper"]
        self.conn = db.connect()
        self.data = DataApi()
        self.gamma = GammaApi()
        self.clob = ClobApi()
        self.watchlist = db.get_cohort_wallets(self.conn, self.pcfg["watchlist_cohort"])
        if not self.watchlist:
            raise SystemExit("no wallets for cohort %r — run discover.py first"
                             % self.pcfg["watchlist_cohort"])
        self.params = {
            "n_traders": self.pcfg["default_n"],
            "window_seconds": int(self.pcfg["default_window_hours"] * 3600),
            "size_floor_usd": self.pcfg["default_size_floor"],
        }
        self.position_usd = float(self.pcfg["position_size_usd"])
        self.wallet_ring = sorted(self.watchlist)   # rotating per-wallet poll order
        self.poll_cursor = 0
        self.start_time = int(time.time())
        self.last_exit_poll = 0.0
        self.last_resolution_poll = 0.0
        self.today = datetime.now(timezone.utc).date()
        self.stats_today = {"signals": 0, "opened": 0, "closed": 0}
        log.info("paper trading started: %d watchlist wallets, params=%s, $%.0f/position",
                 len(self.watchlist), self.params, self.position_usd)

    # ---------- polling ----------

    def poll_feed(self) -> int:
        """Poll the next slice of watchlist wallets via user-filtered /trades.

        Replaces the global-feed poll (2026-07-05): the global feed is a
        platform-wide window of at most 500 trades per request and silently
        drops ~95% of watchlist activity during busy periods — verified by
        comparing per-wallet /trades against live captures. User-filtered
        /trades is complete per wallet and its outcome_index is correct
        (Phase 0), so no Gamma asset-mapping is needed here."""
        k = min(self.pcfg["wallets_per_poll"], len(self.wallet_ring))
        batch = [self.wallet_ring[(self.poll_cursor + i) % len(self.wallet_ring)] for i in range(k)]
        self.poll_cursor = (self.poll_cursor + k) % len(self.wallet_ring)
        # keep only trades recent enough to matter for the detection window
        cutoff = int(time.time()) - 2 * self.params["window_seconds"]
        rows = []
        for w in batch:
            try:
                page = self.data.get_trades(user=w, limit=self.pcfg["poll_trade_limit"])
            except ApiError as e:
                log.debug("wallet poll failed for %s: %s", w[:10], e)
                continue
            for t in page:
                row = db.trade_row_from_api(t)
                if row and row["timestamp"] >= cutoff and row["outcome_index"] >= 0 \
                        and t.get("side") in ("BUY", "SELL"):
                    rows.append(row)
        return db.insert_trades(self.conn, rows) if rows else 0

    def detect_and_open(self) -> None:
        """Run the shared detector over the recent window and open new positions."""
        now = int(time.time())
        window_start = now - self.params["window_seconds"]
        recent = [dict(r) for r in self.conn.execute(
            """SELECT tx_hash, condition_id, wallet, side, outcome_index, size_usd, price, timestamp
               FROM trades WHERE timestamp >= ?""", (window_start,))]
        max_age = self.pcfg["max_signal_age_seconds"]
        for s in sig.detect_signals(recent, self.params):
            exists = self.conn.execute(
                "SELECT 1 FROM paper_trades WHERE condition_id = ? AND outcome_index = ?",
                (s["condition_id"], s["outcome_index"])).fetchone()
            if exists:
                continue
            if now - s["signal_time"] > max_age:
                # late detection (restart backfill / ingest catch-up) — record
                # it so it never re-fires, but do not enter at today's price
                self.conn.execute(
                    """INSERT OR IGNORE INTO paper_trades
                       (condition_id, outcome_index, side, signal_time, n_traders, wallets,
                        exit_type, resolved, status, tx_hashes, position_usd)
                       VALUES (?,?,?,?,?,?,?,0,'STALE',?,?)""",
                    (s["condition_id"], s["outcome_index"], "BUY", s["signal_time"],
                     s["n_traders"], json.dumps(s["wallets"]), self.pcfg["exit_strategy"],
                     json.dumps([t["tx_hash"] for t in s["trades"]]), self.position_usd))
                self.conn.commit()
                log.info("SIGNAL on %s is %.0f min old (cap %.0f) — recorded STALE, not entered",
                         s["condition_id"][:12], (now - s["signal_time"]) / 60, max_age / 60)
                continue
            self.stats_today["signals"] += 1
            self.open_position(s)

    def open_position(self, s: dict) -> None:
        """Simulate a fill from the live book and record the paper trade."""
        market = ensure_market(self.conn, self.gamma, s["condition_id"])
        tokens = json.loads(market.get("clob_token_ids") or "[]")
        if s["outcome_index"] >= len(tokens):
            return
        token = tokens[s["outcome_index"]]
        try:
            book = self.clob.get_book(token)
            mid = self.clob.get_midpoint(token)
        except ApiError as e:
            # e.g. 404 "no orderbook" on already-resolved markets — still record
            # the signal (as SKIPPED below) so it never re-fires
            log.warning("book fetch failed for signal %s: %s", s["condition_id"][:12], e)
            book, mid = None, None
        fill = sig.simulate_book_fill(book["asks"], self.position_usd) if book else None
        status = "OPEN" if fill else "SKIPPED"
        entry = fill["avg_price"] if fill else None
        decay = (entry - s["avg_trader_price"]) if (entry and s["avg_trader_price"]) else None
        self.conn.execute(
            """INSERT OR IGNORE INTO paper_trades
               (condition_id, outcome_index, side, signal_time, n_traders, wallets,
                entry_price, exit_type, resolved, category, token_id,
                book_entry_price, midpoint_at_signal, avg_trader_price, alpha_decay,
                status, tx_hashes, position_usd)
               VALUES (?,?,?,?,?,?,?,?,0,?,?,?,?,?,?,?,?,?)""",
            (s["condition_id"], s["outcome_index"], "BUY", s["signal_time"], s["n_traders"],
             json.dumps(s["wallets"]), entry, self.pcfg["exit_strategy"],
             market.get("category"), token, entry, mid, s["avg_trader_price"], decay,
             status, json.dumps([t["tx_hash"] for t in s["trades"]]), self.position_usd))
        self.conn.commit()
        if fill:
            self.stats_today["opened"] += 1
            log.info("SIGNAL %s outcome=%d @ %.3f (traders avg %.3f, decay %+.3f) — %s",
                     (market.get("question") or s["condition_id"])[:60], s["outcome_index"],
                     entry, s["avg_trader_price"] or -1, decay or 0, market.get("category"))
        else:
            log.info("SIGNAL on %s but book too thin to fill $%.0f — recorded as SKIPPED",
                     s["condition_id"][:12], self.position_usd)

    # ---------- exits ----------

    def open_positions(self) -> list:
        return [dict(r) for r in self.conn.execute("SELECT * FROM paper_trades WHERE status = 'OPEN'")]

    def poll_copy_exits(self) -> None:
        """Refresh signal wallets' recent trades and close positions whose
        signal wallets have exited (shared compute_copy_exit logic)."""
        positions = self.open_positions()
        if not positions:
            return
        wallets = {w for p in positions for w in json.loads(p["wallets"])}
        for w in wallets:
            try:
                page = self.data.get_trades(user=w, limit=200)
            except ApiError:
                continue
            rows = []
            for t in page:
                row = db.trade_row_from_api(t)
                if row and row["timestamp"] >= self.start_time - self.params["window_seconds"]:
                    rows.append(row)
            if rows:
                db.insert_trades(self.conn, rows)

        bcfg = self.cfg["backtest"]
        for p in positions:
            relevant = [dict(r) for r in self.conn.execute(
                """SELECT tx_hash, condition_id, wallet, side, outcome_index, size_usd, price, timestamp
                   FROM trades WHERE condition_id = ?""", (p["condition_id"],))]
            s = {"condition_id": p["condition_id"], "outcome_index": p["outcome_index"],
                 "signal_time": p["signal_time"], "wallets": json.loads(p["wallets"])}
            exit_ts = sig.compute_copy_exit(s, relevant, bcfg["copy_exit_wallet_fraction"],
                                            bcfg["copy_exit_sold_fraction"])
            if exit_ts:
                self.close_position(p, exit_ts, exit_type="copy_exits")

    def poll_resolutions(self) -> None:
        """Close positions whose markets have resolved."""
        for p in self.open_positions():
            try:
                # closed=True: Gamma's default listing excludes closed markets,
                # so an empty result here just means "still open"
                markets = self.gamma.get_markets(condition_ids=[p["condition_id"]], closed=True)
            except ApiError:
                continue
            if not markets or not markets[0].get("closed"):
                continue
            m = markets[0]
            db.upsert_market(self.conn, db.market_row_from_gamma(m))
            try:
                payout = float(json.loads(m["outcome_prices"])[p["outcome_index"]])
            except (TypeError, ValueError, IndexError):
                continue
            self.close_position(p, int(time.time()), exit_type="resolution", exit_price=payout)

    def close_position(self, p: dict, exit_ts: int, exit_type: str,
                       exit_price: float = None) -> None:
        """Compute PnL and mark a paper position CLOSED."""
        slippage = self.cfg["slippage"]["exit_cents"] / 100.0
        if exit_price is None:
            try:
                mid = self.clob.get_midpoint(p["token_id"])
            except ApiError:
                mid = None
            if mid is None:
                return
            exit_price = max(0.0, mid - slippage)
        entry = p["entry_price"]
        if not entry:
            return
        # size at OPEN, not the current config — a config change must not
        # retroactively reprice positions opened at a different stake
        stake = p["position_usd"] or self.position_usd
        shares = stake / entry
        pnl = (exit_price - entry) * shares
        self.conn.execute(
            """UPDATE paper_trades SET status='CLOSED', exit_price=?, exit_time=?, exit_type=?,
               resolved=?, pnl_20=? WHERE id=?""",
            (exit_price, exit_ts, exit_type, 1 if exit_type == "resolution" else 0, pnl, p["id"]))
        self.conn.commit()
        self.stats_today["closed"] += 1
        log.info("CLOSED %s outcome=%d via %s: entry %.3f -> exit %.3f, PnL $%+.2f",
                 p["condition_id"][:12], p["outcome_index"], exit_type, entry, exit_price, pnl)

    # ---------- reporting ----------

    def daily_summary(self) -> None:
        """Log the daily summary to stdout; reports/paper_dashboard.md
        (regenerated by paper_status.py) is the human-readable view —
        the former reports/paper_daily.md append-log is retired."""
        closed = self.conn.execute(
            "SELECT COUNT(*) c, COALESCE(SUM(pnl_20),0) p FROM paper_trades WHERE status='CLOSED'").fetchone()
        decay = self.conn.execute(
            "SELECT AVG(alpha_decay) d FROM paper_trades WHERE alpha_decay IS NOT NULL").fetchone()["d"]
        open_pos = self.open_positions()
        unrealized = 0.0
        for p in open_pos:
            try:
                mid = self.clob.get_midpoint(p["token_id"])
            except ApiError:
                mid = None
            if mid and p["entry_price"]:
                stake = p["position_usd"] or self.position_usd
                unrealized += (mid - p["entry_price"]) * (stake / p["entry_price"])
        lines = [
            f"\n## {self.today.isoformat()}",
            f"- signals fired today: {self.stats_today['signals']}"
            f" | opened: {self.stats_today['opened']} | closed: {self.stats_today['closed']}",
            f"- running realized PnL (all closed): ${closed['p']:+.2f} over {closed['c']} positions",
            f"- avg alpha decay: {decay:+.4f}" if decay is not None else "- avg alpha decay: n/a",
            f"- open positions: {len(open_pos)}, unrealized PnL est: ${unrealized:+.2f}",
            "",
            "By category (all-time paper stats):",
            category_stats.category_table(self.conn, self.pcfg["watchlist_cohort"]),
        ]
        print("\n".join(lines) + "\n")

    # ---------- main loop ----------

    def run(self) -> None:
        """Poll feed / exits / resolutions on their intervals until shutdown."""
        pcfg = self.pcfg
        try:
            while not _shutdown:
                cycle_start = time.time()
                today = datetime.now(timezone.utc).date()
                if today != self.today:
                    self.daily_summary()
                    self.today = today
                    self.stats_today = {"signals": 0, "opened": 0, "closed": 0}
                try:
                    n_new = self.poll_feed()
                    if n_new:
                        log.debug("%d new watchlist trades", n_new)
                        self.detect_and_open()
                    now = time.time()
                    if now - self.last_exit_poll >= pcfg["exit_poll_interval_seconds"]:
                        self.last_exit_poll = now
                        if pcfg["exit_strategy"] == "copy_exits":
                            self.poll_copy_exits()
                    if now - self.last_resolution_poll >= pcfg["resolution_poll_interval_seconds"]:
                        self.last_resolution_poll = now
                        self.poll_resolutions()
                except ApiError as e:
                    # transient API failure escaping an unguarded call (e.g.
                    # ensure_market's Gamma lookups) must not kill the loop —
                    # killed the 2026-07-03 03:38 run while ingest saturated the API
                    log.warning("poll cycle failed (%s) — continuing", e)
                elapsed = time.time() - cycle_start
                time.sleep(max(0.5, pcfg["poll_interval_seconds"] - elapsed))
        except KeyboardInterrupt:
            pass
        log.info("shutting down — writing summary")
        self.daily_summary()


def main() -> None:
    """Entry point: set up logging/signals, record our PID, run the loop."""
    setup_logging()
    os.makedirs(os.path.dirname(PID_FILE), exist_ok=True)
    with open(PID_FILE, "w", encoding="utf-8") as f:
        f.write(str(os.getpid()))
    os_signal.signal(os_signal.SIGTERM, _handle_sigterm)
    PaperTrader().run()


if __name__ == "__main__":
    main()
