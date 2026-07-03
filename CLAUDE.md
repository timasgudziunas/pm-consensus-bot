# CLAUDE.md — Project Rules

> This file is read automatically by Claude Code on every task.
> OVERVIEW.md has the full spec. PLAN.md has the phased task list.
> This file has the rules that apply everywhere, always.

## Project

Polymarket copy-trading bot. Tracks ~100 top traders, detects consensus signals, and copies positions. Currently in backtest/paper phase — no live trading code yet.

## Repo structure

```
polymarket-copybot/
├── CLAUDE.md              # this file — universal rules
├── OVERVIEW.md            # full spec: APIs, schema, strategy logic
├── PLAN.md                # phased build plan with checkboxes
├── config.yaml            # ALL tunables: categories, sweep grid, thresholds, intervals
├── requirements.txt       # requests, pyyaml, tabulate — nothing else
├── data/                  # SQLite DB lives here (gitignored)
├── reports/               # backtest report, equity curves, paper daily logs
└── src/
    ├── data_api.py        # Data API client (leaderboard, trades, positions)
    ├── gamma_api.py       # Gamma API client (markets, events, resolution data)
    ├── clob_api.py        # CLOB API client (price history, order book)
    ├── db.py              # SQLite schema, helpers, upserts
    ├── discover.py        # Phase 1: trader discovery + vetting
    ├── ingest.py          # Phase 2: historical trade ingestion
    ├── signals.py         # shared signal detection (backtest + paper)
    ├── backtest.py        # Phase 3: parameter sweep engine
    ├── report.py          # Phase 4: generate backtest report
    ├── paper.py           # Phase 5: live paper trading loop
    └── live.py            # Phase 6: stub only, do not implement
```

## Non-negotiables

1. **No live execution code.** `live.py` is a stub with comments. Do not write order placement, wallet interaction, key management, or any code that moves real money. Ever. Until explicitly told otherwise.

2. **`signals.py` is shared.** The signal detection function is used identically by `backtest.py` and `paper.py`. It must be a pure function — no DB reads, no API calls, no side effects. Data in, signals out. If you need to change signal logic, change it in one place.

3. **No magic numbers.** Every threshold, interval, parameter, and assumption lives in `config.yaml`. Code reads from config. If you catch yourself typing a literal number that could change, put it in config instead.

4. **Train/validate split is mandatory.** The backtest must split data into first 4 months (train) and last 2 months (validate). Never report only in-sample results. The report must prominently state the survivorship bias caveat from OVERVIEW.md.

5. **Dedupe everything.** Trades dedupe on `(tx_hash, condition_id, wallet)`. Signals fire once per `(condition_id, outcome_index)` per direction. Paper trades dedupe on tx_hash. If you're inserting data, use `INSERT OR IGNORE` or check-before-insert.

6. **Resumable ingestion.** `ingest.py` must be safe to kill and restart. Track progress per wallet. Never re-fetch data that's already in the DB.

7. **API courtesy.** 0.15s minimum between requests (≈6 req/s). Exponential backoff on 429 and 5xx (base 2s, max 3 retries). Cache everything in SQLite — never fetch the same data twice.

8. **Field names from reality, not docs.** On first contact with each endpoint, print raw response keys. If casing or naming differs from OVERVIEW.md, adjust the code and leave a comment noting the discrepancy. Trust the live API over the spec.

## Code conventions

- **Python 3.11+.** No async — plain `requests` + `time.sleep` is fine for this project's throughput needs.
- **Type hints** on all function signatures. No runtime type checking needed, just annotations for readability.
- **Docstrings** on every public function. One-liner is fine. Describe what it does, not how.
- **Logging** via Python's `logging` module. INFO to stdout, DEBUG to file. No bare `print()` except in discovery's human-readable shortlist and report generation.
- **No classes unless they earn it.** Prefer simple functions and dicts/namedtuples. The API clients can be classes (they hold base_url and session state). The signal detector must not be.
- **Error handling:** API calls wrapped in try/except. Log and continue on transient failures. Crash on schema errors or missing config keys — those are bugs, not runtime issues.
- **No external services.** No Docker, no Redis, no Postgres, no message queues. SQLite + Python + cron/manual runs. Keep it simple enough to run on a laptop.
- **Git hygiene:** `data/` and `*.db` in `.gitignore`. Never commit API keys, wallets, or credentials (there shouldn't be any in this phase anyway).

## Config shape (`config.yaml`)

```yaml
categories:
  - POLITICS
  - SPORTS
  - CRYPTO
  # ... discover valid values in Phase 0

lookback_months: 6

discovery:
  min_markets: 20
  min_trades: 50
  max_pnl_concentration: 0.6  # top-2 markets < 60% of total PnL
  mm_roundtrip_threshold: 0.6  # >60% markets with same-day round trips = MM

sweep:
  n_traders: [2, 3, 4, 5]
  window_hours: [1, 6, 24]
  size_floor_usd: [250, 500, 1000]
  exit_strategy: [hold_to_resolution, copy_exits]
  position_size: [20, 50]

slippage:
  entry_cents_20: 1
  entry_cents_50: 2
  exit_cents: 1

paper:
  poll_interval_seconds: 20
  exit_poll_interval_seconds: 300
  default_n: 3
  default_window_hours: 6
  default_size_floor: 500

live:
  max_loss_usd: 200  # kill switch threshold — not used yet
```

## When in doubt

- Read OVERVIEW.md for API details and endpoint parameters.
- Read PLAN.md for what to build next and in what order.
- If an API behaves differently than documented, trust the API.
- If a design decision isn't covered here, ask — don't guess.
- If you're about to write code that places orders or touches real money, stop.
