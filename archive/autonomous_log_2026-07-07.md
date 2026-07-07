# Autonomous session log — 2026-07-07 (overnight, owner asleep ~05:00–13:00 UTC)

Mission (owner instruction, verbatim scope): wallet-level skill verification for
all 250 cohort-B watchlist wallets. Analysis + infrastructure ONLY. Constraints:

- NO changes to live trading logic, cohort membership, weighting, caps, floors.
- NO new wallets added to the live watchlist (discovery output = candidate list only).
- Nothing committed.
- Step 5 (new-wallet discovery) is GATED: only if the quality score demonstrably
  distinguishes skill from noise (plan: score computed on H1 must predict H2
  edge out-of-sample across wallets; if not, say so and stop).

Plan:

1. **P1 per-wallet consistency**: split-half (time) + walk-forward on each
   wallet's OWN trade history; market-split fallback for young wallets.
2. **P2 quality score**: edge consistency, bootstrap CI on own trades,
   win-rate stability, concentration (lucky-trades vs broad edge). Rank all 250.
3. **P3 vs current cohort**: poorly-scoring incumbents, per-category view.
4. **P4 structural correlates** + the "is this distinguishable from noise" verdict.
5. **P5 conditional discovery** (gated on P4 verdict).
6. **P6 proposal draft** (not applied) for quality-weighted selection.
7. Outputs: `reports/wallet_quality_analysis.md`, updated `handoff.md`, this log.

Method decisions (made up front, before results, to avoid metric-shopping):

- Unit of observation = per (wallet, market) NET position PnL, not per trade —
  a wallet spamming 50 buys in one market is ONE bet, not 50 observations.
  PnL(wallet, market) = sells_usd − buys_usd + net_final_shares × resolution
  payout, over resolved markets only. Shares = size_usd / price (API size
  is shares; size_usd stored = shares×price).
- Edge metric = PnL per dollar of buy stake (matches cohort-B/C spirit).
- All analysis on trades with `timestamp < analysis.window_end_utc`
  (2026-07-02) — same cutoff as deep_analysis.py, avoids the paper-poll
  watchlist-skew tail.
- Read-only DB connections (mode=ro); outputs to reports/ + a separate
  scratch SQLite in data/ (gitignored) if caching is needed. Live DB never
  written.
- Bootstrap seeded (reuse config analysis.bootstrap.seed) for reproducibility.
- Honest-uncertainty rule: every number reported with n; anything below
  analysis.bootstrap.min_n_report stated as "cannot tell", not estimated.

## Timeline

- **05:03 UTC** — Session start. Read handoff.md, config.yaml, db.py,
  deep_analysis.py schema/conventions. Paper trading untouched (will do a
  read-only health check mid-session). Day-2 check-in (~13:06 UTC) has a
  backstop scheduled task; owner returns around then.
- **05:05 UTC** — Phase A: per-wallet coverage census starting.
- **05:07 UTC** — Census: all 250 cohort-B wallets have verified-full history;
  median 999 trades / 308 markets / 178-day span, but min 3 trades and max
  397k (bot-grade). Big gap found: **222k of 280k distinct traded markets are
  absent from the markets table** (13.9% of stake) — table only ever got
  signal/vetting markets, a selection-biased subset. Per-wallet PnL on that
  subset would be biased, so fetching ALL missing market resolutions from
  Gamma (ordered by stake desc, resumable): `src/wallet_quality_fetch.py`,
  log `data/logs/wq_fetch.log`. Additive `analysis.wallet_quality` config
  block added. ETA ~40 min at observed rate.
- **05:10 UTC** — One fetch batch 422'd (empty condition_id in trades) — query
  filter fixed for the cleanup rerun; ~20 ids affected, rest unaffected.
- **05:14 UTC** — `src/wallet_quality.py` built and shaken down end-to-end on
  current coverage (86% of stake): 3.9M trades → 584,040 (wallet, market)
  positions: 182,642 RESOLVED ($488M stake), 313k UNKNOWN_MARKET ($32M,
  avg $102 — the fetch will convert these), 58,730 DIRTY ($44M — pre-2026
  inventory detected via negative net shares, excluded by design), 29.5k
  UNRESOLVED. Battery (split-half, walk-forward, market-split, bootstrap CI,
  concentration) runs for all 250 wallets in ~90s.
- **05:14 UTC** — ⚠️ **PRELIMINARY gate result (partial data — do not cite
  yet)**: H1-only quality score vs H2 edge across 187 splittable wallets:
  Spearman **−0.03** (perm p=0.66), top-vs-bottom-quintile H2 edge gap
  **−0.009/$**. On this pass the score has NO out-of-sample predictive power —
  consistent with "category/cohort selection already ate the signal, the rest
  is noise". Will re-run on full coverage before concluding. Note both
  quintiles' H2 edge is ~+0.05/$ — survivorship (cohort was selected partly on
  this window) inflates ALL these levels; the gate tests only SEPARATION.
- **05:16 UTC** — 🚨 **Major data caveat discovered (project-wide, not just
  tonight): the entire trades table is TAKER-ONLY** (`takerOnly=true` is the
  /trades default; verified `takerOnly=false` returns more). Maker fills are
  invisible → cash-flow PnL accounting is systematically wrong for
  passive-exit wallets (explains 52/235 sign disagreements vs leaderboard
  pnl_all, e.g. hot2trot computed −$538k vs +$1.16M lifetime). Also means
  paper's copy-exit detection is partially blind to maker exits (standing
  caveat, not fixable tonight). `/positions` endpoint checked as ground-truth
  alternative: **current holdings only** (12 rows for a 40k-market wallet) —
  dead end for history.
- **05:18 UTC** — Metric reframe (methodological upgrade, not a workaround):
  PRIMARY skill metric = **copyable entry edge** — stake-weighted
  (payout − price) over the wallet's visible taker BUYs, i.e. exactly what
  copying this wallet's signals to resolution earns. Computable exactly from
  existing data; immune to the maker hole (the bot can only copy visible
  buys anyway) and matches the live exit strategy (hold). Cash-flow PnL kept
  as SECONDARY with per-position consistency flag (`cash_dirty`).
  Median wallet copyable edge +0.05/$, 190/248 positive — levels are
  survivorship-inflated by construction; only cross-wallet SEPARATION and
  persistence are informative.
- **05:24 UTC** — Rerun on improved coverage (fetch landing: RESOLVED
  positions 182k→305k, unknown stake $32M→$8.3M). Gate now **NEGATIVE**:
  Spearman(H1 score, H2 edge) = −0.186 (p≈1.0 one-sided), quintile gap
  −0.063/$. BUT this may be **collider bias**, not true anti-persistence:
  cohort selection used the June leaderboard and June is inside H2 —
  conditioning on selection induces exactly this negative correlation
  (weak-H1 wallets needed a lucky June to be here at all). Fix in progress:
  (a) persistence gate restricted to PRE-selection data (Jan–May, June
  excluded from the outcome side), (b) separate market-split RELIABILITY
  gate (is the edge measurable at all, same-period), so period-driven edges
  and pure noise can be told apart.
- **05:30 UTC** — Three-gate results on ~95% coverage (still interim):
  raw copyable edge shows real same-period reliability (market-split
  ρ=+0.21, n=221) and weak/ambiguous cross-time persistence (+0.08, n=166,
  pre-selection). The composite consistency score ANTI-predicts held-out
  edge in every design (ρ −0.17..−0.20) — favorite-buyers score high on
  consistency but have structurally tiny PnL/$; longshot-buyers score low
  with fat-tailed edges. Composite as designed is NOT usable for selection;
  price-level confound needs explicit treatment (per-share edge + price
  buckets added). Gates now also emit per-wallet train/test halves for
  category slicing; power analysis added to report (at n≈166–221 only
  ρ≥~0.17–0.19 is detectable).
- **05:32 UTC** — Mid-session paper health check (read-only): 24 fills,
  52% win rate (AT RISK vs 55% gate line), decay −1.46¢/share (fine), no
  new watchdog restarts. Nothing touched; owner's day-3 review tomorrow.
- **05:35 UTC** — Fetch at 64% (142k/222k, 169 misses). Report generator
  `src/wallet_quality_report.py` written; final pipeline rerun after fetch.
- **05:36 UTC** — Accounting spot-verified: 23/23 positions of a sample
  wallet match hand-recomputation to the cent; hold-vs-cash divergence
  behaves correctly on a sold-early position.
- **05:40 UTC** — 🚨🚨 **Maker-share probe, all 250 wallets (recent ~1000
  trades each, all-side vs stored taker-only): median maker share 84%;
  139/250 wallets >80%; only 25 wallets <20%.** We see a small behavioral
  sliver (their aggressive taker trades) of most watchlist wallets. The
  copyable-edge metric is still the RIGHT metric (it prices exactly the
  slice the bot can see and copy — crossing the spread = conviction), but:
  (a) per-wallet n is a thin behavioral sample for high-maker wallets;
  (b) the copy_exits backtest arm was largely fictional (84% of exits were
  never visible) — good thing hold_to_resolution won and is live;
  (c) leaderboard vol vs our ingested volume mismatches explained.
  Saved per-wallet to scratch `wallet_maker_share`, joined into CSV +
  correlates. Ran at 0.35s throttle to protect paper.py's shared host.
- **05:49–06:01 UTC** — Gamma fetch DONE: 221,635/221,858 markets landed
  (222 genuinely absent from Gamma → `data/wq_fetch_misses.json`; cleanup
  rerun caught the 422 batch). Final pipeline on FULL coverage: 505,598
  resolved positions, $564M stake; unknown-market stake now $213k (0.04%).
  Final gates: reliability +0.224 (p=0.0006) / +0.203 per-share (p=0.0009);
  clean persistence +0.081 (p=0.15, under-powered); composite score
  anti-predicts everywhere (ρ≈−0.18, p≈0.99). Report + CSV generated;
  exec summary, §7 P5-SKIP decision, §8 recommendations written;
  proposal drafted (`reports/proposals/quality_weighted_cohort_proposal.md`);
  handoff.md §0 rewritten; API-quirks memory updated (taker-only, maker
  share, /positions current-only).
- **06:05–06:15 UTC** — Flagship due diligence (report §9): flawfence real
  but one Korean-election cluster inflates its n; solomiy = 4,890 five-minute
  crypto micro-market positions at $20 median — real edge, ZERO
  signal-eligible positions. Added `max_buy_usd` to positions; built
  signal-eligible slice (`reports/wallet_quality_eligible.csv`): 24/250
  wallets have NO ≥$1000 buy in 6 months (can never fire a signal at the
  live floor); rankings robust to floor restriction (ρ=0.93); eligible-slice
  reliability ρ=+0.135 p=0.042.
- **06:30–06:40 UTC** — Robustness checks (report §10): event-cluster split
  reliability ρ=+0.213 p=0.0005 (headline result NOT an intra-event
  correlation artifact); per-component analysis — EVERY consistency
  component individually anti-predicts held-out edge (CI lower −0.21, win
  rate −0.17, walk-forward −0.13, breadth −0.11) vs raw edge +0.08. Any
  future score must be raw-edge-based; constraint added to the proposal.
- **06:45 UTC** — Session wrap. All deliverables in place:
  `reports/wallet_quality_analysis.md` (exec summary + §0–10),
  `reports/wallet_quality_scores.csv`, `reports/wallet_quality_eligible.csv`,
  `reports/proposals/quality_weighted_cohort_proposal.md`, handoff.md §0,
  this log. Constraints honored: no live logic / cohort / weights / caps /
  floors touched; no wallets added anywhere; nothing committed; live DB only
  ever written by the market-metadata fetch (additive cache rows, same as
  ingest); all analysis on read-only connections + scratch
  `data/wq_positions.sqlite`. Paper untouched and healthy at last check.
- **06:55 UTC** — Threshold-sensitivity check: strict-pass census (45) and
  NO_EDGE census (55) are IDENTICAL under all five tested threshold combos
  (n≥30/40/60 × span≥45/60/90d) — table appended to report §10. Final paper
  health check: 24 fills, 52% win rate, no new watchdog restarts. Session
  work complete; artifacts final. Remaining owner-morning items: day-2
  check-in backstop fires ~13:03 UTC; day-3 gate review 2026-07-08 13:00 UTC.
