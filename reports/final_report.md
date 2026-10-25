# Final project report: pm-consensus-bot (archived 2026-10-25)

_Written 2026-10-25 at wind-down. Numbers are from `reports/paper_dashboard.md` (regenerated 2026-10-25 20:53 UTC by `src/paper_status.py`, the last run against the full database) and from the settled analyses linked below. Nothing here is re-derived; this report collects verdicts that were each pre-registered and recorded at the time._

## Verdict

**Wind down.** The pre-registered Oct 15 checkpoint failed its volume criterion, the pre-registered rule said either failure means wind down without re-litigating, and the owner confirmed on 2026-10-25. Paper trading never went live and `src/live.py` is still a stub.

| Oct 15 checkpoint (signals Sep 1 to Oct 15, fixed 2026-08-25) | threshold | measured | result |
|---|---|---|---|
| (a) closed fills | ≥ 30 | 8 | FAIL |
| (b) net expectancy per $ staked | ≥ 0.00/$ | +0.074/$ | PASS |

The 8 closes went 8 for 8 for +$29.70 on $400 staked. That is n=8 on a book that lost money over 78 closes, and it is exactly the kind of number pre-registration exists to stop anyone from acting on.

## What was built

A Polymarket copy-trading bot (2026-07-02 to 2026-10-25, 30 commits before the archive commit). Thesis: when N independently profitable traders open the same side of the same market inside a time window, copy it. Pipeline: per-category leaderboard discovery and vetting (cohort B, 250 wallets), resumable taker-side trade ingestion (5.9M rows), a shared pure signal detector used identically by the backtest sweep and the paper loop, a parameter sweep with a train/validate split, and a paper loop that ran unattended under a watchdog for 112 days.

Live paper parameters, frozen since gate start 2026-07-05: N=5 traders, W=12h window, F=$1000 floor, hold to resolution, $50 per position.

## Paper results, all time (2026-07-05 13:00 UTC to 2026-10-25 20:53 UTC, day 112)

| metric | value |
|---|---|
| signals recorded | 127 (80 filled, 31 skipped for thin or gone book, 16 stale) |
| closed | 78, 48 wins (62%) |
| realized PnL | −$244.60 |
| open at shutdown | 2 positions, $100 staked, mark-to-market +$10.42 |
| net including marks | −$234.18 |
| net expectancy | −0.059/$ on $4,000 staked |
| mean alpha decay | +5.05¢/share (traders' price to our fill) |
| volume | 0.71 fills/day overall; about 7 to 11 signals/day during the World Cup, about 0.25 fills/day after it |

The two open positions (US x Iran ceasefire through Oct 22, entered Oct 19 at 0.923; through Oct 31, entered Oct 22 at 0.75) were left unresolved when the process was stopped and are booked at mark above. They do not change the verdict.

By category: SPORTS took 60 of the 80 fills and lost −$288.74 (−0.096/$, 52% win rate). POLITICS took 12 fills and made +$52.95 (+0.106/$, 12 for 12). Seven unmapped fills lost −$12.76. The POLITICS line is small and was never a pre-registered arm; it is reported, not acted on.

## Why it failed

1. **Selection, not execution.** The copy-gap decomposition (2026-08-17, `reports/copy_gap_analysis.md`) showed consensus fires on the copied wallets' losing trades: signal-forming trades ran −0.157 PnL/$ against the wallets' +0.072 overall, and the copied trades lose even at the wallets' own prices before decay and spread are added. Agreement among good traders selected their worst trades.
2. **Post-filters cannot fix selection.** Four pre-registered v2 arms (no favorites, mid-band, quality-gated, fade) were backtested 2026-08-25 (`reports/proposals/signal_v2_backtest.md`). No arm passed. The expected-outcome clause recorded in advance applied: post-filters cannot salvage the consensus mechanism.
3. **Persistence of wallet skill is at best weak.** The 2026-08-17 checkpoint (`reports/persistence_checkpoint.md`) was inconclusive at n=179; detecting it would need 750 to 1,000 wallets, which only makes sense with a selection fix that item 2 ruled out.
4. **Volume is event-shaped.** Signals clustered in the World Cup, fell about 10x after it, and the NFL season produced 8 closes in six weeks. There was never enough steady-state flow to reach the gate's n=30 outside a tournament.

## What worked and carries forward

- **Pre-registration held.** Every verdict above was fixed before its data: the day-3 gate, the persistence checkpoint and its amendment, the v2 arms and adoption rule, and the Oct 15 criteria. None was re-litigated, including when an 8 for 8 streak made that tempting.
- **The gate rewrite was necessary.** The original win-rate gate showed ON TRACK on a losing book. Net expectancy per dollar staked replaced it on 2026-08-25. A win-rate gate on asymmetric payoffs is a standing hazard for any future trading project.
- **Field names from reality, not docs.** Polymarket's `/trades` is taker-only by default (the median cohort wallet was about 84% maker and therefore mostly invisible), caps at 4k rows per wallet, Gamma hides closed markets, and `outcomeIndex` can be 999. All recorded in `OVERVIEW.md`, `HANDOFF.md` and the project memory.
- **Unattended operation held up.** 112 days under a watchdog with six clean restarts, all from `database is locked` on the trades insert as the DB passed 6 GB. Logs and the DB never rotated; `data/` reached 7.8 GB. Rotation belongs in the design next time, not the wind-down.

## Caveats attached to every number above

- The trades feed is taker-only, so copyable-edge metrics are immune by construction but cash-flow PnL and exit counterfactuals are bounded estimates.
- Survivorship bias on all cohort edges (wallets were selected on the June leaderboard).
- The simulator-vs-paper calibration gap was never closed: the base cell simulated +0.21/$ in validate while paper showed about −0.08/$ in an overlapping regime. Only relative arm-vs-base comparisons were ever used.
- The Jul 16 to 17 outage recovered only about half that day's trades.

## What was turned off and what was kept (2026-10-25)

- Watchdog task disabled first, then `paper.py` (PID 8700, session 0, needed an elevated stop) stopped, then all five `pm-copybot-*` scheduled tasks unregistered. Their XML definitions are in `ops/scheduled-tasks/` for a revive.
- `data/copybot.db` (6.1 GB), `paper.log` (1.6 GB) and the two positions caches were deleted. `src/archive_extract.py` first copied `paper_trades`, `wallets`, `backtest_results`, progress tables, `event_categories` and the 100 referenced `markets` rows into `data/archive_extract.db` (8.5 MB) and wrote `reports/paper_trades_final.csv`. The raw trades, price history and signals tables are gone and cannot be re-fetched because of the 4k cap; no backtest in this repo can be rerun.
- No paid services existed. Polymarket's APIs are public and the code sends no keys.
- GitHub repo pushed and archived read-only. Folder moved to `projects/archives/`.
