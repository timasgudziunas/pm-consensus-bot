# Proposal: liquidity-aware vetting metric for discovery (NOT applied)

Status: draft for owner review, 2026-07-06. No code below has been applied.

## Why "fill-rate" itself is the wrong vetting metric today

The 2026-07-06 analysis (`reports/category_analysis.md` §2) showed the
observed 27/29 skip rate was a stale-feed artifact, not illiquidity: since the
feed fix, live fill rate is 11/11 at half-spread. A per-wallet fill-rate
computed from today's paper data would be ~100% for everyone (no signal), and
it only accumulates for wallets that already co-fire signals — useless at
discovery time for a candidate wallet we've never traded on.

What the data DOES show (category_backtest.md, sensitivity table): when the
size floor drops below ~$500, signals start landing in sub-$1M-volume markets
and those signals collectively lose money (−$170 over 23 signals at F=$100).
The copyability risk lives in *market volume*, and it is measurable at
discovery time from the candidate's own trade sample.

## Proposed metric: `thin_market_share`

Stake-weighted fraction of a candidate's sampled BUY volume placed in markets
whose lifetime volume is below `discovery.thin_market_volume_usd`. Computed
during vetting from data discovery already fetches (trade sample + the market
rows cached by `fetch_resolutions`). Stored on `wallets`, shown in the
shortlist, **not used for selection** until we've watched it against live
outcomes (same "report first, gate later" pattern as the gate metrics).

A live-telemetry counterpart (per-wallet fills vs skips credited to each
signal wallet) is deliberately deferred: post-fix skips are near zero, so
there is nothing to count yet.

## Diff (for review, not applied)

### config.yaml

```diff
 discovery:
   ...
   cohort_size: 250              # top-K selected per cohort before union caps
   cohort_c_min_resolved_buys: 10  # fewer resolved buys than this -> edge metric too noisy, excluded from C
+  # liquidity exposure metric (report-only: printed + stored, NOT a filter).
+  # Stake-weighted share of a candidate's BUY volume in markets whose
+  # lifetime volume is under this — sub-$1M signal markets lost money in the
+  # 2026-07-06 sensitivity analysis (archive/category_backtest.md)
+  thin_market_volume_usd: 1000000
```

### src/db.py — schema migration + upsert

```diff
 def _migrate(conn: sqlite3.Connection) -> None:
     ...
+    _add_column_if_missing(conn, "wallets", "thin_market_share", "REAL")
```

(plus `thin_market_share` added to the `upsert_wallet` column list — mirrors
how `entry_edge` was added.)

### src/discover.py — compute during vetting

```diff
+def thin_market_share(positions: dict, market_volumes: dict, threshold: float) -> Optional[float]:
+    """Stake-weighted share of sampled BUY volume in markets with lifetime
+    volume under threshold. None if no sampled market has a known volume."""
+    thin = total = 0.0
+    for (cond, _idx), p in positions.items():
+        vol = market_volumes.get(cond)
+        if vol is None:
+            continue
+        stake = sum(usd for _price, usd in p["buys"])
+        total += stake
+        if vol < threshold:
+            thin += stake
+    return (thin / total) if total > 0 else None
```

Wired in `main()` next to the existing `entry_edge` call (the market rows are
already in the DB at that point via `fetch_resolutions`):

```diff
         r["entry_edge"], r["resolved_buys"] = entry_edge(pos, payouts)
+        r["thin_market_share"] = thin_market_share(
+            pos, market_volumes, dcfg["thin_market_volume_usd"])
```

with `market_volumes` loaded once:

```diff
+    market_volumes = {row["condition_id"]: row["volume"]
+                      for row in conn.execute("SELECT condition_id, volume FROM markets")}
```

and one extra column in the shortlist print + wallet upsert dict.

## Known limitations (state up front in any review)

- `markets.volume` is lifetime volume as of fetch time — for a market still
  open when vetted, it undercounts final volume (biases toward "thin"). Most
  vetting-sample markets are resolved, so the bias is small but real.
- Volume is a proxy for depth. The only ground truth we have is live books,
  which say $50 fills at half-spread in >$2M-volume markets; we have NO fill
  evidence in sub-$500k markets (no live signal has occurred there).
- If this ever becomes a selection filter, it must be added to the sweep as a
  parameter first (per CLAUDE.md rule 4: never act on in-sample-only evidence).

## Suggested rollout

1. Apply diff, re-run discovery in report-only mode, eyeball the shortlist
   column (expect sports dailies traders to score higher thin-share).
2. Correlate stored `thin_market_share` against live per-signal fill/slippage
   telemetry once enough non-World-Cup signals accumulate.
3. Only then decide whether it becomes a vetting filter or a sweep parameter.
