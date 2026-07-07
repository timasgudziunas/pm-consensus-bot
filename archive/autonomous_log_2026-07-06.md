# Autonomous session log — 2026-07-06

Owner away; instructions: category breakdowns in paper reporting, two-half
category backtest (both exit strategies, liquidity-aware fills), historical
sports skip-rate quantification, findings report, fill-rate vetting proposal.
Hard constraint: NO changes to live trading logic, cohort weighting, or
category caps.

## Log

- Session start. Task list created (#6–#10). Beginning with paper_status.py
  category breakdown.
- **Task 1 DONE** (~16:10 UTC): new `src/category_stats.py` (read-only per-category
  aggregation); wired into `paper_status.py` check-ins and `paper.py`
  `daily_summary()` (reporting-only edit — running paper process NOT restarted,
  picks it up on next restart).
- Found + fixed (offline) a metadata gap: `ensure_market` never backfills
  `category` on markets already cached by ingest, so recent paper trades were
  uncategorized. Backfilled 15,488 `markets.category` values from the
  `event_categories` cache via SQL + 2 Gamma slug lookups. Category is metadata
  only (never used in trading decisions) — no live behavior change. A proper
  `ensure_market` fix is proposed in the findings report, not applied.
- **Finding**: ALL 11 gate-window fills are SPORTS (FIFA World Cup dailies
  mostly). 0 signals from POLITICS/TECH/CRYPTO/FINANCE/CULTURE since gate
  restart. The 27-29 SKIPPED sports signals all predate the gate restart —
  investigating next whether those were true illiquidity or stale-signal
  artifacts of the broken global feed (market already resolved -> no book).
- **Task 3 DONE** (~16:12 UTC): the 28 SKIPPED signals were NOT illiquidity.
  All are from the broken-feed window (07-02/03), on markets with $385k-$16.7M
  volume, all with midpoint_at_signal=None -> orderbook GONE (market already
  resolved when the late signal arrived), not thin. The max_signal_age guard
  (added 07-05) now catches these as STALE. Post-fix sports fill rate: 11/11,
  every fill at exactly half-spread (+0.5c) for $50. **The sports-illiquidity
  premise is unsupported at current parameters** — F=$1000 self-filters to
  markets with >=$876k lifetime volume.
- **Task 2 DONE** (~16:15 UTC): new `src/backtest_category.py` (+ additive
  `analysis:` config section) -> reports/category_backtest.md/.csv. Two halves
  split at 2026-04-02, cohort B, live cell, both exits, $50. Historical
  order-book depth data DOES NOT EXIST (stated in report); volume-proxy
  sensitivity tables included instead.
  Headlines: POLITICS profitable in BOTH halves under hold (+0.119 / +0.155
  PnL/$, 86%/73% win) — the only cross-half-robust category claim. SPORTS is
  H2-only evidence (+0.395 PnL/$, 70% win, n=76) — strong but single-half.
  CAVEAT found: H1 signal scarcity (25 vs 124) is largely a data artifact —
  the /trades 4k-per-wallet cap truncates active (esp. sports) wallets'
  history; only 20/62 sports cohort-B wallets have data reaching H1, vs 37/41
  politics. Exit strategies: politics hold-vs-copy REVERSES between halves
  (H1 copy slightly better, H2 hold much better) — not a robust category claim.
- **Task 4 DONE** (~16:20 UTC): findings report at
  `reports/category_analysis.md`. Bottom line: sports-illiquidity refuted at
  current params; POLITICS the only cross-half-replicated profitable category;
  SPORTS strongest where visible but single-half evidence; current data does
  NOT support a sports cap cut or category multiplier yet — sequencing
  recommendation in §6.
- **Task 5 DONE** (~16:25 UTC): proposal (diff, NOT applied) at
  `reports/proposals/fill_rate_vetting_proposal.md`. Reframed per evidence:
  raw fill-rate is uninformative post-fix (11/11); proposed
  `thin_market_share` (stake-weighted BUY volume in sub-$1M-volume markets,
  computed at vetting time, report-only) instead, with live fill telemetry
  deferred until skips actually occur.

## Session complete — all 5 tasks done

Files changed (all uncommitted, none touch live trading logic):
- NEW `src/category_stats.py` — per-category aggregation for reporting
- NEW `src/backtest_category.py` — rerunnable two-half category backtest
- `src/paper_status.py` — category table appended to check-ins
- `src/paper.py` — category table in daily_summary() ONLY (running process
  not restarted; picks this up on next restart)
- `config.yaml` — additive `analysis:` section (nothing live reads it)
- NEW reports: category_analysis.md (main deliverable), category_backtest.md,
  category_backtest.csv, proposals/fill_rate_vetting_proposal.md, this log
- DB (metadata only): 15,490 markets.category backfilled from the
  event_categories cache + 2 Gamma lookups; no trading tables touched

Landmines for next session:
- The 4k-per-wallet /trades cap makes pre-April history unreliable for
  active (esp. sports) wallets — any backtest reading H1 must say so.
- ensure_market() category gap: proposed one-line fix in
  category_analysis.md §7, not applied.
- Day-3 gate review 2026-07-08 13:00 UTC will effectively grade SPORTS only
  (all live signals are World Cup dailies; politics expected ~0.5/day).

# Session 2 — same day, owner away several hours

Priorities: (1) uncap trade history, (2) size×volume floor grid, (3) politics
deep-dive, (4) bootstrap CIs, (5) walk-forward if data supports, (6) update
category_analysis.md. Constraint: no live logic / weighting / caps / floors,
nothing committed.

## Log

- **P1 breakthrough (~17:0x UTC)**: /trades accepts an UNDOCUMENTED `end`
  (unix ts upper bound) param — verified live: filters timestamp < end,
  composes with offset, empty result below wallet start. This defeats the
  3000-offset cap by walking windows backwards. `get_trades` extended
  (additive param + rule-8 comment); config gains `analysis.full_pull`.
- NEW `src/ingest_full.py`: resumable deep pull, per-wallet checkpoints in new
  `full_history_progress` table (created by the script; nothing live reads
  it). Safety: only inserts trades older than now-24h (live detector reads
  last 12h), same dedupe key, WAL short transactions, least-active wallets
  first. Scale note: top cohort-B wallets trade ~4k/day (17k rows accumulated
  since 07-02 by the paper poll alone) -> full history may be 100k+ trades
  for a handful of whales; page budget 1200/wallet, truncations reported.
- Pull launched in background (~17:10 UTC), log at data/logs/ingest_full.log.
  Writing P2-P4 analysis scripts while it runs.
- NEW `src/deep_analysis.py` + config `analysis.floor_sweep/bootstrap/politics/
  walk_forward`: one read-only driver for P2 (floor grid, H1/H2 discipline),
  P3 (politics sub-topics/concentration/timing/volume), P4 (seeded bootstrap
  CIs), P5 (rolling walk-forward). Memory-bounded: loads only cohort BUYs >=
  $100; copy-exit sells fetched per signal market on demand.
- Walk-correctness scare, investigated and CLEARED (~17:2x UTC): two 'done'
  wallets appeared to have older API trades than the DB. Root cause of the
  discrepancy: DB-min-timestamp conflates walk coverage with insert
  eligibility (pre-2026 rows + outcome_index<0 rows are seen but not
  inserted). Direct verification: fetched both wallets' FULL API history and
  checked every eligible in-window row against the DB — 0 missing on both.
  Also confirmed /trades offset paginates the takerOnly-FILTERED set (a short
  page is genuine exhaustion), so the walk's termination logic is sound.
- deep_analysis.py shakedown run on mid-pull data (~17:51 UTC): all five
  analyses execute cleanly end-to-end. Fixed report defects found in the
  output (timing-bucket labels/order, Gamma noise-tag stoplist, per-category
  grid slices now rendered). Early signals from the mid-pull data, to be
  re-confirmed on the final run: politics H1 PnL/$ shrank to +0.033 with
  fuller coverage (was +0.119 on capped data); politics edge looks BROAD
  across wallets (without top-3: +0.122 PnL/$, 80% win on 60 closed);
  walk-forward window 4 (Apr) is NEGATIVE for politics (-0.110, n=16) —
  politics is not uniformly positive over time.
- Waiting on whale wallets to finish pulling (203/250 done, 281k trades
  added so far), then final analysis run + category_analysis.md v2.
- **P1 COMPLETE (~20:36 UTC)**: 250/250 wallets verified-full, 0 truncated,
  0 failed. 3.63M trades added in 52 min; trades table now 4.5M rows, DB
  ~5.1GB. Coverage: 184/250 wallets' history reaches the Apr-2 boundary,
  141/250 reach January — the shortfall is REAL WALLET AGE (verified full
  pulls), not truncation.
- **P2-P5 COMPLETE (~20:37 UTC)**: final deep_analysis.py run on full data.
  reports/deep_analysis.md + floor_sweep.csv regenerated.
- **P6 COMPLETE (~20:45 UTC)**: category_analysis.md v2 appended (§8-§13)
  with a banner pointing v1 readers forward. Headline changes:
  - Sports' missing H1 was cohort YOUTH not a cap artifact (only 23/62
    sports wallets existed pre-April even with full history) — permanent.
  - Politics downgraded: +0.047/+0.135 across halves, but edge = Iran-crisis
    geopolitics cluster (US-domestic politics NEGATIVE), mega-market
    dependent (Q4 +0.411 vs Q1 -0.109), top-3 wallets = 64% of attributed
    PnL, bootstrap PnL/$ CI includes zero, negative in 3/6 monthly windows.
  - Sports pooled PnL/$ CI excludes zero (+0.018..+0.495, n=126) but is
    98% World-Cup signals.
  - Floor grid mapped: F>=$500 profitable in BOTH halves at every volume
    floor; F<=$250 loses in H2 below V=$2M; V=$5M attractive even at live
    F=$1000. No changes made (owner constraint).

## Session 2 complete — all 6 priorities done

Additional files this session (uncommitted): src/ingest_full.py,
src/deep_analysis.py, reports/deep_analysis.md, reports/floor_sweep.csv,
config.yaml analysis additions, data_api.py get_trades(end=) param,
full_history_progress table in the DB. Live process untouched throughout.
