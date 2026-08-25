# handoff.md — Session Handoff (updated 2026-08-17 ~15:10 UTC, supersedes all 2026-07-18 and earlier versions)

> For a fresh Claude session with no memory of prior conversations. Read this,
> then CLAUDE.md for standing rules. The 2026-08-17 session (owner-directed,
> background) ran the two agreed diagnostics — the overdue pre-registered
> persistence checkpoint and the copy-gap decomposition — and their verdicts
> below are SETTLED. Do not re-run or re-litigate them; the open items are the
> owner decisions in §3.

## 1. Current state (as of 2026-08-17 ~15:10 UTC)

- **Paper trading is LIVE**: cohort B (250 wallets), N=5 W=12h F=$1000 hold,
  $50/position — signal params untouched since gate start (2026-07-05).
  Dashboard as of 2026-08-17 13:55 UTC (day 43): **67 closed, 55% win rate,
  net −$288.79**, mean decay +4.21¢/share, only **8 closes in the last 30
  days** (~0.25 fills/day post-WC — the volume cliff is the standing regime,
  not a blip). Always-current numbers: `reports/paper_dashboard.md`
  (regenerated daily 09:05 local by task **pm-copybot-dashboard-daily**).
- Paper PID **11176** (`data/logs/paper.pid`), alive, restarted once by the
  watchdog on 2026-08-06 16:52 UTC (self-recovered; no data anomaly traced to
  it). Watchdog task **pm-copybot-paper-watchdog** — disable it first if
  stopping paper.py on purpose. Both tasks run S4U (survive sleep/logoff/
  battery) since the 2026-07-18 fix; if either is ever recreated, reapply the
  fix (CLAUDE.md standing rule 2).
- **The formal gate is misaligned and pending rewrite (§3.2)**: 55% win rate
  "passes" while the book is net −$289, because the gate never tested net
  expectancy. Treat the gate table in the dashboard as legacy until rewritten.
- **Owner position (2026-08-17): paper data is at diminishing returns.** The
  question is no longer "keep collecting" but the fork in §3.1.
- Nothing from the 2026-08-17 session is committed (owner reviews first).
  Uncommitted: modified CLAUDE.md/OVERVIEW.md/PLAN.md/README.md/config.yaml,
  new `src/copy_gap_analysis.py` + `src/persistence_checkpoint.py`, new
  reports (§4), extended `src/wallet_quality_fetch.py`, this handoff.
- API keys in gitignored `.env` — never read/print/log/commit. `live.py`
  stays a stub; no order/wallet/key code without direct owner authorization.

## 2. Settled verdicts from 2026-08-17 (standing results — do not re-derive)

### 2a. Persistence main checkpoint: **INCONCLUSIVE**

Pre-registered Aug 5–11 checkpoint, run 2026-08-17 (overdue). Full report:
`reports/persistence_checkpoint.md`; engine `src/persistence_checkpoint.py`
(reuses wallet_quality.py machinery), config `analysis.persistence_checkpoint`.

- (a) Spearman(past edge, forward edge) = +0.136, p=0.0345 → met
- (b) top-vs-bottom quintile forward gap = +0.070/$ → met
- (c) per-share variant p=0.068 → **not met** (needs <0.05) → all-three fails
- n=179 wallets, median forward k=63 — **below the design target (n≈222,
  k≈91)**, so the test ran below designed power.
- Per the pre-registered amendment, "cannot distinguish from noise" is the
  EXPECTED outcome under weak persistence: **keeps status quo, justifies
  neither a quality tilt nor a cohort cut.** No metric-shopping, no reruns
  with different criteria. Two of three criteria met + the min_forward=20
  sensitivity (rho=+0.18, p=0.009) suggest persistence is plausibly real but
  weak — exactly the regime the power model said n≈250 cannot resolve
  (detecting it properly needs ~750–1,000 wallets).

### 2b. Copy-gap decomposition: **selection kills the premise**

Why did copying lose −$289 while the copied wallets' SPORTS entry edge is
+0.072/$? Full report: `reports/copy_gap_analysis.md` (+ per-fill
`copy_gap_fills.csv`); script `src/copy_gap_analysis.py`, config
`analysis.copy_gap`. SPORTS n=59, stake-weighted ¢/share:

- wallet counterfactual **−2.85** (the copied trades lose even at the
  wallets' own prices, before any copying cost) − decay **+3.15** − spread
  **+0.39** = our edge **−6.39** ¢/share. Bootstrap CI [−18.5, +5.8].
- Cross-check on the exact signal-forming trades (604 taker buys, 0 missing):
  **−0.157 PnL/$** vs the wallets' overall +0.072 — consensus fires
  precisely on the wallets' losing trades (adverse selection), it does not
  sample their average trade.
- Favorite anatomy: the 0.8–1.0 bucket won 73% vs 88% breakeven (−$95); the
  0.4–0.6 bucket lost most in total (−$130). Exit policy is a non-factor
  (0/67 fills ever showed a visible copy-exit trigger; taker-only caveat).
- **Strategic read: this cuts against plain cohort expansion** — more wallets
  feeding the same consensus mechanism means more adversely-selected signals,
  not better ones. Expansion is only defensible as a persistence-power play
  combined with a fix to the selection mechanism itself.

## 3. Next steps — owner decisions, in priority order

1. **The fork (owner call, do not let it drop):** cohort expansion to
   ~750–1,000 wallets (fixes signal volume AND persistence detectability;
   weeks of work; see §2b for why expansion alone is suspect) **vs** accepting
   the bot as event-season-only (WC/elections/crises), optionally with the
   F=$500 floor change (both-halves backtest support, `reports/floor_sweep.csv`).
   Both 2026-08-17 results are inputs to this call and are already digested in
   §2. Also stored in session memory (`pm-copybot-pending-decisions`).
2. **Rewrite the paper gate around net expectancy per fill** instead of win
   rate (config `paper.gate` + PLAN.md gate section). Current gate passes a
   losing book.
3. Owner review + commit of the 2026-08-17 work (§1 lists the files).
4. PLAN.md tracked checkpoints are all ticked/annotated as of 2026-08-17 —
   nothing scheduled remains on the analysis calendar.

## 4. Where everything lives (2026-08-17 outputs)

| path | what it is |
|---|---|
| `reports/persistence_checkpoint.md` | Checkpoint verdict + criteria table (read exec summary first) |
| `reports/persistence_checkpoint_wallets.csv` | Per-wallet past/forward edges behind it |
| `src/persistence_checkpoint.py` | Rerunnable engine (scratch DB `data/pc_positions.sqlite`, gitignored) |
| `reports/copy_gap_analysis.md` | Copy-gap decomposition (read exec summary first) |
| `reports/copy_gap_fills.csv` | Per-fill components incl. copy-exit detail |
| `src/copy_gap_analysis.py` | Rerunnable copy-gap script |
| `src/wallet_quality_fetch.py` | Extended: MISSING+REFRESH queue through window_end 2026-08-17; fetched 76,627 (98.8%), misses file `data/wq_fetch_misses.json` |
| `config.yaml` | Additive `analysis.copy_gap` + `analysis.persistence_checkpoint` blocks (nothing live reads them) |
| `reports/proposals/quality_weighted_cohort_proposal.md` | Pre-registration the checkpoint graded against |
| `reports/proposals/persistence_power_and_strict45_analysis.md` | Power model the achieved n/k is compared to |

Older analyses (category v2, floor grid, wallet-quality census) are settled
and condensed in their own reports — router in CLAUDE.md. Politics live test
is effectively dead at observed volume (2 politics fills in 43 days; the
planned n≈30-by-September will not materialize at ~0.25 fills/day overall).

## 5. Data gaps & caveats (carry with any number above)

- **Taker-only trades feed** (median cohort wallet ~84% maker): copyable-edge
  metrics are immune by construction; cash-flow PnL and exit counterfactuals
  are bounded estimates only.
- **Survivorship bias** on all cohort edges (selected on the June
  leaderboard); June-initiated positions excluded from the persistence test
  for exactly this reason.
- **Jul 16–17 outage** recovered only ~half that day's trades — forward
  positions first-bought 2026-07-16 may be missing (coverage gap, not signal).
- Forward-window sports through ~Jul 19 is WC-inflated; slow categories are
  under-represented in resolved forward positions.
- No historical order-book depth exists anywhere; lifetime volume is a
  labeled proxy.

## 6. Operational landmines (permanent — never drop entries)

1. Never use the global `/trades` feed for collection — drops ~95% of
   watchlist trades when busy. Per-wallet rotating poll only.
2. `/trades` is TAKER-ONLY by default and ALL ingested history is taker-only.
   Never treat the trades table as a wallet's full activity.
3. Late-detected signals (>30 min) are recorded STALE, never entered.
4. `paper_trades.pnl_20` is realized PnL regardless of stake (legacy name);
   `position_usd` is the stake at open — never reprice.
5. Windows liveness checks: use `tasklist`, NOT `os.kill(pid, 0)` (it kills).
6. Reconfigure stdout to UTF-8 in any new CLI entry point (emoji usernames).
7. Transient ConnectionResetError/DNS warnings in paper logs self-recover.
8. Recreated scheduled tasks revert to Interactive-only + battery-restricted
   — reapply the S4U fix from an elevated PowerShell (CLAUDE.md rule 2).
9. Analysis scripts against the live DB use read-only connections
   (`file:...?mode=ro`); the sole write exception is batched markets-table
   upserts (wallet_quality_fetch.py pattern).

## Quick health check

```powershell
python src\paper_status.py
Get-Content data\logs\watchdog.log -Tail 3
python -c "import sqlite3,time; c=sqlite3.connect('data/copybot.db'); print('trades last hour:', c.execute('SELECT COUNT(*) FROM trades WHERE ingested_at >= ?', (int(time.time())-3600,)).fetchone()[0])"
```
Healthy ≈ paper PID (data\logs\paper.pid) alive, no new watchdog restarts,
hundreds+ trades/hour.
