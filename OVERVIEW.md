# Polymarket Copy-Trading Bot — Project Overview

## What we're building

A bot that tracks ~100 hand-picked top Polymarket traders and detects **consensus signals**: when N distinct watchlist traders open the same side of the same market within a time window, we copy that position. The core hypothesis is that agreement among independently profitable traders is a stronger signal than any single trader's activity.

Build order is strict: **backtest → paper trade → live**. Do not write any live-execution code until the backtest and paper phases produce results. The backtest is the main deliverable of the first build session — it must tell us, with historical data, whether this strategy would have made money, under which parameters, and in which market categories.

## Owner's decisions (already made — do not re-ask)

- **Exit strategy:** backtest BOTH (a) hold to resolution and (b) copy the traders' exits. Compare them in the final report.
- **Categories:** backtest 5–10 categories (e.g., Politics, Sports, Crypto, Economy/Finance, Geopolitics, Pop Culture, Science/Tech, Elections) and identify the most consistently profitable. Note: different top traders specialize in different categories, so trader discovery is done per category.
- **Position sizing:** simulate fixed sizes of $20 and $50 per signal. Live trading will start at ~$20/position.
- **Stack:** Python 3.11+, `requests`, SQLite. Runs locally. No frameworks needed.

## Data sources (all public, no auth required)

### Data API — `https://data-api.polymarket.com`
- `GET /v1/leaderboard` — params: `category` (OVERALL, POLITICS, SPORTS, CRYPTO, ...), `timePeriod` (DAY, WEEK, MONTH, ALL), `orderBy` (PNL or VOL), `limit` (max 50), `offset` (max 1000). Returns `proxyWallet`, `userName`, `pnl`, `vol`. The wallet address is the primary key for everything.
- `GET /trades` — params: `user` (wallet), `limit` (max 10,000), `offset`, `side` (BUY/SELL), `filterType=CASH` + `filterAmount` (min trade size in $), `takerOnly` (default true). Returns per-trade: `proxyWallet`, `side`, `conditionId`, `outcome`, `outcomeIndex`, `size`, `price`, `timestamp`, `transactionHash`, market `title`/`slug`. Paginate with offset to pull full history per wallet. Use `transactionHash` + `conditionId` + wallet as the dedupe key.
- `GET /positions` — params: `user`. Current open positions with cost basis. Used for trader vetting.
- `GET /activity` — per-user activity feed (trades, redeems). Useful for verifying resolution payouts.

### Gamma API — `https://gamma-api.polymarket.com`
- `GET /markets` — market metadata: `conditionId`, `question`, `slug`, `endDate`, `closed`, `outcomePrices` (for resolved markets this shows the final payout, e.g. `["1","0"]`), `volume`, `liquidity`, and tags/category. This is where the backtest gets **resolution outcomes**.
- `GET /events` — groups related markets; has category tags.
- If category isn't directly on the market object, resolve it via the market's `events`/`tags`.

### CLOB API — `https://clob.polymarket.com` (public endpoints)
- `GET /prices-history` — params: `market` (the outcome **token ID**, not conditionId), `startTs`, `endTs`, `fidelity` (minutes). Historical price series. Used to price backtest entries/exits at signal time.
- `GET /book?token_id=...` — live order book. Used in paper mode to simulate realistic fills (walk the asks).
- Token IDs for a market's outcomes come from Gamma (`clobTokenIds`) or CLOB `/markets`.

**Rate limiting:** these are unauthenticated public APIs. Add polite throttling (e.g., 5–10 req/s max), exponential backoff on 429/5xx, and cache everything in SQLite so re-runs don't re-fetch.

## Phase 1 — Trader discovery & vetting (`discover.py`)

1. For each target category, pull leaderboard pages for `timePeriod=MONTH` and `timePeriod=ALL`, `orderBy=PNL` (paginate: limit 50, offset up to 1000).
2. Candidate pool = traders appearing in the top ranks of BOTH windows (consistency filter).
3. For each candidate, pull trade history and compute vetting stats:
   - distinct markets traded (require ≥ 20 — filters one-hit wonders)
   - total trades (require ≥ 50)
   - **market-maker filter:** if a wallet has both BUYs and SELLs on the same token within short intervals at high frequency across many markets, it's a market maker — exclude. A simple heuristic: exclude if median hold time < 1 hour or if >60% of markets have round-trip trades within the same day.
   - realized PnL across closed positions (positive, and not dominated by 1–2 markets: top-2 markets should be < 60% of total PnL)
4. Output: `watchlist` table in SQLite (wallet, username, categories, vetting stats, selected=true/false). Cap ~100–150 wallets across all categories. Print a human-readable shortlist so the owner can manually approve/remove wallets before backtesting.

## Phase 2 — Historical ingestion (`ingest.py`)

- For every watchlist wallet, pull FULL trade history for the lookback window (target: **6 months**) via `/trades?user=...` with pagination. Store raw trades in SQLite (`trades` table, deduped).
- For every `conditionId` seen, pull Gamma market metadata (question, category, endDate, closed, outcomePrices, clobTokenIds). Store in `markets` table.
- Ingestion must be resumable (track per-wallet high-water mark) — 100 wallets × months of history is many requests.

## Phase 3 — Backtest engine (`signals.py`, `backtest.py`)

### Signal reconstruction (offline)
Group BUY trades by `(conditionId, outcomeIndex)`. Slide a window of length W over time. A **signal fires at the timestamp of the Nth distinct wallet** to buy that outcome with a trade ≥ the size floor F within W. One signal max per (market, outcome) per direction — don't re-enter.

### Entry pricing
Entry price = price from `/prices-history` at (or immediately after) signal time, **plus a slippage haircut**. Model slippage as +1¢ on the price for $20 positions and +2¢ for $50 (crude but honest; refine later with book data from paper mode). Skip signals where the entry price is > 0.95 or < 0.05 (no room) or where market liquidity at signal time is unknown/tiny.

### Exit strategy A — hold to resolution
PnL = (payout per share from `outcomePrices` − entry price) × shares. Only include markets that have resolved; open positions at end of lookback are reported separately as "unresolved."

### Exit strategy B — copy their exits
Track the wallets that formed the signal. When ≥ half of them have SOLD ≥ 50% of their position in that token, exit at the `/prices-history` price at that moment (minus 1¢ slippage). If the market resolves first, use resolution payout.

### Parameter sweep
Grid: N ∈ {2, 3, 4, 5} × W ∈ {1h, 6h, 24h} × F ∈ {$250, $500, $1000} × exit ∈ {A, B} × size ∈ {$20, $50}. Run all cells; per cell compute: signal count, win rate, avg PnL per trade, total PnL, return on capital deployed, max drawdown, and PnL broken down by category.

### Overfitting guard (mandatory)
Split the lookback: **train = first 4 months, validate = last 2 months.** Pick the best cells on train, then report their validate performance. If a parameter set only works in-sample, say so in the report. Do not report only the best in-sample cell as "the result."

### Known bias — state it in the report
**Survivorship bias is baked into this backtest**: the watchlist comes from today's leaderboard, i.e., traders we already know ended up profitable. Their historical trades will look better than a real-time selection would have. Mitigations: (1) the train/validate split above, (2) prefer traders whose train-period PnL was already positive, (3) treat backtest returns as an upper bound, not an expectation. The report must include this caveat prominently.

## Phase 4 — Report (`report.py`)

Generate `reports/backtest_report.md` containing: the parameter grid results as a table (sorted by validate-period return), per-category consistency table, equity curve data (CSV) for the top 3 parameter sets, list of every simulated trade for the best cell (market, entry, exit, PnL), the unresolved-positions count, and the survivorship-bias caveat. Human-readable — the owner decides go/no-go from this file.

## Phase 5 — Paper trading mode (`paper.py`) — same engine, live data

- Poll `GET /trades` (global feed, NO user filter, `takerOnly=true`, limit high) every ~20s; filter locally against the watchlist; dedupe by `transactionHash`.
- Run the SAME signal function as the backtest (shared code in `signals.py` — this is non-negotiable; the backtest is only valid if paper/live use identical logic).
- On signal: fetch `/book` for the token, simulate filling $20 by walking the asks, record simulated entry AND the signal traders' average price. The gap between them = measured alpha decay. Log every signal to SQLite with both numbers.
- Track open paper positions; apply the chosen exit strategy; write a daily summary.

## Phase 6 — Live execution (LATER — do not build yet)

The owner is in the US. The main Polymarket CLOB **blocks US order placement**. Live trading will go through **Polymarket US** (`polymarket.us`) — a separate CFTC-regulated venue with its own API (Ed25519 keys, KYC via iOS app). Open questions to resolve before this phase: market overlap between global Polymarket (signal source) and Polymarket US (execution venue), and price tracking between the two books. Leave a stub `live.py` with these notes; nothing more.

## Repo layout

```
polymarket-copybot/
├── OVERVIEW.md            # this file
├── config.yaml            # categories, lookback, sweep grid, thresholds, poll interval
├── requirements.txt       # requests, pyyaml (keep deps minimal)
├── data/                  # sqlite db (gitignored)
├── reports/               # backtest + paper reports
└── src/
    ├── data_api.py        # Data API client (leaderboard, trades, positions)
    ├── gamma_api.py       # market metadata + resolutions
    ├── clob_api.py        # prices-history, order book
    ├── db.py              # SQLite schema + helpers
    ├── discover.py        # Phase 1
    ├── ingest.py          # Phase 2
    ├── signals.py         # shared signal logic (backtest + paper)
    ├── backtest.py        # Phase 3
    ├── report.py          # Phase 4
    ├── paper.py           # Phase 5
    └── live.py            # stub only
```

## Build order for tonight

1. `db.py` + API clients with throttling/backoff — verify each endpoint with a smoke test against 1 known wallet before proceeding.
2. `discover.py` → produce the shortlist, pause for owner approval of the watchlist.
3. `ingest.py` → run it (this is the long, resumable step).
4. `signals.py` + `backtest.py` + `report.py` → run the sweep, read the report.
5. Only if the report is worth acting on: `paper.py`.

## Guardrails

- No private keys, no wallets, no order placement anywhere in this codebase yet.
- Every API response field name above should be verified against a real response on first call (field casing occasionally differs, e.g. `proxyWallet` vs `proxy_wallet`) — adjust the code to reality, not the doc.
- If an endpoint's behavior contradicts this document, trust the live API and leave a comment noting the discrepancy.
