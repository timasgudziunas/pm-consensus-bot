# Backtest Report — Polymarket Consensus Copy-Trading

_Generated 2026-07-03 05:43 UTC. Lookback 6 months, train = first 4 months, validate = remainder._

## 1. Executive summary

The best parameter set on **validate** data is **N=5 W=24h F=$500 hold_to_resolution $50** with a validate-period total PnL of **$509.98** (27% return on capital deployed), a win rate of 74% over 38 signals (38 closed). Its train-period PnL was $194.69 (86% win rate), so it **was** profitable in both periods. Across the whole grid, 91 of 144 cells were profitable in both train and validate periods.

## 2. Known bias

> **⚠ SURVIVORSHIP BIAS — READ BEFORE ACTING ON ANYTHING BELOW**
>
> The watchlist was selected from **today's** leaderboard: these traders are on it
> *because* their bets ended up winning. Replaying their historical trades therefore
> overstates what a real-time selection would have earned. Mitigations applied:
> (1) train/validate split — parameters are picked on the first 4 months and judged
> on the last 2; (2) treat every number in this report as an **upper bound**, not an
> expectation. A trader whose edge was luck will regress; paper trading (Phase 5)
> is the honest test. See OVERVIEW.md for the full discussion.
>
> **Coverage bias (API limitation):** the Data API caps per-wallet history at its
> 4,000 most recent trades; 85 of 113 watchlist wallets hit that cap, so the most
> active wallets contribute little or nothing to the early (train) months. Trade
> density — and therefore signal counts — is skewed toward the recent (validate)
> period. Treat cross-period comparisons accordingly.


## 3. Full grid results (sorted by validate PnL)

| N          | W   | F     | exit               | size   |   sig(tr) | win(tr)   |   PnL(tr) |   sig(val) | win(val)   |   PnL(val) |   PnL(full) |
|------------|-----|-------|--------------------|--------|-----------|-----------|-----------|------------|------------|------------|-------------|
| **top3** 5 | 24h | $500  | hold_to_resolution | $50    |        16 | 86%       |       195 |         38 | 74%        |        510 |         705 |
| **top3** 4 | 6h  | $1000 | hold_to_resolution | $50    |        13 | 92%       |       204 |         47 | 68%        |        486 |         690 |
| **top3** 5 | 24h | $500  | copy_exits         | $50    |        16 | 80%       |       154 |         38 | 71%        |        471 |         625 |
| 4          | 6h  | $500  | hold_to_resolution | $50    |        14 | 86%       |       174 |         62 | 66%        |        468 |         641 |
| 4          | 6h  | $1000 | copy_exits         | $50    |        13 | 77%       |        92 |         47 | 66%        |        428 |         520 |
| 5          | 6h  | $500  | hold_to_resolution | $50    |         7 | 86%       |        93 |         26 | 73%        |        414 |         507 |
| 4          | 6h  | $500  | copy_exits         | $50    |        14 | 79%       |       110 |         62 | 63%        |        395 |         505 |
| 3          | 24h | $500  | hold_to_resolution | $50    |       102 | 72%       |       244 |        216 | 62%        |        375 |         663 |
| 5          | 24h | $250  | hold_to_resolution | $50    |        20 | 83%       |       289 |         51 | 67%        |        368 |         656 |
| 5          | 6h  | $500  | copy_exits         | $50    |         7 | 86%       |        92 |         26 | 65%        |        347 |         439 |
| 4          | 24h | $1000 | hold_to_resolution | $50    |        19 | 89%       |       247 |         67 | 67%        |        346 |         593 |
| 5          | 24h | $250  | copy_exits         | $50    |        20 | 79%       |       247 |         51 | 65%        |        335 |         582 |
| 3          | 24h | $500  | copy_exits         | $50    |       102 | 61%       |        43 |        216 | 60%        |        320 |         372 |
| 5          | 6h  | $250  | hold_to_resolution | $50    |         7 | 86%       |       110 |         34 | 70%        |        297 |         407 |
| 4          | 24h | $1000 | copy_exits         | $50    |        19 | 84%       |       210 |         67 | 64%        |        293 |         503 |
| 4          | 24h | $500  | hold_to_resolution | $50    |        31 | 72%       |       166 |         89 | 65%        |        279 |         495 |
| 4          | 6h  | $250  | copy_exits         | $50    |        19 | 68%       |       222 |         72 | 64%        |        267 |         489 |
| 4          | 1h  | $250  | hold_to_resolution | $50    |         6 | 83%       |        77 |         28 | 56%        |        261 |         338 |
| 3          | 24h | $500  | hold_to_resolution | $20    |       102 | 72%       |       134 |        216 | 62%        |        258 |         409 |
| 4          | 6h  | $250  | hold_to_resolution | $50    |        19 | 79%       |       317 |         72 | 67%        |        247 |         564 |
| 5          | 6h  | $1000 | hold_to_resolution | $50    |         5 | 100%      |        80 |         16 | 69%        |        245 |         325 |
| 5          | 1h  | $500  | hold_to_resolution | $50    |         3 | 100%      |        75 |          8 | 75%        |        242 |         317 |
| 5          | 1h  | $500  | copy_exits         | $50    |         3 | 100%      |        75 |          8 | 75%        |        240 |         315 |
| 3          | 24h | $500  | copy_exits         | $20    |       102 | 63%       |        51 |        216 | 60%        |        236 |         290 |
| 5          | 6h  | $250  | copy_exits         | $50    |         7 | 86%       |       109 |         34 | 64%        |        229 |         338 |
| 4          | 1h  | $250  | copy_exits         | $50    |         6 | 83%       |        57 |         28 | 48%        |        227 |         284 |
| 5          | 24h | $500  | hold_to_resolution | $20    |        16 | 86%       |        84 |         38 | 74%        |        227 |         311 |
| 3          | 24h | $1000 | hold_to_resolution | $50    |        66 | 80%       |       539 |        173 | 62%        |        226 |         815 |
| 4          | 6h  | $500  | hold_to_resolution | $20    |        14 | 86%       |        75 |         62 | 66%        |        220 |         295 |
| 4          | 6h  | $1000 | hold_to_resolution | $20    |        13 | 92%       |        87 |         47 | 68%        |        219 |         306 |
| 5          | 24h | $1000 | hold_to_resolution | $50    |        12 | 91%       |       150 |         23 | 70%        |        214 |         365 |
| 5          | 24h | $500  | copy_exits         | $20    |        16 | 80%       |        67 |         38 | 71%        |        211 |         279 |
| 5          | 1h  | $250  | hold_to_resolution | $50    |         3 | 100%      |        75 |         11 | 70%        |        205 |         280 |
| 5          | 1h  | $250  | copy_exits         | $50    |         3 | 100%      |        75 |         11 | 70%        |        204 |         279 |
| 4          | 6h  | $1000 | copy_exits         | $20    |        13 | 77%       |        41 |         47 | 66%        |        196 |         237 |
| 4          | 6h  | $500  | copy_exits         | $20    |        14 | 79%       |        49 |         62 | 63%        |        191 |         240 |
| 5          | 6h  | $500  | hold_to_resolution | $20    |         7 | 86%       |        40 |         26 | 73%        |        181 |         222 |
| 5          | 6h  | $1000 | copy_exits         | $50    |         5 | 100%      |        79 |         16 | 56%        |        179 |         258 |
| 4          | 24h | $250  | hold_to_resolution | $50    |        43 | 71%       |       310 |        110 | 63%        |        172 |         532 |
| 5          | 24h | $250  | hold_to_resolution | $20    |        20 | 83%       |       124 |         51 | 67%        |        172 |         296 |
| 4          | 24h | $1000 | hold_to_resolution | $20    |        19 | 89%       |       106 |         67 | 67%        |        167 |         273 |
| 5          | 1h  | $1000 | copy_exits         | $50    |         2 | 100%      |        70 |          5 | 80%        |        163 |         233 |
| 5          | 1h  | $1000 | hold_to_resolution | $50    |         2 | 100%      |        70 |          5 | 80%        |        163 |         233 |
| 3          | 24h | $1000 | hold_to_resolution | $20    |        66 | 80%       |       245 |        173 | 62%        |        161 |         426 |
| 5          | 24h | $250  | copy_exits         | $20    |        20 | 79%       |       107 |         51 | 65%        |        159 |         267 |
| 5          | 6h  | $500  | copy_exits         | $20    |         7 | 86%       |        40 |         26 | 69%        |        154 |         194 |
| 5          | 24h | $1000 | copy_exits         | $50    |        12 | 83%       |       110 |         23 | 65%        |        152 |         262 |
| 4          | 24h | $500  | hold_to_resolution | $20    |        31 | 72%       |        79 |         89 | 65%        |        150 |         249 |
| 4          | 24h | $1000 | copy_exits         | $20    |        19 | 84%       |        91 |         67 | 64%        |        147 |         238 |
| 4          | 1h  | $1000 | hold_to_resolution | $50    |         4 | 100%      |        78 |         16 | 62%        |        142 |         219 |
| 4          | 6h  | $250  | copy_exits         | $20    |        19 | 68%       |        98 |         72 | 64%        |        136 |         235 |
| 5          | 6h  | $250  | hold_to_resolution | $20    |         7 | 86%       |        47 |         34 | 70%        |        136 |         183 |
| 4          | 6h  | $250  | hold_to_resolution | $20    |        19 | 79%       |       137 |         72 | 67%        |        127 |         264 |
| 4          | 1h  | $250  | hold_to_resolution | $20    |         6 | 83%       |        33 |         28 | 56%        |        122 |         155 |
| 3          | 1h  | $500  | copy_exits         | $50    |        22 | 77%       |       150 |         91 | 60%        |        119 |         269 |
| 4          | 24h | $250  | hold_to_resolution | $20    |        43 | 71%       |       144 |        110 | 63%        |        115 |         279 |
| 4          | 1h  | $500  | hold_to_resolution | $50    |         5 | 80%       |        55 |         22 | 64%        |        111 |         166 |
| 4          | 1h  | $250  | copy_exits         | $20    |         6 | 83%       |        25 |         28 | 48%        |        108 |         133 |
| 5          | 6h  | $250  | copy_exits         | $20    |         7 | 86%       |        47 |         34 | 67%        |        108 |         155 |
| 3          | 1h  | $1000 | hold_to_resolution | $50    |        17 | 88%       |       263 |         62 | 59%        |        108 |         371 |
| 5          | 6h  | $1000 | hold_to_resolution | $20    |         5 | 100%      |        34 |         16 | 69%        |        108 |         142 |
| 5          | 1h  | $500  | hold_to_resolution | $20    |         3 | 100%      |        32 |          8 | 75%        |        103 |         134 |
| 5          | 1h  | $500  | copy_exits         | $20    |         3 | 100%      |        32 |          8 | 75%        |        102 |         134 |
| 5          | 24h | $1000 | hold_to_resolution | $20    |        12 | 91%       |        65 |         23 | 70%        |         97 |         162 |
| 5          | 1h  | $250  | hold_to_resolution | $20    |         3 | 100%      |        32 |         11 | 70%        |         89 |         120 |
| 3          | 1h  | $500  | copy_exits         | $20    |        22 | 77%       |        68 |         91 | 60%        |         88 |         156 |
| 5          | 1h  | $250  | copy_exits         | $20    |         3 | 100%      |        32 |         11 | 70%        |         88 |         120 |
| 3          | 1h  | $500  | hold_to_resolution | $50    |        22 | 82%       |       210 |         91 | 61%        |         82 |         292 |
| 5          | 6h  | $1000 | copy_exits         | $20    |         5 | 100%      |        34 |         16 | 62%        |         81 |         115 |
| 4          | 1h  | $1000 | copy_exits         | $50    |         4 | 100%      |        77 |         16 | 56%        |         78 |         155 |
| 3          | 24h | $1000 | copy_exits         | $20    |        66 | 72%       |       215 |        173 | 60%        |         75 |         302 |
| 3          | 1h  | $500  | hold_to_resolution | $20    |        22 | 82%       |        92 |         91 | 61%        |         73 |         165 |
| 5          | 24h | $1000 | copy_exits         | $20    |        12 | 83%       |        48 |         23 | 65%        |         72 |         120 |
| 3          | 1h  | $1000 | hold_to_resolution | $20    |        17 | 88%       |       112 |         62 | 59%        |         70 |         182 |
| 5          | 1h  | $1000 | copy_exits         | $20    |         2 | 100%      |        29 |          5 | 80%        |         69 |          98 |
| 5          | 1h  | $1000 | hold_to_resolution | $20    |         2 | 100%      |        29 |          5 | 80%        |         69 |          98 |
| 4          | 1h  | $1000 | hold_to_resolution | $20    |         4 | 100%      |        33 |         16 | 62%        |         65 |          98 |
| 3          | 6h  | $1000 | hold_to_resolution | $20    |        40 | 77%       |       122 |        129 | 62%        |         63 |         185 |
| 3          | 1h  | $1000 | copy_exits         | $50    |        17 | 88%       |       234 |         62 | 57%        |         60 |         294 |
| 4          | 1h  | $500  | hold_to_resolution | $20    |         5 | 80%       |        24 |         22 | 64%        |         54 |          78 |
| 3          | 1h  | $1000 | copy_exits         | $20    |        17 | 88%       |       101 |         62 | 57%        |         51 |         152 |
| 4          | 1h  | $1000 | copy_exits         | $20    |         4 | 100%      |        33 |         16 | 56%        |         39 |          72 |
| 3          | 6h  | $500  | hold_to_resolution | $20    |        62 | 75%       |       157 |        165 | 62%        |         37 |         193 |
| 3          | 6h  | $1000 | hold_to_resolution | $50    |        40 | 77%       |       269 |        129 | 62%        |         34 |         304 |
| 3          | 6h  | $1000 | copy_exits         | $20    |        40 | 75%       |        94 |        129 | 59%        |         22 |         117 |
| 3          | 24h | $1000 | copy_exits         | $50    |        66 | 69%       |       462 |        173 | 60%        |         20 |         512 |
| 4          | 1h  | $500  | copy_exits         | $20    |         5 | 80%       |        24 |         22 | 55%        |         15 |          39 |
| 4          | 1h  | $500  | copy_exits         | $50    |         5 | 80%       |        54 |         22 | 55%        |         15 |          69 |
| 4          | 24h | $250  | copy_exits         | $20    |        43 | 64%       |        45 |        110 | 57%        |         14 |          70 |
| 3          | 24h | $250  | copy_exits         | $20    |       117 | 63%       |        55 |        272 | 58%        |         14 |          70 |
| 3          | 1h  | $250  | copy_exits         | $20    |        30 | 77%       |       142 |        108 | 59%        |          8 |         162 |
| 3          | 1h  | $250  | hold_to_resolution | $20    |        30 | 80%       |       166 |        108 | 60%        |         -1 |         186 |
| 4          | 24h | $500  | copy_exits         | $20    |        31 | 67%       |        -1 |         89 | 58%        |        -21 |         -11 |
| 3          | 24h | $250  | hold_to_resolution | $20    |       117 | 72%       |       179 |        272 | 60%        |        -25 |         171 |
| 3          | 6h  | $500  | copy_exits         | $20    |        62 | 69%       |       117 |        165 | 58%        |        -36 |          80 |
| 3          | 6h  | $1000 | copy_exits         | $50    |        40 | 70%       |       200 |        129 | 59%        |        -66 |         133 |
| 4          | 24h | $250  | copy_exits         | $50    |        43 | 64%       |        73 |        110 | 57%        |        -73 |          29 |
| 3          | 1h  | $250  | copy_exits         | $50    |        30 | 77%       |       320 |        108 | 59%        |        -88 |         262 |
| 3          | 6h  | $500  | hold_to_resolution | $50    |        62 | 75%       |       337 |        165 | 62%        |        -91 |         243 |
| 3          | 1h  | $250  | hold_to_resolution | $50    |        30 | 80%       |       381 |        108 | 60%        |       -108 |         324 |
| 2          | 1h  | $1000 | hold_to_resolution | $20    |        96 | 72%       |       370 |        282 | 59%        |       -116 |         293 |
| 2          | 1h  | $500  | hold_to_resolution | $20    |       132 | 72%       |       391 |        348 | 58%        |       -127 |         301 |
| 4          | 24h | $500  | copy_exits         | $50    |        31 | 67%       |       -27 |         89 | 58%        |       -134 |        -133 |
| 3          | 6h  | $250  | hold_to_resolution | $20    |        77 | 74%       |       128 |        201 | 60%        |       -184 |         -37 |
| 2          | 1h  | $1000 | copy_exits         | $20    |        96 | 67%       |       380 |        282 | 56%        |       -222 |         189 |
| 3          | 6h  | $250  | copy_exits         | $20    |        77 | 66%       |        75 |        201 | 56%        |       -229 |        -143 |
| 2          | 1h  | $500  | copy_exits         | $20    |       132 | 64%       |       374 |        348 | 53%        |       -250 |         147 |
| 3          | 24h | $250  | copy_exits         | $50    |       117 | 61%       |        40 |        272 | 58%        |       -268 |        -222 |
| 3          | 6h  | $500  | copy_exits         | $50    |        62 | 66%       |       237 |        165 | 58%        |       -275 |         -38 |
| 2          | 6h  | $1000 | hold_to_resolution | $20    |       168 | 75%       |       942 |        377 | 59%        |       -286 |         706 |
| 2          | 1h  | $250  | hold_to_resolution | $20    |       164 | 69%       |       344 |        412 | 58%        |       -328 |          53 |
| 3          | 24h | $250  | hold_to_resolution | $50    |       117 | 72%       |       343 |        272 | 60%        |       -355 |          31 |
| 2          | 1h  | $250  | copy_exits         | $20    |       164 | 61%       |       325 |        412 | 53%        |       -419 |         -70 |
| 2          | 6h  | $250  | hold_to_resolution | $20    |       300 | 67%       |       937 |        555 | 58%        |       -482 |         536 |
| 2          | 24h | $1000 | hold_to_resolution | $20    |       227 | 73%       |       912 |        464 | 59%        |       -496 |         437 |
| 2          | 6h  | $250  | copy_exits         | $20    |       300 | 57%       |       633 |        555 | 53%        |       -526 |         152 |
| 2          | 6h  | $500  | hold_to_resolution | $20    |       240 | 70%       |       763 |        473 | 58%        |       -548 |         241 |
| 2          | 1h  | $1000 | hold_to_resolution | $50    |        96 | 72%       |       789 |        282 | 59%        |       -551 |         336 |
| 2          | 6h  | $500  | copy_exits         | $20    |       240 | 57%       |       526 |        473 | 53%        |       -607 |         -92 |
| 2          | 6h  | $1000 | copy_exits         | $20    |       168 | 65%       |       802 |        377 | 55%        |       -619 |         214 |
| 3          | 6h  | $250  | hold_to_resolution | $50    |        77 | 74%       |       254 |        201 | 60%        |       -656 |        -355 |
| 2          | 24h | $250  | hold_to_resolution | $20    |       396 | 67%       |       808 |        674 | 57%        |       -662 |         294 |
| 2          | 1h  | $500  | hold_to_resolution | $50    |       132 | 72%       |       815 |        348 | 58%        |       -676 |         234 |
| 2          | 24h | $250  | copy_exits         | $20    |       396 | 55%       |       535 |        674 | 53%        |       -689 |         -63 |
| 2          | 24h | $500  | hold_to_resolution | $20    |       304 | 70%       |       775 |        570 | 58%        |       -748 |          75 |
| 3          | 6h  | $250  | copy_exits         | $50    |        77 | 64%       |       121 |        201 | 56%        |       -773 |        -622 |
| 2          | 24h | $1000 | copy_exits         | $20    |       227 | 61%       |       760 |        464 | 55%        |       -788 |          19 |
| 2          | 1h  | $1000 | copy_exits         | $50    |        96 | 64%       |       808 |        282 | 55%        |       -814 |          74 |
| 2          | 24h | $500  | copy_exits         | $20    |       304 | 55%       |       482 |        570 | 52%        |       -867 |        -358 |
| 2          | 1h  | $500  | copy_exits         | $50    |       132 | 62%       |       766 |        348 | 52%        |       -988 |        -161 |
| 2          | 6h  | $1000 | hold_to_resolution | $50    |       168 | 75%       |     2,109 |        377 | 59%        |     -1,079 |       1,156 |
| 2          | 1h  | $250  | hold_to_resolution | $50    |       164 | 69%       |       670 |        412 | 58%        |     -1,200 |        -435 |
| 2          | 1h  | $250  | copy_exits         | $50    |       164 | 59%       |       613 |        412 | 52%        |     -1,435 |        -762 |
| 2          | 24h | $1000 | hold_to_resolution | $50    |       227 | 73%       |     1,989 |        464 | 59%        |     -1,632 |         414 |
| 2          | 6h  | $250  | hold_to_resolution | $50    |       300 | 67%       |     1,916 |        555 | 58%        |     -1,704 |         424 |
| 2          | 6h  | $500  | hold_to_resolution | $50    |       240 | 70%       |     1,613 |        473 | 58%        |     -1,762 |         -77 |
| 2          | 6h  | $250  | copy_exits         | $50    |       300 | 55%       |     1,198 |        555 | 53%        |     -1,836 |        -513 |
| 2          | 6h  | $1000 | copy_exits         | $50    |       168 | 64%       |     1,759 |        377 | 55%        |     -1,859 |         -17 |
| 2          | 6h  | $500  | copy_exits         | $50    |       240 | 55%       |     1,026 |        473 | 53%        |     -1,926 |        -917 |
| 2          | 24h | $250  | hold_to_resolution | $50    |       396 | 67%       |     1,520 |        674 | 57%        |     -2,270 |        -373 |
| 2          | 24h | $500  | hold_to_resolution | $50    |       304 | 70%       |     1,587 |        570 | 58%        |     -2,332 |        -617 |
| 2          | 24h | $1000 | copy_exits         | $50    |       227 | 60%       |     1,609 |        464 | 54%        |     -2,344 |        -612 |
| 2          | 24h | $250  | copy_exits         | $50    |       396 | 54%       |       870 |        674 | 52%        |     -2,362 |      -1,250 |
| 2          | 24h | $500  | copy_exits         | $50    |       304 | 54%       |       862 |        570 | 52%        |     -2,644 |      -1,704 |


## 4. Category consistency (top 3 cells, validate period)


**N=5 W=24h F=$500 hold_to_resolution $50**

| category   |   signals | win rate   | PnL     |
|------------|-----------|------------|---------|
| POLITICS   |        20 | 75%        | $345.51 |
| CRYPTO     |         1 | 100%       | $80.72  |
| SPORTS     |        16 | 69%        | $70.22  |
| UNMAPPED   |         1 | 100%       | $13.53  |

**N=4 W=6h F=$1000 hold_to_resolution $50**

| category   |   signals | win rate   | PnL     |
|------------|-----------|------------|---------|
| SPORTS     |        29 | 66%        | $214.69 |
| POLITICS   |        16 | 69%        | $176.99 |
| CRYPTO     |         1 | 100%       | $80.72  |
| UNMAPPED   |         1 | 100%       | $13.53  |

**N=5 W=24h F=$500 copy_exits $50**

| category   |   signals | win rate   | PnL     |
|------------|-----------|------------|---------|
| POLITICS   |        20 | 70%        | $306.17 |
| CRYPTO     |         1 | 100%       | $80.72  |
| SPORTS     |        16 | 69%        | $70.22  |
| UNMAPPED   |         1 | 100%       | $13.53  |

Categories that appear with positive PnL across all three cells are the consistent earners; categories negative in every cell drag returns and are candidates for exclusion in paper mode.


## 5. Hold-to-resolution vs copy-exits (top 3 N/W/F/size combos)

| combo                |   hold PnL(val) |   copy PnL(val) | winner         |
|----------------------|-----------------|-----------------|----------------|
| N=5 W=24h F=$500 $50 |          509.98 |          470.64 | hold (+$39.34) |
| N=4 W=6h F=$1000 $50 |          485.93 |          428.49 | hold (+$57.44) |


## 6. Equity curves

Validate-period cumulative PnL for the top 3 cells: `reports/equity_curve_top3.csv` (47 rows).

## 7. Best-cell trade log

Every simulated validate-period trade for **N=5 W=24h F=$500 hold_to_resolution $50**: `reports/best_cell_trades.csv` (38 rows).

## 8. Unresolved positions (validate period, top 10 cells)

| cell                                    |   unresolved | capital tied up   |
|-----------------------------------------|--------------|-------------------|
| N=5 W=24h F=$500 hold_to_resolution $50 |            0 | $0                |
| N=4 W=6h F=$1000 hold_to_resolution $50 |            0 | $0                |
| N=5 W=24h F=$500 copy_exits $50         |            0 | $0                |
| N=4 W=6h F=$500 hold_to_resolution $50  |            0 | $0                |
| N=4 W=6h F=$1000 copy_exits $50         |            0 | $0                |
| N=5 W=6h F=$500 hold_to_resolution $50  |            0 | $0                |
| N=4 W=6h F=$500 copy_exits $50          |            0 | $0                |
| N=3 W=24h F=$500 hold_to_resolution $50 |            3 | $150              |
| N=5 W=24h F=$250 hold_to_resolution $50 |            2 | $100              |
| N=5 W=6h F=$500 copy_exits $50          |            0 | $0                |


## 9. Recommended next steps

- Validate-period returns are **positive and consistent with train**. Run paper mode with N=5, window=24h, floor=$500, exit=hold_to_resolution (update the `paper:` block in config.yaml) and compare live alpha decay against the backtest edge of $13.42/trade.
- Do NOT go live until the decision-gate checklist in PLAN.md passes.
