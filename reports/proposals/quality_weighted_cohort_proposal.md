# PROPOSAL (draft, NOT applied): quality-score-weighted cohort selection

> Written 2026-07-07 (autonomous overnight session) per owner task item 6.
> Status: **recommendation is to NOT switch now** — this doc exists so the
> decision is explicit, the tradeoffs are on paper, and the upgrade path is
> pre-registered before anyone sees post-WC data (no metric-shopping later).
> Basis: `reports/wallet_quality_analysis.md` (esp. §3 gates, §7 decision).

## The three options

### A. Status quo — category-based cohort B (current live config)

Selection = top-250 by leaderboard PnL/volume, category caps at the union
level. Wallet-level skill plays no role beyond the discovery filters.

- For: it's what the paper gate is currently measuring; changing selection
  mid-gate destroys the experiment. Its known weakness (event/period-driven
  category edges) is already documented and being tested live.
- Against: tonight's census says 22% of the cohort (55 wallets) showed no
  positive copyable edge over their own 6-month history, and their inclusion
  cost is real (they participate in 19 of the live signal attributions so far).

### B. Switch to quality-score weighting — REJECTED at this time

Replace/weight selection by the wallet quality score.

- **Killer fact:** the composite score ANTI-predicts held-out edge
  (ρ≈−0.18, p≈0.99, all three validation designs). Switching now would
  systematically tilt the cohort toward high-win-rate favorite-price buyers
  with structurally tiny per-dollar edges — measurably worse than random.
- Even the raw copyable edge, which IS reliable same-period (ρ=+0.22,
  p=0.0006), has unproven month-to-month persistence (+0.08, p=0.15,
  under-powered) — and *persistence* is the only thing a selection switch
  actually buys.
- Owner's anticipated failure mode confirmed: a quality-selected cohort
  would concentrate hard. The strict-CONSISTENT set is 45 wallets, 13 of
  them politics; sports would shrink from 65 to ~10 (6 CONSISTENT + 4
  CONSISTENT_YOUNG), i.e. "keep a handful of politics/crypto wallets and
  gut sports" — while sports is the only category whose pooled signal CI
  currently excludes zero.

### C. Hybrid with pre-registered re-validation — RECOMMENDED PATH

Nothing changes now. Concretely:

1. **Keep cohort B and the day-3 gate exactly as they are.**
2. **Pre-register the wallet metric** (this doc): raw copyable edge per
   wallet (PnL/$ AND per-share, market-level positions, exactly as
   implemented in `src/wallet_quality.py`), NOT the composite score.
   Constraint from report §10: every consistency-flavored component
   (win rate, CI tightness, breadth, walk-forward stability) tested
   *individually* anti-predicts held-out edge — a future score may
   shrink or price-control raw edge, but must not blend in consistency
   aesthetics.
3. **Re-validation date:** ~2026-08-05 (30 days of post-selection,
   post-WC paper-era data), rerun with the July+ window as the held-out
   half. **Pre-registered pass criteria** (all three):
   - raw-edge persistence Spearman > 0 with permutation p < 0.05;
   - top-vs-bottom quintile held-out edge gap > 0;
   - result survives the per-share (price-controlled) variant.
4. **If passed:** introduce quality as a *within-category tilt* (e.g.
   overweight top-half wallets per category, never crossing existing
   category caps), sweep-verified against the backtest grid first. This
   preserves category structure and the sports cohort while pruning the
   long tail — the failure mode of a full switch (concentration into 2–3
   categories) is structurally impossible by design.
5. **If failed again at n≈250 wallets:** accept that wallet-level skill is
   not selectable at our sample sizes; wallet quality work stops being a
   selection question and becomes a risk question (e.g. cap per-wallet
   signal participation).

## Tradeoffs stated plainly

- Waiting costs ~a month during which known-NO_EDGE wallets keep
  contributing signals. Cutting them early is tempting and WRONG at current
  evidence: the §3 held-out tests show the bottom quintile performed fine
  out-of-sample (quintile gaps are negative) — the negative tail is mostly
  the same luck-noise as the positive tail, mirrored.
- The re-validation itself is slightly optimistic-biased if July has its own
  event cluster (persistence of event participation, not skill). The
  per-share criterion and the category-tilt-only application bound the
  damage of a false pass.
- If the owner wants ONE low-risk action now: the only defensible one is a
  **participation cap** (no single wallet in more than X% of live signals),
  which is luck-neutral and needs no skill claim. Not configured tonight —
  it touches live signal logic, which was out of scope.
