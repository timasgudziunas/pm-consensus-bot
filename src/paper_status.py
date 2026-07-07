"""Paper-trading status check-in against the day-3 decision gate.

Computes, for everything since paper.gate_start_utc: filled signals (OPEN /
CLOSED), STALE- and SKIPPED-filtered counts, win rate over closed positions,
mean alpha decay, realized + mark-to-market PnL — and compares each number
against the gate thresholds in config (paper.gate, mirrored in PLAN.md).

Run: python src/paper_status.py [--append]
     --append also appends the block to reports/paper_checkins.md
     (used by the scheduled check-in tasks)
"""
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone

import category_stats
import db
from clob_api import ClobApi
from data_api import ApiError, load_config

REPORTS_DIR = os.path.join(db.REPO_ROOT, "reports")
CHECKINS_MD = os.path.join(REPORTS_DIR, "paper_checkins.md")


def build_report() -> str:
    """Return the formatted check-in block."""
    pcfg = load_config()["paper"]
    gate = pcfg["gate"]
    start_ts = int(datetime.fromisoformat(
        pcfg["gate_start_utc"].replace("Z", "+00:00")).timestamp())
    now = int(time.time())
    day = (now - start_ts) / 86400.0

    conn = db.connect()
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM paper_trades WHERE signal_time >= ?", (start_ts,))]
    by_status = Counter(r["status"] for r in rows)
    fills = [r for r in rows if r["status"] in ("OPEN", "CLOSED")]
    closed = [r for r in fills if r["status"] == "CLOSED" and r["pnl_20"] is not None]
    wins = sum(1 for r in closed if r["pnl_20"] > 0)
    win_rate = wins / len(closed) if closed else None
    realized = sum(r["pnl_20"] for r in closed)
    decays = [r["alpha_decay"] for r in fills if r["alpha_decay"] is not None]
    mean_decay = sum(decays) / len(decays) if decays else None

    clob = ClobApi()
    unrealized, priced = 0.0, 0
    for r in fills:
        if r["status"] != "OPEN" or not r["entry_price"] or not r["position_usd"]:
            continue
        try:
            mid = clob.get_midpoint(r["token_id"])
        except ApiError:
            mid = None
        if mid:
            unrealized += (mid - r["entry_price"]) * (r["position_usd"] / r["entry_price"])
            priced += 1

    def verdict(ok, na=False):
        return "n/a yet" if na else ("ON TRACK" if ok else "AT RISK")

    pace = len(fills) / day * 3 if day > 0 else 0.0
    fills_v = verdict(len(fills) >= gate["min_fills"] or pace >= gate["min_fills"])
    if len(closed) >= gate["min_closed_for_win_rate"]:
        win_v = verdict(win_rate >= gate["min_win_rate"])
    else:
        win_v = verdict(realized + unrealized >= 0) + \
            f" (only {len(closed)} closed — using MTM-neutral-or-positive criterion)"
    decay_v = verdict(mean_decay is not None and mean_decay < gate["max_mean_alpha_decay"],
                      na=mean_decay is None)

    lines = [
        f"## Paper check-in — day {day:.2f} of 3 "
        f"({datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')})",
        f"- signals recorded (filled): {len(fills)} "
        f"({by_status.get('OPEN', 0)} open, {by_status.get('CLOSED', 0)} closed)",
        f"- filtered out: {by_status.get('STALE', 0)} STALE (too old to copy), "
        f"{by_status.get('SKIPPED', 0)} SKIPPED (book too thin/gone)",
        f"- win rate: {f'{win_rate * 100:.0f}% ({wins}/{len(closed)})' if closed else 'n/a (nothing closed yet)'}",
        f"- mean alpha decay: "
        f"{f'{mean_decay * 100:+.2f}c/share over {len(decays)} fills' if decays else 'n/a (no fills yet)'}",
        f"- PnL: ${realized:+.2f} realized ({len(closed)} closed), "
        f"${unrealized:+.2f} MTM over {priced} priced open positions",
        "",
        "Gate tracking (thresholds in PLAN.md / config paper.gate):",
        f"- fills >= {gate['min_fills']} by day 3: {len(fills)} so far, "
        f"pace ~{pace:.0f} -> {fills_v}",
        f"- win rate >= {gate['min_win_rate']:.0%} "
        f"(needs >= {gate['min_closed_for_win_rate']} closed): {win_v}",
        f"- mean decay < {gate['max_mean_alpha_decay'] * 100:.0f}c/share: {decay_v}",
        "",
        f"By category (watchlist cohort {pcfg['watchlist_cohort']}; paper stats since gate start):",
        category_stats.category_table(conn, pcfg["watchlist_cohort"], start_ts),
    ]
    return "\n".join(lines)


def main() -> None:
    """Print the check-in; --append also writes it to reports/paper_checkins.md."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    report = build_report()
    print(report)
    if "--append" in sys.argv:
        os.makedirs(REPORTS_DIR, exist_ok=True)
        with open(CHECKINS_MD, "a", encoding="utf-8") as f:
            f.write(report + "\n\n")


if __name__ == "__main__":
    main()
