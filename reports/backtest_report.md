# Backtest Report — Polymarket Consensus Copy-Trading (cohort sweep)

_Generated 2026-07-03 09:47 UTC. Lookback 6 months, train = first 4 months, validate = remainder. Cohorts: A = raw month PnL (control), B = PnL per dollar of volume, C = stake-weighted entry edge, union = all selected wallets._

## 1. Executive summary

The best wallet set is **cohort B** and the best parameter cell is **N=5 W=12h F=$1000 hold_to_resolution $100** (robust: its parameter neighborhood is profitable in validate). Validate-period total PnL **$3,482.39** (29% return on capital), win rate 71% over 122 signals (119 closed); train-period PnL $88.74 (78% win rate).

## 2. Known bias

> **⚠ SURVIVORSHIP BIAS — READ BEFORE ACTING ON ANYTHING BELOW**
>
> The watchlist was selected from **today's** leaderboard: these traders are on it
> *because* their bets ended up winning. Replaying their historical trades therefore
> overstates what a real-time selection would have earned. This applies to EVERY
> cohort below — cohort B and C rankings are computed over the same
> leaderboard-derived pool, so comparing cohorts is fair, but absolute numbers are
> inflated for all of them. Mitigations applied:
> (1) train/validate split — parameters are picked on the first 4 months and judged
> on the last 2; (2) neighborhood robustness check — single spectacular grid cells
> are flagged as suspect unless their parameter neighbors are also profitable;
> (3) treat every number in this report as an **upper bound**, not an expectation.
> A trader whose edge was luck will regress; paper trading (Phase 5) is the honest
> test. See OVERVIEW.md for the full discussion.
>
> **Coverage bias (API limitation):** the Data API caps per-wallet history at its
> 4,000 most recent trades — 266 of 431 selected wallets hit that cap, so the
> most active wallets contribute little or nothing to the early (train) months.
> Trade density — and therefore signal counts — is skewed toward the recent
> (validate) period. Treat cross-period comparisons accordingly.


## 3. Cohort comparison

| cohort   |   cells |   both-profitable | breadth   | best cell (val PnL sort)                  |   PnL(val) | best ROBUST cell                          |   PnL(val) | nbr prof.   |
|----------|---------|-------------------|-----------|-------------------------------------------|------------|-------------------------------------------|------------|-------------|
| A        |    1260 |               497 | 39%       | N=6 W=12h F=$500 hold_to_resolution $100  |      2,917 | N=6 W=12h F=$500 hold_to_resolution $100  |      2,917 | 83%         |
| B        |    1260 |               632 | 50%       | N=5 W=12h F=$1000 hold_to_resolution $100 |      3,482 | N=5 W=12h F=$1000 hold_to_resolution $100 |      3,482 | 83%         |
| C        |    1260 |               646 | 51%       | N=7 W=48h F=$500 hold_to_resolution $100  |      2,969 | N=8 W=48h F=$500 hold_to_resolution $100  |      2,256 | 100%        |
| union    |    1260 |               301 | 24%       | N=8 W=6h F=$250 hold_to_resolution $100   |      2,731 | N=8 W=6h F=$250 hold_to_resolution $100   |      2,731 | 100%        |

**Verdict:** cohort **B** wins on the best robust validate cell. Breadth (share of cells profitable in both periods) is the tie-breaker to trust when robust winners are close — a cohort that is broadly profitable beats one spectacular cell. Robustness threshold: ≥75% of a cell's grid neighbors (N±1, window ±1 step, floor ±1 step) profitable in validate.


## 4. Top 40 grid cells per cohort (sorted by validate PnL)


### Cohort A

|   N | W   | F     | exit               | size   |   sig(tr) | win(tr)   |   PnL(tr) |   sig(val) | win(val)   |   PnL(val) | nbrs prof.   | robust   |
|-----|-----|-------|--------------------|--------|-----------|-----------|-----------|------------|------------|------------|--------------|----------|
|   6 | 12h | $500  | hold_to_resolution | $100   |        27 | 73%       |        19 |        161 | 66%        |      2,917 | 83%          | ROBUST   |
|   6 | 12h | $1000 | hold_to_resolution | $100   |        23 | 82%       |       192 |        121 | 68%        |      2,506 | 100%         | ROBUST   |
|   6 | 24h | $1000 | hold_to_resolution | $100   |        31 | 83%       |       281 |        142 | 66%        |      2,421 | 100%         | ROBUST   |
|   8 | 6h  | $100  | hold_to_resolution | $100   |         9 | 56%       |      -166 |         94 | 73%        |      2,398 | 100%         |          |
|   7 | 12h | $500  | hold_to_resolution | $100   |        16 | 75%       |        59 |        113 | 72%        |      2,396 | 100%         | ROBUST   |
|   6 | 12h | $1000 | copy_exits         | $100   |        23 | 73%       |        95 |        121 | 67%        |      2,366 | 100%         | ROBUST   |
|   7 | 6h  | $500  | hold_to_resolution | $100   |         9 | 67%       |       -35 |         99 | 71%        |      2,329 | 100%         |          |
|   6 | 48h | $1000 | hold_to_resolution | $100   |        43 | 78%       |        52 |        155 | 68%        |      2,304 | 100%         | ROBUST   |
|   8 | 3h  | $100  | hold_to_resolution | $100   |         5 | 60%       |        25 |         76 | 73%        |      2,282 | 100%         | ROBUST   |
|   7 | 6h  | $250  | hold_to_resolution | $100   |        12 | 75%       |       240 |        118 | 69%        |      2,243 | 100%         | ROBUST   |
|   8 | 3h  | $100  | copy_exits         | $100   |         5 | 60%       |        25 |         76 | 72%        |      2,240 | 100%         | ROBUST   |
|   7 | 3h  | $1000 | hold_to_resolution | $100   |         3 | 100%      |       165 |         66 | 75%        |      2,206 | 100%         | ROBUST   |
|   7 | 3h  | $250  | hold_to_resolution | $100   |         7 | 71%       |        60 |         99 | 71%        |      2,192 | 100%         | ROBUST   |
|   7 | 3h  | $500  | hold_to_resolution | $100   |         6 | 83%       |       160 |         86 | 73%        |      2,175 | 100%         | ROBUST   |
|   8 | 48h | $500  | hold_to_resolution | $100   |        29 | 71%       |        93 |        103 | 73%        |      2,172 | 100%         | ROBUST   |
|   7 | 48h | $1000 | hold_to_resolution | $100   |        30 | 79%       |       195 |        106 | 72%        |      2,164 | 100%         | ROBUST   |
|   7 | 6h  | $1000 | hold_to_resolution | $100   |         6 | 83%       |        68 |         74 | 75%        |      2,144 | 100%         | ROBUST   |
|   7 | 3h  | $1000 | copy_exits         | $100   |         3 | 100%      |       165 |         66 | 74%        |      2,111 | 100%         | ROBUST   |
|   6 | 6h  | $500  | hold_to_resolution | $100   |        19 | 68%       |       -84 |        141 | 67%        |      2,107 | 83%          |          |
|   6 | 12h | $2500 | hold_to_resolution | $100   |         9 | 75%       |       -16 |         64 | 71%        |      2,106 | 100%         |          |
|   7 | 6h  | $1000 | copy_exits         | $100   |         6 | 83%       |        67 |         74 | 74%        |      2,087 | 100%         | ROBUST   |
|   8 | 6h  | $250  | hold_to_resolution | $100   |         6 | 83%       |       122 |         78 | 74%        |      2,083 | 100%         | ROBUST   |
|   7 | 3h  | $500  | copy_exits         | $100   |         6 | 83%       |       187 |         86 | 71%        |      2,082 | 100%         | ROBUST   |
|   6 | 48h | $2500 | hold_to_resolution | $100   |        24 | 82%       |        84 |         89 | 72%        |      2,033 | 100%         | ROBUST   |
|   6 | 24h | $500  | hold_to_resolution | $100   |        39 | 76%       |       361 |        192 | 66%        |      2,028 | 83%          | ROBUST   |
|   7 | 48h | $500  | hold_to_resolution | $100   |        40 | 79%       |       785 |        142 | 72%        |      2,014 | 100%         | ROBUST   |
|   7 | 12h | $1000 | hold_to_resolution | $100   |         9 | 78%       |        31 |         79 | 74%        |      1,952 | 100%         | ROBUST   |
|   7 | 12h | $1000 | copy_exits         | $100   |         9 | 78%       |        28 |         79 | 72%        |      1,895 | 100%         | ROBUST   |
|   8 | 12h | $500  | hold_to_resolution | $100   |         8 | 75%       |        72 |         78 | 71%        |      1,859 | 100%         | ROBUST   |
|   7 | 12h | $500  | copy_exits         | $100   |        16 | 75%       |       210 |        113 | 69%        |      1,850 | 100%         | ROBUST   |
|   8 | 3h  | $250  | hold_to_resolution | $100   |         4 | 75%       |        65 |         65 | 72%        |      1,839 | 100%         | ROBUST   |
|   8 | 6h  | $100  | copy_exits         | $100   |         9 | 56%       |      -115 |         94 | 71%        |      1,835 | 100%         |          |
|   6 | 12h | $500  | copy_exits         | $100   |        27 | 65%       |        98 |        161 | 64%        |      1,827 | 67%          |          |
|   7 | 24h | $1000 | hold_to_resolution | $100   |        21 | 80%       |        79 |         96 | 71%        |      1,822 | 100%         | ROBUST   |
|   6 | 12h | $2500 | copy_exits         | $100   |         9 | 62%       |       -56 |         64 | 69%        |      1,819 | 80%          |          |
|   8 | 3h  | $250  | copy_exits         | $100   |         4 | 75%       |        65 |         65 | 70%        |      1,802 | 100%         | ROBUST   |
|   8 | 3h  | $1000 | copy_exits         | $100   |         2 | 100%      |       138 |         40 | 79%        |      1,800 | 100%         | ROBUST   |
|   6 | 1h  | $1000 | copy_exits         | $100   |         2 | 100%      |       133 |         47 | 74%        |      1,794 | 100%         | ROBUST   |
|   6 | 48h | $2500 | copy_exits         | $100   |        24 | 71%       |        25 |         89 | 71%        |      1,793 | 75%          | ROBUST   |
|   7 | 24h | $1000 | copy_exits         | $100   |        21 | 80%       |       218 |         96 | 70%        |      1,791 | 100%         | ROBUST   |

(1260 cells total for cohort A; full grid lives in the backtest_results table.)

### Cohort B

|   N | W   | F     | exit               | size   |   sig(tr) | win(tr)   |   PnL(tr) |   sig(val) | win(val)   |   PnL(val) | nbrs prof.   | robust   |
|-----|-----|-------|--------------------|--------|-----------|-----------|-----------|------------|------------|------------|--------------|----------|
|   5 | 12h | $1000 | hold_to_resolution | $100   |        39 | 78%       |        89 |        122 | 71%        |      3,482 | 83%          | ROBUST   |
|   6 | 48h | $1000 | hold_to_resolution | $100   |        48 | 78%       |       115 |        102 | 77%        |      3,240 | 100%         | ROBUST   |
|   5 | 6h  | $1000 | hold_to_resolution | $100   |        31 | 80%       |       179 |        103 | 73%        |      2,956 | 100%         | ROBUST   |
|   6 | 24h | $1000 | hold_to_resolution | $100   |        38 | 81%       |       110 |         89 | 77%        |      2,882 | 100%         | ROBUST   |
|   5 | 48h | $2500 | copy_exits         | $100   |        37 | 71%       |        44 |         97 | 71%        |      2,848 | 100%         | ROBUST   |
|   5 | 12h | $1000 | copy_exits         | $100   |        39 | 76%       |        52 |        122 | 69%        |      2,835 | 83%          | ROBUST   |
|   5 | 48h | $2500 | hold_to_resolution | $100   |        37 | 83%       |       213 |         97 | 72%        |      2,819 | 100%         | ROBUST   |
|   5 | 24h | $1000 | hold_to_resolution | $100   |        52 | 76%       |       -41 |        144 | 68%        |      2,816 | 83%          |          |
|   7 | 24h | $1000 | hold_to_resolution | $100   |        22 | 86%       |       220 |         56 | 87%        |      2,795 | 100%         | ROBUST   |
|   6 | 48h | $1000 | copy_exits         | $100   |        48 | 74%       |        13 |        102 | 74%        |      2,746 | 100%         | ROBUST   |
|   6 | 12h | $1000 | hold_to_resolution | $100   |        26 | 80%       |       216 |         70 | 79%        |      2,731 | 100%         | ROBUST   |
|   6 | 3h  | $1000 | hold_to_resolution | $100   |        12 | 73%       |       110 |         54 | 85%        |      2,724 | 100%         | ROBUST   |
|   5 | 12h | $500  | hold_to_resolution | $100   |        61 | 75%       |        80 |        159 | 66%        |      2,683 | 83%          | ROBUST   |
|   6 | 6h  | $1000 | hold_to_resolution | $100   |        16 | 73%       |        -9 |         64 | 79%        |      2,662 | 100%         |          |
|   7 | 48h | $1000 | hold_to_resolution | $100   |        35 | 83%       |        94 |         68 | 82%        |      2,607 | 100%         | ROBUST   |
|   5 | 24h | $500  | hold_to_resolution | $100   |        86 | 74%       |        96 |        188 | 66%        |      2,552 | 83%          | ROBUST   |
|   8 | 24h | $500  | hold_to_resolution | $100   |        26 | 76%       |        62 |         53 | 84%        |      2,548 | 100%         | ROBUST   |
|   7 | 24h | $1000 | copy_exits         | $100   |        22 | 82%       |       145 |         56 | 85%        |      2,545 | 100%         | ROBUST   |
|   5 | 24h | $2500 | copy_exits         | $100   |        26 | 79%       |        98 |         83 | 70%        |      2,543 | 100%         | ROBUST   |
|   7 | 3h  | $500  | hold_to_resolution | $100   |         9 | 78%       |        90 |         42 | 95%        |      2,534 | 100%         | ROBUST   |
|   7 | 24h | $500  | hold_to_resolution | $100   |        34 | 76%       |        -6 |         81 | 78%        |      2,504 | 100%         |          |
|   8 | 48h | $500  | hold_to_resolution | $100   |        37 | 78%       |       133 |         69 | 79%        |      2,465 | 100%         | ROBUST   |
|   5 | 1h  | $500  | hold_to_resolution | $100   |        11 | 80%       |       291 |         62 | 82%        |      2,457 | 100%         | ROBUST   |
|   7 | 48h | $1000 | copy_exits         | $100   |        35 | 77%       |       -29 |         68 | 80%        |      2,452 | 100%         |          |
|   7 | 3h  | $500  | copy_exits         | $100   |         9 | 78%       |        88 |         42 | 93%        |      2,447 | 100%         | ROBUST   |
|   5 | 12h | $500  | copy_exits         | $100   |        61 | 71%       |         9 |        159 | 62%        |      2,445 | 83%          | ROBUST   |
|   5 | 24h | $500  | copy_exits         | $100   |        86 | 70%       |      -214 |        188 | 64%        |      2,414 | 83%          |          |
|   5 | 24h | $2500 | hold_to_resolution | $100   |        26 | 88%       |       186 |         83 | 70%        |      2,404 | 100%         | ROBUST   |
|   6 | 3h  | $1000 | copy_exits         | $100   |        12 | 73%       |        96 |         54 | 85%        |      2,375 | 100%         | ROBUST   |
|   5 | 3h  | $1000 | hold_to_resolution | $100   |        19 | 83%       |       220 |         86 | 73%        |      2,371 | 100%         | ROBUST   |
|   4 | 6h  | $2500 | copy_exits         | $100   |        25 | 75%       |        68 |        121 | 64%        |      2,368 | 60%          |          |
|   5 | 6h  | $1000 | copy_exits         | $100   |        31 | 77%       |       165 |        103 | 71%        |      2,362 | 83%          | ROBUST   |
|   6 | 12h | $1000 | copy_exits         | $100   |        26 | 80%       |       278 |         70 | 78%        |      2,352 | 100%         | ROBUST   |
|   7 | 12h | $500  | hold_to_resolution | $100   |        23 | 74%       |        17 |         66 | 80%        |      2,348 | 100%         | ROBUST   |
|   5 | 48h | $1000 | hold_to_resolution | $100   |        67 | 74%       |      -237 |        168 | 67%        |      2,326 | 80%          |          |
|   5 | 3h  | $1000 | copy_exits         | $100   |        19 | 67%       |        95 |         86 | 71%        |      2,310 | 100%         | ROBUST   |
|   5 | 24h | $1000 | copy_exits         | $100   |        52 | 72%       |       -57 |        144 | 66%        |      2,304 | 83%          |          |
|   6 | 6h  | $1000 | copy_exits         | $100   |        16 | 73%       |        98 |         64 | 77%        |      2,300 | 100%         | ROBUST   |
|   6 | 6h  | $250  | hold_to_resolution | $100   |        43 | 67%       |      -352 |        107 | 71%        |      2,281 | 100%         |          |
|   6 | 12h | $250  | hold_to_resolution | $100   |        53 | 69%       |      -319 |        134 | 70%        |      2,273 | 100%         |          |

(1260 cells total for cohort B; full grid lives in the backtest_results table.)

### Cohort C

|   N | W   | F     | exit               | size   |   sig(tr) | win(tr)   |   PnL(tr) |   sig(val) | win(val)   |   PnL(val) | nbrs prof.   | robust   |
|-----|-----|-------|--------------------|--------|-----------|-----------|-----------|------------|------------|------------|--------------|----------|
|   7 | 48h | $500  | hold_to_resolution | $100   |        40 | 68%       |      -428 |        101 | 73%        |      2,969 | 100%         |          |
|   7 | 48h | $500  | copy_exits         | $100   |        40 | 68%       |      -392 |        101 | 71%        |      2,583 | 100%         |          |
|   7 | 3h  | $250  | hold_to_resolution | $100   |         8 | 75%       |       -20 |         66 | 74%        |      2,531 | 100%         |          |
|   8 | 48h | $250  | hold_to_resolution | $100   |        37 | 68%       |      -348 |        100 | 73%        |      2,363 | 100%         |          |
|   8 | 48h | $500  | hold_to_resolution | $100   |        24 | 75%       |        56 |         75 | 76%        |      2,256 | 100%         | ROBUST   |
|   7 | 6h  | $250  | hold_to_resolution | $100   |        16 | 69%       |        88 |         76 | 72%        |      2,252 | 100%         | ROBUST   |
|   8 | 48h | $250  | copy_exits         | $100   |        37 | 59%       |      -333 |        100 | 70%        |      2,239 | 100%         |          |
|   7 | 12h | $500  | hold_to_resolution | $100   |        16 | 69%       |       -74 |         70 | 72%        |      2,221 | 100%         |          |
|   7 | 3h  | $250  | copy_exits         | $100   |         8 | 75%       |       -20 |         66 | 74%        |      2,206 | 100%         |          |
|   6 | 3h  | $500  | hold_to_resolution | $100   |        12 | 75%       |        77 |         82 | 73%        |      2,147 | 100%         | ROBUST   |
|   7 | 24h | $500  | hold_to_resolution | $100   |        26 | 68%       |      -218 |         86 | 73%        |      2,137 | 100%         |          |
|   7 | 3h  | $500  | copy_exits         | $100   |         4 | 75%       |        40 |         51 | 78%        |      2,098 | 100%         | ROBUST   |
|   7 | 3h  | $500  | hold_to_resolution | $100   |         4 | 75%       |        40 |         51 | 78%        |      2,098 | 100%         | ROBUST   |
|   7 | 24h | $250  | hold_to_resolution | $100   |        37 | 72%       |        20 |        116 | 70%        |      2,097 | 100%         | ROBUST   |
|   7 | 12h | $250  | hold_to_resolution | $100   |        25 | 72%       |       121 |         96 | 71%        |      2,089 | 100%         | ROBUST   |
|   8 | 24h | $250  | hold_to_resolution | $100   |        24 | 71%       |       -53 |         84 | 72%        |      2,086 | 100%         |          |
|   8 | 24h | $500  | hold_to_resolution | $100   |        18 | 78%       |        94 |         63 | 74%        |      2,074 | 100%         | ROBUST   |
|   5 | 48h | $1000 | hold_to_resolution | $100   |        53 | 75%       |      -181 |        185 | 72%        |      2,067 | 80%          |          |
|   7 | 12h | $250  | copy_exits         | $100   |        25 | 72%       |       103 |         96 | 68%        |      1,991 | 100%         | ROBUST   |
|   6 | 24h | $500  | hold_to_resolution | $100   |        40 | 70%       |       -31 |        143 | 69%        |      1,986 | 100%         |          |
|   6 | 24h | $1000 | hold_to_resolution | $100   |        29 | 75%       |      -155 |         98 | 73%        |      1,983 | 100%         |          |
|   7 | 6h  | $250  | copy_exits         | $100   |        16 | 69%       |        86 |         76 | 68%        |      1,980 | 100%         | ROBUST   |
|   5 | 3h  | $1000 | copy_exits         | $100   |        13 | 46%       |      -314 |        100 | 71%        |      1,966 | 100%         |          |
|   7 | 24h | $1000 | copy_exits         | $100   |        12 | 75%       |       221 |         61 | 73%        |      1,963 | 100%         | ROBUST   |
|   7 | 12h | $1000 | copy_exits         | $100   |         7 | 100%      |       267 |         46 | 78%        |      1,959 | 100%         | ROBUST   |
|   8 | 12h | $500  | hold_to_resolution | $100   |        10 | 80%       |       111 |         48 | 74%        |      1,941 | 100%         | ROBUST   |
|   6 | 12h | $1000 | copy_exits         | $100   |        16 | 62%       |      -150 |         80 | 69%        |      1,930 | 100%         |          |
|   7 | 6h  | $500  | hold_to_resolution | $100   |        10 | 70%       |        20 |         57 | 73%        |      1,907 | 100%         | ROBUST   |
|   8 | 48h | $500  | copy_exits         | $100   |        24 | 75%       |        35 |         75 | 72%        |      1,907 | 100%         | ROBUST   |
|   6 | 6h  | $250  | hold_to_resolution | $100   |        32 | 69%       |       197 |        130 | 68%        |      1,906 | 100%         | ROBUST   |
|   7 | 12h | $500  | copy_exits         | $100   |        16 | 69%       |       -74 |         70 | 71%        |      1,896 | 100%         |          |
|   5 | 3h  | $1000 | hold_to_resolution | $100   |        13 | 62%       |      -191 |        100 | 71%        |      1,895 | 100%         |          |
|   7 | 12h | $1000 | hold_to_resolution | $100   |         7 | 100%      |       270 |         46 | 78%        |      1,894 | 100%         | ROBUST   |
|   6 | 6h  | $1000 | hold_to_resolution | $100   |        12 | 67%       |       -92 |         68 | 74%        |      1,878 | 100%         |          |
|   6 | 3h  | $1000 | hold_to_resolution | $100   |         6 | 67%       |        11 |         62 | 75%        |      1,876 | 100%         | ROBUST   |
|   8 | 24h | $250  | copy_exits         | $100   |        24 | 67%       |       -40 |         84 | 71%        |      1,876 | 100%         |          |
|   7 | 24h | $500  | copy_exits         | $100   |        26 | 65%       |      -267 |         86 | 74%        |      1,874 | 100%         |          |
|   6 | 3h  | $1000 | copy_exits         | $100   |         6 | 50%       |       -22 |         62 | 75%        |      1,867 | 100%         |          |
|   6 | 6h  | $1000 | copy_exits         | $100   |        12 | 58%       |      -132 |         68 | 74%        |      1,859 | 100%         |          |
|   7 | 48h | $1000 | copy_exits         | $100   |        20 | 75%       |       105 |         72 | 73%        |      1,850 | 100%         | ROBUST   |

(1260 cells total for cohort C; full grid lives in the backtest_results table.)

### Cohort union

|   N | W   | F     | exit               | size   |   sig(tr) | win(tr)   |   PnL(tr) |   sig(val) | win(val)   |   PnL(val) | nbrs prof.   | robust   |
|-----|-----|-------|--------------------|--------|-----------|-----------|-----------|------------|------------|------------|--------------|----------|
|   8 | 6h  | $250  | hold_to_resolution | $100   |        42 | 73%       |       277 |        120 | 71%        |      2,731 | 100%         | ROBUST   |
|   8 | 12h | $500  | hold_to_resolution | $100   |        40 | 75%       |       -52 |        111 | 73%        |      2,731 | 100%         |          |
|   8 | 24h | $500  | hold_to_resolution | $100   |        51 | 73%       |       161 |        129 | 72%        |      2,657 | 100%         | ROBUST   |
|   8 | 12h | $250  | hold_to_resolution | $100   |        53 | 69%       |      -102 |        146 | 70%        |      2,642 | 100%         |          |
|   8 | 3h  | $500  | hold_to_resolution | $100   |        18 | 67%       |      -159 |         81 | 74%        |      2,610 | 100%         |          |
|   7 | 6h  | $500  | hold_to_resolution | $100   |        37 | 75%       |       118 |        128 | 68%        |      2,553 | 100%         | ROBUST   |
|   6 | 48h | $2500 | hold_to_resolution | $100   |        44 | 78%       |       115 |        108 | 71%        |      2,522 | 100%         | ROBUST   |
|   8 | 6h  | $500  | hold_to_resolution | $100   |        28 | 71%       |       -72 |         94 | 72%        |      2,521 | 100%         |          |
|   7 | 3h  | $1000 | hold_to_resolution | $100   |        18 | 67%       |      -142 |         82 | 74%        |      2,515 | 100%         |          |
|   6 | 48h | $2500 | copy_exits         | $100   |        44 | 68%       |       -11 |        108 | 70%        |      2,483 | 100%         |          |
|   8 | 24h | $500  | copy_exits         | $100   |        51 | 65%       |      -400 |        129 | 69%        |      2,483 | 100%         |          |
|   7 | 3h  | $1000 | copy_exits         | $100   |        18 | 56%       |      -208 |         82 | 73%        |      2,447 | 100%         |          |
|   7 | 3h  | $500  | hold_to_resolution | $100   |        25 | 71%       |      -173 |        111 | 70%        |      2,378 | 100%         |          |
|   7 | 12h | $1000 | hold_to_resolution | $100   |        35 | 71%       |      -195 |        105 | 71%        |      2,343 | 100%         |          |
|   8 | 48h | $500  | copy_exits         | $100   |        80 | 65%       |      -679 |        148 | 69%        |      2,336 | 75%          |          |
|   8 | 12h | $500  | copy_exits         | $100   |        40 | 70%       |       -13 |        111 | 70%        |      2,323 | 100%         |          |
|   7 | 6h  | $1000 | hold_to_resolution | $100   |        26 | 73%       |      -111 |         93 | 71%        |      2,321 | 100%         |          |
|   7 | 12h | $1000 | copy_exits         | $100   |        35 | 60%       |      -428 |        105 | 69%        |      2,318 | 100%         |          |
|   6 | 12h | $1000 | hold_to_resolution | $100   |        51 | 76%       |      -178 |        152 | 67%        |      2,304 | 83%          |          |
|   7 | 12h | $500  | hold_to_resolution | $100   |        51 | 76%       |       108 |        152 | 69%        |      2,298 | 100%         | ROBUST   |
|   8 | 3h  | $250  | hold_to_resolution | $100   |        24 | 71%       |       -97 |        102 | 70%        |      2,212 | 100%         |          |
|   8 | 12h | $250  | copy_exits         | $100   |        53 | 62%       |       -60 |        146 | 67%        |      2,197 | 100%         |          |
|   6 | 48h | $1000 | hold_to_resolution | $100   |        90 | 73%       |      -432 |        202 | 67%        |      2,185 | 60%          |          |
|   7 | 6h  | $1000 | copy_exits         | $100   |        26 | 62%       |      -302 |         93 | 69%        |      2,171 | 100%         |          |
|   8 | 3h  | $500  | copy_exits         | $100   |        18 | 67%       |       -67 |         81 | 70%        |      2,090 | 100%         |          |
|   6 | 48h | $1000 | copy_exits         | $100   |        90 | 64%       |      -294 |        202 | 64%        |      2,082 | 60%          |          |
|   8 | 48h | $500  | hold_to_resolution | $100   |        80 | 73%       |        90 |        148 | 72%        |      2,071 | 100%         | ROBUST   |
|   7 | 24h | $500  | hold_to_resolution | $100   |        72 | 74%       |       394 |        175 | 67%        |      2,048 | 83%          | ROBUST   |
|   8 | 24h | $1000 | hold_to_resolution | $100   |        34 | 75%       |      -103 |         91 | 74%        |      2,001 | 100%         |          |
|   8 | 6h  | $500  | copy_exits         | $100   |        28 | 64%       |      -224 |         94 | 68%        |      1,986 | 100%         |          |
|   7 | 12h | $500  | copy_exits         | $100   |        51 | 68%       |       -62 |        152 | 66%        |      1,969 | 100%         |          |
|   7 | 24h | $1000 | hold_to_resolution | $100   |        45 | 74%       |      -197 |        124 | 69%        |      1,968 | 100%         |          |
|   8 | 6h  | $250  | copy_exits         | $100   |        42 | 66%       |       246 |        120 | 68%        |      1,958 | 100%         | ROBUST   |
|   6 | 24h | $2500 | hold_to_resolution | $100   |        33 | 83%       |       321 |         89 | 68%        |      1,936 | 100%         | ROBUST   |
|   8 | 48h | $1000 | hold_to_resolution | $100   |        51 | 73%       |      -167 |        104 | 73%        |      1,915 | 100%         |          |
|   8 | 12h | $1000 | hold_to_resolution | $100   |        26 | 77%       |        11 |         75 | 73%        |      1,819 | 100%         | ROBUST   |
|   7 | 24h | $500  | copy_exits         | $100   |        72 | 67%       |       258 |        175 | 66%        |      1,798 | 83%          | ROBUST   |
|   6 | 12h | $1000 | copy_exits         | $100   |        51 | 66%       |      -160 |        152 | 65%        |      1,784 | 83%          |          |
|   6 | 24h | $2500 | copy_exits         | $100   |        33 | 73%       |        67 |         89 | 67%        |      1,776 | 100%         | ROBUST   |
|   8 | 12h | $100  | copy_exits         | $100   |        71 | 62%       |      -420 |        185 | 63%        |      1,765 | 50%          |          |

(1260 cells total for cohort union; full grid lives in the backtest_results table.)


## 5. Category consistency (cohort B top 3 cells, validate period)


**N=5 W=12h F=$1000 hold_to_resolution $100**

| category   |   signals | win rate   | PnL       |
|------------|-----------|------------|-----------|
| SPORTS     |        87 | 69%        | $2,663.30 |
| POLITICS   |        33 | 75%        | $654.00   |
| CRYPTO     |         1 | 100%       | $154.78   |
| UNMAPPED   |         1 | 100%       | $10.31    |

**N=6 W=48h F=$1000 hold_to_resolution $100**

| category   |   signals | win rate   | PnL       |
|------------|-----------|------------|-----------|
| SPORTS     |        58 | 78%        | $2,323.66 |
| POLITICS   |        41 | 74%        | $757.89   |
| CRYPTO     |         2 | 100%       | $158.89   |
| UNMAPPED   |         1 | —          | $0.00     |

**N=5 W=6h F=$1000 hold_to_resolution $100**

| category   |   signals | win rate   | PnL       |
|------------|-----------|------------|-----------|
| SPORTS     |        78 | 71%        | $1,986.59 |
| POLITICS   |        23 | 78%        | $804.23   |
| CRYPTO     |         1 | 100%       | $154.78   |
| UNMAPPED   |         1 | 100%       | $10.31    |

Categories positive across all three cells are the consistent earners; categories negative in every cell drag returns and are candidates for exclusion in paper mode.


## 6. Hold-to-resolution vs copy-exits (cohort B, top 3 combos)

| combo                  |   hold PnL(val) |   copy PnL(val) | winner          |
|------------------------|-----------------|-----------------|-----------------|
| N=5 W=12h F=$1000 $100 |         3482.39 |         2834.57 | hold (+$647.82) |
| N=6 W=48h F=$1000 $100 |         3240.43 |         2746.21 | hold (+$494.22) |
| N=5 W=6h F=$1000 $100  |         2955.91 |         2362.44 | hold (+$593.47) |


## 7. Equity curves

Validate-period cumulative PnL for cohort B's top 3 cells: `reports/equity_curve_top3.csv` (119 rows).

## 8. Best-cell trade log

Every simulated validate-period trade for cohort B **N=5 W=12h F=$1000 hold_to_resolution $100**: `reports/best_cell_trades.csv` (122 rows).

## 9. Unresolved positions (cohort B, validate period, top 10 cells)

| cell                                      |   unresolved | capital tied up   |
|-------------------------------------------|--------------|-------------------|
| N=5 W=12h F=$1000 hold_to_resolution $100 |            3 | $300              |
| N=6 W=48h F=$1000 hold_to_resolution $100 |            6 | $600              |
| N=5 W=6h F=$1000 hold_to_resolution $100  |            2 | $200              |
| N=6 W=24h F=$1000 hold_to_resolution $100 |            3 | $300              |
| N=5 W=48h F=$2500 copy_exits $100         |            3 | $300              |
| N=5 W=12h F=$1000 copy_exits $100         |            3 | $300              |
| N=5 W=48h F=$2500 hold_to_resolution $100 |            3 | $300              |
| N=5 W=24h F=$1000 hold_to_resolution $100 |            5 | $500              |
| N=7 W=24h F=$1000 hold_to_resolution $100 |            3 | $300              |
| N=6 W=48h F=$1000 copy_exits $100         |            4 | $400              |


## 10. Recommended next steps

- Best robust cell **differs from the current paper config** (paper: N=5 W=24h F=$500 hold_to_resolution). Update the `paper:` block to N=5, window=12h, floor=$1000, exit=hold_to_resolution, and run paper on cohort B's wallets.
- Do NOT go live until the decision-gate checklist in PLAN.md passes.
