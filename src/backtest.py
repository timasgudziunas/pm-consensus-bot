"""Phase 3: parameter sweep backtest.

Replays ingested watchlist trades through the shared signal detector
(signals.detect_signals — the same function paper.py uses live), prices
entries from historical CLOB candles, simulates both exit strategies, and
writes per-cell metrics to backtest_results for report.py.

Run: python src/backtest.py
"""
import itertools
import json
import logging
import time
from bisect import bisect_left
from collections import defaultdict
from datetime import datetime, timezone

import db
import signals as sig
from data_api import load_config

log = logging.getLogger(__name__)

SECONDS_PER_MONTH = 30.44 * 86400


def load_data(conn) -> tuple:
    """Load trades, markets, and price history into memory for the sweep."""
    trades = [dict(r) for r in conn.execute(
        """SELECT tx_hash, condition_id, wallet, side, outcome_index, size_usd, price, timestamp
           FROM trades WHERE outcome_index >= 0 ORDER BY timestamp""")]
    markets = {r["condition_id"]: dict(r) for r in conn.execute("SELECT * FROM markets")}
    prices: dict = {}
    for r in conn.execute("SELECT token_id, timestamp, price FROM price_history ORDER BY token_id, timestamp"):
        prices.setdefault(r["token_id"], ([], []))
        ts_list, p_list = prices[r["token_id"]]
        ts_list.append(r["timestamp"])
        p_list.append(r["price"])
    return trades, markets, prices


def price_at_or_after(prices: dict, token: str, ts: int, max_gap: int) -> float:
    """First price candle at/after ts (within max_gap seconds), else None."""
    if token not in prices:
        return None
    ts_list, p_list = prices[token]
    i = bisect_left(ts_list, ts)
    if i < len(ts_list) and ts_list[i] - ts <= max_gap:
        return p_list[i]
    return None


def resolution_payout(market: dict, outcome_index: int) -> float:
    """Resolved payout per share for an outcome, or None if not resolved."""
    if not market or not market.get("closed"):
        return None
    try:
        return float(json.loads(market["outcome_prices"])[outcome_index])
    except (TypeError, ValueError, IndexError):
        return None


def market_end_ts(market: dict) -> int:
    """Market end date as unix ts, or None."""
    try:
        return int(datetime.fromisoformat(market["end_date"].replace("Z", "+00:00")).timestamp())
    except (TypeError, ValueError, AttributeError):
        return None


def evaluate_signal(s: dict, exit_strategy: str, markets: dict, prices: dict,
                    trades_by_cond: dict, cfg: dict) -> dict:
    """Price one signal's entry and exit. Returns a result dict or None to skip.

    entry_price in the result is PRE-slippage; pnl_20/pnl_50 each apply their
    own configured entry haircut. Unresolved positions get pnl=None."""
    bcfg = cfg["backtest"]
    slip = cfg["slippage"]
    market = markets.get(s["condition_id"])
    if not market or not market.get("clob_token_ids"):
        return None
    try:
        tokens = json.loads(market["clob_token_ids"])
        token = tokens[s["outcome_index"]]
    except (ValueError, IndexError, TypeError):
        return None
    raw_entry = price_at_or_after(prices, token, s["signal_time"], bcfg["entry_price_max_gap_seconds"])
    if raw_entry is None or not (bcfg["entry_price_min"] <= raw_entry <= bcfg["entry_price_max"]):
        return None

    payout = resolution_payout(market, s["outcome_index"])
    end_ts = market_end_ts(market)

    exit_price, exit_time, exit_kind, resolved = None, None, None, 0
    if exit_strategy == "hold_to_resolution":
        if payout is not None:
            exit_price, exit_time, exit_kind, resolved = payout, end_ts, "resolution", 1
    else:  # copy_exits
        cond_trades = trades_by_cond.get(s["condition_id"], [])
        exit_ts = sig.compute_copy_exit(s, cond_trades, bcfg["copy_exit_wallet_fraction"],
                                        bcfg["copy_exit_sold_fraction"])
        resolved_first = (payout is not None and end_ts is not None
                          and (exit_ts is None or end_ts < exit_ts))
        if resolved_first:
            exit_price, exit_time, exit_kind, resolved = payout, end_ts, "resolution", 1
        elif exit_ts is not None:
            p = price_at_or_after(prices, token, exit_ts, bcfg["entry_price_max_gap_seconds"])
            if p is None and payout is not None:
                exit_price, exit_time, exit_kind, resolved = payout, end_ts, "resolution", 1
            elif p is not None:
                exit_price = max(0.0, p - slip["exit_cents"] / 100.0)
                exit_time, exit_kind, resolved = exit_ts, "copy_exits", 1
        elif payout is not None:
            exit_price, exit_time, exit_kind, resolved = payout, end_ts, "resolution", 1

    pnls = {}
    for size in cfg["sweep"]["position_size"]:
        entry = raw_entry + slip[f"entry_cents_{int(size)}"] / 100.0
        if exit_price is None or entry <= 0 or entry >= 1:
            pnls[size] = None
        else:
            pnls[size] = (exit_price - entry) * (size / entry)

    return {
        "entry_price": raw_entry, "exit_price": exit_price, "exit_time": exit_time,
        "exit_kind": exit_kind, "resolved": resolved, "pnls": pnls,
        "category": market.get("category") or "UNMAPPED",
    }


def cell_metrics(results: list, size: float) -> dict:
    """Aggregate metrics over evaluated signals for one position size."""
    entered = [r for r in results if r is not None]
    closed = [r for r in entered if r["pnls"][size] is not None]
    pnl_list = [r["pnls"][size] for r in closed]
    total = sum(pnl_list)
    wins = sum(1 for p in pnl_list if p > 0)
    capital = size * len(entered)
    # max drawdown over cumulative PnL in exit-time order
    peak, dd, cum = 0.0, 0.0, 0.0
    for r in sorted(closed, key=lambda r: r["exit_time"] or 0):
        cum += r["pnls"][size]
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    by_cat: dict = defaultdict(lambda: {"signals": 0, "wins": 0, "closed": 0, "total_pnl": 0.0})
    for r in entered:
        c = by_cat[r["category"]]
        c["signals"] += 1
        p = r["pnls"][size]
        if p is not None:
            c["closed"] += 1
            c["total_pnl"] += p
            c["wins"] += 1 if p > 0 else 0
    breakdown = {cat: {"signals": v["signals"],
                       "win_rate": v["wins"] / v["closed"] if v["closed"] else None,
                       "total_pnl": round(v["total_pnl"], 2)}
                 for cat, v in by_cat.items()}
    return {
        "signal_count": len(entered), "resolved_count": len(closed),
        "unresolved_count": len(entered) - len(closed),
        "win_rate": wins / len(closed) if closed else None,
        "avg_pnl": total / len(closed) if closed else None,
        "total_pnl": total,
        "return_on_capital": total / capital if capital else None,
        "max_drawdown": dd,
        "category_breakdown": json.dumps(breakdown),
    }


def main() -> None:
    """Run the full parameter sweep per wallet cohort for train/validate/full splits."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg = load_config()
    sweep = cfg["sweep"]
    conn = db.connect()
    trades, markets, prices = load_data(conn)
    if not trades:
        raise SystemExit("no trades in DB — run ingest.py first")

    # one calendar boundary from ALL trades so every cohort's split is comparable
    t_min = trades[0]["timestamp"]
    t_max = trades[-1]["timestamp"]
    boundary = int(t_min + cfg["backtest"]["train_months"] * SECONDS_PER_MONTH)
    log.info("%d trades %s -> %s; train/validate boundary %s", len(trades),
             datetime.fromtimestamp(t_min, tz=timezone.utc).date(),
             datetime.fromtimestamp(t_max, tz=timezone.utc).date(),
             datetime.fromtimestamp(boundary, tz=timezone.utc).date())

    # copy-exit evaluation only reads the signal wallets' own trades, so the
    # global by-condition index is correct for every cohort
    trades_by_cond: dict = defaultdict(list)
    for t in trades:
        trades_by_cond[t["condition_id"]].append(t)

    conn.execute("DELETE FROM signals")
    conn.execute("DELETE FROM backtest_results")
    conn.commit()

    combos = list(itertools.product(sweep["n_traders"], sweep["window_hours"], sweep["size_floor_usd"]))
    cohorts = sweep["cohorts"]
    n_cells = len(combos) * len(sweep["exit_strategy"]) * len(sweep["position_size"])
    log.info("sweeping %d combos x %d exits x %d sizes x 3 splits (%d cells) x %d cohorts",
             len(combos), len(sweep["exit_strategy"]), len(sweep["position_size"]),
             n_cells, len(cohorts))

    started = time.time()
    for cohort in cohorts:
        wset = db.get_cohort_wallets(conn, cohort)
        ctrades = [t for t in trades if t["wallet"] in wset]
        if not ctrades:
            log.warning("cohort %s: no wallets/trades — skipped", cohort)
            continue
        splits = {
            "train": [t for t in ctrades if t["timestamp"] < boundary],
            "validate": [t for t in ctrades if t["timestamp"] >= boundary],
            "full": ctrades,
        }
        log.info("cohort %s: %d wallets, %d trades (%d train / %d validate)",
                 cohort, len(wset), len(ctrades), len(splits["train"]), len(splits["validate"]))
        for ci, (n, wh, floor) in enumerate(combos, 1):
            params = {"n_traders": n, "window_seconds": int(wh * 3600), "size_floor_usd": floor}
            for split_name, split_trades in splits.items():
                detected = sig.detect_signals(split_trades, params)
                for exit_strategy in sweep["exit_strategy"]:
                    results = [evaluate_signal(s, exit_strategy, markets, prices, trades_by_cond, cfg)
                               for s in detected]
                    sig_rows = []
                    for s, r in zip(detected, results):
                        if r is None:
                            continue
                        sig_rows.append((
                            s["condition_id"], s["outcome_index"], "BUY", s["signal_time"],
                            n, json.dumps(s["wallets"]), r["entry_price"], r["exit_price"],
                            r["exit_time"], exit_strategy,
                            r["pnls"].get(20), r["pnls"].get(50), r["pnls"].get(100),
                            r["resolved"], r["category"], wh, floor, split_name, cohort))
                    conn.executemany(
                        """INSERT INTO signals (condition_id, outcome_index, side, signal_time,
                           n_traders, wallets, entry_price, exit_price, exit_time, exit_type,
                           pnl_20, pnl_50, pnl_100, resolved, category, window_hours, size_floor,
                           split, cohort)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", sig_rows)
                    for size in sweep["position_size"]:
                        m = cell_metrics(results, size)
                        conn.execute(
                            """INSERT OR REPLACE INTO backtest_results
                               (cohort, n_traders, window_hours, size_floor, exit_strategy,
                                position_size, split, signal_count, resolved_count, unresolved_count,
                                win_rate, avg_pnl, total_pnl, return_on_capital, max_drawdown,
                                category_breakdown)
                               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (cohort, n, wh, floor, exit_strategy, size, split_name,
                             m["signal_count"], m["resolved_count"], m["unresolved_count"],
                             m["win_rate"], m["avg_pnl"], m["total_pnl"],
                             m["return_on_capital"], m["max_drawdown"], m["category_breakdown"]))
                conn.commit()
            if ci % 20 == 0 or ci == len(combos):
                log.info("cohort %s: combo %d/%d (N=%d W=%gh F=$%d), %.0fs elapsed",
                         cohort, ci, len(combos), n, wh, floor, time.time() - started)

    log.info("sweep complete: %d cells across %d cohorts", n_cells * 3 * len(cohorts), len(cohorts))


if __name__ == "__main__":
    main()
