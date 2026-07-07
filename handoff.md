# handoff.md — Session Handoff (updated 2026-07-07 ~06:15 UTC, supersedes earlier 2026-07-07 version)

> For a fresh Claude session with no memory of prior conversations. Read this,
> then CLAUDE.md for standing rules. Previous session did a full day of
> category analysis on 2026-07-06 (owner-directed, autonomous); cleared for
> token cost, nothing wrong.

## 0. OVERNIGHT 2026-07-07 (owner asleep ~05:00–13:00 UTC): wallet-level skill verification

Owner-directed, autonomous, analysis+infrastructure only — **no live logic,
cohort, weights, caps, floors touched; no wallets added to any watchlist.**
Committed 2026-07-07 morning at the owner's request (together with the
2026-07-06 category-analysis outputs).

### TL;DR — the core question ("consistent persistent edge, or lucky run?")

1. **Wallet edges are real measurements, not pure noise.** Splitting each
   wallet's own history across *markets* (same period), edge on one half
   predicts the other: ρ=+0.22, permutation p=0.0006, n=221 wallets.
   Survives price-level control (per-share ρ=+0.20) and event-cluster
   leakage control (ρ=+0.21).
2. **Persistence across time is unproven — "we can't tell yet."** The clean
   test (Jan–May only; June excluded because cohort selection on the June
   leaderboard collider-biases anything containing it) gives ρ=+0.08,
   p=0.15 — below the ρ≈0.19 detectability floor at n=166. Not proven
   absent; unproven.
3. **The composite consistency score actively fails validation** — it
   *anti-predicts* held-out edge (ρ≈−0.18, p≈0.99, all three designs).
   Every consistency component individually anti-predicts (win rate −0.17,
   CI tightness −0.21, breadth −0.11): "consistency" proxies favorite-price
   buying, whose per-dollar edge is structurally tiny. Do not select on it.

**Census:** 45/250 wallets pass the strictest individual-consistency bar
(invariant across all tested threshold choices), 55/250 show no positive
copyable edge at all. Sports-young wallets got market-split tests only,
labeled `*_YOUNG` (breadth evidence, NOT persistence), per the task brief.

**P5 gate: NOT passed → new-wallet discovery skipped.** The only validated
signal is *same-period* reliability; discovery needs forward persistence,
which is exactly the unresolved part. Re-validation pre-registered for
~2026-08-05 on post-WC paper-era data, with pass criteria written down in
the proposal doc BEFORE anyone sees that data.

### Two data discoveries that outrank the analysis

1. **The entire trades table is TAKER-ONLY** (`takerOnly=true` is the API
   default; verified live). Measured per wallet: **median wallet does 84%
   of its trading as invisible maker fills** (139/250 wallets >80%; scratch
   table `wallet_maker_share`). The primary metric — *copyable entry edge*
   (payout − price over visible taker buys) — is immune by construction and
   is exactly what the bot copies. But cash-flow PnL from our data is
   unreliable, and all past **copy_exits backtest numbers were evaluated
   against ~16% of real exits** (live runs hold_to_resolution, unaffected).
   The MM roundtrip filter was also computed on taker-only data.
2. **24 of the 250 watchlist wallets have never made a single ≥$1000 buy**
   in six months — they can never fire a signal at the live floor (e.g.
   solomiy: real +0.33/$ edge, but entirely $20 bets on 5-minute crypto
   micro-markets). Also: the markets table now covers all ~222k markets the
   cohort ever traded (resumable `src/wallet_quality_fetch.py`; 222
   genuinely gone from Gamma → `data/wq_fetch_misses.json`; categories on
   new rows are NULL — no event lookups were done).

### Where everything lives

- `reports/wallet_quality_analysis.md` — full report (**read the executive
  summary first**), + `wallet_quality_scores.csv` (all 250 wallets) and
  `wallet_quality_eligible.csv` (signal-eligible slice)
- `reports/proposals/quality_weighted_cohort_proposal.md` — P6 draft, **not
  applied**; recommends no switch now, pre-registers the August
  re-validation, and explains why a naive quality switch would gut sports
  to ~10 wallets
- `archive/autonomous_log_2026-07-07.md` — full chronology incl. dead-ends
- New infra: `src/wallet_quality.py` / `wallet_quality_fetch.py` /
  `wallet_quality_report.py`; additive `analysis.wallet_quality` config
  block; scratch DB `data/wq_positions.sqlite` (gitignored). All analysis
  ran on read-only connections against the live DB.

Report §0 lists the standing caveats (survivorship, June-selection
collider, price-level confound) — don't quote any wallet edge number
without them. Accounting was spot-verified to the cent against raw trades.

Paper checked three times overnight (read-only): healthy, 24 fills, 52% win
rate (**AT RISK vs the 55% gate line — owner's day-3 call on 2026-07-08**),
decay −1.46¢/share, no watchdog restarts. Day-2 check-in backstop task
fires ~09:03 EDT.

## 1. Current state

- **Paper trading is LIVE and untouched**: cohort B (250 wallets), N=5 W=12h
  F=$1000 hold, $50/position. As of 2026-07-07 00:40 UTC: **21 fills
  (6 open, 15 closed), 53% win rate, +$43.88 realized, −$64.13 MTM**, mean
  decay −1.13¢/share. PID in `data/logs/paper.pid`, resurrected by scheduled
  task **pm-copybot-paper-watchdog** (disable it first if stopping on purpose).
- The 2026-07-06 category-analysis outputs (list in §5) and the 2026-07-07
  wallet-quality outputs (§0) were **committed 2026-07-07 morning** at the
  owner's request. No changes to live trading logic, cohort weighting,
  category caps, or size/volume floors were made in either session.
- `src/paper.py` got a reporting-only edit (category table in
  `daily_summary()`); the RUNNING process predates it and picks it up on its
  next restart. Do not restart just for that.
- Day-3 **decision gate review due 2026-07-08 09:00 EDT**; day-2 check-in due
  2026-07-07 ~09:06 EDT (`python src\paper_status.py`, then sanity-check
  `data/logs/watchdog.log`; backstop scheduled tasks pm-copybot-checkin-day2/3
  regenerate `reports/paper_dashboard.md` (the single paper report; old paper_checkins/paper_daily archived 2026-07-07)). Gate criteria: config
  `paper.gate` + PLAN.md.
- API keys in gitignored `.env` — never read/print/log/commit. `live.py`
  stays a stub; no order/wallet/key code without direct owner authorization.
- DB is now ~5.1GB (4.5M trades) after the deep history pull (§2).

## 2. Key findings — v2 deep analysis (2026-07-06)

Full story: `reports/category_analysis.md` §8–§13; tables in
`reports/deep_analysis.md`. Basis: FULL uncapped trade history — an
undocumented `end` param on `/trades` defeats the 3000-offset cap;
`src/ingest_full.py` pulled 250/250 wallets complete (3.63M trades added,
0 truncated, 0 failed, completeness spot-verified).

- **Sports cohort-youth**: only 23/62 sports cohort-B wallets traded at all
  before April (vs 39/41 politics). The earlier "sports H1 is a data
  artifact" theory is dead — the cohort is World-Cup-era young, so
  single-period sports evidence is PERMANENT. Sports' pooled PnL/$ CI is the
  only one excluding zero (+0.018..+0.495, n=126) but is 98% WC signals.
- **Politics downgrade**: replicates in sign across halves (+0.047 H1 /
  +0.135 H2, ~72% win) BUT: the edge is the Iran-crisis geopolitics cluster
  (US-domestic politics is NEGATIVE, Trump-tag −$157); it lives in
  mega-markets (top volume quartile +0.411, bottom quartile −0.109); top-3
  wallets carry 64% of attributed PnL (+0.033/$ without them); bootstrap
  PnL/$ CI **includes zero** (−0.097..+0.318); walk-forward negative in 3 of
  6 monthly windows (positives coincide with geopolitical event clusters).
- **Floor grid** (the actionable map): **F≥$500 is profitable in BOTH halves
  at every volume floor** (25/35 cells qualify). F≤$250 loses in H2 below
  V=$2M. V=$5M lifts even the live F=$1000 cell (+0.055→+0.119 H1,
  +0.222→+0.307 H2). Grid: `reports/floor_sweep.csv`.
- Also standing from v1: the 27/29 "skipped sports signals" were stale-feed
  artifacts (market already resolved), NOT illiquidity; live fills go off at
  half-spread; sports illiquidity is refuted at current params.

## 3. Current verdict

**No sports cap cut. No category multiplier.** Both categories' edges are
event/period-driven (World Cup; Iran crisis) — a static category weight
cannot capture that, and the statistical support isn't there (politics CI
includes zero; sports is one-period). Evidence, not policy: nothing changed.

## 4. Decisive open tests (owner-agreed sequencing)

1. **Politics live test (~2 months)**: at ~0.5 politics signals/day, paper
   accumulates n≈30 politics fills by ~early September. The Iran cluster has
   partly resolved — if the edge was event-specific it won't reappear.
2. **Sports persistence test (mid-July onward)**: World Cup ends mid-July;
   the weeks after are the natural experiment for whether sports consensus
   survives the tournament.
3. Day-3 gate (2026-07-08) proceeds as planned — it effectively grades
   WC-sports copying only (all live signals so far are sports).
4. If floors are ever revisited post-gate: F≥$500 is the safety boundary,
   V=$5M the quality lever — as a sweep-validated config change, never a
   category cap.

## 5. Where everything lives (2026-07-06 outputs, all uncommitted)

| path | what it is |
|---|---|
| `reports/category_analysis.md` | Main findings doc; §1–7 = v1 (capped data), §8–13 = v2 (full data) — read v2 first |
| `reports/deep_analysis.md` | All v2 tables: floor grid, politics dive, bootstrap CIs, walk-forward |
| `reports/floor_sweep.csv` | Machine-readable F×V grid results per half |
| `archive/category_backtest.md` / `.csv` | v1 two-half category backtest (superseded by deep_analysis but kept for audit) |
| `archive/autonomous_log_2026-07-06.md` | Chronological log of both autonomous sessions, incl. dead-ends and the walk-verification scare |
| `reports/proposals/fill_rate_vetting_proposal.md` | Draft diff (NOT applied): `thin_market_share` discovery vetting metric |
| `src/ingest_full.py` | Deep-history puller (resumable, checkpoints in `full_history_progress` table); rerun-safe |
| `src/deep_analysis.py` | Rerunnable v2 analysis driver (P2 grid, politics dive, bootstrap, walk-forward) |
| `src/backtest_category.py` | v1 two-half category backtest script |
| `src/category_stats.py` | Per-category aggregation used by paper_status.py + paper.py daily summary |
| `src/paper_status.py` / `src/paper.py` | Modified: category breakdown table appended to check-ins / daily summary (reporting only) |
| `src/data_api.py` | Modified: `get_trades(end=...)` param + rule-8 comment documenting the undocumented API behavior |
| `config.yaml` | Modified: additive `analysis:` section (floor_sweep, bootstrap, politics, walk_forward, full_pull) — nothing live reads it |

## 6. Data gaps & caveats (do not paper over these)

- **No historical order-book depth exists anywhere** (hourly candles only;
  Gamma `liquidity` is a present-day snapshot). All liquidity reasoning uses
  lifetime market volume as a LABELED proxy. Only ground truth: live paper
  fills ($50 at half-spread in >$2M markets).
- **Politics wallet-concentration is unstable**: mid-pull run said edge
  survives top-3 removal (+0.122/$); full-data run said it thins to
  +0.033/$. The question is unanswerable at n≈87 — don't cite either number
  without this caveat.
- **Sports early-history gap is real cohort youth** — re-pulling cannot fix
  it; only post-WC live data can.
- Survivorship bias applies to ALL backtest numbers (watchlist selected on
  the same window it's tested on; OVERVIEW.md caveat).
- `ensure_market()` in paper.py never backfills `category` on cached market
  rows (fix proposed in category_analysis.md §7, NOT applied; offline
  backfill done 2026-07-06 — 0 uncategorized paper trades remain).
- Categories on wallets are comma-lists; `markets.volume` is lifetime volume
  as of fetch time (undercounts still-open markets).

## 7. Old operational landmines (still true, from the prior handoff)

1. Never use the global `/trades` feed for collection — it silently drops
   ~95% of watchlist trades when busy. Per-wallet rotating poll only.
1b. `/trades` is TAKER-ONLY by default and ALL ingested history is taker-only
   (2026-07-07). Median watchlist wallet is 84% maker — never treat our
   trades table as a wallet's full activity, and never compute cash-flow
   PnL from it without the `cash_dirty`/maker-share caveats (see §0).
2. Late-detected signals (>30 min) are recorded STALE, never entered.
3. `paper_trades.pnl_20` is the realized-PnL column regardless of stake
   (legacy name); `position_usd` is the stake at open — never reprice.
4. Windows liveness checks: use `tasklist`, NOT `os.kill(pid, 0)` (it kills).
5. Reconfigure stdout to UTF-8 in any new CLI entry point (emoji usernames).
6. Transient ConnectionResetError/DNS warnings in paper logs self-recover.

## Quick health check

```powershell
python src\paper_status.py
Get-Content data\logs\watchdog.log -Tail 3
python -c "import sqlite3,time; c=sqlite3.connect('data/copybot.db'); print('trades last hour:', c.execute('SELECT COUNT(*) FROM trades WHERE ingested_at >= ?', (int(time.time())-3600,)).fetchone()[0])"
```
Healthy ≈ paper PID alive, no new watchdog restarts, hundreds+ trades/hour.
