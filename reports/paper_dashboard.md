# Paper Trading Dashboard

_Regenerated 2026-08-25 15:37 UTC by `src/paper_status.py` from `data/copybot.db` (single source of truth). Live stake: $50/position (older rows keep their opening stake)._

## Bottom line (all-time)

**Net PnL: $-277.50** = $-276.29 realized + $-1.21 mark-to-market on open positions

- Closed: 68 positions, win rate 56% (38/68), realized $-276.29
- Open: 1 positions, $50.00 staked, MTM $-1.21 (1 priced)
- Mean alpha decay: +4.47c/share over 69 fills
- Filtered out (never filled): 30 SKIPPED (book too thin/gone), 13 STALE (detected too late)

## Decision gate — day 51.11 of 3 (window since 2026-07-05T13:00:00Z; thresholds in config `paper.gate`)

- fills >= 15 by day 3: 69 so far, pace ~4 -> **ON TRACK**
- win rate >= 55% (needs >= 10 closed): 56% -> **ON TRACK**
- mean decay < 10c/share: +4.47c -> **ON TRACK**

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
| 2026-07-18 | 1 | +67.10 | -257.10 |
| 2026-07-19 | 3 | -16.40 | -273.50 |
| 2026-07-20 | 0 | +0.00 | -273.50 |
| 2026-07-21 | 0 | +0.00 | -273.50 |
| 2026-07-22 | 0 | +0.00 | -273.50 |
| 2026-07-23 | 0 | +0.00 | -273.50 |
| 2026-07-24 | 1 | +4.35 | -269.15 |
| 2026-07-25 | 0 | +0.00 | -269.15 |
| 2026-07-26 | 0 | +0.00 | -269.15 |
| 2026-07-27 | 0 | +0.00 | -269.15 |
| 2026-07-28 | 0 | +0.00 | -269.15 |
| 2026-07-29 | 0 | +0.00 | -269.15 |
| 2026-07-30 | 0 | +0.00 | -269.15 |
| 2026-07-31 | 1 | +16.31 | -252.84 |
| 2026-08-01 | 0 | +0.00 | -252.84 |
| 2026-08-02 | 1 | -50.00 | -302.84 |
| 2026-08-03 | 0 | +0.00 | -302.84 |
| 2026-08-04 | 1 | +0.25 | -302.59 |
| 2026-08-05 | 0 | +0.00 | -302.59 |
| 2026-08-06 | 0 | +0.00 | -302.59 |
| 2026-08-07 | 0 | +0.00 | -302.59 |
| 2026-08-08 | 1 | +13.80 | -288.79 |
| 2026-08-09 | 0 | +0.00 | -288.79 |
| 2026-08-10 | 0 | +0.00 | -288.79 |
| 2026-08-11 | 0 | +0.00 | -288.79 |
| 2026-08-12 | 0 | +0.00 | -288.79 |
| 2026-08-13 | 0 | +0.00 | -288.79 |
| 2026-08-14 | 0 | +0.00 | -288.79 |
| 2026-08-15 | 0 | +0.00 | -288.79 |
| 2026-08-16 | 0 | +0.00 | -288.79 |
| 2026-08-17 | 0 | +0.00 | -288.79 |
| 2026-08-18 | 0 | +0.00 | -288.79 |
| 2026-08-19 | 0 | +0.00 | -288.79 |
| 2026-08-20 | 0 | +0.00 | -288.79 |
| 2026-08-21 | 1 | +12.50 | -276.29 |
| 2026-08-22 | 0 | +0.00 | -276.29 |
| 2026-08-23 | 0 | +0.00 | -276.29 |
| 2026-08-24 | 0 | +0.00 | -276.29 |
| 2026-08-25 | 0 | +0.00 | -276.29 |

## By category (watchlist cohort B, all-time)

| category | wallets | wl pnl/vol | wl edge | signals | filled | skipped | fill% | PnL $ | PnL/$ | win% | paper edge | decay |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| POLITICS | 58 | 0.94 | +0.034 | 4 | 3 | 0 | 100% | +30.11 | +0.301 | 100% | +0.231 | +0.051 |
| TECH | 41 | 0.79 | +0.032 | 0 | 0 | 0 | - | - | - | - | - | - |
| CRYPTO | 24 | 0.69 | +0.048 | 0 | 0 | 0 | - | - | - | - | - | - |
| FINANCE | 62 | 0.40 | +0.033 | 0 | 0 | 0 | - | - | - | - | - | - |
| CULTURE | 43 | 0.39 | +0.027 | 0 | 0 | 0 | - | - | - | - | - | - |
| SPORTS | 65 | 0.22 | +0.072 | 91 | 60 | 30 | 67% | -288.74 | -0.096 | 52% | -0.060 | +0.038 |
|  | 0 | - | - | 1 | 1 | 0 | 100% | +3.94 | +0.079 | 100% | +0.073 | +0.022 |
| UNMAPPED | 0 | - | - | 16 | 5 | 0 | 100% | -21.61 | -0.086 | 80% | -0.019 | +0.132 |
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
- 2026-07-19 13:05 UTC — day 14.00/3 | fills 59 (0 open/59 closed) | win 53% | realized $-257.10 | MTM $+0.00 | net $-257.10
- 2026-07-20 13:05 UTC — day 15.00/3 | fills 63 (1 open/62 closed) | win 53% | realized $-273.50 | MTM $+3.99 | net $-269.51
- 2026-07-21 13:05 UTC — day 16.00/3 | fills 63 (1 open/62 closed) | win 53% | realized $-273.50 | MTM $+4.21 | net $-269.29
- 2026-07-22 13:05 UTC — day 17.00/3 | fills 63 (1 open/62 closed) | win 53% | realized $-273.50 | MTM $+4.27 | net $-269.23
- 2026-07-24 13:05 UTC — day 19.00/3 | fills 64 (1 open/63 closed) | win 54% | realized $-269.15 | MTM $-0.50 | net $-269.65
- 2026-07-25 13:05 UTC — day 20.00/3 | fills 64 (1 open/63 closed) | win 54% | realized $-269.15 | MTM $-0.50 | net $-269.65
- 2026-07-26 21:52 UTC — day 21.37/3 | fills 64 (1 open/63 closed) | win 54% | realized $-269.15 | MTM $+0.00 | net $-269.15
- 2026-07-27 13:05 UTC — day 22.00/3 | fills 64 (1 open/63 closed) | win 54% | realized $-269.15 | MTM $+2.49 | net $-266.67
- 2026-07-28 21:02 UTC — day 23.33/3 | fills 64 (1 open/63 closed) | win 54% | realized $-269.15 | MTM $+0.80 | net $-268.36
- 2026-08-02 13:05 UTC — day 28.00/3 | fills 66 (1 open/65 closed) | win 54% | realized $-302.84 | MTM $+0.23 | net $-302.61
- 2026-08-04 09:52 UTC — day 29.87/3 | fills 66 (1 open/65 closed) | win 54% | realized $-302.84 | MTM $+0.00 | net $-302.84
- 2026-08-04 13:05 UTC — day 30.00/3 | fills 66 (0 open/66 closed) | win 55% | realized $-302.59 | MTM $+0.00 | net $-302.59
- 2026-08-08 16:51 UTC — day 34.16/3 | fills 67 (1 open/66 closed) | win 55% | realized $-302.59 | MTM $+0.00 | net $-302.59
- 2026-08-09 14:06 UTC — day 35.05/3 | fills 67 (0 open/67 closed) | win 55% | realized $-288.79 | MTM $+0.00 | net $-288.79
- 2026-08-13 01:29 UTC — day 38.52/3 | fills 67 (0 open/67 closed) | win 55% | realized $-288.79 | MTM $+0.00 | net $-288.79
- 2026-08-14 11:46 UTC — day 39.95/3 | fills 67 (0 open/67 closed) | win 55% | realized $-288.79 | MTM $+0.00 | net $-288.79
- 2026-08-14 14:25 UTC — day 40.06/3 | fills 67 (0 open/67 closed) | win 55% | realized $-288.79 | MTM $+0.00 | net $-288.79
- 2026-08-16 02:30 UTC — day 41.56/3 | fills 67 (0 open/67 closed) | win 55% | realized $-288.79 | MTM $+0.00 | net $-288.79
- 2026-08-17 13:55 UTC — day 43.04/3 | fills 67 (0 open/67 closed) | win 55% | realized $-288.79 | MTM $+0.00 | net $-288.79
- 2026-08-21 07:45 UTC — day 46.78/3 | fills 67 (0 open/67 closed) | win 55% | realized $-288.79 | MTM $+0.00 | net $-288.79
- 2026-08-24 15:13 UTC — day 50.09/3 | fills 68 (0 open/68 closed) | win 56% | realized $-276.29 | MTM $+0.00 | net $-276.29
- 2026-08-25 15:37 UTC — day 51.11/3 | fills 69 (1 open/68 closed) | win 56% | realized $-276.29 | MTM $-1.21 | net $-277.50
