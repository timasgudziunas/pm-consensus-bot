"""Paper-trading dashboard + day-3 gate check-in.

Regenerates reports/paper_dashboard.md in full from data/copybot.db
(paper_trades is the single source of truth). The dashboard leads with the
bottom line — net PnL = realized + mark-to-market — then gate tracking
against config paper.gate, daily realized PnL by exit date, the per-category
table, and a compact one-line-per-check-in history (the only appended part;
it survives regeneration via the history-section marker).

Replaces the former reports/paper_checkins.md + reports/paper_daily.md pair,
which overlapped and reported different time windows (archived 2026-07-07).

Run: python src/paper_status.py [--append]
     --append also (re)writes reports/paper_dashboard.md and adds a history
     line (used by the scheduled check-in tasks)
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
DASHBOARD_MD = os.path.join(REPORTS_DIR, "paper_dashboard.md")
HISTORY_HEADER = "## Check-in history"


def gather_stats(conn, since_ts: int | None = None) -> dict:
    """Aggregate fill/close/PnL/decay stats from paper_trades, optionally windowed."""
    where, args = ("WHERE signal_time >= ?", (since_ts,)) if since_ts else ("", ())
    rows = [dict(r) for r in conn.execute(f"SELECT * FROM paper_trades {where}", args)]
    by_status = Counter(r["status"] for r in rows)
    fills = [r for r in rows if r["status"] in ("OPEN", "CLOSED")]
    closed = [r for r in fills if r["status"] == "CLOSED" and r["pnl_20"] is not None]
    wins = sum(1 for r in closed if r["pnl_20"] > 0)
    decays = [r["alpha_decay"] for r in fills if r["alpha_decay"] is not None]
    return {
        "by_status": by_status,
        "fills": fills,
        "n_open": by_status.get("OPEN", 0),
        "closed": closed,
        "wins": wins,
        "win_rate": wins / len(closed) if closed else None,
        "realized": sum(r["pnl_20"] for r in closed),
        "staked_open": sum(r["position_usd"] or 0 for r in fills if r["status"] == "OPEN"),
        "mean_decay": sum(decays) / len(decays) if decays else None,
        "n_decays": len(decays),
    }


def price_open_positions(fills: list[dict], clob: ClobApi) -> tuple[float, int, int]:
    """Mark open positions to CLOB midpoints; returns (mtm, priced, unpriced)."""
    mtm, priced, unpriced = 0.0, 0, 0
    for r in fills:
        if r["status"] != "OPEN" or not r["entry_price"] or not r["position_usd"]:
            continue
        try:
            mid = clob.get_midpoint(r["token_id"])
        except ApiError:
            mid = None
        if mid:
            mtm += (mid - r["entry_price"]) * (r["position_usd"] / r["entry_price"])
            priced += 1
        else:
            unpriced += 1
    return mtm, priced, unpriced


def daily_pnl_table(conn) -> str:
    """Markdown table of realized PnL by exit date, with running cumulative."""
    lines = ["| exit date | closed | realized $ | cumulative $ |",
             "|---|---|---|---|"]
    cum = 0.0
    for r in conn.execute(
            "SELECT date(exit_time,'unixepoch') d, COUNT(*) n, SUM(pnl_20) p "
            "FROM paper_trades WHERE status='CLOSED' AND exit_time IS NOT NULL "
            "GROUP BY 1 ORDER BY 1"):
        cum += r["p"]
        lines.append(f"| {r['d']} | {r['n']} | {r['p']:+.2f} | {cum:+.2f} |")
    return "\n".join(lines)


def build_dashboard() -> tuple[str, str]:
    """Return (dashboard_markdown_without_history, one_line_history_entry)."""
    cfg = load_config()["paper"]
    gate = cfg["gate"]
    gate_start = int(datetime.fromisoformat(
        cfg["gate_start_utc"].replace("Z", "+00:00")).timestamp())
    now_dt = datetime.now(timezone.utc)
    day = (int(time.time()) - gate_start) / 86400.0

    conn = db.connect()
    alltime = gather_stats(conn)
    in_gate = gather_stats(conn, gate_start)
    mtm, priced, unpriced = price_open_positions(alltime["fills"], ClobApi())
    net = alltime["realized"] + mtm

    def money(x: float) -> str:
        return f"${x:+,.2f}"

    def verdict(ok, na=False):
        return "n/a yet" if na else ("ON TRACK" if ok else "AT RISK")

    g = in_gate
    pace = len(g["fills"]) / day * 3 if day > 0 else 0.0
    fills_v = verdict(len(g["fills"]) >= gate["min_fills"] or pace >= gate["min_fills"])
    if len(g["closed"]) >= gate["min_closed_for_win_rate"]:
        win_v = verdict(g["win_rate"] >= gate["min_win_rate"])
    else:
        win_v = verdict(g["realized"] + mtm >= 0) + \
            f" (only {len(g['closed'])} closed — using MTM-neutral-or-positive criterion)"
    decay_v = verdict(g["mean_decay"] is not None and g["mean_decay"] < gate["max_mean_alpha_decay"],
                      na=g["mean_decay"] is None)

    wr = alltime["win_rate"]
    lines = [
        "# Paper Trading Dashboard",
        "",
        f"_Regenerated {now_dt.strftime('%Y-%m-%d %H:%M UTC')} by `src/paper_status.py` "
        f"from `data/copybot.db` (single source of truth). Live stake: "
        f"${cfg['position_size_usd']}/position (older rows keep their opening stake)._",
        "",
        "## Bottom line (all-time)",
        "",
        f"**Net PnL: {money(net)}** = {money(alltime['realized'])} realized "
        f"+ {money(mtm)} mark-to-market on open positions"
        f"{f' ({unpriced} open positions unpriced)' if unpriced else ''}",
        "",
        f"- Closed: {len(alltime['closed'])} positions, win rate "
        f"{f'{wr:.0%} ({alltime['wins']}/{len(alltime['closed'])})' if wr is not None else 'n/a'}, "
        f"realized {money(alltime['realized'])}",
        f"- Open: {alltime['n_open']} positions, ${alltime['staked_open']:,.2f} staked, "
        f"MTM {money(mtm)} ({priced} priced)",
        f"- Mean alpha decay: "
        f"{f'{alltime['mean_decay'] * 100:+.2f}c/share over {alltime['n_decays']} fills' if alltime['mean_decay'] is not None else 'n/a'}",
        f"- Filtered out (never filled): {alltime['by_status'].get('SKIPPED', 0)} SKIPPED "
        f"(book too thin/gone), {alltime['by_status'].get('STALE', 0)} STALE (detected too late)",
        "",
        f"## Decision gate — day {day:.2f} of 3 "
        f"(window since {cfg['gate_start_utc']}; thresholds in config `paper.gate`)",
        "",
        f"- fills >= {gate['min_fills']} by day 3: {len(g['fills'])} so far, "
        f"pace ~{pace:.0f} -> **{fills_v}**",
        f"- win rate >= {gate['min_win_rate']:.0%} "
        f"(needs >= {gate['min_closed_for_win_rate']} closed): "
        f"{f'{g['win_rate']:.0%}' if g['win_rate'] is not None else 'n/a'} -> **{win_v}**",
        f"- mean decay < {gate['max_mean_alpha_decay'] * 100:.0f}c/share: "
        f"{f'{g['mean_decay'] * 100:+.2f}c' if g['mean_decay'] is not None else 'n/a'} -> **{decay_v}**",
        "",
        "## Daily realized PnL (by exit date)",
        "",
        daily_pnl_table(conn),
        "",
        f"## By category (watchlist cohort {cfg['watchlist_cohort']}, all-time)",
        "",
        category_stats.category_table(conn, cfg["watchlist_cohort"]),
        "",
    ]
    history_line = (
        f"- {now_dt.strftime('%Y-%m-%d %H:%M UTC')} — day {day:.2f}/3 | "
        f"fills {len(alltime['fills'])} ({alltime['n_open']} open/{len(alltime['closed'])} closed) | "
        f"win {f'{wr:.0%}' if wr is not None else 'n/a'} | "
        f"realized {money(alltime['realized'])} | MTM {money(mtm)} | net {money(net)}")
    return "\n".join(lines), history_line


def read_existing_history() -> list[str]:
    """Return prior history lines from the dashboard, if any."""
    try:
        with open(DASHBOARD_MD, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return []
    if HISTORY_HEADER not in text:
        return []
    tail = text.split(HISTORY_HEADER, 1)[1]
    return [ln for ln in tail.splitlines() if ln.startswith("- ")]


def main() -> None:
    """Print the dashboard; --append also rewrites reports/paper_dashboard.md."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    body, history_line = build_dashboard()
    print(body)
    print(HISTORY_HEADER + "\n\n" + history_line)
    if "--append" in sys.argv:
        history = read_existing_history() + [history_line]
        os.makedirs(REPORTS_DIR, exist_ok=True)
        with open(DASHBOARD_MD, "w", encoding="utf-8") as f:
            f.write(body + HISTORY_HEADER + "\n\n" + "\n".join(history) + "\n")


if __name__ == "__main__":
    main()
