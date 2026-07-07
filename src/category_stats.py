"""Per-category aggregation for paper reporting (read-only, no side effects).

Used by paper_status.py (gate check-ins) and paper.py's daily summary to break
watchlist composition and paper-trade outcomes out by category. Categories on
paper_trades rows are backfilled read-only from the markets cache when the row
itself predates category recording.
"""
import sqlite3
from collections import defaultdict
from typing import Optional

CATEGORIES = ["POLITICS", "TECH", "CRYPTO", "FINANCE", "CULTURE", "SPORTS"]


def watchlist_by_category(conn: sqlite3.Connection, cohort: str) -> dict:
    """Per-category watchlist composition: wallet count, avg pnl/vol, avg entry edge.

    Multi-category wallets (e.g. 'FINANCE,TECH') count toward each of their
    categories, matching how discover.py's per-category caps treat them."""
    if cohort == "union":
        rows = conn.execute(
            "SELECT category, pnl_per_vol, entry_edge FROM wallets WHERE selected = 1")
    else:
        rows = conn.execute(
            """SELECT category, pnl_per_vol, entry_edge FROM wallets
               WHERE selected = 1 AND (',' || cohorts || ',') LIKE ?""",
            (f"%,{cohort},%",))
    acc: dict = defaultdict(lambda: {"wallets": 0, "ppv": [], "edge": []})
    for r in rows:
        for cat in (r["category"] or "UNMAPPED").split(","):
            a = acc[cat]
            a["wallets"] += 1
            if r["pnl_per_vol"] is not None:
                a["ppv"].append(r["pnl_per_vol"])
            if r["entry_edge"] is not None:
                a["edge"].append(r["entry_edge"])
    return {cat: {
        "wallets": a["wallets"],
        "avg_pnl_per_vol": sum(a["ppv"]) / len(a["ppv"]) if a["ppv"] else None,
        "avg_entry_edge": sum(a["edge"]) / len(a["edge"]) if a["edge"] else None,
    } for cat, a in acc.items()}


def paper_by_category(conn: sqlite3.Connection, since_ts: int = 0) -> dict:
    """Per-category paper outcomes since since_ts.

    Returns {category: {signals, open, closed, skipped, stale, fill_rate,
    realized_pnl, pnl_per_dollar, win_rate, entry_edge, mean_decay}}.
    fill_rate excludes STALE rows (never attempted, by design)."""
    rows = conn.execute(
        """SELECT pt.status, pt.pnl_20, pt.entry_price, pt.exit_price, pt.resolved,
                  pt.alpha_decay, pt.position_usd,
                  COALESCE(pt.category, m.category, 'UNMAPPED') AS cat
           FROM paper_trades pt
           LEFT JOIN markets m ON m.condition_id = pt.condition_id
           WHERE pt.signal_time >= ?""", (since_ts,))
    acc: dict = defaultdict(lambda: {
        "signals": 0, "open": 0, "closed": 0, "skipped": 0, "stale": 0,
        "pnl": 0.0, "stakes": 0.0, "wins": 0, "closed_pnl_n": 0,
        "edge": [], "decay": []})
    for r in rows:
        a = acc[r["cat"]]
        a["signals"] += 1
        key = r["status"].lower()
        if key in a:
            a[key] += 1
        if r["alpha_decay"] is not None:
            a["decay"].append(r["alpha_decay"])
        if r["status"] == "CLOSED" and r["pnl_20"] is not None:
            a["closed_pnl_n"] += 1
            a["pnl"] += r["pnl_20"]
            a["stakes"] += r["position_usd"] or 0.0
            a["wins"] += 1 if r["pnl_20"] > 0 else 0
            if r["resolved"] and r["entry_price"] and r["exit_price"] is not None:
                a["edge"].append(r["exit_price"] - r["entry_price"])
    out = {}
    for cat, a in acc.items():
        fills = a["open"] + a["closed"]
        attempted = fills + a["skipped"]
        out[cat] = {
            "signals": a["signals"], "open": a["open"], "closed": a["closed"],
            "skipped": a["skipped"], "stale": a["stale"],
            "fill_rate": fills / attempted if attempted else None,
            "realized_pnl": a["pnl"],
            "pnl_per_dollar": a["pnl"] / a["stakes"] if a["stakes"] else None,
            "win_rate": a["wins"] / a["closed_pnl_n"] if a["closed_pnl_n"] else None,
            "entry_edge": sum(a["edge"]) / len(a["edge"]) if a["edge"] else None,
            "mean_decay": sum(a["decay"]) / len(a["decay"]) if a["decay"] else None,
        }
    return out


def _fmt(v: Optional[float], spec: str, na: str = "-") -> str:
    return format(v, spec) if v is not None else na


def category_table(conn: sqlite3.Connection, cohort: str, since_ts: int = 0) -> str:
    """Markdown table: watchlist composition + paper outcomes per category."""
    wl = watchlist_by_category(conn, cohort)
    pp = paper_by_category(conn, since_ts)
    cats = CATEGORIES + sorted((set(wl) | set(pp)) - set(CATEGORIES))
    lines = [
        "| category | wallets | wl pnl/vol | wl edge | signals | filled | skipped |"
        " fill% | PnL $ | PnL/$ | win% | paper edge | decay |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for cat in cats:
        w = wl.get(cat, {})
        p = pp.get(cat, {})
        if not w and not p:
            continue
        fills = (p.get("open", 0) or 0) + (p.get("closed", 0) or 0)
        lines.append("| {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
            cat, w.get("wallets", 0),
            _fmt(w.get("avg_pnl_per_vol"), ".2f"), _fmt(w.get("avg_entry_edge"), "+.3f"),
            p.get("signals", 0), fills, p.get("skipped", 0),
            _fmt(p.get("fill_rate"), ".0%"),
            _fmt(p.get("realized_pnl"), "+.2f"), _fmt(p.get("pnl_per_dollar"), "+.3f"),
            _fmt(p.get("win_rate"), ".0%"), _fmt(p.get("entry_edge"), "+.3f"),
            _fmt(p.get("mean_decay"), "+.3f")))
    return "\n".join(lines)
