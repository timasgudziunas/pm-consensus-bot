# Paper Trading Dashboard

_Regenerated 2026-10-19 17:35 UTC by `src/paper_status.py` from `data/copybot.db` (single source of truth). Live stake: $50/position (older rows keep their opening stake)._

## Bottom line (all-time)

**Net PnL: $-244.60** = $-244.60 realized + $+0.00 mark-to-market on open positions

- Closed: 78 positions, win rate 62% (48/78), realized $-244.60
- Open: 0 positions, $0.00 staked, MTM $+0.00 (0 priced)
- Mean alpha decay: +4.96c/share over 78 fills
- Filtered out (never filled): 31 SKIPPED (book too thin/gone), 16 STALE (detected too late)

## Decision gate — day 106 (window since 2026-07-05T13:00:00Z; thresholds in config `paper.gate`; rewritten 2026-08-25 — net expectancy replaces win rate)

- net expectancy >= +0.00/$ staked: -0.063/$ over 78 fills ($3,900 staked) -> **AT RISK**
- live-ready bar (>= +0.05/$, >= 30 closed): **NOT MET**
- volume >= 0.5 fills/day: 0.73/day -> **ON TRACK**
- mean decay < 10c/share: +4.96c -> **ON TRACK**

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
| 2026-08-26 | 1 | +0.71 | -275.58 |
| 2026-08-27 | 0 | +0.00 | -275.58 |
| 2026-08-28 | 0 | +0.00 | -275.58 |
| 2026-08-29 | 1 | +1.28 | -274.30 |
| 2026-08-30 | 0 | +0.00 | -274.30 |
| 2026-08-31 | 0 | +0.00 | -274.30 |
| 2026-09-01 | 0 | +0.00 | -274.30 |
| 2026-09-02 | 0 | +0.00 | -274.30 |
| 2026-09-03 | 0 | +0.00 | -274.30 |
| 2026-09-04 | 0 | +0.00 | -274.30 |
| 2026-09-05 | 0 | +0.00 | -274.30 |
| 2026-09-06 | 0 | +0.00 | -274.30 |
| 2026-09-07 | 0 | +0.00 | -274.30 |
| 2026-09-08 | 0 | +0.00 | -274.30 |
| 2026-09-09 | 0 | +0.00 | -274.30 |
| 2026-09-10 | 0 | +0.00 | -274.30 |
| 2026-09-11 | 0 | +0.00 | -274.30 |
| 2026-09-12 | 0 | +0.00 | -274.30 |
| 2026-09-13 | 0 | +0.00 | -274.30 |
| 2026-09-14 | 0 | +0.00 | -274.30 |
| 2026-09-15 | 0 | +0.00 | -274.30 |
| 2026-09-16 | 0 | +0.00 | -274.30 |
| 2026-09-17 | 0 | +0.00 | -274.30 |
| 2026-09-18 | 1 | +1.89 | -272.41 |
| 2026-09-19 | 0 | +0.00 | -272.41 |
| 2026-09-20 | 1 | +2.08 | -270.33 |
| 2026-09-21 | 1 | +3.19 | -267.14 |
| 2026-09-22 | 0 | +0.00 | -267.14 |
| 2026-09-23 | 1 | +8.14 | -259.00 |
| 2026-09-24 | 0 | +0.00 | -259.00 |
| 2026-09-25 | 0 | +0.00 | -259.00 |
| 2026-09-26 | 0 | +0.00 | -259.00 |
| 2026-09-27 | 0 | +0.00 | -259.00 |
| 2026-09-28 | 0 | +0.00 | -259.00 |
| 2026-09-29 | 0 | +0.00 | -259.00 |
| 2026-09-30 | 1 | +1.55 | -257.45 |
| 2026-10-01 | 0 | +0.00 | -257.45 |
| 2026-10-02 | 0 | +0.00 | -257.45 |
| 2026-10-03 | 0 | +0.00 | -257.45 |
| 2026-10-04 | 0 | +0.00 | -257.45 |
| 2026-10-05 | 3 | +12.85 | -244.60 |
| 2026-10-06 | 0 | +0.00 | -244.60 |
| 2026-10-07 | 0 | +0.00 | -244.60 |
| 2026-10-08 | 0 | +0.00 | -244.60 |
| 2026-10-09 | 0 | +0.00 | -244.60 |
| 2026-10-10 | 0 | +0.00 | -244.60 |
| 2026-10-11 | 0 | +0.00 | -244.60 |
| 2026-10-12 | 0 | +0.00 | -244.60 |
| 2026-10-13 | 0 | +0.00 | -244.60 |
| 2026-10-14 | 0 | +0.00 | -244.60 |
| 2026-10-15 | 0 | +0.00 | -244.60 |
| 2026-10-16 | 0 | +0.00 | -244.60 |
| 2026-10-17 | 0 | +0.00 | -244.60 |
| 2026-10-18 | 0 | +0.00 | -244.60 |
| 2026-10-19 | 0 | +0.00 | -244.60 |

## By category (watchlist cohort B, all-time)

| category | wallets | wl pnl/vol | wl edge | signals | filled | skipped | fill% | PnL $ | PnL/$ | win% | paper edge | decay |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| POLITICS | 58 | 0.94 | +0.034 | 13 | 10 | 1 | 91% | +52.95 | +0.106 | 100% | +0.089 | +0.079 |
| TECH | 41 | 0.79 | +0.032 | 0 | 0 | 0 | - | - | - | - | - | - |
| CRYPTO | 24 | 0.69 | +0.048 | 0 | 0 | 0 | - | - | - | - | - | - |
| FINANCE | 62 | 0.40 | +0.033 | 0 | 0 | 0 | - | - | - | - | - | - |
| CULTURE | 43 | 0.39 | +0.027 | 0 | 0 | 0 | - | - | - | - | - | - |
| SPORTS | 65 | 0.22 | +0.072 | 91 | 60 | 30 | 67% | -288.74 | -0.096 | 52% | -0.060 | +0.038 |
|  | 0 | - | - | 1 | 1 | 0 | 100% | +3.94 | +0.079 | 100% | +0.073 | +0.022 |
| UNMAPPED | 0 | - | - | 20 | 7 | 0 | 100% | -12.76 | -0.036 | 86% | +0.008 | +0.115 |
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
- 2026-08-26 13:05 UTC — day 52 | fills 70 (1 open/69 closed) | win 57% | exp -0.078/$ | realized $-275.58 | MTM $+1.00 | net $-274.58
- 2026-08-27 13:22 UTC — day 53 | fills 70 (1 open/69 closed) | win 57% | exp -0.079/$ | realized $-275.58 | MTM $+0.02 | net $-275.55
- 2026-08-31 13:40 UTC — day 57 | fills 70 (0 open/70 closed) | win 57% | exp -0.078/$ | realized $-274.30 | MTM $+0.00 | net $-274.30
- 2026-09-01 14:51 UTC — day 58 | fills 70 (0 open/70 closed) | win 57% | exp -0.078/$ | realized $-274.30 | MTM $+0.00 | net $-274.30
- 2026-09-04 13:05 UTC — day 61 | fills 70 (0 open/70 closed) | win 57% | exp -0.078/$ | realized $-274.30 | MTM $+0.00 | net $-274.30
- 2026-09-05 18:54 UTC — day 62 | fills 70 (0 open/70 closed) | win 57% | exp -0.078/$ | realized $-274.30 | MTM $+0.00 | net $-274.30
- 2026-09-06 13:05 UTC — day 63 | fills 70 (0 open/70 closed) | win 57% | exp -0.078/$ | realized $-274.30 | MTM $+0.00 | net $-274.30
- 2026-09-08 21:31 UTC — day 65 | fills 71 (1 open/70 closed) | win 57% | exp -0.077/$ | realized $-274.30 | MTM $+0.21 | net $-274.09
- 2026-09-09 14:08 UTC — day 66 | fills 71 (1 open/70 closed) | win 57% | exp -0.077/$ | realized $-274.30 | MTM $-0.39 | net $-274.69
- 2026-09-11 13:05 UTC — day 68 | fills 71 (1 open/70 closed) | win 57% | exp -0.077/$ | realized $-274.30 | MTM $+0.99 | net $-273.31
- 2026-09-13 17:22 UTC — day 70 | fills 71 (1 open/70 closed) | win 57% | exp -0.077/$ | realized $-274.30 | MTM $+0.29 | net $-274.01
- 2026-09-14 13:05 UTC — day 71 | fills 71 (1 open/70 closed) | win 57% | exp -0.077/$ | realized $-274.30 | MTM $+0.52 | net $-273.78
- 2026-09-15 16:36 UTC — day 72 | fills 72 (2 open/70 closed) | win 57% | exp -0.076/$ | realized $-274.30 | MTM $+2.07 | net $-272.23
- 2026-09-16 14:24 UTC — day 73 | fills 72 (2 open/70 closed) | win 57% | exp -0.075/$ | realized $-274.30 | MTM $+2.75 | net $-271.55
- 2026-09-18 13:05 UTC — day 75 | fills 72 (1 open/71 closed) | win 58% | exp -0.075/$ | realized $-272.41 | MTM $+1.22 | net $-271.19
- 2026-09-19 20:29 UTC — day 76 | fills 72 (1 open/71 closed) | win 58% | exp -0.075/$ | realized $-272.41 | MTM $+1.51 | net $-270.90
- 2026-09-20 18:24 UTC — day 77 | fills 72 (1 open/71 closed) | win 58% | exp -0.076/$ | realized $-272.41 | MTM $+0.00 | net $-272.41
- 2026-09-21 13:05 UTC — day 78 | fills 73 (1 open/72 closed) | win 58% | exp -0.074/$ | realized $-270.33 | MTM $+0.00 | net $-270.33
- 2026-09-22 15:28 UTC — day 79 | fills 73 (0 open/73 closed) | win 59% | exp -0.073/$ | realized $-267.14 | MTM $+0.00 | net $-267.14
- 2026-09-24 13:05 UTC — day 81 | fills 74 (0 open/74 closed) | win 59% | exp -0.070/$ | realized $-259.00 | MTM $+0.00 | net $-259.00
- 2026-09-25 13:05 UTC — day 82 | fills 74 (0 open/74 closed) | win 59% | exp -0.070/$ | realized $-259.00 | MTM $+0.00 | net $-259.00
- 2026-09-27 18:48 UTC — day 84 | fills 74 (0 open/74 closed) | win 59% | exp -0.070/$ | realized $-259.00 | MTM $+0.00 | net $-259.00
- 2026-09-28 13:05 UTC — day 85 | fills 74 (0 open/74 closed) | win 59% | exp -0.070/$ | realized $-259.00 | MTM $+0.00 | net $-259.00
- 2026-09-29 13:05 UTC — day 86 | fills 74 (0 open/74 closed) | win 59% | exp -0.070/$ | realized $-259.00 | MTM $+0.00 | net $-259.00
- 2026-09-30 13:05 UTC — day 87 | fills 75 (0 open/75 closed) | win 60% | exp -0.069/$ | realized $-257.45 | MTM $+0.00 | net $-257.45
- 2026-10-02 13:05 UTC — day 89 | fills 75 (0 open/75 closed) | win 60% | exp -0.069/$ | realized $-257.45 | MTM $+0.00 | net $-257.45
- 2026-10-04 03:18 UTC — day 91 | fills 75 (0 open/75 closed) | win 60% | exp -0.069/$ | realized $-257.45 | MTM $+0.00 | net $-257.45
- 2026-10-05 13:05 UTC — day 92 | fills 78 (0 open/78 closed) | win 62% | exp -0.063/$ | realized $-244.60 | MTM $+0.00 | net $-244.60
- 2026-10-06 13:05 UTC — day 93 | fills 78 (0 open/78 closed) | win 62% | exp -0.063/$ | realized $-244.60 | MTM $+0.00 | net $-244.60
- 2026-10-07 14:11 UTC — day 94 | fills 78 (0 open/78 closed) | win 62% | exp -0.063/$ | realized $-244.60 | MTM $+0.00 | net $-244.60
- 2026-10-09 14:15 UTC — day 96 | fills 78 (0 open/78 closed) | win 62% | exp -0.063/$ | realized $-244.60 | MTM $+0.00 | net $-244.60
- 2026-10-13 21:01 UTC — day 100 | fills 78 (0 open/78 closed) | win 62% | exp -0.063/$ | realized $-244.60 | MTM $+0.00 | net $-244.60
- 2026-10-14 13:05 UTC — day 101 | fills 78 (0 open/78 closed) | win 62% | exp -0.063/$ | realized $-244.60 | MTM $+0.00 | net $-244.60
- 2026-10-17 23:39 UTC — day 104 | fills 78 (0 open/78 closed) | win 62% | exp -0.063/$ | realized $-244.60 | MTM $+0.00 | net $-244.60
- 2026-10-18 17:24 UTC — day 105 | fills 78 (0 open/78 closed) | win 62% | exp -0.063/$ | realized $-244.60 | MTM $+0.00 | net $-244.60
- 2026-10-19 17:35 UTC — day 106 | fills 78 (0 open/78 closed) | win 62% | exp -0.063/$ | realized $-244.60 | MTM $+0.00 | net $-244.60
