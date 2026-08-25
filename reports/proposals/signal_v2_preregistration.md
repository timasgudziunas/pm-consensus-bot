# Signal v2 pre-registration — consensus post-filters

_Drafted 2026-08-25, BEFORE any v2 backtest code was written or run. Owner
sign-off required on the arms and adoption rule below before execution.
Criteria are fixed once signed off — no metric-shopping, no post-hoc arms._

## Motivation (settled evidence, not re-litigated here)

`reports/copy_gap_analysis.md` (2026-08-17, regenerated 2026-08-25): the
consensus mechanism adversely selects — signal-forming trades score
−0.157 PnL/$ vs the same wallets' +0.072 overall, and the copied trades lose
even at the wallets' own prices (−2.85¢/share SPORTS wallet counterfactual).
Favorite anatomy: the 0.8–1.0 entry-price bucket won 73% vs an 88% breakeven
requirement (−$95); only the 0.6–0.8 bucket was net positive (+$39).
`reports/persistence_checkpoint.md`: wallet skill persistence is plausibly
real but weak (rho ≈ +0.14–0.18).

**Hypothesis-formation contamination (stated up front):** all arms below were
suggested by the paper-period fills (2026-07-05 onward). The paper window is
therefore NOT independent validation; it is reported as a counterfactual with
bootstrap CI, never as sole grounds for adoption. The backtest train/validate
windows predate the paper period and were not used to form these hypotheses —
but the BASE parameters (N=5, W=12h, F=$1000, hold) were tuned there, so
absolute simulated PnL is not trustworthy either. **All judgments are
RELATIVE: arm vs base, inside the same window and simulator.**

## Arms

All arms are post-filters applied to the base signal stream (N=5, W=12h,
F=$1000, hold_to_resolution, cohort B). `signals.py` is NOT modified; filters
act on already-detected signals. Parameters live in config `analysis.signal_v2`.

- **A. No-favorites:** drop signals with entry price > 0.80. Mechanism:
  structural favorite-longshot asymmetry — a favorite's payout markup is too
  small to cover its breakeven win rate.
- **B. Mid-band:** keep only 0.20 ≤ entry price ≤ 0.80 (A plus dropping
  longshots < 0.20, which went 0-for-2 and have the worst decay exposure).
- **C. Quality-gated:** require ≥ 3 of the 5 consensus wallets to be in the
  top half of cohort B by past entry edge. Ranking computed ONCE on the train
  window (Jan–Apr) only — no lookahead into validate or paper windows.
- **D. Fade (descriptive only, no adoption path this cycle):** take the
  opposite outcome at 1 − price. Suggested by the −0.157 PnL/$ selection
  finding; n is far too small to adopt on one cycle, so this arm is reported
  for information only.

## Evaluation windows

| window | data | role |
|---|---|---|
| Train (first 4 months of ingested history, per config `backtest.train_months`) | ingested trades + candles | guard: arm must not be negative where base was ≈ flat (+$89) |
| Validate (remainder through 2026-07-02) | same | primary: arm vs base, out-of-sample w.r.t. hypothesis formation |
| Paper counterfactual (fills since 2026-07-05) | actual 68 closed paper fills | secondary: filtered realized expectancy + bootstrap CI (contaminated — formed the hypotheses) |

## Pre-registered adoption rule (ALL must hold for an arm to replace the live paper config)

1. **Validate:** arm expectancy per $ staked ≥ base expectancy per $ in the
   same window, AND arm retains ≥ 40% of base fills (no cherry-cell starvation).
2. **Train:** arm expectancy per $ ≥ 0.
3. **Paper counterfactual:** filtered fills' realized expectancy ≥ 0.00/$
   (base: −0.080/$) over ≥ 20 retained fills.
4. **Neighborhood robustness:** for price-cutoff arms (A, B), shifting each
   cutoff by ±0.05 keeps the validate improvement's sign. For arm C, the gate
   at ≥ 2-of-5 and ≥ 4-of-5 keeps the validate improvement's sign.

Tie-break if multiple arms pass: best paper-counterfactual expectancy; then
fewer fills dropped.

## Expected-outcome clauses

- **No arm passes:** verdict = "post-filters cannot salvage the consensus
  mechanism." This is a REAL possible outcome, feeds the standing
  event-season-only vs wind-down decision, and does NOT license inventing new
  arms this cycle.
- **An arm passes:** flip config `paper` to it (config-only change; signals.py
  gains a config-driven post-filter applied identically in backtest and
  paper), reset `gate_start_utc`, and evaluate against the rewritten
  net-expectancy gate on fresh fills — realistically once September sports
  volume returns.
- **Ambiguous (passes 1–3, fails 4):** do not adopt; document and hold.

## Standing caveats (inherited, attach to every number)

- Taker-only trades feed; survivorship bias on cohort selection; validate
  window is WC-inflated; simulator-vs-paper calibration gap is unresolved
  (base validate showed +29% ROC while live paper showed −0.080/$ in an
  overlapping regime — this is exactly why judgments are relative-only).
- Jul 16–17 ingestion outage: paper-window signals near those dates may be
  undercounted; affects the counterfactual denominator, not the backtest.
