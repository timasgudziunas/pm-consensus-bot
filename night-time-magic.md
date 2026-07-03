# night-time-magic.md — Overnight Work Order & Session Handoff

> Written 2026-07-03 by Claude (previous session) at the owner's request.
> Purpose: a fresh Claude Code session should be able to read THIS file and
> execute the overnight plan without any other context.
> The owner reviewed the plan below in draft form; execute it unless their
> new-session prompt says otherwise.

---

## Current state (as of 2026-07-03 ~02:00 UTC)

All of Phases 0–5 are BUILT and DONE (see PLAN.md checkboxes). Do not rebuild.

- **Watchlist:** 113 wallets selected (of 137 vetted), 6 categories. `wallets` table + `reports/watchlist_preview.txt`.
- **Data ingested:** 241,904 trades (2026-01-01 → 2026-07-03), 1,409 signal-candidate markets with metadata, 380k+ hourly price candles. All in `data/copybot.db`.
- **Backtest done:** 144 cells × train/validate/full. Best validate cell: **N=5, W=24h, F=$500, hold_to_resolution, $50 → +$510 PnL, 74% win rate, 27% ROC, 38 signals**. 91/144 cells profitable in both periods. Full report: `reports/backtest_report.md` (read its bias caveats before trusting numbers).
- **Paper trading RUNNING** as a detached OS process (PID in `data/logs/pids.txt`, currently 16892) with N=5/24h/$500/hold_to_resolution at **$20**/position. Logs: `data/logs/paper_stdout.log`, `data/paper.log`; daily summary appends to `reports/paper_daily.md`.
- **Everything is UNCOMMITTED** — `git status` shows the whole build untracked. First overnight step is committing it.
- Restart command pattern (PowerShell, detached so it survives the session):
  `Start-Process -FilePath python -ArgumentList "src\paper.py" -WorkingDirectory <repo> -WindowStyle Hidden -RedirectStandardOutput "<repo>\data\logs\paper_stdout.log" -RedirectStandardError "<repo>\data\logs\paper_stderr.log"`
  (same pattern for `src\ingest.py`; update `data\logs\pids.txt` after restarts)

## API landmines (verified live; also in module docstrings + memory)

1. `/trades`: limit silently capped at 1000, offset hard-capped at 3000 → **max 4,000 most-recent trades per wallet**; no time filters work. 85/113 current wallets are truncated (thin early-month data — flagged in the report).
2. Gamma `/markets` **hides closed markets** unless `closed=true` — query open and closed separately (clients already do this).
3. Global `/trades` feed returns `outcomeIndex=999`; map via `asset` token id → market `clobTokenIds` (paper.py already does).
4. `/trades` `size` = SHARES; USD = size × price.
5. CLOB `/prices-history` 400s on intervals > ~15 days at fidelity 60 (config uses 14-day chunks).
6. Leaderboard categories: only POLITICS, SPORTS, CRYPTO, FINANCE, CULTURE, TECH (+OVERALL) are valid.

---

## THE OVERNIGHT PLAN (owner's 3 instructions, expanded)

### 0. First: commit the current build
Commit everything as a known-good baseline before changing anything (message like "Phases 0-5: full build, first backtest + paper live"). Tonight's changes must be cleanly diffable.

### 1. Paper stake $20 → $50
- `config.yaml` → `paper.position_size_usd: 50`, restart paper (detached, pattern above).
- Restart paper AFTER step 2's watchlist update so it picks up the new wallets in one restart (paper loads the watchlist at startup).
- Known effects: $50 walks deeper into the book (worse fills = honest), old $20 positions stay $20, the 3-day paper clock effectively restarts tonight.

### 2. Bigger watchlist (~500 wallets) + much wider sweep
**a) Discovery: three selection cohorts, ~500-wallet union** (`discover.py` + config):
The owner wants "efficient profitable traders" — efficiency has several defensible
definitions, so we test them empirically instead of picking one. Select candidates
under THREE cohorts, tag each wallet with every cohort that picked it (new
`cohorts` column or similar on `wallets`), ingest the union:
- **Cohort A — raw PnL** (today's method, keep as the control).
- **Cohort B — PnL per dollar of volume** (leaderboard `pnl` / `vol`): return per dollar traded.
- **Cohort C — entry edge per dollar staked**: from the vetting trade sample +
  market resolutions, mean of (resolution payout − entry price) weighted by stake
  across their resolved buys. Most aligned with copy-trading (we copy entries, not
  portfolio management). Needs Gamma resolution lookups for the sample's markets —
  batch them (20 condition_ids/request, open+closed passes) and cache in `markets`;
  reuse anything already in the DB.
- Also compute and store a **consistency score** for every candidate (market-level
  win rate or mean/std of per-market PnL proxy — nearly free from vetting data).
  Use it as a tie-breaker within cohorts, not a fourth cohort.
- **Target: ~500 wallets total** in the selected union. Config caps:
  `max_candidates_per_category` 25 → ~120 (vetted pool shared by all cohorts),
  `max_watchlist` 120 → 500, `max_per_category` 25 → ~100 (union-level; a wallet in
  several categories/cohorts counts once).
- Keep hard filters (min_markets 20, min_trades 50, MM exclusion) but log how many
  wallets each filter rejects.
- Re-running discover.py is safe: it upserts wallets and re-selects; existing
  ingested data is untouched. NOTE: vetting ~720 candidates plus Cohort C's
  resolution lookups is the slow part of discovery — budget an hour-plus of API time.

**b) Ingest the new wallets** (`ingest.py` — already resumable/incremental):
- Only new wallets get fetched (per-wallet done flags in `ingest_progress`); new candidate markets get metadata + price history incrementally. With ~390 new wallets expect this to run for several hours unattended — it is the night's long pole. Run detached, monitor via `data/logs/ingest_stderr.log` (Python logging goes to stderr).

**c) Wider sweep, run per cohort AND pooled** (`config.yaml` sweep block, then `backtest.py` + `report.py`):
- N: [2,3,4,5,6,7,8] · W hours: [1,3,6,12,24,48] · F: [100,250,500,1000,2500] · exits: both · sizes: [20,50,100]
- Run the sweep FOUR times over different wallet sets: Cohort A only, B only, C only,
  and the pooled union — i.e., filter the trades fed to `detect_signals()` by the
  cohort's wallets. Tag results (add a `cohort` column to `signals` and
  `backtest_results`). The report must answer: **which definition of "efficient"
  produces the most profitable consensus signals?**
- NOTE: `signals` table columns `pnl_20`/`pnl_50` and backtest.py's `r["pnls"][20]`/`[50]` are hardcoded to the two sizes — adding $100 requires a small schema/code touch (add `pnl_100` or store JSON). Do this carefully or drop the $100 size if it gets messy.
- ~840 cells × 4 cohort runs — compute is local and still fast (last 144-cell sweep: 5 seconds). Re-run report.py after.
- **Overfitting guard, mandatory:** with a grid this big, single-cell winners are suspect. Add to the report (or a supplementary section): the top cells' parameter *neighborhoods* — a winner only counts as robust if adjacent cells (N±1, W one step, F one step) are also profitable in validate. Say so explicitly in the report. Same skepticism applies across cohorts: prefer a cohort whose top cells are broadly profitable over one with a single spectacular cell.

### 3. After the sweep: reconcile paper params
- If the new best validate cell (robust per the neighborhood check, from the best
  cohort) differs from N=5/24h/$500/hold, update the `paper:` block and restart
  paper once more.
- Paper's watchlist: run it on the **winning cohort's wallets** if one cohort is
  clearly best; otherwise the pooled union. (paper.py loads `selected=1` wallets —
  set `selected` accordingly, or filter by the cohort tag if that's cleaner.)
- Morning deliverable: updated `reports/backtest_report.md`, bigger `reports/watchlist_preview.txt`, overnight `reports/paper_daily.md`, and a summary of what changed and what the go/no-go picture looks like.

---

## Standing rules (unchanged, from CLAUDE.md — the short version)
- **No live-execution code, ever** (live.py stays a stub). No keys, no wallets, no orders.
- All tunables in config.yaml, no magic numbers; signals.py stays pure and shared; dedupe everything; 0.15s API throttle; trust the live API over docs and comment discrepancies.
- Watchlist approval pauses are **waived** — auto-select wallets that pass filters (owner standing instruction from the first run).

## Owner must do (nothing else requires supervision)
- **Keep the machine awake** — it slept ~2h last night and paused both loops. Plug in, disable sleep.
- Morning: read the regenerated report + paper daily summary; decide on the PLAN.md day-3 decision gate (Polymarket US KYC is the only external prerequisite and only matters if the gate passes).
