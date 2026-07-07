# PLAN.md — Build Plan

> Reference OVERVIEW.md for API details, endpoint params, and design rationale.
> This file is the task list. Work through it top to bottom. Do not skip ahead.

---

## Phase 0 — Scaffolding & smoke tests
**Goal:** repo structure exists, every API endpoint we depend on is proven to work with a real response, and the DB schema is ready.

### Tasks
- [x] Create the repo layout exactly as specified in OVERVIEW.md (`src/`, `data/`, `reports/`, `config.yaml`, `requirements.txt`).
- [x] `requirements.txt`: `requests`, `pyyaml`, `tabulate` (for report tables). Nothing else.
- [x] `config.yaml`: define all tunables in one place — categories list, lookback months, sweep grid values (N, W, F), poll interval, throttle settings, slippage assumptions. Every other file reads from this; no magic numbers in code.
- [x] `src/db.py` — SQLite schema with these tables:
  - `wallets` (address TEXT PK, username, category, pnl_month, pnl_all, markets_traded, total_trades, is_mm BOOL, selected BOOL, discovered_at)
  - `trades` (tx_hash TEXT, condition_id, wallet, side, outcome_index, size_usd, price, timestamp INT, ingested_at) — composite PK on (tx_hash, condition_id, wallet)
  - `markets` (condition_id TEXT PK, question, slug, category, end_date, closed BOOL, outcome_prices TEXT, clob_token_ids TEXT, volume, liquidity)
  - `price_history` (token_id TEXT, timestamp INT, price REAL) — PK on (token_id, timestamp)
  - `signals` (id INTEGER PK, condition_id, outcome_index, side, signal_time INT, n_traders INT, wallets TEXT, entry_price, exit_price, exit_time INT, exit_type TEXT, pnl_20 REAL, pnl_50 REAL, resolved BOOL, category)
  - `paper_trades` (same shape as signals, plus fields: book_entry_price, alpha_decay, status TEXT)
  - Helper functions: upsert, bulk insert, get-or-create patterns. Use `INSERT OR IGNORE` for dedupe.
- [x] `src/data_api.py` — thin client wrapping Data API. Methods:
  - `get_leaderboard(category, time_period, order_by, limit, offset)` → list of dicts
  - `get_trades(user=None, limit=100, offset=0, side=None, taker_only=True)` → list of trade dicts
  - `get_positions(user)` → list of position dicts
  - `get_activity(user)` → list of activity dicts
  - Built-in: 0.15s sleep between calls, retry with exponential backoff on 429/5xx (max 3 retries), response-field normalization (snake_case all keys).
- [x] `src/gamma_api.py` — thin client wrapping Gamma API. Methods:
  - `get_markets(condition_ids=None, slug=None, limit=100, offset=0, closed=None)` → list of market dicts
  - `get_events(slug=None, tag=None)` → list of event dicts
  - Same throttle/retry as data_api.
- [x] `src/clob_api.py` — thin client wrapping CLOB public endpoints. Methods:
  - `get_price_history(token_id, start_ts, end_ts, fidelity=60)` → list of (timestamp, price)
  - `get_book(token_id)` → dict with bids/asks
  - `get_midpoint(token_id)` → float
- [x] **Smoke tests** — after writing each client, run a standalone script that:
  - Pulls page 1 of the OVERALL leaderboard and prints 3 rows.
  - Pulls recent trades for one known top-trader wallet and prints 3 rows.
  - Pulls market metadata for one known conditionId and prints it.
  - Pulls price history for one known token ID and prints 5 rows.
  - **Print raw JSON keys** to verify casing — update clients if field names differ from OVERVIEW.md. Leave a comment on any discrepancy found.
- [x] Verify: can we get **category** from market metadata? Check if Gamma `/markets` returns a `tags` or `category` field, or if we need to go through `/events`. Document what we find — the category-mapping approach for Phase 1 depends on this.

**Done when:** all smoke tests pass, DB creates cleanly, and the category-mapping approach is documented.

---

## Phase 1 — Trader discovery (`discover.py`)
**Goal:** produce a vetted shortlist of ~100–150 wallets across categories, stored in the `wallets` table, ready for owner review.

### Tasks
- [x] Define the category list in `config.yaml`. Start with what the leaderboard API actually accepts — run a quick test to enumerate valid category values. Target 5–10 categories.
- [x] For each category:
  - Pull `timePeriod=MONTH`, `orderBy=PNL`, paginate offset 0→1000 (20 pages × 50).
  - Pull `timePeriod=ALL`, `orderBy=PNL`, same pagination.
  - Intersect: keep wallets appearing in top ranks of BOTH windows.
- [x] For each candidate wallet, pull enough trade history to compute vetting stats:
  - Distinct `conditionId` count (require ≥ 20).
  - Total trade count (require ≥ 50).
  - **Market-maker filter:** for each market the wallet traded, check if they have both BUY and SELL on the same outcomeIndex within the same day. If >60% of their markets show this round-trip pattern, flag `is_mm = True` and exclude.
  - PnL concentration: if top-2 markets by absolute PnL account for >60% of total, flag as concentrated and deprioritize (don't hard-exclude, but mark it).
- [x] Insert all candidates into `wallets` table with stats. Set `selected = True` for those passing all filters.
- [x] **Print a human-readable shortlist** to stdout AND save to `reports/watchlist_preview.txt`:
  - Columns: wallet (truncated), username, category, PnL (month), PnL (all), markets traded, trade count, is_mm, concentrated, selected.
  - Sorted by category then PnL.
  - Print count per category at the bottom.
- [x] **PAUSE HERE.** Tell the owner to review the shortlist, manually toggle `selected` in the DB or edit `watchlist_preview.txt`, then re-import. Do not proceed to Phase 2 until the owner confirms the watchlist.

**Done when:** `wallets` table is populated, the preview file exists, and the owner has approved.

---

## Phase 2 — Historical ingestion (`ingest.py`)
**Goal:** full trade history for every selected wallet, plus market metadata and price history for every market they touched, all in SQLite.

### Tasks
- [x] For each wallet where `selected = True`:
  - Pull ALL trades via `get_trades(user=wallet)`, paginating with offset until an empty page is returned. Store in `trades` table (dedupe on tx_hash + condition_id + wallet).
  - Track a per-wallet high-water mark (max offset successfully ingested) so the script is **resumable** — if it crashes at wallet 47, re-running picks up at wallet 47.
  - Print progress: `[23/108] @username — 1,847 trades ingested`.
- [x] Collect all unique `conditionId` values from the `trades` table.
- [x] For each conditionId, fetch market metadata from Gamma and store in `markets` table. Include resolution data (`closed`, `outcomePrices`). Resolve category from tags/events (using the approach documented in Phase 0).
- [x] For each market's CLOB token IDs (both outcome tokens), fetch price history spanning the full lookback window. Store in `price_history` table. Fidelity = 60 min (hourly candles are sufficient for a 6h–24h signal window).
- [x] Print ingestion summary:
  - Total trades ingested.
  - Total unique markets.
  - Markets resolved vs. still open.
  - Category distribution of markets.
  - Date range coverage (earliest trade → latest trade).
- [x] Sanity check: are there markets with trades but no Gamma metadata? Markets with no price history? Log warnings for these — they'll need to be excluded from the backtest.

**Done when:** `trades`, `markets`, and `price_history` tables are populated. The summary stats look reasonable (thousands of trades, hundreds of markets, 5+ months of coverage).

---

## Phase 3 — Backtest (`signals.py` + `backtest.py`)
**Goal:** run the full parameter sweep, produce PnL results for every cell, with train/validate split.

### `signals.py` — shared signal detection (used by BOTH backtest and paper mode)
- [x] Function: `detect_signals(trades, params) → list[Signal]`
  - Input: a list of trades (sorted by timestamp), and a params dict `{n_traders, window_seconds, size_floor_usd}`.
  - Logic: slide through trades grouped by `(conditionId, outcomeIndex, side=BUY)`. For each group, sort by time. Walk forward: at each trade, look back `window_seconds` and count distinct wallets with trades ≥ `size_floor_usd`. When the count hits `n_traders`, emit a signal at that timestamp. **One signal max per (conditionId, outcomeIndex) — do not re-fire.**
  - Output: list of Signal objects/dicts: `{condition_id, outcome_index, side, signal_time, n_traders, contributing_wallets, market_category}`.
- [x] **This function must be pure** — no DB reads, no API calls. It takes data in and returns signals out. Backtest and paper mode both call it.

### `backtest.py` — sweep engine
- [x] Load all trades from DB for selected wallets within the lookback window. Load all market metadata.
- [x] **Train/validate split:** compute the time boundary (first 4 months = train, last 2 = validate based on the actual date range in the data). Tag each trade accordingly.
- [x] Define the parameter grid from `config.yaml`:
  - `n_traders`: [2, 3, 4, 5]
  - `window`: [1h, 6h, 24h] (in seconds)
  - `size_floor`: [$250, $500, $1000] (this is the per-trader minimum trade size to count toward a signal — NOT the bot's position size)
  - `exit_strategy`: [hold_to_resolution, copy_exits]
  - `position_size`: [$20, $50]
- [x] For each grid cell, for each split (train / validate / full):
  - Run `detect_signals()` on that split's trades.
  - For each signal, compute entry price:
    - Look up `price_history` at or immediately after `signal_time` for that token.
    - Add slippage: +$0.01 for $20 positions, +$0.02 for $50.
    - Skip if entry price > 0.95 or < 0.05.
  - For **hold_to_resolution** exit:
    - Look up `markets.outcome_prices` for this conditionId. If `closed = True`, payout = the resolved price for this outcomeIndex (1.0 or 0.0 typically). PnL = (payout − entry_price) × shares. If not closed, mark as unresolved.
  - For **copy_exits** exit:
    - Track the wallets that formed this signal. Scan their subsequent trades for SELL activity on this same (conditionId, outcomeIndex). When ≥ 50% of signal wallets have sold ≥ 50% of their position, that timestamp = exit time. Exit price = price_history at exit time minus $0.01 slippage. If market resolves first, use resolution payout.
  - Store signal + result in `signals` table.
- [x] Compute per-cell metrics:
  - Signal count, resolved count, unresolved count.
  - Win rate (PnL > 0).
  - Average PnL per trade.
  - Total PnL.
  - Return on capital deployed (total PnL / total capital used, where capital = position_size × signal_count).
  - Max drawdown (running cumulative PnL, max peak-to-trough).
  - **Per-category breakdown** of all the above.
- [x] Print a progress indicator during the sweep (it's 4×3×3×2×2 = 144 cells, some may take a while).

**Done when:** all 144 cells have metrics computed for train, validate, and full periods.

---

## Phase 4 — Report (`report.py`)
**Goal:** a human-readable report that the owner uses to decide go/no-go.

### Tasks
- [x] Generate `reports/backtest_report.md` containing:

  **1. Executive summary** (3–5 sentences)
  - Best parameter set on VALIDATE data (not train).
  - Its validate-period return, win rate, and signal count.
  - Whether any parameter set was consistently profitable across both periods.

  **2. Survivorship bias caveat** (mandatory, prominent)
  - Watchlist was selected from today's leaderboard = we already know these traders ended up profitable. Historical returns are an upper bound. See OVERVIEW.md for mitigations.

  **3. Full grid results table**
  - Columns: N, Window, Floor, Exit, Size, Signals (train), Win% (train), PnL (train), Signals (val), Win% (val), PnL (val), PnL (full).
  - Sorted by validate-period PnL descending.
  - Bold or mark the top 3 validate rows.

  **4. Category consistency table**
  - For the top 3 parameter sets: per-category win rate and PnL.
  - Highlight which categories are consistently profitable vs. which drag returns.

  **5. Strategy A vs B comparison**
  - For each of the top 3 N/W/F combos: side-by-side hold-to-resolution vs copy-exits PnL.
  - Note which exit strategy won and by how much.

  **6. Equity curves**
  - Export `reports/equity_curve_top3.csv` with columns: `trade_number, timestamp, cumulative_pnl_cell1, cumulative_pnl_cell2, cumulative_pnl_cell3` (using validate-period trades for the top 3 cells).

  **7. Trade log for the best cell**
  - Export `reports/best_cell_trades.csv`: every simulated trade for the #1 validate cell — market question, signal_time, entry_price, exit_price, exit_type, PnL, category.

  **8. Unresolved positions summary**
  - Count and total capital tied up in unresolved markets per cell.

  **9. Recommended next steps**
  - If validate returns are positive: suggest running paper mode with these parameters.
  - If negative or flat: suggest the strategy may not have edge; do not proceed to live.

**Done when:** `reports/backtest_report.md`, `reports/equity_curve_top3.csv`, and `reports/best_cell_trades.csv` all exist and are populated.

---

## Phase 5 — Paper trading (`paper.py`)
**Goal:** run the signal engine live against real-time trades, simulate fills with real order book data, measure alpha decay.

> **Start this as soon as the watchlist is approved (Phase 1 done).** It runs in parallel with Phases 2–4. The 3-day clock starts when this goes live.

### Tasks
- [x] **Polling loop:**
  - Every 20 seconds, call `get_trades(taker_only=True, limit=500)` (global feed, no user filter).
  - Filter locally: keep only trades where `wallet` is in the selected watchlist.
  - Dedupe against `paper_trades` table by tx_hash.
  - Feed new trades into `detect_signals()` using the parameters chosen from config (or the best backtest cell once Phase 4 is done — initially use reasonable defaults: N=3, W=6h, F=$500).
- [x] **On signal fire:**
  - Fetch `/book` for the signal's token ID.
  - Simulate filling $20 by walking the order book asks (sum ask levels until $20 is filled; volume-weighted average = simulated entry price).
  - Record: signal details, book_entry_price, midpoint at signal time, average price of the signal traders' fills, alpha_decay = (book_entry_price − avg_signal_trader_price).
  - Store in `paper_trades` table with `status = OPEN`.
- [x] **Position tracking:**
  - For copy_exits: poll signal wallets' trades every 5 min to detect their exits.
  - For hold_to_resolution: poll Gamma market metadata every hour to detect resolution.
  - On exit/resolution: compute PnL, update `paper_trades` row, set `status = CLOSED`.
- [x] **Daily summary** (print to stdout + append to `reports/paper_daily.md`):
  - Signals fired today, positions opened, positions closed.
  - Running PnL (closed positions only).
  - Average alpha decay observed.
  - Open position count and unrealized PnL estimate (based on current midpoint).
- [x] **Graceful shutdown:** Ctrl+C saves state cleanly; restart picks up without duplicating positions.
- [x] **Logging:** use Python `logging` module, INFO level to stdout, DEBUG level to `data/paper.log`.

**Done when:** the polling loop runs unattended, signals fire and get logged, daily summaries generate automatically.

---

## Phase 6 — Live execution (`live.py`) — STUB ONLY
**Do not build this until the owner explicitly says go, with both backtest and paper results in hand.**

### Tasks (for later)
- [x] Stub file with docstring explaining: Polymarket US API, KYC requirement, Ed25519 auth, market overlap verification needed.
- [x] Note: signal source = global Polymarket data API. Execution venue = Polymarket US. Must verify market availability on US venue before placing orders.
- [x] Note: position size = $20 initially. Hard cap in config, not adjustable without editing config.yaml.
- [x] Note: kill switch — if cumulative realized loss exceeds a configurable threshold (e.g., -$200), halt all new entries and alert.

**Done when:** `live.py` exists as a commented stub with the above notes. Nothing executable.

---

## Tonight's execution order

```
1. Phase 0  (~45 min)    Scaffold + smoke tests
2. Phase 1  (~30 min)    Discovery → watchlist preview → PAUSE for owner review
3. Phase 5  (~30 min)    Start paper trading (runs in background, 3-day clock starts)
4. Phase 2  (~runs overnight)  Kick off ingestion (resumable, unattended)
5. Phase 3  (tomorrow)   Backtest sweep after ingestion completes
6. Phase 4  (tomorrow)   Generate report, update paper mode params if needed
```

Paper trading starts BEFORE the backtest — they run in parallel.
The backtest report arrives during the paper window, not after it.
By day 3 you have: backtest results + 3 days of live paper data + alpha decay measurements.

---

## Decision gate (day 3–4)

Before going live, ALL of these must be true:
- [ ] At least one parameter set is profitable in the validate period of the backtest.
- [ ] That same parameter set shows positive or neutral paper PnL (or at minimum, signals are firing and alpha decay is manageable).
- [ ] Average alpha decay < 50% of average backtest PnL per trade (if decay eats most of the theoretical edge, the strategy doesn't work live).
- [ ] Polymarket US KYC is complete and API keys are generated.
- [ ] At least 5 of the paper-mode signal markets exist on Polymarket US.

Quantitative thresholds agreed with the owner 2026-07-03 (fixed BEFORE the paper
data arrived, so the numbers can't negotiate with us). Gate clock: restarted by
the owner at **2026-07-05 09:00 EDT** (gate review due 2026-07-08 09:00 EDT)
after the global-feed undersampling bug invalidated Jul 3–5 collection — paper
runs cohort B / N=5 / 12h / $1000 / hold / $50 with per-wallet polling:
- [ ] Sample floor: >= 15 paper signals with real fills (OPEN or CLOSED; SKIPPED
      and STALE don't count) by gate day.
- [ ] Win rate: >= 55% over closed positions if >= 10 have closed; with fewer
      closes (expected under hold_to_resolution), mark-to-market PnL across
      open positions must be neutral or positive instead.
- [ ] Alpha decay: mean paper alpha_decay small relative to the backtested edge
      (backtest avg ~ $16/trade at $50, i.e. ~20c/share edge; the 50%-of-edge
      rule above means mean decay must stay under ~10c, and under ~5c is the
      comfortable zone).

If any of these fail, do not proceed to live. Revisit the strategy or parameters first.

### Tracked checkpoints after the day-3 gate (added 2026-07-07, owner-directed)

Context: the day-3 gate is measured on World-Cup-inflated volume (~7–11
signals/day vs ~1/day at the May pre-WC baseline) and shouldn't be read as
representative of steady state. Power analysis:
`reports/proposals/persistence_power_and_strict45_analysis.md`.

- [ ] **~Jul 19 — WC volume cliff watch.** World Cup ends 2026-07-19; expect
      live signal volume to drop roughly 10× toward the May baseline.
- [ ] **Mid-to-late July (once volume settles, ~Jul 26–31) — steady-state
      performance read.** Fresh look at fills/day, win rate, decay, and PnL
      on post-WC flow only. Separate from (and NOT a rerun of) the day-3 gate.
- [ ] **Jul 21–28 — persistence early peek** (64–73% best-case power; a pass
      is valid, a non-pass defers to the main checkpoint).
- [ ] **Aug 5–11 — persistence main checkpoint** (pre-registered criteria in
      `reports/proposals/quality_weighted_cohort_proposal.md`, incl. the
      2026-07-07 amendment: an inconclusive result is an EXPECTED outcome
      under weak persistence, not a failure).
