# Two-half category backtest — generated 2026-07-06 16:13 UTC

Cohort B, live paper cell (N=5, W=12h, F=$1000), $50/position, history cut at 2026-07-02T00:00:00Z (ingest boundary), half boundary 2026-04-02.

**Liquidity caveat (explicit): historical order-book depth data does not exist** — the DB has hourly price candles only, and Gamma's `liquidity` field is a present-day snapshot (≈$36 avg on closed markets). Fills below use the candle+configured-slippage model from backtest.py. Lifetime market volume is used as a stated PROXY to flag possibly-thin markets; see sensitivity tables. The live-book evidence we do have (11 paper fills, all sports): $50 fills at half-spread (+0.5c) in every case.

Survivorship bias caveat: the watchlist is traders who look good over the SAME window the backtest replays (see OVERVIEW.md); category comparisons inherit it. H1-vs-H2 agreement mitigates look-ahead in pattern selection, not survivorship.

## H1 (first half)

### hold_to_resolution
| category | signals | closed | unresolved | win% | PnL $ | PnL/$ | avg edge/share |
|---|---|---|---|---|---|---|---|
| SPORTS | 1 | 1 | 0 | 100% | +14.52 | +0.290 | +0.245 |
| POLITICS | 24 | 22 | 2 | 86% | +130.90 | +0.119 | +0.150 |

### copy_exits
| category | signals | closed | unresolved | win% | PnL $ | PnL/$ | avg edge/share |
|---|---|---|---|---|---|---|---|
| SPORTS | 1 | 1 | 0 | 100% | +14.52 | +0.290 | +0.245 |
| POLITICS | 24 | 22 | 2 | 86% | +137.18 | +0.125 | +0.131 |

## H2 (second half)

### hold_to_resolution
| category | signals | closed | unresolved | win% | PnL $ | PnL/$ | avg edge/share |
|---|---|---|---|---|---|---|---|
| CRYPTO | 1 | 1 | 0 | 100% | +80.72 | +1.614 | +0.637 |
| SPORTS | 76 | 76 | 0 | 70% | +1500.81 | +0.395 | +0.135 |
| POLITICS | 46 | 45 | 1 | 73% | +347.73 | +0.155 | +0.056 |
| UNMAPPED | 1 | 1 | 0 | 100% | +5.77 | +0.115 | +0.124 |

### copy_exits
| category | signals | closed | unresolved | win% | PnL $ | PnL/$ | avg edge/share |
|---|---|---|---|---|---|---|---|
| CRYPTO | 1 | 1 | 0 | 100% | +80.72 | +1.614 | +0.637 |
| SPORTS | 76 | 76 | 0 | 70% | +1500.81 | +0.395 | +0.135 |
| UNMAPPED | 1 | 1 | 0 | 100% | +5.77 | +0.115 | +0.124 |
| POLITICS | 46 | 45 | 1 | 64% | -46.09 | -0.020 | -0.003 |

## Hypotheses from H1 (hold_to_resolution), tested on H2

Stated only for categories with >= 15 closed signals in the half being read. Verdicts are mechanical — nothing was tuned on H2.

| # | hypothesis (from H1) | H2 verdict |
|---|---|---|
| 1 | POLITICS is profitable (PnL/$ +0.119) | HOLDS |

## Liquidity / signal-availability sensitivity (full window, hold)

How the signal set changes as the per-trader size floor drops — this is where illiquid markets would enter the pool.

| size floor | signals | min market vol | p10 market vol | n < $100k (PnL$) | n < $500k (PnL$) | n < $1000k (PnL$) |
|---|---|---|---|---|---|---|
| $100 | 369 | 36,056 | 1,159,693 | 0 (+0) | 10 (-158) | 23 (-170) |
| $250 | 283 | 145,092 | 1,382,706 | 0 (+0) | 5 (-78) | 14 (-29) |
| $500 | 208 | 151,673 | 2,265,457 | 0 (+0) | 1 (+10) | 6 (+34) |
| $1000 | 149 | 876,625 | 3,362,743 | 0 (+0) | 0 (+0) | 2 (+17) |

Per-floor category mix: F=$100: POLITICS 200, SPORTS 141, CULTURE 9, UNMAPPED 8, TECH 5, CRYPTO 5, FINANCE 1; F=$250: POLITICS 152, SPORTS 118, UNMAPPED 5, CULTURE 4, TECH 3, CRYPTO 1; F=$500: POLITICS 107, SPORTS 95, TECH 2, UNMAPPED 2, CULTURE 1, CRYPTO 1; F=$1000: SPORTS 77, POLITICS 70, CRYPTO 1, UNMAPPED 1

