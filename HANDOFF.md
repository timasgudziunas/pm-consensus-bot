# HANDOFF.md: Session Handoff (updated 2026-10-19 ~18:30 UTC, supersedes all 2026-08-25 and earlier versions)

> For a fresh Claude session with no memory of prior conversations. Read this,
> then CLAUDE.md for standing rules. The 2026-08-25 session (owner present)
> resolved the strategic fork: signal v2 post-filters were pre-registered,
> backtested, and FAILED; the bot has run as **event-season-only with config
> frozen** since. **The pre-registered Oct 15 final checkpoint is now DUE and
> UNRESOLVED. Read §3 item 1 before anything else.** All verdicts in §2 are
> SETTLED; do not re-run or re-litigate them.

## 1. Current state (as of 2026-10-19 ~18:30 UTC)

- **THE OCT 15 CHECKPOINT CAME DUE FOUR DAYS AGO AND HAS NO RECORDED
  VERDICT.** §3 item 1 has the measured numbers. It is the only thing about
  this project that matters right now. Everything below is routine.
- **Paper trading is LIVE and healthy, config still FROZEN**: cohort B (250
  wallets), N=5 W=12h F=$1000 hold, $50/position. Signal params untouched
  since gate start (2026-07-05).
- Paper PID **8700** (`data/logs/paper.pid`), alive, ~3,000 trades/hour
  ingested at check time, 0 open positions. Watchdog last restarted paper.py
  on 2026-10-12 01:32 UTC and has been quiet since. Tasks
  **pm-copybot-paper-watchdog** (fires every few minutes) and
  **pm-copybot-dashboard-daily** (09:05 local) both still run S4U; disable
  the watchdog FIRST if stopping paper.py on purpose.
- Dashboard as of 2026-10-19 17:35 UTC (day 106, all time): **78 closed, 62%
  win rate, net −$244.60 realized**, mean decay +4.96¢/share, volume 0.73
  fills/day. Only 10 closes in the 55 days since 2026-08-25. Expectancy on
  the full book is **−0.063/$ → AT RISK** against the `paper.gate`
  keep-testing floor of 0.00/$.
- **The gate was REWRITTEN 2026-08-25** (owner decision): net expectancy per
  $ staked replaces win rate (config `paper.gate`; keep-testing floor
  ≥ 0.00/$, live-ready ≥ +0.05/$ with ≥ 30 closed, volume ≥ 0.5 fills/day,
  decay < 10¢ unchanged). The old win-rate gate falsely said ON TRACK on a
  losing book; PLAN.md's gate section carries the superseded banner.
- **Disk is now a real constraint.** `data/copybot.db` is 6.1 GB,
  `data/paper.log` is 1.6 GB and still growing, `data/` totals roughly 7.7 GB.
  Nothing rotates any of it. Factor this into either a wind-down or a revive.
- The recurring watchdog trigger since September is
  `sqlite3.OperationalError: database is locked` on the trades insert, six
  times between 2026-09-17 and 2026-10-12. Each time the watchdog restarted
  cleanly and no data anomaly was traced, but it is a real contention problem
  that grows with DB size, not transient network noise.
- `handoff.md` was renamed to `HANDOFF.md` on 2026-10-19 to match every other
  repo under `projects/`. In-repo references were updated in the same commit.
- The three `pm-copybot-checkin-day1/2/3` tasks are still registered and
  enabled but have no future trigger (their one-time July triggers already
  fired). Harmless leftovers from the retired day-3 gate. Delete them
  whenever this project is touched again.
- **Everything is committed** through the 2026-10-19 housekeeping commit (the
  dashboard regen, the `HANDOFF.md` rename, and this refresh). No uncommitted
  analysis work. Working tree should be clean.
- API keys in gitignored `.env` — never read/print/log/commit. `live.py`
  stays a stub; no order/wallet/key code without direct owner authorization.

## 2. Settled verdicts (standing results — do not re-derive)

### 2a. Copy-gap decomposition (2026-08-17): selection kills the premise

Consensus fires on the copied wallets' LOSING trades (signal-forming trades
−0.157 PnL/$ vs the wallets' +0.072 overall); the copied trades lose even at
the wallets' own prices (SPORTS wallet counterfactual −2.85¢/share) before
decay (+3.15¢) and spread (+0.39¢). Full report `reports/copy_gap_analysis.md`
(regenerated 2026-08-25, reconciles to −$276.29 over 68 closed).

### 2b. Persistence checkpoint (2026-08-17): INCONCLUSIVE

2 of 3 pre-registered criteria met, underpowered (n=179 vs design n≈222);
persistence plausibly real but weak — detecting it needs ~750–1,000 wallets.
Keeps status quo per the amendment. `reports/persistence_checkpoint.md`.

### 2c. Signal v2 post-filter backtest (2026-08-25): NO ARM PASSES

Pre-registered (committed before results, `reports/proposals/
signal_v2_preregistration.md` incl. the 2026-08-25 amendment on the base
reference) and run same day. Arms: A no-favorites (>0.80), B mid-band
(0.20–0.80), C quality-gated (3-of-5 top-half), D fade (descriptive only).
- A improved simulated validate (+0.289/$ vs +0.211 base, 79% retained,
  neighborhood-robust) but the paper counterfactual stayed negative
  (−0.073/$) → failed criterion 3. B failed train and neighborhood; C failed
  retention (34%) and paper n (14). D: strongly negative in both simulated
  windows; paper +0.425/$ is the contaminated hypothesis-forming sample with
  a CI spanning zero — no adoption path by design.
- **Standing verdict per the expected-outcome clause: post-filters cannot
  salvage the consensus mechanism. Do NOT invent new filter arms.** Full
  report `reports/proposals/signal_v2_backtest.md`.
- Context for any backtest work: the 2026-07-06/07 deep backfill grew
  cohort-B pre-Jul-2 trades ~10x past what `backtest_report.md` (2026-07-03)
  saw — that report's exact signal stream is unreproducible; today's-DB base
  is the reference (157 validate signals, +$3,307.60 at $100/position).

### 2d. Owner fork decisions (2026-08-25)

Cohort expansion: parked (only defensible with a selection-mechanism fix,
which 2c just ruled out for post-filters). Wind-down: deferred to the Oct 15
checkpoint. Chosen path: **event-season hold** (§3).

## 3. Next steps, in priority order

1. **RESOLVE THE OCT 15 CHECKPOINT. Owner decision. Nothing else first.**
   Criteria were pre-registered 2026-08-25 in PLAN.md "Tracked checkpoints",
   fixed before the data. I measured them read-only on 2026-10-19 and
   deliberately did NOT record a verdict or tick the PLAN.md box, because
   accepting a wind-down verdict is the owner's call, not a session's:

   | criterion | threshold | measured | result |
   |---|---|---|---|
   | (a) closed fills, signal_time in [2026-09-01, 2026-10-15) | ≥ 30 | **8** | **FAIL** |
   | (b) net expectancy per $ staked, same window | ≥ +0.00/$ | **+0.074/$** | PASS |

   Those 8 closes went 8 for 8, +$29.70 realized on $400 staked.

   **The pre-registered rule is "either failure implies wind down without
   re-litigating," so the registered verdict is WIND DOWN.** Criterion (a)
   was deliberately a volume-viability test: NFL season was the entire point
   of the hold, and it produced 8 closes in 6 weeks. The 100% win rate is
   n=8 on a book that is still net −$244.60 all time, and it is exactly the
   kind of number the pre-registration existed to stop anyone from acting on.
   Do not read it as evidence of edge. Do not propose new filter arms (§2c is
   a standing verdict). If the owner wants to continue anyway, that is a
   documented override of a pre-registration, not a reanalysis, and it should
   be written down as such.

2. **If winding down** (the registered outcome), in this order: disable
   `pm-copybot-paper-watchdog` FIRST, then stop paper.py, then disable
   `pm-copybot-dashboard-daily`, then delete the three dead
   `pm-copybot-checkin-day1/2/3` tasks, then write the final project report,
   then archive per the 8 point checklist in `../archives/README.md`.
   Deal with the 7.7 GB of `data/` on the way out; it is gitignored, so it
   does not travel with the repo but it does sit on disk.
3. **Routine health checks only** until that decision is made. Config stays
   frozen. See "Quick health check" at the bottom of this file.

## 4. Where everything lives (recent outputs)

| path | what it is |
|---|---|
| `reports/proposals/signal_v2_preregistration.md` | Frozen v2 arms + adoption rule + 2026-08-25 amendment (committed before results) |
| `reports/proposals/signal_v2_backtest.md` | v2 verdict report — read the verdict table + amendment note first |
| `reports/proposals/signal_v2_signals.csv` | Per-signal audit rows (validate window, per-arm retained flags) |
| `src/backtest_signal_v2.py` | Rerunnable v2 engine (read-only DB; reuses signals.detect_signals + backtest.evaluate_signal; ~100s) |
| `reports/copy_gap_analysis.md` + `copy_gap_fills.csv` | Copy-gap decomposition (rerunnable; frozen-constant bug fixed 2026-08-25) |
| `reports/persistence_checkpoint.md` + `_wallets.csv` | Persistence verdict + per-wallet edges |
| `reports/paper_dashboard.md` | Single paper report, regenerated daily 09:05 local (`pm-copybot-dashboard-daily`); run `python src\paper_status.py` for fresh numbers |
| `config.yaml` | ALL tunables; `paper.gate` = rewritten expectancy gate; `analysis.signal_v2` = v2 params |
| PLAN.md "Tracked checkpoints" | Oct 15 final checkpoint criteria (pre-registered) |

## 5. Data gaps & caveats (carry with any number above)

- **Taker-only trades feed** (median cohort wallet ~84% maker): copyable-edge
  metrics immune by construction; cash-flow PnL and exit counterfactuals are
  bounded estimates only.
- **Survivorship bias** on all cohort edges (selected on the June leaderboard).
- **Simulator-vs-paper calibration gap unresolved**: base cell simulates
  +0.21/$ in validate while live paper shows −0.08/$ in an overlapping
  regime — simulated absolute PnL is never trustworthy; only relative
  (arm-vs-base) comparisons were used in 2c.
- **Jul 16–17 outage** recovered only ~half that day's trades.
- Validate-window sports is WC-inflated; no historical order-book depth
  exists anywhere (lifetime volume is a labeled proxy).

## 6. Operational landmines (permanent — never drop entries)

1. Never use the global `/trades` feed for collection — drops ~95% of
   watchlist trades when busy. Per-wallet rotating poll only.
2. `/trades` is TAKER-ONLY by default and ALL ingested history is taker-only.
   Never treat the trades table as a wallet's full activity.
3. Late-detected signals (>30 min) are recorded STALE, never entered.
4. `paper_trades.pnl_20` is realized PnL regardless of stake (legacy name);
   `position_usd` is the stake at open — never reprice.
5. Windows liveness checks: use `tasklist`, NOT `os.kill(pid, 0)` (it kills).
6. Reconfigure stdout to UTF-8 in any new CLI entry point (emoji usernames).
7. Transient ConnectionResetError/DNS warnings in paper logs self-recover.
8. Recreated scheduled tasks revert to Interactive-only + battery-restricted
   — reapply the S4U fix from an elevated PowerShell (CLAUDE.md rule 2).
9. Analysis scripts against the live DB use read-only connections
   (`file:...?mode=ro`); the sole write exception is batched markets-table
   upserts (wallet_quality_fetch.py pattern).
10. The trades table holds ~10x more pre-Jul-2 history than existed when
    `backtest_report.md` was generated (2026-07-06/07 deep backfill) — never
    expect to reproduce that report's exact numbers; and always clip
    backtests to `analysis.window_end_utc` to exclude paper-poll-era rows.

## Quick health check

```powershell
python src\paper_status.py
Get-Content data\logs\watchdog.log -Tail 3
python -c "import sqlite3,time; c=sqlite3.connect('data/copybot.db'); print('trades last hour:', c.execute('SELECT COUNT(*) FROM trades WHERE ingested_at >= ?', (int(time.time())-3600,)).fetchone()[0])"
```
Healthy ≈ paper PID (data\logs\paper.pid) alive, no new watchdog restarts,
hundreds+ trades/hour. Expect ~0 fills/day until September sports volume.
