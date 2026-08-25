# Copy-gap diagnosis — generated 2026-08-25 15:51 UTC

**Question**: paper trading shows net realized $-276.29 over 68 CLOSED fills, while the copied wallets' own measured entry edge on SPORTS is positive (+0.072 PnL/$). Where does the copy gap come from — selection (consensus fires on the wallets' bad trades), timing/decay (price moves before our entry), spread cost (we cross the book), or exit policy (hold_to_resolution vs the wallets' own exits)?

## Executive summary

- **Headline (SPORTS, n=60 CLOSED fills, stake-weighted ¢/share):** wallet counterfactual edge -2.20c, minus pre-signal decay +3.36c, minus spread/slippage +0.40c, = our realized edge -5.95c/share.
- mean(payout − avg_trader_price) over SPORTS closed fills is **-2.20c/share (negative)** -> **SELECTION kills the premise** (the copied trades lose even at the wallets' own prices, before any copying cost); decay adds a comparable-size cost on top, spread is negligible — see the component magnitudes in the headline line above.
- Bootstrap 95% CI on the SPORTS mean our-edge/share (simple, unweighted; n=60, seed 20260817, 10000 iters): mean -5.95c/share, CI [-17.99c, +6.11c].
- Overall (all categories, n=68, stake-weighted): wallet CF -0.22c, decay +3.97c, spread +0.41c, our edge -4.60c/share.
- Reconciliation: sum(pnl_20) over all 68 CLOSED fills = $-276.29; decomposition components re-sum to the DB's own pnl_20 over the 68 decomposed fills — **MATCH**.

## 1. Per-share decomposition (identity: our = wallet_cf − decay − spread, verified on every row)

$ totals additive to realized PnL; ¢/share is the $-stake-weighted mean of the per-share component (bigger positions weight the average more; 'simple' is the plain unweighted mean, the convention used elsewhere in this repo's dashboard/decay figures, shown for comparability).

| slice | n | wallet CF $ | decay $ | spread $ | our $ | wallet CF c/sh (wtd/simple) | decay c/sh (wtd/simple) | spread c/sh (wtd/simple) | our c/sh (wtd/simple) |
|---|---|---|---|---|---|---|---|---|---|
| ALL | 68 | -15510.01 | -15292.36 | +58.64 | -276.29 | -0.22 / -0.22 | +3.97 / +3.97 | +0.41 / +0.41 | -4.60 / -4.60 |
|  | 1 | +5.14 | +0.51 | +0.70 | +3.94 | +9.54 / +9.54 | +0.94 / +0.94 | +1.29 / +1.29 | +7.31 / +7.31 |
| POLITICS | 2 | +33.01 | +2.40 | +0.49 | +30.11 | +25.39 / +25.39 | +1.89 / +1.89 | +0.38 / +0.38 | +23.12 / +23.12 |
| SPORTS | 60 | -15565.21 | -15332.53 | +56.05 | -288.74 | -2.20 / -2.20 | +3.36 / +3.36 | +0.40 / +0.40 | -5.95 / -5.95 |
| UNMAPPED | 5 | +17.05 | +37.26 | +1.40 | -21.61 | +11.32 / +11.32 | +12.80 / +12.80 | +0.42 / +0.42 | -1.90 / -1.90 |

**$ column caveat (SPORTS):** a single fill (id=84, entry_price=$0.001) contributes 91% of the SPORTS wallet-CF $ total and 92% of the decay $ total. $ components scale with shares = stake/entry_price, so a very low entry_price inflates the implied share count and swamps the $ sum even though the per-share value is unremarkable. The stake-weighted c/share aggregate above is NOT affected by this (weighted by $ stake, not shares) — recomputed excluding this one fill (n=59): wallet-CF -1.76c/share vs -2.20c/share including it — materially unchanged. **Read the $ columns in this table as directional only; the c/share columns are the reliable read.**

Component share of the gap in cents/share terms (SPORTS, stake-weighted — the reliable metric per the caveat above, NOT the $ columns):

- wallet counterfactual: -2.20c/share
- minus decay: +3.36c/share (89% of |decay|+|spread|)
- minus spread/slippage: +0.40c/share (11% of |decay|+|spread|)
- = our realized edge: -5.95c/share (-288.74 total realized $ on these 60 fills)

## 2. Selection effect vs cohort baseline (SPORTS)

- Cohort-B SPORTS wallets' overall entry edge (context, quoted not recomputed, see config `analysis.copy_gap.sports_wallet_entry_edge_context`): **+0.072 PnL/$ of stake**.
- Signal-subset wallet edge from avg_trader_price (this analysis, SPORTS, stake-weighted c/share): -2.20c/share.
- Signal-subset wallet edge from the exact signal-forming trades (tx_hashes -> trades cross-check, SPORTS, stake-weighted, 609 trades matched, 0 missing): -6.67c/share = -0.154 PnL/$ of stake (unit-matched to the +0.072 context number above).

Units note: the +0.072 context figure and the per-dollar cross-check above are both PnL per dollar of stake; the c/share figures are price-unit edges per share and are not directly comparable to +0.072 without dividing by entry price — both are shown so the comparison is auditable either way.

## 3. Favorite-longshot anatomy (SPORTS CLOSED fills, by entry_price bucket)

| bucket | n | win% | avg win $ | avg loss $ | breakeven win% | total $ | our edge/share (wtd/simple, c) |
|---|---|---|---|---|---|---|---|
| 0.0-0.2 | 2 | 0% | - | -50.00 | - | -100.00 | -1.55 / -1.55 |
| 0.2-0.4 | 10 | 30% | +111.49 | -50.00 | 31% | -15.54 | -2.66 / -2.66 |
| 0.4-0.6 | 20 | 40% | +58.73 | -50.00 | 46% | -130.15 | -9.37 / -9.37 |
| 0.6-0.8 | 16 | 69% | +26.29 | -50.00 | 66% | +39.24 | +0.78 / +0.78 |
| 0.8-1.0 | 12 | 75% | +7.52 | -50.00 | 87% | -82.28 | -12.71 / -12.71 |

Losses in the >=0.6 (favorite) buckets: $-82.28 of $-327.98 total realized losses across all buckets (25% of total losses concentrate at favorite prices).
**Every loss costs exactly the full stake** ($50, or $20 for older rows) regardless of entry price — a binary market resolving to 0 wipes out (payout-entry)*shares = 0*shares - stake = -stake exactly, so avg loss $ is flat across buckets by construction. The real favorite/longshot asymmetry is on the WIN side: avg win shrinks in the two highest buckets (0.6-0.8: +26.29, 0.8-1.0: +7.52) since a favorite payout of 1.0 is only a small markup over an entry already near 1.0, which raises the win rate needed just to break even (breakeven win% column). The 0.8-1.0 bucket wins 75% of the time but needed 87% to break even, so it still lost $82.28 net despite winning most bets.

## 4. Exit-policy counterfactual — BOUNDED ESTIMATE, not a measurement

**Caveat (applies to every number in this section):** the `trades` feed is TAKER-ONLY and the median watchlist wallet does ~84% of its volume as invisible maker fills, so observed exits are ~16% of real exits. Fills below where no exit was ever observed are scored as hold (same as realized) by construction — this systematically understates how often and how early a copy-exit strategy would actually have triggered. Treat this as a **lower bound on exit-following opportunity**, not a measurement of it.

- 0/68 CLOSED fills had an observed copy-exit trigger (>= `backtest.copy_exit_wallet_fraction`=0.5 of signal wallets selling >= `backtest.copy_exit_sold_fraction`=0.5 of their signal-time position) strictly before the actual resolution close.
- Realized hold_to_resolution total: $-276.29.
- Copy-exit counterfactual total (same fills, exit priced at the signal wallets' own stake-weighted sell price where triggered, else = hold): $-276.29.
- Difference: $+0.00 (copy-exits would have hurt or been neutral, on the ~16%-visible sample that triggered at all).

No per-fill table shown: 0/68 fills ever had >= 50% of signal wallets' visible SELLs cross the sold-fraction threshold before resolution — every row is identical (copy-exit PnL = hold PnL, diff $0.00). Full per-fill detail (including copy_exit_ts for fills where a partial sell was observed but never crossed threshold) is in `reports/copy_gap_fills.csv`.

## 5. SKIPPED / STALE counterfactual

Hypothetical PnL at the signal's stake, priced at midpoint_at_signal (fall back to entry_price; skipped and counted where neither exists), against markets.outcome_prices where the market has since resolved.

### SKIPPED (book too thin/gone): 30 rows
- computable (has a price proxy AND a resolved market on file): 2
- has price proxy but market not yet resolved in our DB: 0
- no price proxy recorded (book/market fetch never happened or failed at signal time): 28
- neither price proxy nor resolved market: 0
- hypothetical PnL sum over computable rows: $+0.28

### STALE (detected >30min late): 13 rows
- computable (has a price proxy AND a resolved market on file): 0
- has price proxy but market not yet resolved in our DB: 0
- no price proxy recorded (book/market fetch never happened or failed at signal time): 10
- neither price proxy nor resolved market: 3
- hypothetical PnL sum over computable rows: $+0.00

**Combined, over the 2 computable rows out of 43 SKIPPED+STALE: the filters COST money (forgone profit) of $0.28.** This is a small, likely non-representative slice — most SKIPPED/STALE rows have no price proxy on file (paper.py never recorded one when the book/market fetch itself failed), so this verdict should not be generalized to the full 30 SKIPPED + 11 STALE population.

## Standing caveats (apply to every number above)

- **Taker-only feed**: `trades` only sees taker fills; the median watchlist wallet does ~84% of its volume as invisible maker fills. `avg_trader_price` and the tx_hashes cross-check in §2 are computed over VISIBLE taker BUYs only — if maker buys are priced differently, the true wallet counterfactual edge could differ from what's shown here. Section 4's exit counterfactual is a stated lower bound for the same reason (repeated there).
- **Survivorship bias**: cohort B was selected on its own trailing PnL/vol window; the +0.072 context edge and all per-wallet figures inherit that bias (see `reports/wallet_quality_analysis.md` §0).
- **Small n**: 60 SPORTS CLOSED fills. The bootstrap CI above quantifies this for the headline mean; bucket-level and per-category splits in §1/§3 have even smaller n and should be read as directional, not precise.
- avg_trader_price and the §2 cross-check price only the signal-forming trades that were visible taker buys; wallets with a mostly-maker style are underrepresented in whatever edge they contributed to a signal.

