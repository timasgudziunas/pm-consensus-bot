# archive/ — historical, superseded

Everything here is kept for audit only. It describes past state and in places
**contradicts current state** (old cohort sizes, old paper params, reversed
feed strategy). Do not read these for current facts — read `handoff.md`.

- `night-time-magic.md` — 2026-07-03 overnight work order (completed). States 113 wallets, N=5/24h/$500/$20 and "use global /trades feed" — **all reversed since**.
- `overnight_summary_2026-07-03.md` — cohort-expansion snapshot (431-wallet era; live cohort is now 250).
- `autonomous_log_2026-07-06.md` — chronology behind `reports/category_analysis.md`.
- `autonomous_log_2026-07-07.md` — chronology behind `reports/wallet_quality_analysis.md`.
- `category_backtest.md` / `.csv` — v1 category backtest on 4k-capped data; superseded by `reports/deep_analysis.md` + `reports/floor_sweep.csv`.
- `watchlist_preview.txt` — 431-wallet-era discovery output (126KB); regenerate with `src/discover.py` if needed.
- `paper_checkins.md` / `paper_daily.md` — the old overlapping paper logs (gate-window check-ins vs all-time daily appends; they reported different windows at different times and read as contradictory). Replaced 2026-07-07 by `reports/paper_dashboard.md`, regenerated from the DB by `src/paper_status.py`. Note: the first window's day 1–2 check-ins (all zeros) predate the 07-05 gate-clock restart.
