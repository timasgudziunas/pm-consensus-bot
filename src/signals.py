"""Shared signal detection — used identically by backtest.py and paper.py.

Everything in this module is PURE: data in, results out. No DB reads, no API
calls, no side effects. If signal logic needs to change, change it here only.
"""
import math
from collections import defaultdict
from typing import Optional


def detect_signals(trades: list, params: dict) -> list:
    """Detect consensus signals in a list of trade dicts.

    trades: dicts with keys wallet, condition_id, outcome_index, side,
            size_usd, price, timestamp (any order; sorted internally).
    params: {"n_traders": int, "window_seconds": int, "size_floor_usd": float}

    A signal fires at the timestamp of the Nth DISTINCT wallet to BUY the same
    (condition_id, outcome_index) with a trade >= size_floor_usd within the
    window. One signal max per (condition_id, outcome_index) — never re-fires.

    Returns signal dicts: {condition_id, outcome_index, side, signal_time,
    n_traders, wallets (contributing, in firing order), avg_trader_price
    (size-weighted across contributing trades), trades (the contributing
    trade dicts)}.
    """
    n_traders = int(params["n_traders"])
    window = int(params["window_seconds"])
    floor = float(params["size_floor_usd"])

    groups: dict = defaultdict(list)
    for t in trades:
        if t["side"] == "BUY" and t["size_usd"] >= floor and t.get("outcome_index", -1) >= 0:
            groups[(t["condition_id"], t["outcome_index"])].append(t)

    signals = []
    for (cond, idx), rows in groups.items():
        rows.sort(key=lambda t: t["timestamp"])
        window_rows: list = []  # trades within the lookback window
        for t in rows:
            cutoff = t["timestamp"] - window
            window_rows = [r for r in window_rows if r["timestamp"] >= cutoff]
            window_rows.append(t)
            distinct = {}
            for r in window_rows:
                distinct.setdefault(r["wallet"], []).append(r)
            if len(distinct) >= n_traders:
                contributing = [r for rs in distinct.values() for r in rs]
                total_usd = sum(r["size_usd"] for r in contributing)
                avg_price = (sum(r["price"] * r["size_usd"] for r in contributing) / total_usd
                             if total_usd else None)
                signals.append({
                    "condition_id": cond,
                    "outcome_index": idx,
                    "side": "BUY",
                    "signal_time": t["timestamp"],
                    "n_traders": len(distinct),
                    "wallets": list(distinct.keys()),
                    "avg_trader_price": avg_price,
                    "trades": contributing,
                })
                break  # one signal max per (condition_id, outcome_index)
    signals.sort(key=lambda s: s["signal_time"])
    return signals


def wallet_position_at(trades: list, wallet: str, condition_id: str,
                       outcome_index: int, at_time: int) -> float:
    """Net shares a wallet holds in (condition_id, outcome_index) at a moment.

    trades: trade dicts as in detect_signals (shares = size_usd / price)."""
    pos = 0.0
    for t in trades:
        if (t["wallet"] == wallet and t["condition_id"] == condition_id
                and t.get("outcome_index") == outcome_index and t["timestamp"] <= at_time
                and t["price"] > 0):
            shares = t["size_usd"] / t["price"]
            pos += shares if t["side"] == "BUY" else -shares
    return pos


def compute_copy_exit(signal: dict, all_trades: list, wallet_fraction: float,
                      sold_fraction: float) -> Optional[int]:
    """Exit timestamp for the copy-exits strategy, or None if it never triggers.

    Walk the signal wallets' SELL trades on the signal token after signal_time.
    A wallet counts as exited once it has sold >= sold_fraction of the position
    it held at signal time. The exit fires at the timestamp when
    >= wallet_fraction of the signal wallets have exited.

    all_trades: full trade history covering the signal wallets (pure data)."""
    wallets = signal["wallets"]
    cond, idx, t0 = signal["condition_id"], signal["outcome_index"], signal["signal_time"]

    positions = {}
    for w in wallets:
        pos = wallet_position_at(all_trades, w, cond, idx, t0)
        positions[w] = pos if pos > 0 else None  # no measurable position -> first sell counts

    sells = sorted(
        (t for t in all_trades
         if t["side"] == "SELL" and t["condition_id"] == cond
         and t.get("outcome_index") == idx and t["wallet"] in set(wallets)
         and t["timestamp"] > t0 and t["price"] > 0),
        key=lambda t: t["timestamp"],
    )

    needed = max(1, math.ceil(wallet_fraction * len(wallets)))
    sold: dict = defaultdict(float)
    exited: set = set()
    for s in sells:
        w = s["wallet"]
        if w in exited:
            continue
        sold[w] += s["size_usd"] / s["price"]
        pos = positions[w]
        if pos is None or sold[w] >= sold_fraction * pos:
            exited.add(w)
            if len(exited) >= needed:
                return s["timestamp"]
    return None


def simulate_book_fill(asks: list, usd_amount: float) -> Optional[dict]:
    """Simulate filling usd_amount by walking asks (ascending price levels).

    asks: [{"price": float, "size": float (shares)}, ...] sorted ascending.
    Returns {"avg_price", "shares", "filled_usd"} or None if the book is too
    thin to fill the full amount."""
    remaining = usd_amount
    shares = 0.0
    for level in asks:
        level_usd = level["price"] * level["size"]
        take_usd = min(remaining, level_usd)
        if level["price"] > 0:
            shares += take_usd / level["price"]
        remaining -= take_usd
        if remaining <= 1e-9:
            filled = usd_amount
            return {"avg_price": filled / shares, "shares": shares, "filled_usd": filled}
    return None
