"""Offline deep analysis on the uncapped trade history (owner request 2026-07-06).

Covers, in one load pass (all read-only, writes to reports/ only):
  P2  size-floor x market-volume-floor grid at the live cell params, with
      H1-derive / H2-validate discipline (grids reported separately, never blended)
  P3  politics deep-dive: sub-topics via event tags, wallet concentration,
      signal timing vs resolution, volume dependence, two-half re-test
  P4  bootstrap CIs on win rate and PnL/$ per category (seeded, reproducible)
  P5  rolling-window walk-forward at the live cell

Liquidity caveat carried over from category_backtest.py: historical order-book
depth does not exist; market lifetime volume is a stated proxy. Fills use the
candle+slippage model from backtest.py.

Memory: only cohort BUY trades >= the smallest grid floor are loaded for
detection (hold_to_resolution never needs sells; copy-exit sells are pulled
per signal market on demand for the politics dive).

Run: python src/deep_analysis.py
"""
import json
import logging
import os
import random
import sys
from collections import defaultdict
from datetime import datetime, timezone

import backtest as bt
import db
import signals as sig
from data_api import load_config

log = logging.getLogger("deep_analysis")

REPORT_MD = os.path.join(db.REPO_ROOT, "reports", "deep_analysis.md")
SWEEP_CSV = os.path.join(db.REPO_ROOT, "reports", "floor_sweep.csv")


# ---------- loading ----------

def load_inputs(conn, cfg: dict) -> dict:
    """Load detection BUYs, markets, prices, and coverage stats (read-only)."""
    acfg = cfg["analysis"]
    wset = db.get_cohort_wallets(conn, cfg["paper"]["watchlist_cohort"])
    end_ts = int(datetime.fromisoformat(
        acfg["window_end_utc"].replace("Z", "+00:00")).timestamp())
    min_floor = min(acfg["floor_sweep"]["size_floors"])
    ph = ",".join("?" * len(wset))
    buys = [dict(r) for r in conn.execute(
        f"""SELECT tx_hash, condition_id, wallet, side, outcome_index, size_usd, price, timestamp
            FROM trades WHERE side='BUY' AND size_usd >= ? AND outcome_index >= 0
            AND timestamp < ? AND wallet IN ({ph}) ORDER BY timestamp""",
        [min_floor, end_ts, *sorted(wset)])]
    markets = {r["condition_id"]: dict(r) for r in conn.execute("SELECT * FROM markets")}
    prices: dict = {}
    for r in conn.execute("SELECT token_id, timestamp, price FROM price_history ORDER BY token_id, timestamp"):
        prices.setdefault(r["token_id"], ([], []))
        prices[r["token_id"]][0].append(r["timestamp"])
        prices[r["token_id"]][1].append(r["price"])

    # coverage: how complete did the deep pull leave each wallet's history?
    hist_start = int(datetime.fromisoformat(
        acfg["full_pull"]["history_start_utc"].replace("Z", "+00:00")).timestamp())
    prog = {r["wallet"]: dict(r) for r in conn.execute("SELECT * FROM full_history_progress")}
    firsts = {r["wallet"]: r["ft"] for r in conn.execute(
        f"SELECT wallet, MIN(timestamp) ft FROM trades WHERE wallet IN ({ph}) GROUP BY wallet",
        sorted(wset))}
    full = partial = missing = 0
    for w in wset:
        p = prog.get(w)
        if p and p["done"] and not p["truncated"]:
            full += 1
        elif p and (p["pages_done"] or 0) > 0:
            partial += 1
        else:
            missing += 1
    coverage = {
        "wallets": len(wset), "full": full, "partial_or_truncated": partial,
        "no_progress": missing,
        "reach_boundary": sum(1 for w in wset
                              if firsts.get(w) is not None and firsts[w] <= (hist_start + end_ts) // 2),
        "reach_start": sum(1 for w in wset
                           if firsts.get(w) is not None and firsts[w] <= hist_start + 86400 * 14),
    }
    return {"buys": buys, "markets": markets, "prices": prices, "wset": wset,
            "end_ts": end_ts, "coverage": coverage}


def sells_for_conditions(conn, cond_ids: set, end_ts: int) -> dict:
    """All trades for the given markets (for copy-exit evaluation), batched."""
    out: dict = defaultdict(list)
    ids = sorted(cond_ids)
    for i in range(0, len(ids), 500):
        chunk = ids[i:i + 500]
        ph = ",".join("?" * len(chunk))
        for r in conn.execute(
                f"""SELECT tx_hash, condition_id, wallet, side, outcome_index, size_usd, price, timestamp
                    FROM trades WHERE condition_id IN ({ph}) AND timestamp < ?""",
                [*chunk, end_ts]):
            out[r["condition_id"]].append(dict(r))
    return out


# ---------- shared eval ----------

def eval_signals(detected: list, exit_strategy: str, inputs: dict,
                 trades_by_cond: dict, cfg: dict, size: int) -> list:
    """Price detected signals; returns per-signal rows with market metadata."""
    rows = []
    for s in detected:
        r = bt.evaluate_signal(s, exit_strategy, inputs["markets"], inputs["prices"],
                               trades_by_cond, cfg)
        if r is None:
            continue
        m = inputs["markets"].get(s["condition_id"], {})
        rows.append({
            "condition_id": s["condition_id"], "category": r["category"],
            "pnl": r["pnls"][size], "entry": r["entry_price"], "exit": r["exit_price"],
            "resolved": r["resolved"], "volume": m.get("volume"),
            "signal_time": s["signal_time"], "end_ts": bt.market_end_ts(m),
            "wallets": s["wallets"], "event_slug": m.get("event_slug"),
        })
    return rows


def metrics(rows: list, size: int) -> dict:
    """signals/closed/win/pnl/pnl_per_dollar over eval rows."""
    closed = [r for r in rows if r["pnl"] is not None]
    pnl = sum(r["pnl"] for r in closed)
    return {"signals": len(rows), "closed": len(closed),
            "win_rate": (sum(1 for r in closed if r["pnl"] > 0) / len(closed)) if closed else None,
            "total_pnl": pnl,
            "pnl_per_dollar": pnl / (size * len(closed)) if closed else None}


def fmt(v, spec, na="-"):
    return format(v, spec) if v is not None else na


# ---------- P2: floor grid ----------

def floor_grid(inputs: dict, cfg: dict, size: int) -> dict:
    """H1/H2 grids over (size_floor, volume_floor); detection reused per floor."""
    fs = cfg["analysis"]["floor_sweep"]
    pcfg = cfg["paper"]
    buys = inputs["buys"]
    t0, t1 = buys[0]["timestamp"], buys[-1]["timestamp"]
    mid = (t0 + t1) // 2
    halves = {"H1": [t for t in buys if t["timestamp"] < mid],
              "H2": [t for t in buys if t["timestamp"] >= mid]}
    grid: dict = {}
    for half, htr in halves.items():
        for F in fs["size_floors"]:
            params = {"n_traders": pcfg["default_n"],
                      "window_seconds": int(pcfg["default_window_hours"] * 3600),
                      "size_floor_usd": F}
            detected = sig.detect_signals(htr, params)
            rows = eval_signals(detected, "hold_to_resolution", inputs, {}, cfg, size)
            for V in fs["volume_floors"]:
                kept = [r for r in rows if (r["volume"] or 0) >= V]
                cell = metrics(kept, size)
                cell["by_cat"] = {c: metrics([r for r in kept if r["category"] == c], size)
                                  for c in {r["category"] for r in kept}}
                grid[(half, F, V)] = cell
        log.info("floor grid %s done (%d trades)", half, len(htr))
    return {"grid": grid, "mid": mid, "halves": {h: len(v) for h, v in halves.items()}}


# ---------- P3: politics deep-dive ----------

def politics_dive(inputs: dict, conn, cfg: dict, size: int) -> dict:
    """Sub-topics, wallet concentration, timing, volume dependence, halves."""
    pcfg = cfg["paper"]
    pol_cfg = cfg["analysis"]["politics"]
    params = {"n_traders": pcfg["default_n"],
              "window_seconds": int(pcfg["default_window_hours"] * 3600),
              "size_floor_usd": pcfg["default_size_floor"]}
    buys = inputs["buys"]
    t0, t1 = buys[0]["timestamp"], buys[-1]["timestamp"]
    mid = (t0 + t1) // 2

    detected = sig.detect_signals(buys, params)
    pol_conds = {s["condition_id"] for s in detected
                 if (inputs["markets"].get(s["condition_id"]) or {}).get("category") == "POLITICS"}
    trades_by_cond = sells_for_conditions(conn, pol_conds, inputs["end_ts"])
    out: dict = {}
    for ex in ("hold_to_resolution", "copy_exits"):
        rows = eval_signals(detected, ex, inputs, trades_by_cond, cfg, size)
        pol = [r for r in rows if r["category"] == "POLITICS"]
        out[ex] = {
            "all": metrics(pol, size),
            "H1": metrics([r for r in pol if r["signal_time"] < mid], size),
            "H2": metrics([r for r in pol if r["signal_time"] >= mid], size),
        }
        if ex == "hold_to_resolution":
            out["rows"] = pol

    pol = out["rows"]
    # sub-topics from event tags (label[1] = first tag more specific than the bucket)
    tag_of = {}
    slugs = {r["event_slug"] for r in pol if r["event_slug"]}
    for s in slugs:
        row = conn.execute("SELECT tags FROM event_categories WHERE slug = ?", (s,)).fetchone()
        try:
            labels = json.loads(row["tags"]) if row else []
        except (TypeError, ValueError):
            labels = []
        # skip the bucket tag itself and Gamma structural noise tags
        stop = ("politics", "parent for derivative", "games", "recurring")
        specific = [x for x in labels if x.lower() not in stop]
        tag_of[s] = specific[0] if specific else "untagged"
    by_topic = defaultdict(list)
    for r in pol:
        by_topic[tag_of.get(r["event_slug"], "untagged")].append(r)
    out["topics"] = {t: metrics(rs, size) for t, rs in by_topic.items()}

    # wallet concentration: participation-weighted PnL attribution
    wallet_pnl = defaultdict(float)
    wallet_n = defaultdict(int)
    for r in pol:
        if r["pnl"] is None:
            continue
        share = r["pnl"] / len(r["wallets"])
        for w in r["wallets"]:
            wallet_pnl[w] += share
            wallet_n[w] += 1
    ranked = sorted(wallet_pnl, key=lambda w: -wallet_pnl[w])
    total = sum(wallet_pnl.values())
    k = pol_cfg["concentration_top_k"]
    out["concentration"] = {
        "n_wallets": len(ranked),
        "top_k": [(w, wallet_pnl[w], wallet_n[w]) for w in ranked[:k]],
        "top_k_share": (sum(wallet_pnl[w] for w in ranked[:k]) / total) if total else None,
        "positive_wallets": sum(1 for w in ranked if wallet_pnl[w] > 0),
    }
    # robustness: re-detect with top-k wallets removed entirely
    excl = set(ranked[:k])
    detected2 = sig.detect_signals([t for t in buys if t["wallet"] not in excl], params)
    rows2 = eval_signals(detected2, "hold_to_resolution", inputs, {}, cfg, size)
    out["without_top_k"] = metrics([r for r in rows2 if r["category"] == "POLITICS"], size)

    # timing: days from signal to market end
    buckets = pol_cfg["timing_buckets_days"]
    labels = [f"{'0' if i == 0 else buckets[i - 1]}-{b}d" for i, b in enumerate(buckets)]
    labels += [f">{buckets[-1]}d", "end<=signal or missing"]
    def bucket(r):
        if not r["end_ts"] or r["end_ts"] <= r["signal_time"]:
            return labels[-1]
        d = (r["end_ts"] - r["signal_time"]) / 86400
        for i, b in enumerate(buckets):
            if d <= b:
                return labels[i]
        return labels[len(buckets)]
    by_time = defaultdict(list)
    for r in pol:
        by_time[bucket(r)].append(r)
    out["timing"] = [(b, metrics(by_time[b], size)) for b in labels if b in by_time]

    # volume dependence: quartiles + Spearman rank corr (pnl vs volume)
    withv = [r for r in pol if r["volume"] is not None and r["pnl"] is not None]
    withv.sort(key=lambda r: r["volume"])
    qs = []
    for qi in range(4):
        chunk = withv[qi * len(withv) // 4:(qi + 1) * len(withv) // 4]
        if chunk:
            qs.append({"vol_range": (chunk[0]["volume"], chunk[-1]["volume"]),
                       **metrics(chunk, size)})
    out["volume_quartiles"] = qs
    out["spearman"] = spearman([r["volume"] for r in withv], [r["pnl"] for r in withv])
    return out


def spearman(xs: list, ys: list):
    """Spearman rank correlation (average ranks for ties)."""
    n = len(xs)
    if n < 3:
        return None
    def ranks(vals):
        order = sorted(range(n), key=lambda i: vals[i])
        rk = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and vals[order[j + 1]] == vals[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for t in range(i, j + 1):
                rk[order[t]] = avg
            i = j + 1
        return rk
    rx, ry = ranks(xs), ranks(ys)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((rx[i] - mx) * (ry[i] - my) for i in range(n))
    den = (sum((r - mx) ** 2 for r in rx) * sum((r - my) ** 2 for r in ry)) ** 0.5
    return num / den if den else None


# ---------- P4: bootstrap ----------

def bootstrap_ci(pnls: list, size: int, bcfg: dict) -> dict:
    """Percentile bootstrap CIs for win rate and PnL/$ over per-signal PnLs."""
    n = len(pnls)
    if n < bcfg["min_n_report"]:
        return {"n": n, "too_thin": True}
    rng = random.Random(bcfg["seed"])
    wr, ppd = [], []
    for _ in range(bcfg["iterations"]):
        sample = [pnls[rng.randrange(n)] for _ in range(n)]
        wr.append(sum(1 for p in sample if p > 0) / n)
        ppd.append(sum(sample) / (size * n))
    wr.sort(), ppd.sort()
    lo, hi = int(0.025 * len(wr)), int(0.975 * len(wr)) - 1
    return {"n": n, "too_thin": False, "unstable": n < bcfg["min_n_stable"],
            "win_rate_ci": (wr[lo], wr[hi]), "pnl_per_dollar_ci": (ppd[lo], ppd[hi])}


# ---------- P5: walk-forward ----------

def walk_forward(inputs: dict, cfg: dict, size: int) -> list:
    """Per-category metrics over n contiguous windows at the live cell."""
    pcfg = cfg["paper"]
    nw = cfg["analysis"]["walk_forward"]["n_windows"]
    params = {"n_traders": pcfg["default_n"],
              "window_seconds": int(pcfg["default_window_hours"] * 3600),
              "size_floor_usd": pcfg["default_size_floor"]}
    buys = inputs["buys"]
    t0, t1 = buys[0]["timestamp"], buys[-1]["timestamp"] + 1
    step = (t1 - t0) // nw
    out = []
    for wi in range(nw):
        lo, hi = t0 + wi * step, t0 + (wi + 1) * step
        wtr = [t for t in buys if lo <= t["timestamp"] < hi]
        rows = eval_signals(sig.detect_signals(wtr, params), "hold_to_resolution",
                            inputs, {}, cfg, size)
        out.append({"window": wi + 1,
                    "start": datetime.fromtimestamp(lo, tz=timezone.utc).date().isoformat(),
                    "by_cat": {c: metrics([r for r in rows if r["category"] == c], size)
                               for c in {r["category"] for r in rows}},
                    "total": metrics(rows, size)})
    return out


# ---------- report ----------

def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cfg = load_config()
    size = int(cfg["paper"]["position_size_usd"])
    conn = db.connect()
    inputs = load_inputs(conn, cfg)
    log.info("loaded %d detection BUYs, coverage: %s", len(inputs["buys"]), inputs["coverage"])

    grid_res = floor_grid(inputs, cfg, size)
    log.info("P2 grid done")
    pol = politics_dive(inputs, conn, cfg, size)
    log.info("P3 politics dive done")

    # P4 bootstrap over live-cell full-window signals per category
    pcfg = cfg["paper"]
    params = {"n_traders": pcfg["default_n"],
              "window_seconds": int(pcfg["default_window_hours"] * 3600),
              "size_floor_usd": pcfg["default_size_floor"]}
    rows = eval_signals(sig.detect_signals(inputs["buys"], params),
                        "hold_to_resolution", inputs, {}, cfg, size)
    boot = {}
    for cat in sorted({r["category"] for r in rows}):
        pnls = [r["pnl"] for r in rows if r["category"] == cat and r["pnl"] is not None]
        boot[cat] = bootstrap_ci(pnls, size, cfg["analysis"]["bootstrap"])
    log.info("P4 bootstrap done")

    wf = walk_forward(inputs, cfg, size)
    log.info("P5 walk-forward done")

    write_report(cfg, size, inputs, grid_res, pol, boot, wf)
    log.info("wrote %s", REPORT_MD)


def write_report(cfg, size, inputs, grid_res, pol, boot, wf) -> None:
    acfg = cfg["analysis"]
    fs = acfg["floor_sweep"]
    cov = inputs["coverage"]
    grid = grid_res["grid"]
    L = [
        "# Deep analysis on uncapped history — generated "
        + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "",
        f"Live cell N={cfg['paper']['default_n']} W={cfg['paper']['default_window_hours']}h, "
        f"${size}/position, cohort {cfg['paper']['watchlist_cohort']}, "
        f"history to {acfg['window_end_utc']}, halves split at "
        f"{datetime.fromtimestamp(grid_res['mid'], tz=timezone.utc).date()}.", "",
        "## Data coverage after the deep pull (trust anchor for everything below)", "",
        f"- wallets: {cov['wallets']}; verified-full history: {cov['full']}; "
        f"partial/truncated: {cov['partial_or_truncated']}; no progress: {cov['no_progress']}",
        f"- history reaching the half boundary: {cov['reach_boundary']}/{cov['wallets']}",
        f"- history reaching the window start (±14d): {cov['reach_start']}/{cov['wallets']}",
        "",
        "Liquidity caveat: historical order-book depth does not exist; volume "
        "floors below use lifetime market volume as a stated proxy.",
        "", "## P2: size-floor x volume-floor grid (hold_to_resolution)", "",
        "PnL/$ per cell; H1 and H2 shown separately. A cell is only trustworthy "
        "if positive in BOTH halves.",
    ]
    for half in ("H1", "H2"):
        L += ["", f"### {half} (PnL/$ | closed n)", "",
              "| size floor \\ vol floor | " + " | ".join(f"${v//1000}k" if v else "$0"
                                                          for v in fs["volume_floors"]) + " |",
              "|---|" + "---|" * len(fs["volume_floors"])]
        for F in fs["size_floors"]:
            cells = []
            for V in fs["volume_floors"]:
                c = grid[(half, F, V)]
                cells.append(f"{fmt(c['pnl_per_dollar'], '+.3f')} ({c['closed']})")
            L.append(f"| ${F} | " + " | ".join(cells) + " |")
    all_cells = [(F, V) for F in fs["size_floors"] for V in fs["volume_floors"]]
    both = [c for c in all_cells
            if (grid[("H1", *c)]["pnl_per_dollar"] or -1) > 0
            and (grid[("H2", *c)]["pnl_per_dollar"] or -1) > 0
            and grid[("H1", *c)]["closed"] >= acfg["min_closed_for_hypothesis"]
            and grid[("H2", *c)]["closed"] >= acfg["min_closed_for_hypothesis"]]
    if len(both) == len(all_cells):
        L += ["", f"**Every cell** ({len(both)}/{len(all_cells)}) is profitable in both "
              f"halves with >= {acfg['min_closed_for_hypothesis']} closed each."]
    else:
        L += ["", f"Cells profitable in BOTH halves with >= {acfg['min_closed_for_hypothesis']} "
              f"closed each ({len(both)}/{len(all_cells)}): "
              + (", ".join(f"(F=${F}, V=${V // 1000}k)" for F, V in both) or "NONE")]
    # per-category slice of the live size-floor row across volume floors
    live_F = cfg["paper"]["default_size_floor"]
    L += ["", f"### Per-category at the live size floor (F=${live_F}), PnL/$ (closed n)", ""]
    cats = sorted({c for (h, F, V) in grid if F == live_F
                   for c in grid[(h, F, V)]["by_cat"]})
    L += ["| half | category | " + " | ".join(f"${v // 1000}k" if v else "$0"
                                              for v in fs["volume_floors"]) + " |",
          "|---|---|" + "---|" * len(fs["volume_floors"])]
    for half in ("H1", "H2"):
        for cat in cats:
            cells = []
            for V in fs["volume_floors"]:
                m = grid[(half, live_F, V)]["by_cat"].get(cat)
                cells.append(f"{fmt(m['pnl_per_dollar'], '+.3f')} ({m['closed']})" if m else "-")
            L.append(f"| {half} | {cat} | " + " | ".join(cells) + " |")

    L += ["", "## P3: politics deep-dive (hold unless noted)", ""]
    for ex in ("hold_to_resolution", "copy_exits"):
        for k in ("all", "H1", "H2"):
            m = pol[ex][k]
            L.append(f"- {ex} {k}: n={m['closed']}, win {fmt(m['win_rate'], '.0%')}, "
                     f"PnL {fmt(m['total_pnl'], '+.2f')}, PnL/$ {fmt(m['pnl_per_dollar'], '+.3f')}")
    L += ["", "### Sub-topics (first specific event tag)", "",
          "| topic | signals | closed | win% | PnL $ | PnL/$ |", "|---|---|---|---|---|---|"]
    for t, m in sorted(pol["topics"].items(), key=lambda kv: -(kv[1]["total_pnl"] or 0)):
        L.append(f"| {t} | {m['signals']} | {m['closed']} | {fmt(m['win_rate'], '.0%')} | "
                 f"{fmt(m['total_pnl'], '+.2f')} | {fmt(m['pnl_per_dollar'], '+.3f')} |")
    c = pol["concentration"]
    k = acfg["politics"]["concentration_top_k"]
    L += ["", "### Wallet concentration",
          f"- {c['n_wallets']} wallets ever in a politics signal; "
          f"{c['positive_wallets']} have positive attributed PnL",
          f"- top-{k} wallets' share of attributed PnL: {fmt(c['top_k_share'], '.0%')}"]
    for w, p, n in c["top_k"]:
        L.append(f"  - {w[:10]}…: ${p:+.2f} over {n} signals")
    m = pol["without_top_k"]
    L += [f"- politics WITHOUT top-{k} wallets (re-detected): n={m['closed']}, "
          f"win {fmt(m['win_rate'], '.0%')}, PnL/$ {fmt(m['pnl_per_dollar'], '+.3f')}",
          "", "### Timing (signal -> resolution)", "",
          "| bucket | signals | closed | win% | PnL/$ |", "|---|---|---|---|---|"]
    for b, m in pol["timing"]:
        L.append(f"| {b} | {m['signals']} | {m['closed']} | {fmt(m['win_rate'], '.0%')} | "
                 f"{fmt(m['pnl_per_dollar'], '+.3f')} |")
    L += ["", "### Volume dependence", "",
          "| vol quartile | range | closed | win% | PnL/$ |", "|---|---|---|---|---|"]
    for i, q in enumerate(pol["volume_quartiles"], 1):
        L.append(f"| Q{i} | {q['vol_range'][0]:,.0f}–{q['vol_range'][1]:,.0f} | {q['closed']} | "
                 f"{fmt(q['win_rate'], '.0%')} | {fmt(q['pnl_per_dollar'], '+.3f')} |")
    L.append(f"\nSpearman rank corr (volume vs signal PnL): {fmt(pol['spearman'], '+.3f')}")

    bcfg = acfg["bootstrap"]
    L += ["", f"## P4: bootstrap 95% CIs ({bcfg['iterations']} iters, seed {bcfg['seed']})", "",
          "| category | n | win-rate CI | PnL/$ CI | flag |", "|---|---|---|---|---|"]
    for cat, b in sorted(boot.items()):
        if b["too_thin"]:
            L.append(f"| {cat} | {b['n']} | – | – | TOO THIN (n < {bcfg['min_n_report']}) |")
        else:
            flag = f"UNSTABLE (n < {bcfg['min_n_stable']})" if b["unstable"] else ""
            L.append(f"| {cat} | {b['n']} | {b['win_rate_ci'][0]:.0%}–{b['win_rate_ci'][1]:.0%} | "
                     f"{b['pnl_per_dollar_ci'][0]:+.3f}–{b['pnl_per_dollar_ci'][1]:+.3f} | {flag} |")

    L += ["", f"## P5: walk-forward ({acfg['walk_forward']['n_windows']} windows, live cell)", "",
          "| window | start | total closed | total PnL/$ | POLITICS PnL/$ (n) | SPORTS PnL/$ (n) |",
          "|---|---|---|---|---|---|"]
    for w in wf:
        p = w["by_cat"].get("POLITICS", {})
        s = w["by_cat"].get("SPORTS", {})
        L.append(f"| {w['window']} | {w['start']} | {w['total']['closed']} | "
                 f"{fmt(w['total']['pnl_per_dollar'], '+.3f')} | "
                 f"{fmt(p.get('pnl_per_dollar'), '+.3f')} ({p.get('closed', 0)}) | "
                 f"{fmt(s.get('pnl_per_dollar'), '+.3f')} ({s.get('closed', 0)}) |")
    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")

    import csv
    with open(SWEEP_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["half", "size_floor", "volume_floor", "signals", "closed",
                    "win_rate", "total_pnl", "pnl_per_dollar"])
        for (half, F, V), c in sorted(grid.items()):
            w.writerow([half, F, V, c["signals"], c["closed"], c["win_rate"],
                        round(c["total_pnl"], 2), c["pnl_per_dollar"]])


if __name__ == "__main__":
    main()
