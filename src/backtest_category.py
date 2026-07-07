"""Offline analysis: two-half category backtest (owner request, 2026-07-06).

Splits the ingested history into two equal time halves, runs the shared signal
detector at the live paper cell (cohort B, N/W/F from config paper.*) for both
exit strategies, and reports per-category performance for each half SEPARATELY:
hypotheses are stated from half 1 and mechanically re-tested on half 2.

Liquidity: true historical order-book depth does not exist (we only have hourly
price candles), so fills use the candle+slippage model from backtest.py, and
markets are flagged by lifetime volume (config analysis.volume_flags_usd) as an
explicit PROXY for possible illiquidity. Flagged-signal sensitivity is reported
alongside the headline numbers, never silently blended in.

Reads the DB read-only; writes reports/category_backtest.md and .csv only.
Run: python src/backtest_category.py
"""
import csv
import logging
import os
from collections import defaultdict
from datetime import datetime, timezone

import backtest as bt
import db
import signals as sig
from data_api import load_config

log = logging.getLogger(__name__)

REPORT_MD = os.path.join(db.REPO_ROOT, "reports", "category_backtest.md")
REPORT_CSV = os.path.join(db.REPO_ROOT, "reports", "category_backtest.csv")


def eval_cell(trades: list, params: dict, exit_strategy: str, markets: dict,
              prices: dict, trades_by_cond: dict, cfg: dict, size: int) -> list:
    """Detect signals on a trade slice and price them; returns per-signal rows."""
    rows = []
    for s in sig.detect_signals(trades, params):
        r = bt.evaluate_signal(s, exit_strategy, markets, prices, trades_by_cond, cfg)
        if r is None:
            continue
        m = markets.get(s["condition_id"], {})
        rows.append({
            "category": r["category"], "pnl": r["pnls"][size],
            "entry": r["entry_price"], "exit": r["exit_price"],
            "resolved": r["resolved"], "volume": m.get("volume"),
            "signal_time": s["signal_time"], "condition_id": s["condition_id"],
        })
    return rows


def agg(rows: list, size: int) -> dict:
    """Per-category aggregates over evaluated signal rows."""
    out: dict = {}
    by_cat: dict = defaultdict(list)
    for r in rows:
        by_cat[r["category"]].append(r)
    for cat, rs in by_cat.items():
        closed = [r for r in rs if r["pnl"] is not None]
        pnl = sum(r["pnl"] for r in closed)
        stake = size * len(closed)
        out[cat] = {
            "signals": len(rs), "closed": len(closed),
            "unresolved": len(rs) - len(closed),
            "win_rate": (sum(1 for r in closed if r["pnl"] > 0) / len(closed)) if closed else None,
            "total_pnl": pnl,
            "pnl_per_dollar": pnl / stake if stake else None,
            "avg_edge": (sum((r["exit"] - r["entry"]) for r in closed) / len(closed)) if closed else None,
        }
    return out


def flag_sensitivity(rows: list, size: int, thresholds: list) -> list:
    """PnL impact of dropping signals whose market volume is under each threshold."""
    out = []
    closed = [r for r in rows if r["pnl"] is not None]
    base = sum(r["pnl"] for r in closed)
    for th in thresholds:
        flagged = [r for r in closed if r["volume"] is not None and r["volume"] < th]
        out.append({"threshold": th, "flagged": len(flagged),
                    "flagged_pnl": sum(r["pnl"] for r in flagged),
                    "kept_pnl": base - sum(r["pnl"] for r in flagged)})
    return out


def fmt(v, spec: str, na: str = "-") -> str:
    return format(v, spec) if v is not None else na


def hypotheses_from(aggs: dict, min_closed: int) -> list:
    """Derive category-level statements from one half's aggregates.

    Each hypothesis is (id, text, test_fn) where test_fn(aggs)->bool|None
    re-evaluates the statement on another half (None = not enough data)."""
    hyps = []
    eligible = {c: a for c, a in aggs.items() if a["closed"] >= min_closed}
    for cat, a in sorted(eligible.items()):
        sign = a["pnl_per_dollar"] > 0
        hyps.append((
            f"{cat}-sign",
            f"{cat} is {'profitable' if sign else 'unprofitable'} "
            f"(PnL/$ {a['pnl_per_dollar']:+.3f})",
            lambda x, cat=cat, sign=sign: (
                None if cat not in x or x[cat]["closed"] < min_closed
                else (x[cat]["pnl_per_dollar"] > 0) == sign)))
    ranked = sorted(eligible, key=lambda c: -eligible[c]["pnl_per_dollar"])
    for hi, lo in zip(ranked, ranked[1:]):
        hyps.append((
            f"{hi}>{lo}",
            f"{hi} outperforms {lo} on PnL/$ "
            f"({eligible[hi]['pnl_per_dollar']:+.3f} vs {eligible[lo]['pnl_per_dollar']:+.3f})",
            lambda x, hi=hi, lo=lo: (
                None if hi not in x or lo not in x
                or x[hi]["closed"] < min_closed or x[lo]["closed"] < min_closed
                else x[hi]["pnl_per_dollar"] > x[lo]["pnl_per_dollar"])))
    return hyps


def main() -> None:
    """Run the two-half category backtest and write the report."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg = load_config()
    acfg = cfg["analysis"]
    pcfg = cfg["paper"]
    size = int(pcfg["position_size_usd"])
    params = {"n_traders": pcfg["default_n"],
              "window_seconds": int(pcfg["default_window_hours"] * 3600),
              "size_floor_usd": pcfg["default_size_floor"]}
    min_closed = acfg["min_closed_for_hypothesis"]

    conn = db.connect()
    trades, markets, prices = bt.load_data(conn)
    end_ts = int(datetime.fromisoformat(
        acfg["window_end_utc"].replace("Z", "+00:00")).timestamp())
    trades = [t for t in trades if t["timestamp"] < end_ts]
    wset = db.get_cohort_wallets(conn, pcfg["watchlist_cohort"])
    ctrades = [t for t in trades if t["wallet"] in wset]
    t_min, t_max = ctrades[0]["timestamp"], ctrades[-1]["timestamp"]
    mid = (t_min + t_max) // 2
    halves = {"H1": [t for t in ctrades if t["timestamp"] < mid],
              "H2": [t for t in ctrades if t["timestamp"] >= mid]}
    trades_by_cond: dict = defaultdict(list)
    for t in trades:
        trades_by_cond[t["condition_id"]].append(t)
    log.info("cohort %s: %d trades %s -> %s, half boundary %s",
             pcfg["watchlist_cohort"], len(ctrades),
             datetime.fromtimestamp(t_min, tz=timezone.utc).date(),
             datetime.fromtimestamp(t_max, tz=timezone.utc).date(),
             datetime.fromtimestamp(mid, tz=timezone.utc).date())

    # headline: paper cell, both exits, each half separately
    results: dict = {}   # (half, exit) -> {"rows": [...], "agg": {...}}
    for half, htr in halves.items():
        for ex in cfg["sweep"]["exit_strategy"]:
            rows = eval_cell(htr, params, ex, markets, prices, trades_by_cond, cfg, size)
            results[(half, ex)] = {"rows": rows, "agg": agg(rows, size)}
            log.info("%s %s: %d signals", half, ex, len(rows))

    # hypotheses from H1 (hold_to_resolution as primary), tested on H2
    h1 = results[("H1", "hold_to_resolution")]["agg"]
    h2 = results[("H2", "hold_to_resolution")]["agg"]
    hyps = hypotheses_from(h1, min_closed)

    # liquidity sensitivity: signal availability + volume floor per size floor
    # (full window — this is about availability, not performance holdout)
    sens = []
    for floor in acfg["sensitivity_size_floors"]:
        p = dict(params, size_floor_usd=floor)
        rows = eval_cell(ctrades, p, "hold_to_resolution", markets, prices,
                         trades_by_cond, cfg, size)
        vols = sorted(r["volume"] for r in rows if r["volume"] is not None)
        by_cat = defaultdict(int)
        for r in rows:
            by_cat[r["category"]] += 1
        sens.append({"floor": floor, "signals": len(rows),
                     "min_vol": vols[0] if vols else None,
                     "p10_vol": vols[int(0.1 * (len(vols) - 1))] if vols else None,
                     "flags": flag_sensitivity(rows, size, acfg["volume_flags_usd"]),
                     "by_cat": dict(by_cat)})

    write_report(cfg, params, size, mid, halves, results, hyps, h1, h2, sens)
    log.info("wrote %s and %s", REPORT_MD, REPORT_CSV)


def write_report(cfg, params, size, mid, halves, results, hyps, h1, h2, sens) -> None:
    """Render category_backtest.md / .csv from the computed results."""
    acfg = cfg["analysis"]
    min_closed = acfg["min_closed_for_hypothesis"]
    L = []
    L.append("# Two-half category backtest — generated "
             + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
    L.append("")
    L.append(f"Cohort {cfg['paper']['watchlist_cohort']}, live paper cell "
             f"(N={params['n_traders']}, W={params['window_seconds'] // 3600}h, "
             f"F=${params['size_floor_usd']}), ${size}/position, "
             f"history cut at {acfg['window_end_utc']} (ingest boundary), "
             f"half boundary {datetime.fromtimestamp(mid, tz=timezone.utc).date()}.")
    L.append("")
    L.append("**Liquidity caveat (explicit): historical order-book depth data does "
             "not exist** — the DB has hourly price candles only, and Gamma's "
             "`liquidity` field is a present-day snapshot (≈$36 avg on closed "
             "markets). Fills below use the candle+configured-slippage model from "
             "backtest.py. Lifetime market volume is used as a stated PROXY to "
             "flag possibly-thin markets; see sensitivity tables. The live-book "
             "evidence we do have (11 paper fills, all sports): $50 fills at half-"
             "spread (+0.5c) in every case.")
    L.append("")
    L.append("Survivorship bias caveat: the watchlist is traders who look good "
             "over the SAME window the backtest replays (see OVERVIEW.md); "
             "category comparisons inherit it. H1-vs-H2 agreement mitigates "
             "look-ahead in pattern selection, not survivorship.")
    for half in halves:
        L.append("")
        L.append(f"## {half} ({'first' if half == 'H1' else 'second'} half)")
        for ex in cfg["sweep"]["exit_strategy"]:
            a = results[(half, ex)]["agg"]
            L.append("")
            L.append(f"### {ex}")
            L.append("| category | signals | closed | unresolved | win% | PnL $ | PnL/$ | avg edge/share |")
            L.append("|---|---|---|---|---|---|---|---|")
            for cat in sorted(a, key=lambda c: -(a[c]["pnl_per_dollar"] or -9)):
                v = a[cat]
                L.append("| {} | {} | {} | {} | {} | {} | {} | {} |".format(
                    cat, v["signals"], v["closed"], v["unresolved"],
                    fmt(v["win_rate"], ".0%"), fmt(v["total_pnl"], "+.2f"),
                    fmt(v["pnl_per_dollar"], "+.3f"), fmt(v["avg_edge"], "+.3f")))
    L.append("")
    L.append("## Hypotheses from H1 (hold_to_resolution), tested on H2")
    L.append("")
    L.append(f"Stated only for categories with >= {min_closed} closed signals in "
             "the half being read. Verdicts are mechanical — nothing was tuned "
             "on H2.")
    L.append("")
    L.append("| # | hypothesis (from H1) | H2 verdict |")
    L.append("|---|---|---|")
    for i, (_hid, text, test) in enumerate(hyps, 1):
        v = test(h2)
        verdict = "insufficient H2 data" if v is None else ("HOLDS" if v else "FAILS")
        L.append(f"| {i} | {text} | {verdict} |")
    L.append("")
    L.append("## Liquidity / signal-availability sensitivity (full window, hold)")
    L.append("")
    L.append("How the signal set changes as the per-trader size floor drops — "
             "this is where illiquid markets would enter the pool.")
    L.append("")
    L.append("| size floor | signals | min market vol | p10 market vol | " +
             " | ".join(f"n < ${th // 1000}k (PnL$)" for th in acfg["volume_flags_usd"]) + " |")
    L.append("|---|---|---|---|" + "---|" * len(acfg["volume_flags_usd"]))
    for srow in sens:
        cells = " | ".join(f"{f['flagged']} ({f['flagged_pnl']:+.0f})" for f in srow["flags"])
        L.append(f"| ${srow['floor']} | {srow['signals']} | "
                 f"{fmt(srow['min_vol'], ',.0f')} | {fmt(srow['p10_vol'], ',.0f')} | {cells} |")
    L.append("")
    L.append("Per-floor category mix: " + "; ".join(
        f"F=${srow['floor']}: " + ", ".join(f"{c} {n}" for c, n in
                                            sorted(srow["by_cat"].items(), key=lambda kv: -kv[1]))
        for srow in sens))
    L.append("")
    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")

    with open(REPORT_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["half", "exit_strategy", "category", "signals", "closed",
                    "win_rate", "total_pnl", "pnl_per_dollar", "avg_edge"])
        for (half, ex), res in results.items():
            for cat, v in res["agg"].items():
                w.writerow([half, ex, cat, v["signals"], v["closed"],
                            v["win_rate"], round(v["total_pnl"], 2),
                            v["pnl_per_dollar"], v["avg_edge"]])


if __name__ == "__main__":
    main()
