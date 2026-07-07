# Overnight Summary — 2026-07-03 (cohort expansion night)

All three instructions from `night-time-magic.md` are done. Everything is committed
(5 commits, `53f12e8..fd78894`); paper trading is running on the new configuration.

## What changed

**Watchlist: 113 → 431 wallets.** 638 candidates vetted (top ~120 per category from
the MONTH∩ALL leaderboards), 431 selected as the union of three 250-wallet cohorts:

- **A — raw month PnL** (old method, control)
- **B — PnL per dollar of volume** (leaderboard pnl/vol)
- **C — stake-weighted entry edge** ((resolution payout − entry price) weighted by
  stake over each wallet's resolved sample buys; needed ~93,600 Gamma resolution
  lookups, now cached in the DB)

Overlap: 86 wallets in all three cohorts; 68/55/75 unique to A/B/C. Every wallet also
got a consistency score (tie-breaker). Filters rejected: 45 min_markets,
41 min_trades, 24 market-makers.

**Data: 242k → 796k trades**, 9,227 signal-candidate markets with metadata + hourly
price history (1M+ candles). 266 of 431 wallets are truncated at the API's
4,000-trade cap (train-period coverage is thin for them — stated in the report).

**Sweep: 144 → 15,120 cells.** N 2–8 × window 1–48h × floor $100–2500 × 2 exits ×
$20/50/100, run separately per cohort and for the pooled union, with a new
neighborhood-robustness guard (a winner counts only if ≥75% of its grid neighbors
are also profitable in validate).

## The night's question: which "efficiency" definition wins?

**Cohort B (PnL per dollar of volume).** From `reports/backtest_report.md`:

| cohort | breadth (cells profitable in both periods) | best robust cell | validate PnL |
|--------|-----|------|------|
| A (raw PnL) | 39% | N=6 W=12h F=$500 hold $100 | $2,917 |
| **B (PnL/vol)** | **50%** | **N=5 W=12h F=$1000 hold $100** | **$3,482** |
| C (entry edge) | 51% | N=8 W=48h F=$500 hold $100 | $2,256 |
| union | 24% | N=8 W=6h F=$250 hold $100 | $2,731 |

B has the best robust cell at both $100 and $50 stakes and near-best breadth.
Notable: the pooled union is the *worst* set — diluting good cohorts with everything
hurts. C has the best breadth but weaker peaks. Hold-to-resolution beats copy-exits
in every top cell. PnL is driven by SPORTS ($2.6k) and POLITICS ($654); no category
is a consistent loser.

## Paper trading now

- **Cohort B watchlist (250 wallets), N=5, W=12h, F=$1000, hold_to_resolution,
  $50/position** (owner-set stake; params = best robust B cell at $50 too:
  +$1,955 validate, 71% win rate, 122 signals).
- PID in `data/logs/pids.txt`. Positions opened at $20 stay $20 (per-row
  `position_usd` added).
- The 3-day paper clock effectively restarts today (~05:50 local).

## Incidents (all handled)

1. `discover.py` crashed printing an emoji username to the cp1252 console — after
   the DB persist, so nothing lost; stdout is now UTF-8 and the preview was
   regenerated from the DB.
2. The 03:35 paper process died at 03:38: an unguarded Gamma lookup in the poll
   loop raised `ApiError` (likely 429s while ingest saturated the API). The poll
   cycle is now guarded (log and continue); restarted 05:50 and stable since.
   ~2 hours of live polling were lost — no positions existed yet.

## Go/no-go picture for the day-3 gate

Backtest says **go-ish, with the usual caveats**: robust, broadly profitable
parameter regions exist (not just single cells), consistent across train/validate
and across cohort definitions. But every number is an upper bound (survivorship +
coverage bias — see report §2), and train-period PnL for the winning cell is small
(+$70 at $50). The honest test is the paper run that started tonight: watch
`reports/paper_daily.md` for realized PnL and alpha decay vs the backtested
~$16/trade average. Polymarket US KYC remains the only external prerequisite if
the gate passes.
