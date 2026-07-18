# Paper Trading Dashboard

_Regenerated 2026-07-18 13:46 UTC by `src/paper_status.py` from `data/copybot.db` (single source of truth). Live stake: $50/position (older rows keep their opening stake)._

## Bottom line (all-time)

**Net PnL: $-324.20** = $-324.20 realized + $+0.00 mark-to-market on open positions

- Closed: 58 positions, win rate 52% (30/58), realized $-324.20
- Open: 0 positions, $0.00 staked, MTM $+0.00 (0 priced)
- Mean alpha decay: +3.76c/share over 58 fills
- Filtered out (never filled): 29 SKIPPED (book too thin/gone), 3 STALE (detected too late)

## Decision gate — day 13.03 of 3 (window since 2026-07-05T13:00:00Z; thresholds in config `paper.gate`)

- fills >= 15 by day 3: 58 so far, pace ~13 -> **ON TRACK**
- win rate >= 55% (needs >= 10 closed): 52% -> **AT RISK**
- mean decay < 10c/share: +3.76c -> **ON TRACK**

## Daily realized PnL (by exit date)

| exit date | closed | realized $ | cumulative $ |
|---|---|---|---|
| 2026-07-05 | 5 | +28.20 | +28.20 |
| 2026-07-06 | 10 | +15.67 | +43.88 |
| 2026-07-07 | 17 | -203.51 | -159.63 |
| 2026-07-08 | 0 | +0.00 | -159.63 |
| 2026-07-09 | 7 | -55.82 | -215.46 |
| 2026-07-10 | 5 | +28.67 | -186.79 |
| 2026-07-11 | 0 | +0.00 | -186.79 |
| 2026-07-12 | 9 | -83.67 | -270.46 |
| 2026-07-13 | 0 | +0.00 | -270.46 |
| 2026-07-14 | 4 | -57.68 | -328.14 |
| 2026-07-15 | 0 | +0.00 | -328.14 |
| 2026-07-16 | 1 | +3.94 | -324.20 |
| 2026-07-17 | 0 | +0.00 | -324.20 |
| 2026-07-18 | 0 | +0.00 | -324.20 |

## By category (watchlist cohort B, all-time)

| category | wallets | wl pnl/vol | wl edge | signals | filled | skipped | fill% | PnL $ | PnL/$ | win% | paper edge | decay |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| POLITICS | 58 | 0.94 | +0.034 | 0 | 0 | 0 | - | - | - | - | - | - |
| TECH | 41 | 0.79 | +0.032 | 0 | 0 | 0 | - | - | - | - | - | - |
| CRYPTO | 24 | 0.69 | +0.048 | 0 | 0 | 0 | - | - | - | - | - | - |
| FINANCE | 62 | 0.40 | +0.033 | 0 | 0 | 0 | - | - | - | - | - | - |
| CULTURE | 43 | 0.39 | +0.027 | 0 | 0 | 0 | - | - | - | - | - | - |
| SPORTS | 65 | 0.22 | +0.072 | 84 | 54 | 29 | 65% | -301.93 | -0.112 | 50% | -0.069 | +0.034 |
|  | 0 | - | - | 1 | 1 | 0 | 100% | +3.94 | +0.079 | 100% | +0.073 | +0.022 |
| UNMAPPED | 0 | - | - | 5 | 3 | 0 | 100% | -26.21 | -0.175 | 67% | -0.060 | +0.117 |
## Check-in history

- 2026-07-07 17:45 UTC — day 2.20/3 | fills 30 (9 open/21 closed) | win 52% | realized $-51.40 | MTM $-160.69 | net $-212.09
- 2026-07-07 19:33 UTC — day 2.27/3 | fills 30 (3 open/27 closed) | win 48% | realized $-73.27 | MTM $+30.94 | net $-42.33
- 2026-07-08 05:20 UTC — day 2.68/3 | fills 35 (3 open/32 closed) | win 47% | realized $-159.63 | MTM $+29.81 | net $-129.83
- 2026-07-08 13:03 UTC — day 3.00/3 | fills 35 (3 open/32 closed) | win 47% | realized $-159.63 | MTM $+30.35 | net $-129.28
- 2026-07-08 13:05 UTC — day 3.00/3 | fills 35 (3 open/32 closed) | win 47% | realized $-159.63 | MTM $+30.35 | net $-129.28
- 2026-07-09 13:05 UTC — day 4.00/3 | fills 35 (2 open/33 closed) | win 48% | realized $-155.29 | MTM $+28.17 | net $-127.11
- 2026-07-09 14:20 UTC — day 4.06/3 | fills 35 (2 open/33 closed) | win 48% | realized $-155.29 | MTM $+28.17 | net $-127.11
- 2026-07-10 13:05 UTC — day 5.00/3 | fills 41 (0 open/41 closed) | win 49% | realized $-187.25 | MTM $+0.00 | net $-187.25
- 2026-07-11 13:05 UTC — day 6.00/3 | fills 45 (1 open/44 closed) | win 50% | realized $-186.79 | MTM $-0.53 | net $-187.33
- 2026-07-12 13:05 UTC — day 7.00/3 | fills 54 (1 open/53 closed) | win 51% | realized $-270.46 | MTM $-1.53 | net $-272.00
- 2026-07-13 13:05 UTC — day 8.00/3 | fills 54 (1 open/53 closed) | win 51% | realized $-270.46 | MTM $+0.73 | net $-269.73
- 2026-07-14 13:05 UTC — day 9.00/3 | fills 54 (1 open/53 closed) | win 51% | realized $-270.46 | MTM $+1.11 | net $-269.35
- 2026-07-17 03:30 UTC — day 11.60/3 | fills 58 (0 open/58 closed) | win 52% | realized $-324.20 | MTM $+0.00 | net $-324.20
- 2026-07-17 13:05 UTC — day 12.00/3 | fills 58 (0 open/58 closed) | win 52% | realized $-324.20 | MTM $+0.00 | net $-324.20
- 2026-07-18 13:05 UTC — day 13.00/3 | fills 58 (0 open/58 closed) | win 52% | realized $-324.20 | MTM $+0.00 | net $-324.20
- 2026-07-18 13:46 UTC — day 13.03/3 | fills 58 (0 open/58 closed) | win 52% | realized $-324.20 | MTM $+0.00 | net $-324.20
