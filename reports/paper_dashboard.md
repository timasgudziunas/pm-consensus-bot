# Paper Trading Dashboard

_Regenerated 2026-07-07 17:45 UTC by `src/paper_status.py` from `data/copybot.db` (single source of truth). Live stake: $50/position (older rows keep their opening stake)._

## Bottom line (all-time)

**Net PnL: $-212.09** = $-51.40 realized + $-160.69 mark-to-market on open positions

- Closed: 21 positions, win rate 52% (11/21), realized $-51.40
- Open: 9 positions, $+450.00 staked, MTM $-160.69 (9 priced)
- Mean alpha decay: +3.30c/share over 30 fills
- Filtered out (never filled): 28 SKIPPED (book too thin/gone), 1 STALE (detected too late)

## Decision gate — day 2.20 of 3 (window since 2026-07-05T13:00:00Z; thresholds in config `paper.gate`)

- fills >= 15 by day 3: 30 so far, pace ~41 -> **ON TRACK**
- win rate >= 55% (needs >= 10 closed): 52% -> **AT RISK**
- mean decay < 10c/share: +3.30c -> **ON TRACK**

## Daily realized PnL (by exit date)

| exit date | closed | realized $ | cumulative $ |
|---|---|---|---|
| 2026-07-05 | 5 | +28.20 | +28.20 |
| 2026-07-06 | 10 | +15.67 | +43.88 |
| 2026-07-07 | 6 | -95.27 | -51.40 |

## By category (watchlist cohort B, all-time)

| category | wallets | wl pnl/vol | wl edge | signals | filled | skipped | fill% | PnL $ | PnL/$ | win% | paper edge | decay |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| POLITICS | 58 | 0.94 | +0.034 | 0 | 0 | 0 | - | - | - | - | - | - |
| TECH | 41 | 0.79 | +0.032 | 0 | 0 | 0 | - | - | - | - | - | - |
| CRYPTO | 24 | 0.69 | +0.048 | 0 | 0 | 0 | - | - | - | - | - | - |
| FINANCE | 62 | 0.40 | +0.033 | 0 | 0 | 0 | - | - | - | - | - | - |
| CULTURE | 43 | 0.39 | +0.027 | 0 | 0 | 0 | - | - | - | - | - | - |
| SPORTS | 65 | 0.22 | +0.072 | 56 | 27 | 28 | 49% | -20.84 | -0.022 | 53% | +0.009 | +0.024 |
| UNMAPPED | 0 | - | - | 3 | 3 | 0 | 100% | -30.56 | -0.306 | 50% | -0.130 | +0.117 |
## Check-in history

- 2026-07-07 17:45 UTC — day 2.20/3 | fills 30 (9 open/21 closed) | win 52% | realized $-51.40 | MTM $-160.69 | net $-212.09
