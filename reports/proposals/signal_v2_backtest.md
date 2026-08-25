# Signal v2 post-filter backtest -- generated 2026-08-25 16:19 UTC

Pre-registration: `reports/proposals/signal_v2_preregistration.md` (frozen before this script was run; criteria below are applied mechanically, no post-hoc arms). Engine: `src/backtest_signal_v2.py`, reusing `backtest.py`'s `evaluate_signal`/pricing and `signals.py`'s `detect_signals` unmodified. Base cell: cohort B, N=5, W=12h, F=$1000, hold_to_resolution, $100/position.

## Amendment 2026-08-25 & calibration note (read before the numbers below)

Full text: `reports/proposals/signal_v2_preregistration.md` section "Amendment 2026-08-25", written and committed BEFORE any arm was evaluated. The original sanity gate (reproduce `backtest_report.md`'s 2026-07-03 base cell within +/-10%) failed structurally: DB forensics showed only 10% of cohort-B's clipped trades existed when that report was generated; a 2026-07-06/07 deep-history backfill (`ingest_full.py`) grew the data ~10x, with cohort membership unchanged (100% overlap). **The gate was accordingly narrowed to a PnL-only calibration check, and the base reference for every arm-vs-base comparison below is this run's OWN today's-DB base simulation (validate: 157 signals, +3307.60), not the stale report.**

**Calibration: PASS** -- reproduced validate PnL $+3307.60 vs original $+3482.39 (-5.0%, tolerance +/-10%) -- informational only, does not gate arm evaluation. Signal/closed counts (157 vs 122, 157 vs 119) are EXPECTED to differ (more historical data now) and are not part of the gate.

Diagnosis (ingestion-timing forensics):

Cohort-B trades strictly before analysis.window_end_utc (2026-07-02T00:00:00Z), grouped by the DB row's actual `ingested_at` date: 2026-07-03: 383,244; 2026-07-06: 802,910; 2026-07-07: 2,723,612. Of 3,909,766 such trades now in the DB, only 383,244 (10%) were ingested on or before 2026-07-03, the date backtest_report.md (the calibration reference) was generated (09:47 UTC). The remainder was ingested on 2026-07-06/07 -- almost certainly `ingest_full.py`'s deep-history backfill (config `analysis.full_pull`, run 2026-07-07 overnight per the wallet_quality section), which walks `/trades` backwards past the original ingest's 3000-offset/4000-trade-per-wallet cap. Cohort-B wallet MEMBERSHIP is unchanged since 2026-07-03 (both `discovered_at` timestamps for cohort-B wallets are 2026-07-03; a spot-check against reports/persistence_checkpoint_wallets.csv's 179-wallet eligible subset shows 100% overlap with the current cohort-B set) -- this rules out cohort redefinition. Per the pre-registration's Amendment 2026-08-25 (written and committed BEFORE any arm was evaluated), this is a structural, diagnosed data-growth effect, not a bug, and the sanity gate was accordingly narrowed to a PnL-only calibration check that does not block arm evaluation -- the base reference for every arm-vs-base comparison below is this run's own today's-DB base simulation.

## Base-cell reproduction (today's-DB base -- THE reference for all arms below)

| window | n signals | n closed | win rate | total PnL |
|---|---|---|---|---|
| train | 63 | 60 | 70% | +12.54 |
| validate | 157 | 157 | 69% | +3307.60 |

Train/validate boundary and global trade range logged at run time (see console log); train = first `backtest.train_months` months of the clipped (pre-`analysis.window_end_utc`) cohort-B data, validate = remainder, exactly matching `backtest.py`'s split.

## Train-window quality ranking (arm C)

203 cohort-B wallets ranked (>= 10 resolved train BUYs on resolved markets); top half by stake-weighted entry edge = 102 wallets. All other cohort-B wallets (unranked or bottom half) count as not-top-half.

## Per-arm-per-window metrics

Expectancy = sum(closed PnL) / sum(closed-position stake); retention = n retained / n base-window signals (all entered, resolved or not).

| arm | window | n retained | retention | n closed | win rate | total PnL | expectancy/$ |
|---|---|---|---|---|---|---|---|
| base | train | 63 | 100% | 60 | 70% | +12.54 | +0.0021 |
| base | validate | 157 | 100% | 157 | 69% | +3307.60 | +0.2107 |
| base | paper | 68 | 100% | 68 | 56% | -276.29 | -0.0813 |
| A | train | 46 | 73% | 44 | 64% | +101.65 | +0.0231 |
| A | validate | 124 | 79% | 124 | 65% | +3584.62 | +0.2891 |
| A | paper | 53 | 78% | 53 | 49% | -194.40 | -0.0734 |
| B | train | 44 | 70% | 42 | 64% | -163.47 | -0.0389 |
| B | validate | 117 | 75% | 117 | 68% | +2631.39 | +0.2249 |
| B | paper | 51 | 75% | 51 | 51% | -94.40 | -0.0370 |
| C | train | 34 | 54% | 33 | 79% | +201.63 | +0.0611 |
| C | validate | 53 | 34% | 53 | 68% | +859.81 | +0.1622 |
| C | paper | 14 | 21% | 14 | 64% | +17.43 | +0.0249 |
| D | train | 63 | 100% | 60 | 30% | -1883.52 | -0.3139 |
| D | validate | 157 | 100% | 157 | 31% | -2268.56 | -0.1445 |
| D | paper | 68 | 100% | 68 | 44% | +1446.06 | +0.4253 |

Paper counterfactual bootstrap 95% CI on filtered expectancy (10,000 iters, seed 20260825):

| arm | n | mean | CI lo | CI hi |
|---|---|---|---|---|
| base | 68 | -0.0813 | -0.3013 | +0.1445 |
| A | 53 | -0.0734 | -0.3449 | +0.2129 |
| B | 51 | -0.0370 | -0.3203 | +0.2513 |
| C | 14 | +0.0249 | -0.4222 | +0.5371 |
| D | 68 | +0.4253 | -0.1986 | +1.3185 |

## Neighborhood robustness (validate window)

| arm | variant | rule | validate expectancy | delta vs base | sign kept vs nominal? |
|---|---|---|---|---|---|
| A | nominal | <= 0.80 | +0.2891 | +0.0784 | (reference) |
| A | cutoff-0.05 | <= 0.75 | +0.3548 | +0.1441 | yes |
| A | cutoff+0.05 | <= 0.85 | +0.2744 | +0.0637 | yes |
| B | nominal | [0.20,0.80] | +0.2249 | +0.0142 | (reference) |
| B | low-0.05 | [0.15,0.80] | +0.1943 | -0.0164 | no |
| B | low+0.05 | [0.25,0.80] | +0.1510 | -0.0597 | no |
| B | high-0.05 | [0.20,0.75] | +0.2843 | +0.0736 | yes |
| B | high+0.05 | [0.20,0.85] | +0.2125 | +0.0018 | yes |
| C | nominal | >= 3-of-5 | +0.1622 | -0.0484 | (reference) |
| C | 2-of-5 | >= 2-of-5 | +0.2055 | -0.0051 | yes |
| C | 4-of-5 | >= 4-of-5 | -0.1388 | -0.3494 | yes |

## Verdict (pre-registered adoption rule, applied mechanically)

All 4 criteria must hold for adoption. Arm D has no adoption path by design (reported for information only).

| arm | 1. validate (exp>=base & retain>=40%) | 2. train (exp>=0) | 3. paper (n>=20 & exp>=0.00) | 4. neighborhood (sign kept) | verdict |
|---|---|---|---|---|---|
| A | PASS | PASS | FAIL | PASS | **FAIL** |
| B | PASS | FAIL | FAIL | FAIL | **FAIL** |
| C | FAIL | PASS | FAIL | PASS | **FAIL** |

**No arm passes.** Per pre-registration's expected-outcome clause: "post-filters cannot salvage the consensus mechanism." This is a real possible outcome and feeds the standing event-season-only vs wind-down decision. It does not license inventing new arms this cycle.

## Arm D (fade) -- descriptive only, no adoption path

Opposite outcome entered at (1 - entry price), same exit at resolution (payout read directly from the opposite outcome's `outcome_prices` entry, not assumed as 1-payout, though both should coincide for binary markets). See the per-arm-per-window table above for D's train/validate/paper numbers -- n is far too small in the paper window to draw a conclusion from on this cycle.

## Standing caveats

- **Hypothesis-formation contamination**: all four arms were suggested by the paper-period fills (2026-07-05 onward). The paper counterfactual is therefore NOT independent validation of the hypotheses -- it is reported with a bootstrap CI, never as sole grounds for adoption.
- **All judgments are relative** (arm vs base, same window, same simulator) -- absolute simulated PnL is not trustworthy; the base parameters themselves were tuned on this same train/validate split.
- **Taker-only trades feed**; survivorship bias on cohort selection; the validate window is World-Cup-inflated; a simulator-vs-paper calibration gap is unresolved (base validate showed strong simulated returns while live paper showed negative expectancy in an overlapping regime) -- exactly why every judgment above is relative-only.
- **Jul 16-17 ingestion outage**: paper-window signals near those dates may be undercounted, affecting the paper counterfactual's denominator (not the backtest windows).

