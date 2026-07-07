# Deep analysis on uncapped history — generated 2026-07-07 00:36 UTC

Live cell N=5 W=12h, $50/position, cohort B, history to 2026-07-02T00:00:00Z, halves split at 2026-04-02.

## Data coverage after the deep pull (trust anchor for everything below)

- wallets: 250; verified-full history: 250; partial/truncated: 0; no progress: 0
- history reaching the half boundary: 184/250
- history reaching the window start (±14d): 141/250

Liquidity caveat: historical order-book depth does not exist; volume floors below use lifetime market volume as a stated proxy.

## P2: size-floor x volume-floor grid (hold_to_resolution)

PnL/$ per cell; H1 and H2 shown separately. A cell is only trustworthy if positive in BOTH halves.

### H1 (PnL/$ | closed n)

| size floor \ vol floor | $0 | $100k | $250k | $500k | $1000k | $2000k | $5000k |
|---|---|---|---|---|---|---|---|
| $100 | +0.069 (133) | +0.069 (116) | +0.077 (114) | +0.085 (110) | +0.105 (93) | +0.091 (82) | +0.069 (69) |
| $250 | +0.141 (91) | +0.145 (79) | +0.145 (79) | +0.145 (78) | +0.141 (71) | +0.139 (65) | +0.174 (55) |
| $500 | +0.195 (66) | +0.201 (59) | +0.201 (59) | +0.201 (59) | +0.208 (55) | +0.200 (52) | +0.233 (44) |
| $750 | +0.061 (49) | +0.072 (43) | +0.072 (43) | +0.072 (43) | +0.093 (41) | +0.074 (38) | +0.109 (33) |
| $1000 | +0.030 (40) | +0.031 (35) | +0.031 (35) | +0.031 (35) | +0.055 (33) | +0.055 (33) | +0.119 (30) |

### H2 (PnL/$ | closed n)

| size floor \ vol floor | $0 | $100k | $250k | $500k | $1000k | $2000k | $5000k |
|---|---|---|---|---|---|---|---|
| $100 | -0.010 (521) | -0.010 (514) | -0.005 (498) | -0.002 (474) | +0.004 (454) | +0.019 (395) | +0.062 (270) |
| $250 | -0.019 (356) | -0.019 (356) | -0.017 (352) | -0.015 (345) | -0.014 (340) | -0.004 (305) | +0.041 (210) |
| $500 | +0.095 (248) | +0.095 (248) | +0.094 (247) | +0.094 (247) | +0.098 (244) | +0.110 (231) | +0.145 (168) |
| $750 | +0.138 (207) | +0.138 (207) | +0.138 (207) | +0.138 (207) | +0.143 (204) | +0.166 (194) | +0.215 (147) |
| $1000 | +0.214 (176) | +0.214 (176) | +0.214 (176) | +0.214 (176) | +0.222 (174) | +0.231 (170) | +0.307 (131) |

Cells profitable in BOTH halves with >= 15 closed each (25/35): (F=$100, V=$1000k), (F=$100, V=$2000k), (F=$100, V=$5000k), (F=$250, V=$5000k), (F=$500, V=$0k), (F=$500, V=$100k), (F=$500, V=$250k), (F=$500, V=$500k), (F=$500, V=$1000k), (F=$500, V=$2000k), (F=$500, V=$5000k), (F=$750, V=$0k), (F=$750, V=$100k), (F=$750, V=$250k), (F=$750, V=$500k), (F=$750, V=$1000k), (F=$750, V=$2000k), (F=$750, V=$5000k), (F=$1000, V=$0k), (F=$1000, V=$100k), (F=$1000, V=$250k), (F=$1000, V=$500k), (F=$1000, V=$1000k), (F=$1000, V=$2000k), (F=$1000, V=$5000k)

### Per-category at the live size floor (F=$1000), PnL/$ (closed n)

| half | category | $0 | $100k | $250k | $500k | $1000k | $2000k | $5000k |
|---|---|---|---|---|---|---|---|---|
| H1 | CRYPTO | - | - | - | - | - | - | - |
| H1 | POLITICS | +0.047 (37) | +0.058 (33) | +0.058 (33) | +0.058 (33) | +0.085 (31) | +0.085 (31) | +0.157 (28) |
| H1 | SPORTS | -0.180 (3) | -0.415 (2) | -0.415 (2) | -0.415 (2) | -0.415 (2) | -0.415 (2) | -0.415 (2) |
| H1 | UNMAPPED | - | - | - | - | - | - | - |
| H2 | CRYPTO | +1.614 (1) | +1.614 (1) | +1.614 (1) | +1.614 (1) | +1.614 (1) | +1.614 (1) | +1.614 (1) |
| H2 | POLITICS | +0.113 (51) | +0.113 (51) | +0.113 (51) | +0.113 (51) | +0.114 (50) | +0.114 (48) | +0.166 (38) |
| H2 | SPORTS | +0.246 (123) | +0.246 (123) | +0.246 (123) | +0.246 (123) | +0.256 (122) | +0.267 (121) | +0.350 (92) |
| H2 | UNMAPPED | +0.115 (1) | +0.115 (1) | +0.115 (1) | +0.115 (1) | +0.115 (1) | - | - |

## P3: politics deep-dive (hold unless noted)

- hold_to_resolution all: n=87, win 72%, PnL +425.39, PnL/$ +0.098
- hold_to_resolution H1: n=37, win 73%, PnL +86.94, PnL/$ +0.047
- hold_to_resolution H2: n=50, win 72%, PnL +338.44, PnL/$ +0.135
- copy_exits all: n=89, win 67%, PnL +36.27, PnL/$ +0.008
- copy_exits H1: n=39, win 72%, PnL +97.86, PnL/$ +0.050
- copy_exits H2: n=50, win 64%, PnL -61.59, PnL/$ -0.025

### Sub-topics (first specific event tag)

| topic | signals | closed | win% | PnL $ | PnL/$ |
|---|---|---|---|---|---|
| Geopolitics | 16 | 16 | 75% | +265.45 | +0.332 |
| Iran | 23 | 23 | 70% | +146.58 | +0.127 |
| Iran Ceasefire | 5 | 5 | 80% | +92.51 | +0.370 |
| Trump-Zelenskyy | 1 | 1 | 100% | +86.99 | +1.740 |
| Reza Pahlavi | 4 | 3 | 100% | +61.47 | +0.410 |
| HFC | 10 | 10 | 80% | +19.58 | +0.039 |
| U.S. x Iran | 1 | 1 | 100% | +11.35 | +0.227 |
| Strait of Hormuz | 2 | 2 | 100% | +9.68 | +0.097 |
| Iran Regime | 2 | 2 | 100% | +6.66 | +0.067 |
| Middle East | 6 | 6 | 67% | +3.29 | +0.011 |
| Jerome Powell | 1 | 1 | 100% | +2.36 | +0.047 |
| Trade War | 1 | 1 | 100% | +2.22 | +0.044 |
| Davos | 2 | 0 | - | +0.00 | - |
| Peru | 1 | 0 | - | +0.00 | - |
| Gov Shutdown | 2 | 2 | 50% | -34.64 | -0.346 |
| Oil | 2 | 2 | 50% | -41.52 | -0.415 |
| Texas Senate | 1 | 1 | 0% | -50.00 | -1.000 |
| Trump | 11 | 11 | 55% | -156.59 | -0.285 |

### Wallet concentration
- 63 wallets ever in a politics signal; 40 have positive attributed PnL
- top-3 wallets' share of attributed PnL: 64%
  - 0x25257a6a…: $+103.49 over 17 signals
  - 0x05ab749a…: $+91.47 over 7 signals
  - 0xfc2f4f50…: $+75.63 over 31 signals
- politics WITHOUT top-3 wallets (re-detected): n=65, win 75%, PnL/$ +0.033

### Timing (signal -> resolution)

| bucket | signals | closed | win% | PnL/$ |
|---|---|---|---|---|
| 0-1d | 8 | 8 | 62% | -0.193 |
| 1-7d | 15 | 15 | 73% | +0.343 |
| 7-30d | 25 | 25 | 80% | +0.325 |
| >30d | 23 | 20 | 70% | -0.069 |
| end<=signal or missing | 20 | 19 | 68% | -0.097 |

### Volume dependence

| vol quartile | range | closed | win% | PnL/$ |
|---|---|---|---|---|
| Q1 | 876,625–5,536,436 | 20 | 70% | -0.109 |
| Q2 | 5,651,394–11,324,069 | 21 | 76% | +0.075 |
| Q3 | 11,787,943–41,754,060 | 21 | 67% | +0.031 |
| Q4 | 44,375,995–269,049,107 | 21 | 76% | +0.411 |

Spearman rank corr (volume vs signal PnL): +0.132

## P4: bootstrap 95% CIs (10000 iters, seed 20260706)

| category | n | win-rate CI | PnL/$ CI | flag |
|---|---|---|---|---|
| CRYPTO | 1 | – | – | TOO THIN (n < 10) |
| POLITICS | 87 | 63%–82% | -0.097–+0.318 |  |
| SPORTS | 126 | 60%–75% | +0.018–+0.495 |  |
| UNMAPPED | 1 | – | – | TOO THIN (n < 10) |

## P5: walk-forward (6 windows, live cell)

| window | start | total closed | total PnL/$ | POLITICS PnL/$ (n) | SPORTS PnL/$ (n) |
|---|---|---|---|---|---|
| 1 | 2026-01-01 | 13 | -0.006 | -0.006 (13) | - (0) |
| 2 | 2026-01-31 | 16 | -0.153 | -0.116 (14) | -0.415 (2) |
| 3 | 2026-03-02 | 12 | +0.350 | +0.355 (11) | +0.290 (1) |
| 4 | 2026-04-02 | 21 | -0.048 | -0.134 (20) | +1.667 (1) |
| 5 | 2026-05-02 | 19 | +0.312 | +0.202 (16) | +0.546 (2) |
| 6 | 2026-06-01 | 137 | +0.232 | +0.264 (16) | +0.229 (120) |
