# Paper Trading Dashboard

_Regenerated 2026-07-08 05:20 UTC by `src/paper_status.py` from `data/copybot.db` (single source of truth). Live stake: $50/position (older rows keep their opening stake)._

## Bottom line (all-time)

**Net PnL: $-129.83** = $-159.63 realized + $+29.81 mark-to-market on open positions

- Closed: 32 positions, win rate 47% (15/32), realized $-159.63
- Open: 3 positions, $150.00 staked, MTM $+29.81 (3 priced)
- Mean alpha decay: +3.95c/share over 35 fills
- Filtered out (never filled): 28 SKIPPED (book too thin/gone), 1 STALE (detected too late)

## Decision gate — day 2.68 of 3 (window since 2026-07-05T13:00:00Z; thresholds in config `paper.gate`)

- fills >= 15 by day 3: 35 so far, pace ~39 -> **ON TRACK**
- win rate >= 55% (needs >= 10 closed): 47% -> **AT RISK**
- mean decay < 10c/share: +3.95c -> **ON TRACK**

## Daily realized PnL (by exit date)

| exit date | closed | realized $ | cumulative $ |
|---|---|---|---|
| 2026-07-05 | 5 | +28.20 | +28.20 |
| 2026-07-06 | 10 | +15.67 | +43.88 |
| 2026-07-07 | 17 | -203.51 | -159.63 |

## By category (watchlist cohort B, all-time)

| category | wallets | wl pnl/vol | wl edge | signals | filled | skipped | fill% | PnL $ | PnL/$ | win% | paper edge | decay |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| POLITICS | 58 | 0.94 | +0.034 | 0 | 0 | 0 | - | - | - | - | - | - |
| TECH | 41 | 0.79 | +0.032 | 0 | 0 | 0 | - | - | - | - | - | - |
| CRYPTO | 24 | 0.69 | +0.048 | 0 | 0 | 0 | - | - | - | - | - | - |
| FINANCE | 62 | 0.40 | +0.033 | 0 | 0 | 0 | - | - | - | - | - | - |
| CULTURE | 43 | 0.39 | +0.027 | 0 | 0 | 0 | - | - | - | - | - | - |
| SPORTS | 65 | 0.22 | +0.072 | 61 | 32 | 28 | 53% | -129.08 | -0.086 | 47% | -0.087 | +0.032 |
| UNMAPPED | 0 | - | - | 3 | 3 | 0 | 100% | -30.56 | -0.306 | 50% | -0.130 | +0.117 |
## Check-in history

- 2026-07-07 17:45 UTC — day 2.20/3 | fills 30 (9 open/21 closed) | win 52% | realized $-51.40 | MTM $-160.69 | net $-212.09
- 2026-07-07 19:33 UTC — day 2.27/3 | fills 30 (3 open/27 closed) | win 48% | realized $-73.27 | MTM $+30.94 | net $-42.33
- 2026-07-08 05:20 UTC — day 2.68/3 | fills 35 (3 open/32 closed) | win 47% | realized $-159.63 | MTM $+29.81 | net $-129.83
