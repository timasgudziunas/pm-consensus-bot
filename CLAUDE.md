# CLAUDE.md — Project Rules & File Router

> Read automatically every session. Rules here apply everywhere, always.
> For current operational state, read `handoff.md` — it is authoritative.

## Project

Polymarket copy-trading bot. Tracks ~250 vetted top traders (cohort B),
detects consensus signals, copies positions. Backtest/paper phase — no live
trading code. **`src/paper.py` is running as a live process under a watchdog
(`pm-copybot-paper-watchdog` scheduled task). Do not move/rename src modules,
config.yaml, or report paths that code writes to without checking.**

## File router — read the right file, skip the rest

| You need | Read | Notes |
|---|---|---|
| Current state: live params, cohort, gate status, landmines | `handoff.md` | Authoritative; supersedes everything older |
| Design spec, API endpoints/params, strategy rationale | `OVERVIEW.md` | Timeless spec; trust live API over it |
| Gate criteria & clock | `PLAN.md` → "Decision gate" section only | Rest of PLAN.md is a completed checklist (its Phase-5 boxes describe the old global-feed design — since replaced) |
| Any tunable/threshold | `config.yaml` | Sole source of truth; `paper.gate` = live gate thresholds |
| Latest wallet-skill analysis | `reports/wallet_quality_analysis.md` | Condensed in handoff §0 |
| Latest category analysis | `reports/category_analysis.md` **§8+ only** + `reports/deep_analysis.md` | §1–7 are superseded v1, kept for audit |
| Paper-trading results | `reports/paper_checkins.md` (freshest) or `reports/paper_daily.md` (daily) | Both append-only, written by code |
| Open proposals (drafted, NOT applied) | `reports/proposals/` | |
| Chosen-parameter provenance | `reports/backtest_report.md` | ⚠ numbers rest on old capped data / 431-wallet cohort — see its banner |

**Do NOT read:**
- `archive/` — superseded/historical; in places it contradicts current state.
- `reports/*.csv` wholesale — generated data (up to 67KB). Grep the rows you
  need or regenerate via the script that owns the file.
- `.env` — secrets.

## Repo map

```
├── CLAUDE.md / OVERVIEW.md / PLAN.md / handoff.md   # see router above
├── config.yaml            # ALL tunables
├── archive/               # superseded docs/outputs — audit only
├── data/                  # SQLite DBs (gitignored)
├── reports/               # current analyses, paper logs, proposals/
└── src/
    # core pipeline (actively used):
    ├── data_api.py / gamma_api.py / clob_api.py   # API clients (throttled)
    ├── db.py               # SQLite schema + helpers
    ├── signals.py          # PURE shared signal detection (backtest + paper)
    ├── discover.py         # trader discovery/vetting (writes reports/watchlist_preview.txt)
    ├── ingest.py           # resumable trade ingestion
    ├── backtest.py         # parameter sweep engine
    ├── report.py           # writes reports/backtest_report.md + csvs
    ├── paper.py            # LIVE paper loop (running process)
    ├── paper_status.py     # gate check-ins → reports/paper_checkins.md
    ├── watchdog.py         # restarts paper.py (Windows scheduled task)
    ├── category_stats.py   # read-only per-category aggregation
    ├── live.py             # STUB ONLY — never implement
    # one-off analysis scripts (rerunnable):
    ├── smoke_test.py / ingest_full.py / backtest_category.py
    ├── deep_analysis.py    # writes reports/deep_analysis.md
    └── wallet_quality*.py  # 3 scripts → reports/wallet_quality_*.{md,csv}
```

## Non-negotiables

1. **No live execution code.** `live.py` is a stub with comments. Do not write
   order placement, wallet interaction, key management, or any code that moves
   real money. Ever. Until explicitly told otherwise.

2. **`signals.py` is shared.** Used identically by `backtest.py` and
   `paper.py`. Must be a pure function — no DB reads, no API calls, no side
   effects. Change signal logic in one place only.

3. **No magic numbers.** Every threshold, interval, parameter, and assumption
   lives in `config.yaml`. Code reads from config.

4. **Train/validate split is mandatory.** First 4 months train, last 2
   validate. Never report only in-sample results. Reports must state the
   survivorship-bias caveat from OVERVIEW.md.

5. **Dedupe everything.** Trades on `(tx_hash, condition_id, wallet)`; signals
   once per `(condition_id, outcome_index)` per direction; paper trades on
   tx_hash. Use `INSERT OR IGNORE` or check-before-insert.

6. **Resumable ingestion.** `ingest.py` safe to kill and restart. Track
   progress per wallet. Never re-fetch data already in the DB.

7. **API courtesy.** 0.15s min between requests. Exponential backoff on
   429/5xx (base 2s, max 3 retries). Cache everything in SQLite.

8. **Field names from reality, not docs.** On first contact with an endpoint,
   print raw response keys. If they differ from OVERVIEW.md, adjust the code,
   comment the discrepancy, trust the live API.

## Code conventions

- **Python 3.11+.** No async — plain `requests` + `time.sleep`.
- **Type hints** on all signatures; **docstrings** (one-liner fine) on public
  functions.
- **Logging** via `logging`: INFO→stdout, DEBUG→file. No bare `print()` except
  discovery shortlist and report generation.
- **No classes unless they earn it.** API clients may be classes; the signal
  detector must not be.
- **Errors:** try/except around API calls — log and continue on transient
  failures. Crash on schema errors or missing config keys (those are bugs).
- **No external services.** SQLite + Python + scheduled/manual runs only.
- **Git hygiene:** `data/`, `*.db`, `.env` gitignored. Never commit keys,
  wallets, or credentials.

## When in doubt

- OVERVIEW.md for API details; handoff.md for current state; PLAN.md gate
  section for what's pending.
- If an API behaves differently than documented, trust the API.
- If a design decision isn't covered here, ask — don't guess.
- About to write code that places orders or touches real money? Stop.
