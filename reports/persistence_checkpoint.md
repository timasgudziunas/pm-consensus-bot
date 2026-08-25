# Pre-registered wallet-edge persistence checkpoint (Aug 2026, overdue Aug 5-11)

Generated 2026-08-17 14:46 UTC. Engine: `src/persistence_checkpoint.py` (reuses `src/wallet_quality.py` position-building and gate machinery). Full per-wallet table: `reports/persistence_checkpoint_wallets.csv`. Pre-registration: `reports/proposals/quality_weighted_cohort_proposal.md` §C.3 + Amendment.

## Question

Does each cohort-B wallet's PAST raw copyable edge (per-(wallet, market) net position, pnl_hold = buy_shares×payout − buy_usd, edge = pnl/stake) predict its edge on the held-out JULY+ forward window? This is the pre-registered re-validation gate for whether wallet-level quality is a selectable signal at all — it decides nothing about live trading directly (see proposal §C.4-5 for what a PASS/INCONCLUSIVE implies).

## Executive summary

**Verdict: INCONCLUSIVE**

- (a) Spearman(past edge, forward edge) = +0.136, one-sided permutation p = 0.0345 (n=179) -> MET
- (b) top-vs-bottom quintile forward-edge gap = +0.070/$ -> MET
- (c) per-share Spearman = +0.112, p = 0.0680 (n=179) -> not met
- Achieved sample: n=179 eligible wallets, median forward k=63 resolved positions (see Power section below for how this compares to the design target).

**"Cannot distinguish from noise" is the EXPECTED outcome under weak-but-real persistence, not a failed experiment or a failed strategy** (pre-registration Amendment, clause 2). It keeps the status quo (cohort B, category-based selection, unchanged) and justifies neither a quality tilt (proposal §C.4) nor a cohort cut (proposal §B). Do not re-shop metrics or re-run this test with different criteria based on this result.

## Pre-registered pass criteria (quoted, before results)

> Pre-registered pass criteria (all three):
> - raw-edge persistence Spearman > 0 with permutation p < 0.05;
> - top-vs-bottom quintile held-out edge gap > 0;
> - result survives the per-share (price-controlled) variant.

> "Cannot distinguish from noise" is an EXPECTED outcome, not a failed experiment or a failed strategy ... An inconclusive result keeps option A (status quo) and does NOT justify either a quality tilt (§C.4) or a cohort cut (§B).

— `reports/proposals/quality_weighted_cohort_proposal.md` §C.3 + Amendment clause 2.

## Results

| criterion | value | threshold | met? |
|---|---|---|---|
| (a) raw edge Spearman rho | +0.1355 | > 0 | yes |
| (a) raw edge permutation p (one-sided, 10,000 perms) | 0.0345 | < 0.05 | yes |
| (b) top-bottom quintile forward-edge gap | +0.0696/$ | > 0 | yes |
|   top quintile mean forward edge | +0.0599/$ | - | - |
|   bottom quintile mean forward edge | -0.0098/$ | - | - |
| (c) per-share Spearman rho | +0.1121 | > 0 | yes |
| (c) per-share permutation p | 0.0680 | < 0.05 | no |

Sample: n=179 eligible wallets (>= 10 resolved PAST positions AND >= 10 resolved FORWARD positions). Seed 20260817 (config `analysis.persistence_checkpoint.seed`) — rerun-stability check (same seed twice): **PASS**.

## Achieved sample vs. the power model's design target

From `reports/proposals/persistence_power_and_strict45_analysis.md` (Monte-Carlo power model, calibrated to the observed sigma_T=0.048 same-period reliability):

| date | design n | design median forward k | best-case power (rho_true=1.0) |
|---|---|---|---|
| Aug 11 | 218 | 84 | 83% |
| Aug 18 | 222 | 91 | 84% |

**Actual (this run, window end 2026-08-17): n=179, median forward k=63.**
Below the Aug 11-18 design range, so the test ran below designed power — treat a non-pass as even less informative than the pre-registered expected-outcome clause already assumes.

This is a power statement, not a hedge on the verdict above: the pre-registered criteria and their thresholds are exactly as stated regardless of achieved power. It only calibrates how much weight an INCONCLUSIVE result should carry.

## Secondary analyses (NOT decision criteria)

### Per-category Spearman slices (wallets.category, first tag)

| category | n | Spearman rho (raw edge) | permutation p |
|---|---|---|---|
| FINANCE | 47 | +0.038 | 0.4044 |
| CULTURE | 38 | +0.377 | 0.0113 |
| SPORTS | 33 | -0.057 | 0.6244 |
| POLITICS | 31 | +0.080 | 0.3278 |
| CRYPTO | 18 | +0.302 | 0.1040 |
| TECH | 12 | +0.210 | 0.2553 |

Sample sizes per category are small; these are descriptive slices, not independent tests.

### Sensitivity: rerun at min_resolved_forward=20

n=161, Spearman rho=+0.1828, p=0.0092, quintile gap=+0.1246/$.

### Quintile gap on the per-share metric

top quintile mean forward edge_per_share=+0.0107, bottom quintile=-0.0046, gap=+0.0154 (n=179).

## Verification

Spot-checked accounting (independent recomputation from raw trades + outcome_prices vs the scratch DB's stored value):

- wallet `0x000d257d...`, market `0xdc1fcdc0...`: recomputed pnl_hold=2005.6193, stored=2005.6193, diff=0.000000 -> matches to the cent
- wallet `0xfea31bc0...`, market `0x3c34b6dc...`: recomputed pnl_hold=7874.5621, stored=7874.5621, diff=0.000000 -> matches to the cent

Rerun-stability (same seed twice, identical rho/p): **confirmed**.

## Robustness footnote: PAST positions with post-window add-on trades

9272 of 338177 PAST positions (first buy before 2026-06-01) have a most-recent trade on or after 2026-06-01 — i.e. the wallet added to that position after the PAST window nominally ended (positions are aggregated over their whole trade history up to 2026-08-17, not truncated at past_end_utc, per spec). 173216 June-initiated positions were dropped entirely (first buy in June — collider risk from June-leaderboard cohort selection).

## Standing caveats (do not paper over these)

- **WC-era sports composition of the first ~2.5 weeks of the forward window.** The forward window opens 2026-07-01; the World Cup ran through ~Jul 19 (handoff §0a). Forward-side sports positions opened before ~Jul 19 are WC-inflated, not steady-state — any per-category sports read above inherits that.
- **~24.5h ingestion outage, 2026-07-16 02:52 UTC → 2026-07-17 03:27 UTC**, recovered only about half that window's trades (~10.2k captured vs ~20k/day typical, per handoff §0b). Forward positions with a first buy on 2026-07-16 may be undercounted or missing entirely — this is a coverage gap, not a signal.
- **The trades feed is TAKER-ONLY** (median cohort wallet ~84% maker). The copyable-edge metric used here (pnl_hold over visible taker BUYs) is immune by construction — it is exactly what the bot could copy — but "wallet activity" in this data is not the wallet's full activity.
- **Survivorship bias**: cohort B was selected on the June leaderboard. PAST-side edge levels for June-and-earlier are inflated by that selection; June-initiated positions are dropped entirely from both sides for exactly this reason, but the PAST window itself (pre-June) still describes wallets that went on to be selected, not a random sample.
- **Recently-opened forward positions are disproportionately unresolved** — a position opened days before window_end_utc has not had time to resolve, and slow categories (e.g. TECH, median resolution lag ~21 days per the July power-model analysis) are under-represented in the resolved forward set relative to fast categories (POLITICS/SPORTS). The per-category slice above should be read with this skew in mind, not as representative category composition.
- **Markets Gamma no longer serves** are recorded in `data/wq_fetch_misses.json` (1,169 condition_ids as of this run) and excluded from both position-building and the coverage denominator below — they are neither PAST nor FORWARD data, they simply cannot be priced.
- **Market-metadata coverage**: after the extended fetch/refresh pass, 0.00% of condition_ids traded by cohort-B wallets up to 2026-08-17 still have no markets row (excluding recorded misses). See the fetch log for the run that produced this.

