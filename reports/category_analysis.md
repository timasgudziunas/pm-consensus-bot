# Category analysis — evidence review (2026-07-06)

> **v2 UPDATE (same day, evening): §8 onward re-examines everything on FULL
> uncapped trade history (3.63M additional trades, 250/250 wallets verified
> complete). Several v1 conclusions changed — most notably, the politics
> edge is weaker, event-driven, and not statistically established; and
> sports' missing early history turned out to be cohort youth, not a data
> artifact. Read §8–§13 as the current view; §1–§7 kept for the audit trail.**

Owner question: does the data support down-weighting SPORTS (cap or category
multiplier) in favor of categories whose traders "know something" (POLITICS,
TECH)? **No changes were made** — this document is evidence only.

Companion artifacts: `archive/category_backtest.md` (full two-half tables),
`archive/category_backtest.csv`, `archive/autonomous_log_2026-07-06.md`
(session log), `src/backtest_category.py` (methodology, rerunnable),
`src/category_stats.py` (per-category paper reporting, now wired into
check-ins and the daily summary).

## TL;DR

1. **The sports-illiquidity premise is wrong.** The 27/29 skipped sports
   signals were stale-feed artifacts (market already resolved, book gone), not
   thin books. Since the feed fix: 11/11 sports fills, every one at
   half-spread (+0.5c) for $50. At the live size floor (F=$1000), consensus
   signals mathematically cannot fire on thin markets (minimum signal-market
   lifetime volume observed: $876k).
2. **POLITICS is the only category whose profitability replicates across both
   backtest halves** (+0.119 PnL/$ in H1, +0.155 in H2 under hold;
   86%/73% win). This is the strongest evidence in the direction of the
   owner's hypothesis.
3. **SPORTS shows the LARGEST backtested edge, but only one half of data can
   see it** (+0.395 PnL/$, 70% win, n=76 — all H2). H1 sports data is
   structurally missing (see coverage caveat), so this neither replicates nor
   fails — it is unverifiable with current data.
4. **The data does NOT support cutting sports today.** It supports (a) keeping
   both, (b) fixing the measurement gaps listed below, and (c) revisiting
   after the World Cup ends and more politics signals accumulate live.

## 1. Live paper by category (since gate restart 2026-07-05 13:00 UTC)

| category | signals | filled | skipped | fill% | PnL $ | win% | mean decay |
|---|---|---|---|---|---|---|---|
| SPORTS | 11 | 11 | 0 | 100% | −14.74 | 45% | −9.9c |
| all others | 0 | 0 | 0 | – | – | – | – |

Every live signal so far is SPORTS (FIFA World Cup dailies). This is not
alarming for politics: the H2 backtest rate is ~0.5 politics signals/day, so
~0 in 1.1 days of gate window is expected. But it means the day-3 gate verdict
will effectively be a verdict on sports copying only.

## 2. The skip-rate question (owner asked: is 27/29 typical or a fluke?)

Neither — it was a **measurement artifact**, now fixed. All 28 SKIPPED rows:

- date-stamped 07-02/07-03, inside the invalid broken-feed window;
- on World Cup markets with $385k–$16.7M lifetime volume (not thin);
- `midpoint_at_signal = NULL` on every one → the CLOB returned *no book at
  all* (market resolved before the late signal arrived), which is a
  staleness symptom, not a depth symptom.

The `max_signal_age` guard added 07-05 records such signals as STALE instead
of attempting fills. Post-fix fill rate is 11/11 with +0.5c slippage each.
**Conclusion (well-supported): sports illiquidity is not a real constraint at
$50/position and F=$1000.**

## 3. Two-half backtest (cohort B, live cell N=5/W=12h/F=$1000, $50/pos)

Protocol: history 2026-01-01 → 2026-07-02 (ingest boundary), split at
2026-04-02. Patterns were stated from H1 only and mechanically re-tested on
H2 (nothing tuned on H2). Full tables in `archive/category_backtest.md`.

| half | exit | category | signals | closed | win% | PnL $ | PnL/$ |
|---|---|---|---|---|---|---|---|
| H1 | hold | POLITICS | 24 | 22 | 86% | +130.90 | +0.119 |
| H1 | hold | SPORTS | 1 | 1 | 100% | +14.52 | +0.290 |
| H2 | hold | SPORTS | 76 | 76 | 70% | +1500.81 | +0.395 |
| H2 | hold | POLITICS | 46 | 45 | 73% | +347.73 | +0.155 |
| H2 | hold | CRYPTO | 1 | 1 | 100% | +80.72 | +1.614 |

H1→H2 hypothesis verdicts (only categories with ≥15 closed in H1 qualify):

| hypothesis (from H1) | H2 verdict |
|---|---|
| POLITICS is profitable (PnL/$ +0.119) | **HOLDS** (+0.155) |

Sports could not generate an H1 hypothesis (n=1) — see caveat below.

**Exit strategies:** sports results are identical under both exits (daily
markets resolve before copy-exits trigger). For politics the preference
REVERSES between halves: H1 copy_exits +0.125 vs hold +0.119 (copy slightly
better); H2 copy_exits −0.020 vs hold +0.155 (hold much better). So "hold
beats copy for politics" is an H2-only observation, not a robust rule. The
live setting (hold) remains consistent with the original sweep's validate
results.

## 4. Liquidity: what we can and cannot know

**Historical order-book depth data does not exist.** The DB has hourly price
candles; Gamma's `liquidity` field is a present-day snapshot (avg ≈$36 on
closed markets — meaningless historically). Any backtested "would this have
filled" number would be invented, so none is reported. What we have instead:

- Live book evidence: 11/11 $50 fills at +0.5c (high-volume sports markets).
- Structural filter: at F=$1000 a signal needs 5 traders staking ≥$1000 each
  within 12h — observed minimum signal-market volume $876k, and 0 signals
  under the $500k volume flag.
- Sensitivity (volume proxy, full window, hold): illiquidity risk only enters
  at lower size floors. At F=$100: 23/369 signals under $1M volume,
  collectively −$170 PnL (they lose). At F=$250: 14 under $1M, −$29. At the
  live F=$1000: 2 under $1M, +$17.
  **If the size floor is ever lowered, a market-volume floor should be added
  with it** — that is where "thin market" losses actually live in the data.

## 5. Coverage caveats (read before acting on any of this)

- **/trades 4k-per-wallet cap skews history recent.** 61/250 cohort-B wallets
  are at the cap; the median wallet's data starts 2026-01-31. Only 20/62
  sports wallets have data reaching back to the H1/H2 boundary, vs 37/41
  politics. Consensus detection needs N=5 wallets *simultaneously visible*, so
  H1 sports signals are structurally suppressed. The H1 25-signal vs H2
  124-signal asymmetry is largely this artifact.
- **Seasonality:** H2 sports edge is dominated by FIFA World Cup consensus
  (June–July). Whether it generalizes to regular-season sports is untested.
- **Survivorship:** the watchlist was selected on performance over the same
  window the backtest replays (OVERVIEW.md caveat). H1/H2 discipline protects
  against pattern-mining, not against survivorship.
- Samples are small everywhere: politics 67 closed across both halves, sports
  77 closed in one half, everything else single digits. Live paper: 11 fills.

## 6. Verdict on the owner's question

| claim | verdict | basis |
|---|---|---|
| Sports has an illiquidity/skip problem | **Refuted** at current params | §2, §4 |
| Politics traders have a copyable edge | **Supported, replicates** (both halves, but small n and survivorship apply) | §3 |
| Sports edge is fake/whale-volume only | **Not supported** — biggest PnL contributor where visible (H2), 70% win | §3 |
| Lower sports cap / add category multiplier now | **Not supported by current evidence** | all |

Recommended sequencing instead of a cap change (all future work, not done):
1. Let the day-3 gate run its course — it is currently grading sports copying.
2. Fix the coverage gap before re-testing H1: re-ingest with time-windowed
   pagination if the API allows, or accept that only ~Apr→now is analyzable.
3. Accumulate ≥30 live politics fills before any category weighting decision
   (at backtest rates ≈ 2 months of paper).
4. If the size floor is ever lowered below $500, add a market-volume floor
   (see §4) — that is the actual liquidity lever, not a category cap.
5. Optional next analysis: cohort A vs B split by category to directly test
   the "whale PnL vs efficiency" framing on holdout data.

## 7. Bug found during this work (proposed fix, not applied)

`paper.py ensure_market()` returns a cached market row without backfilling
`category`, so paper trades on pre-ingested markets record `category=NULL`
(9 of 11 gate-window fills were affected until today's offline backfill).
One-line fix candidate (NOT applied — touches the live file): after the cache
hit, if `row["category"]` is NULL and `event_slug` resolves via
`event_categories`, update the row. Offline backfill applied today:
15,488 markets.category values filled from the existing event_categories
cache + 2 Gamma slug lookups; 0 uncategorized paper trades remain.

---

# v2 — full uncapped history (2026-07-06 evening)

Companion artifacts: `reports/deep_analysis.md` (all tables),
`reports/floor_sweep.csv`, `src/ingest_full.py` (deep pull),
`src/deep_analysis.py` (rerunnable methodology).

## 8. Data foundation — what the deep pull achieved

The /trades endpoint's hard 3000-offset cap (max ~4k trades/wallet) was
bypassed via an **undocumented `end` parameter** (verified live: filters
`timestamp < end`, composes with offset pagination over the taker-filtered
set). `ingest_full.py` walked every cohort-B wallet's history backwards to
2026-01-01 with per-wallet checkpoints.

- **250/250 wallets verified-full, 0 truncated, 0 failed.** 3.63M trades
  added (trades table now 4.5M rows). Walk correctness was spot-verified by
  refetching two wallets' complete API history and checking every eligible
  row against the DB (0 missing).
- History reaching the half boundary (Apr 2): 184/250 wallets. Reaching
  January: 141/250. **The rest are wallets that did not exist or did not
  trade earlier — real wallet age, not truncation.**
- Detection-relevant data in H1 grew ~4x (48k -> 195k qualifying BUYs).

**Trust statement**: coverage is now complete for every wallet's actual
lifetime. Remaining gaps are structural (young wallets), not fixable by more
pulling.

## 9. What changed vs v1

| v1 claim (§1–§7) | v2 status on full data |
|---|---|
| Sports H1 absence is a /trades-cap artifact | **WRONG — it's cohort youth.** Only 23/62 sports cohort-B wallets traded at all before Apr 2 (vs 39/41 politics). The sports cohort is dominated by wallets born in the World-Cup run-up. Single-period sports evidence is permanent, not a data gap. |
| Politics replicates: +0.119 H1 -> +0.155 H2 | **Still replicates in sign, much weaker in H1: +0.047 -> +0.135** (n=37/50, win 73%/72%). |
| Politics is the strongest "knows something" case | **Downgraded — see §10.** Edge is event-driven (Iran-crisis geopolitics), concentrated in mega-markets and partly in 3 wallets; bootstrap CI on PnL/$ includes zero. |
| Sports illiquidity refuted at current params | **Stands.** Volume floors barely bind at F>=$500 (see §11). |
| Hold beats copy_exits for politics (H2-only claim) | **Stands on full data**: copy_exits H2 politics -0.025 vs hold +0.135; H1 ~tied (+0.050 vs +0.047). |

## 10. Politics deep-dive (the dedicated section)

Full tables: deep_analysis.md §P3. Live cell, $50/position, hold unless noted.

**Headline**: politics remains profitable in both halves (+0.047 / +0.135
PnL/$; 72-73% win), but the composition undermines the "steady informed edge"
reading:

1. **It's a geopolitics/Iran story, not a politics story.** The
   Geopolitics + Iran-cluster tags contribute roughly the entire +$425:
   Geopolitics +$265, Iran +$147, Iran Ceasefire +$93, Trump-Zelenskyy +$87,
   Reza Pahlavi +$61. **US-domestic politics is NEGATIVE**: Trump-tag −$157,
   Texas Senate −$50, Gov Shutdown −$35. "Politics traders know something"
   is more precisely "watchlist consensus was profitable on war/crisis
   markets during a war/crisis period."
2. **Wallet concentration is material.** Top-3 wallets carry 64% of
   participation-attributed PnL. Re-detected without those 3 wallets,
   politics stays positive but thin: +0.033 PnL/$ (win rate holds at 75%).
   (Note: the mid-pull shakedown run showed the opposite — +0.122 without
   top-3 — the conclusion flips with exactly which signals exist, i.e. it is
   not robust either way at this sample size.)
3. **Timing**: the edge lives 1–30 days before resolution (+0.33 PnL/$).
   Same-day signals (−0.19) and >30d signals (−0.07) lose. Signals on
   markets with end<=signal or missing end dates also lose (−0.10).
4. **Volume dependence — politics is NOT size-independent**: top volume
   quartile (>$44M markets) carries the category (+0.411 PnL/$); the bottom
   quartile is negative (−0.109). Spearman(volume, PnL) = +0.132. Same
   direction as sports, stronger at the top end.
5. **Bootstrap (n=87)**: win-rate 95% CI 63%–82% (solidly above coin-flip);
   **PnL/$ CI −0.097 to +0.318 — includes zero.** High win rate with
   inconclusive PnL/$ means wins are frequent but losers are expensive. The
   dollar edge is NOT statistically established at this sample size.
6. **Walk-forward (6 windows)**: politics PnL/$ by month: −0.006, −0.116,
   +0.355, −0.134, +0.202, +0.264. **Negative in 3 of 6 windows**; the
   positive months coincide with major geopolitical event clusters
   (March; May–June Iran crisis).

## 11. Floor grid — the actionable map (P2)

Full grids in deep_analysis.md. Discipline: H1 and H2 evaluated separately;
a cell counts only if profitable in BOTH with >=15 closed each.

- **25/35 cells qualify. The load-bearing lever is the SIZE floor**: every
  cell with F>=$500 is profitable in both halves at every volume floor.
- **F<=$250 is where losses live**: H2 is negative at F=$100/$250 for all
  volume floors below $2M (e.g. F=$250/V=$0: −0.019 over 356 closed). The
  v1 finding (−$170 on 23 thin-market signals at F=$100) generalizes.
- **The volume floor is a monotone improver, mostly at low F**: at F=$100 it
  turns H2 from −0.010 (V=0) to +0.062 (V=$5M). At the live F=$1000 it
  barely binds until $5M, where PnL/$ jumps (+0.055->+0.119 H1,
  +0.222->+0.307 H2 going V=$1M->$5M) at acceptable n cost (33->30, 174->131).
- Live cell (F=$1000, V=0) on full data: **+0.030 H1 / +0.214 H2**.

No change is recommended or made here (owner constraint); the map is for the
post-gate discussion. If floors are ever revisited, the data say: never below
F=$500 without V>=$2M, and V=$5M is attractive even at F=$1000.

## 12. Sports and the other categories on full data

- Sports at the live cell: H1 n=3 (−0.180), H2 n=123 (+0.246). The pooled
  bootstrap CI (n=126) on PnL/$ is +0.018–+0.495 — **excludes zero**, the
  only category where it does. But the pool is 98% H2/World-Cup signals, so
  read it as "the WC period was really profitable," not "sports has a stable
  edge." Win-rate CI 60–75%.
- Cohort youth (§9) means sports' pre-WC behavior is unknowable for ~2/3 of
  its wallets. Post-WC live data is the only way to test persistence — the
  tournament ends mid-July; the weeks after are the natural experiment.
- CRYPTO/TECH/FINANCE/CULTURE: still ~zero signals at the live cell (1
  crypto signal total). The consensus mechanism at N=5/F=$1000 effectively
  only fires on sports and politics with this watchlist.

## 13. Verdict v2

| claim | verdict | change vs v1 |
|---|---|---|
| Sports illiquidity/skip problem | Refuted at current params | unchanged |
| Politics has a copyable, steady edge | **Not established** — positive both halves, but event-driven, size-dependent, partly wallet-concentrated, PnL/$ CI includes 0, negative in 3/6 monthly windows | downgraded |
| Sports edge is real | WC-period edge is statistically solid (CI excludes 0); persistence beyond WC untestable until post-WC live data | slightly upgraded, heavily caveated |
| Lower sports cap / add category multiplier now | **Still not supported** — now for a stronger reason: neither category's edge shape justifies a static weight; both are event/period-driven | unchanged conclusion, better evidence |
| Size/volume floor region | Mapped: F>=$500 robust everywhere; V>=$2M rescues low F; V=$5M attractive at live F | new |

**Sequencing recommendation (analysis only, nothing changed):**
1. Day-3 gate (07-08) proceeds as planned — it grades WC-sports copying.
2. The decisive politics test is live: at ~0.5 politics signals/day, ~2
   months of paper accumulates n≈30 live politics fills. The Iran cluster
   has partly resolved; if the "edge" was event-specific it will not
   reappear — that is exactly the information needed.
3. Post-WC weeks (mid-July onward) are the sports persistence test.
4. If the gate passes and floors are ever discussed: the grid says F>=$500
   is the safety boundary, V=$5M the quality lever — as a sweep-validated
   config change, not a category cap.
