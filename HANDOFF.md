# HANDOFF.md: Session Handoff (final, 2026-10-25 ~21:00 UTC)

**STATUS: ARCHIVED as of 2026-10-25.** The pre-registered Oct 15 checkpoint
(PLAN.md "Tracked checkpoints") failed criterion (a): 8 closed fills in the
Sep 1 to Oct 15 window against a threshold of 30. Criterion (b) passed at
+0.074/$. The rule fixed on 2026-08-25 was "either failure means wind down
without re-litigating." The owner confirmed on 2026-10-25 and the project
was archived the same day. **Read `reports/final_report.md` for the verdict,
the numbers and why the strategy failed.** Nothing external is on.

## What was turned off (2026-10-25, in this order)

1. `pm-copybot-paper-watchdog` disabled first (otherwise it relaunches paper.py).
2. `paper.py` PID 8700 stopped. It ran in session 0 under S4U, so an
   unelevated `Stop-Process` and `taskkill` were both denied; it took an
   elevated shell via a UAC prompt. Expect the same on any future S4U-launched
   process.
3. `pm-copybot-dashboard-daily` disabled.
4. All five `pm-copybot-*` tasks unregistered: the two above plus the dead
   `pm-copybot-checkin-day1/2/3`. `Get-ScheduledTask` shows zero `pm-copybot*`
   tasks. XML exports are in `ops/scheduled-tasks/`; re-import with
   `Register-ScheduledTask -Xml` on revive, then reapply the S4U and battery
   fixes (CLAUDE.md standing rule 2).
5. Final dashboard regenerated at 20:53 UTC (`reports/paper_dashboard.md`,
   day 112: 78 closed, 62% win, realized −$244.60, 2 open at MTM +$10.42,
   net −$234.18, −0.059/$ on $4,000 staked).
6. `src/archive_extract.py` copied `paper_trades` (127), `wallets` (638),
   `backtest_results` (15,120), both progress tables, `event_categories`
   and the 100 referenced `markets` rows into `data/archive_extract.db`
   (8.5 MB), and wrote `reports/paper_trades_final.csv`. Integrity check
   passed (78 closed, −$244.60).
7. Deleted: `data/copybot.db` (6.1 GB, 5.9M trades, 5.7M price_history,
   2.2M signals), `data/paper.log` (1.6 GB), `data/pc_positions.sqlite`
   (260 MB), `data/wq_positions.sqlite` (196 MB). `data/` is now about 17 MB.
   **The raw trades cannot be re-fetched** (Polymarket `/trades` caps at 4k
   rows per wallet), so no backtest or analysis script in `src/` can be
   rerun. `paper_status.py` will not run either. The markdown and CSV
   reports are the record.
8. No paid services existed. The gitignored `.env` (168 bytes) travels with
   the folder; the code reads no environment variables and sends no keys.
9. GitHub repo pushed and archived read-only (unarchive before pushing on
   revive). Folder moved to `projects/archives/pm-consensus-bot`.

## Two paper positions were open at shutdown

US x Iran ceasefire through Oct 22 (signal 2026-10-19, entry 0.923, $50) and
through Oct 31 (signal 2026-10-22, entry 0.75, $50). Booked at mark
(+$10.42) in the final report. They stay `OPEN` in `archive_extract.db`.

## If reviving

Do not revive to continue the consensus strategy; the settled verdicts in
`reports/final_report.md` (selection kills the premise, post-filters cannot
fix it, persistence is weak, volume is event-shaped) stand and are not to be
re-litigated. A revive only makes sense for a different mechanism reusing the
plumbing (API clients, `db.py`, `signals.py` as a pattern, the watchdog).
You would start from zero data: re-run `discover.py` and `ingest.py`, and
read `OVERVIEW.md` knowing it is stale where `config.yaml` disagrees.

## Operational landmines (kept for whoever reuses the plumbing)

1. Never use the global `/trades` feed for collection; it drops ~95% of
   watchlist trades when busy. Per-wallet rotating poll only.
2. `/trades` is TAKER-ONLY by default. The median cohort wallet was ~84%
   maker and therefore mostly invisible. Never treat it as full activity.
3. `/trades` caps at 4k rows per wallet; Gamma hides closed markets;
   `outcomeIndex` can be 999; `size` is shares; `/positions` is current
   holdings only.
4. Late-detected signals (>30 min) are recorded STALE, never entered.
5. `paper_trades.pnl_20` is realized PnL regardless of stake (legacy name);
   `position_usd` is the stake at open.
6. Windows liveness checks: use `tasklist`, not `os.kill(pid, 0)`.
7. Reconfigure stdout to UTF-8 in any CLI entry point (emoji usernames).
8. Recreated scheduled tasks revert to Interactive-only and battery-restricted;
   reapply the S4U fix from an elevated PowerShell.
9. A single-file SQLite DB with no rotation hit `database is locked` six
   times after it passed 6 GB, each time restarting cleanly under the
   watchdog. Build rotation in from the start next time.
10. A win-rate gate reads ON TRACK on a losing book with asymmetric payoffs.
    Gate on net expectancy per dollar staked.
