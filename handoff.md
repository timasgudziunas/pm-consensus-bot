# handoff.md — Session Handoff (written 2026-07-06)

> For a fresh Claude session (or the owner) picking up the paper-trading gate
> window. Read this, then CLAUDE.md for the standing rules. The previous
> session was cleared for token cost on 2026-07-06; nothing else was wrong.

## Where things stand

- **Phases 0–5 built and committed** (main branch, through `9a311d0`+). Backtest
  done: cohort B (PnL-per-volume wallets) won — best robust cell
  **N=5, W=12h, F=$1000, hold_to_resolution** (+$3,482 validate at $100 size,
  +$1,955 at $50; 83% of grid neighbors profitable). Full story:
  `reports/backtest_report.md`, `reports/overnight_summary_2026-07-03.md`.
- **Paper trading is LIVE** on that cell: cohort-B watchlist (250 wallets),
  $50/position. PID in `data/logs/paper.pid`; supervised by Windows scheduled
  task **pm-copybot-paper-watchdog** (every 5 min, runs `src/watchdog.py`,
  restarts paper if dead, logs to `data/logs/watchdog.log`). To stop paper on
  purpose: DISABLE that task first, or it resurrects paper within 5 min.
- **KYC is done.** API keys are in repo-root `.env` (`POLYMARKET_KEY_ID`,
  `POLYMARKET_SECRET_KEY`) — gitignored, untracked. **Never read, print, log,
  or commit their values.** They are unused until the owner explicitly starts
  the live phase.
- **live.py stays a stub.** Do not write order/wallet/key code under any
  circumstances until the owner says so in a direct message.

## The decision gate (the current mission)

Gate clock: **started 2026-07-05 09:00 EDT (13:00 UTC)** — owner reset it after
the feed bug (below). **Day-3 gate review due 2026-07-08 09:00 EDT.**
Criteria are frozen in PLAN.md ("Decision gate" section) and config
`paper.gate`: ≥15 filled signals; ≥55% win rate once ≥10 closed (else
MTM-neutral-or-positive); mean alpha decay < 10¢/share. Plus PLAN.md's other
checkboxes — including verifying ≥5 paper-signal markets exist on Polymarket
US (still unchecked; do it at the review).

**Daily check-ins the owner expects** (day 2 due 2026-07-07 ~09:06 EDT, day-3
gate review due 2026-07-08 ~09:06 EDT — the old session's in-chat schedule died
with it):
1. Run `python src\paper_status.py` (prints the standard block; the gate math
   is inside the script, anchored to config `paper.gate_start_utc`).
2. Sanity-check `data/logs/watchdog.log` (unexpected restarts?) and the tail of
   `data/logs/paper_stdout.log` (anomalies vs the known transient warnings).
3. Post: signals filled, STALE count, SKIPPED count, win rate, mean alpha
   decay, PnL realized+MTM, per-criterion ON TRACK/AT RISK, plus a short
   judgment paragraph.
- Backstop: scheduled tasks **pm-copybot-checkin-day2/day3** (Jul 7/8 09:03
  EDT) append the raw stats to `reports/paper_checkins.md` even with no
  Claude session.
- At the gate review: explicit PASS/FAIL per criterion + recommendation
  (proceed toward live / extend paper / revisit parameters). Verdict aside,
  live code remains forbidden without direct owner authorization.

## Day-1 results (2026-07-06 09:06 EDT) — for trend comparison

11 fills, all closed same-day (World Cup knockout markets), **45% win rate
(5/11), −$14.74 realized**, mean decay −9.85¢/share. Volume ON TRACK,
win rate AT RISK, decay ON TRACK. Color: all 11 signals came from two live
matches; consensus flipped in-play so we held both sides of the same market in
4 of 11 entries; the negative decay is partly adverse selection (entering into
falling prices), not pure edge. Small sample — judgment deferred.

## Hard-won landmines (beyond the module docstrings)

1. **The global `/trades` feed silently drops ~95% of watchlist trades in busy
   periods** (platform-wide ≤500-trade window). This blinded paper for Jul 3–5
   and invalidated the first gate window. paper.py now polls user-filtered
   `/trades` per wallet on rotation (complete + correct outcome_index). Never
   go back to the global feed for collection.
2. Signals detected >30 min late (restart backfill) are recorded **STALE** and
   never entered (`paper.max_signal_age_seconds`).
3. `paper_trades.position_usd` is the stake at open — config changes must not
   reprice old rows. `pnl_20` is the realized-PnL column regardless of stake
   (legacy name).
4. Windows: `os.kill(pid, 0)` TERMINATES the process — liveness checks must
   use `tasklist` (see watchdog.py). Git-bash `kill -0` can't see native PIDs.
5. Emoji usernames crash cp1252 stdout — stdout is reconfigured to UTF-8 in
   discover.py/paper_status.py; keep doing that in new CLI entry points.
6. Transient `ConnectionResetError`/DNS warnings in paper logs are normal and
   self-recover; the poll loop is guarded against ApiError. A silent log is
   fine if `trades.ingested_at` shows recent inserts.

## Quick health check (run any time)

```powershell
python src\paper_status.py
Get-Content data\logs\watchdog.log -Tail 3
python -c "import sqlite3,time; c=sqlite3.connect('data/copybot.db'); print('trades last hour:', c.execute('SELECT COUNT(*) FROM trades WHERE ingested_at >= ?', (int(time.time())-3600,)).fetchone()[0])"
```
Healthy ≈ paper PID alive, no new watchdog restarts, hundreds+ trades/hour.
