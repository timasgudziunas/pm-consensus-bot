"""Phase 4: generate the human-readable backtest report.

Reads backtest_results + signals (written by backtest.py) and produces:
- reports/backtest_report.md
- reports/equity_curve_top3.csv
- reports/best_cell_trades.csv

Run: python src/report.py
"""
import csv
import json
import os
from datetime import datetime, timezone

from tabulate import tabulate

import db
from data_api import load_config

REPORTS_DIR = os.path.join(db.REPO_ROOT, "reports")

SURVIVORSHIP_CAVEAT = """\
> **⚠ SURVIVORSHIP BIAS — READ BEFORE ACTING ON ANYTHING BELOW**
>
> The watchlist was selected from **today's** leaderboard: these traders are on it
> *because* their bets ended up winning. Replaying their historical trades therefore
> overstates what a real-time selection would have earned. Mitigations applied:
> (1) train/validate split — parameters are picked on the first 4 months and judged
> on the last 2; (2) treat every number in this report as an **upper bound**, not an
> expectation. A trader whose edge was luck will regress; paper trading (Phase 5)
> is the honest test. See OVERVIEW.md for the full discussion.
>
> **Coverage bias (API limitation):** the Data API caps per-wallet history at its
> 4,000 most recent trades; 85 of 113 watchlist wallets hit that cap, so the most
> active wallets contribute little or nothing to the early (train) months. Trade
> density — and therefore signal counts — is skewed toward the recent (validate)
> period. Treat cross-period comparisons accordingly.
"""


def fmt(v, spec=",.0f", none="—"):
    """Format a possibly-None number."""
    return none if v is None else format(v, spec)


def pct(v):
    return "—" if v is None else f"{v * 100:.0f}%"


def cell_label(r) -> str:
    return f"N={r['n_traders']} W={r['window_hours']:g}h F=${r['size_floor']:.0f} {r['exit_strategy']} ${r['position_size']:.0f}"


def main() -> None:
    """Build the report from backtest_results and signals tables."""
    conn = db.connect()
    cfg = load_config()
    rows = {(r["n_traders"], r["window_hours"], r["size_floor"], r["exit_strategy"],
             r["position_size"], r["split"]): dict(r)
            for r in conn.execute("SELECT * FROM backtest_results")}
    if not rows:
        raise SystemExit("no backtest results — run backtest.py first")

    cells = sorted({k[:5] for k in rows},
                   key=lambda c: -(rows.get((*c, "validate"), {}).get("total_pnl") or float("-inf")))

    def r_of(cell, split):
        return rows.get((*cell, split), {})

    top3 = cells[:3]
    best = top3[0]
    best_val = r_of(best, "validate")
    best_train = r_of(best, "train")

    consistent = [c for c in cells
                  if (r_of(c, "validate").get("total_pnl") or 0) > 0
                  and (r_of(c, "train").get("total_pnl") or 0) > 0]

    lines = []
    lines.append("# Backtest Report — Polymarket Consensus Copy-Trading")
    lines.append(f"\n_Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}. "
                 f"Lookback {cfg['lookback_months']} months, train = first "
                 f"{cfg['backtest']['train_months']} months, validate = remainder._\n")

    # 1. Executive summary
    lines.append("## 1. Executive summary\n")
    lines.append(
        f"The best parameter set on **validate** data is **{cell_label(best_val)}** with a "
        f"validate-period total PnL of **${fmt(best_val.get('total_pnl'), ',.2f')}** "
        f"({pct(best_val.get('return_on_capital'))} return on capital deployed), a win rate of "
        f"{pct(best_val.get('win_rate'))} over {best_val.get('signal_count')} signals "
        f"({best_val.get('resolved_count')} closed). "
        f"Its train-period PnL was ${fmt(best_train.get('total_pnl'), ',.2f')} "
        f"({pct(best_train.get('win_rate'))} win rate), so it "
        f"{'**was** profitable in both periods' if best in consistent else '**was not** consistently profitable across both periods'}. "
        f"Across the whole grid, {len(consistent)} of {len(cells)} cells were profitable in "
        f"both train and validate periods.\n")

    # 2. Survivorship caveat
    lines.append("## 2. Known bias\n")
    lines.append(SURVIVORSHIP_CAVEAT)

    # 3. Full grid
    lines.append("\n## 3. Full grid results (sorted by validate PnL)\n")
    table = []
    for i, c in enumerate(cells):
        tr, va, fu = r_of(c, "train"), r_of(c, "validate"), r_of(c, "full")
        mark = "**top3** " if i < 3 else ""
        table.append([
            mark + str(c[0]), f"{c[1]:g}h", f"${c[2]:.0f}", c[3], f"${c[4]:.0f}",
            tr.get("signal_count"), pct(tr.get("win_rate")), fmt(tr.get("total_pnl"), ",.0f"),
            va.get("signal_count"), pct(va.get("win_rate")), fmt(va.get("total_pnl"), ",.0f"),
            fmt(fu.get("total_pnl"), ",.0f"),
        ])
    lines.append(tabulate(table, headers=["N", "W", "F", "exit", "size",
                                          "sig(tr)", "win(tr)", "PnL(tr)",
                                          "sig(val)", "win(val)", "PnL(val)", "PnL(full)"],
                          tablefmt="github"))

    # 4. Category consistency for top 3
    lines.append("\n\n## 4. Category consistency (top 3 cells, validate period)\n")
    for c in top3:
        va = r_of(c, "validate")
        lines.append(f"\n**{cell_label(va)}**\n")
        breakdown = json.loads(va.get("category_breakdown") or "{}")
        cat_table = [[cat, v["signals"], pct(v["win_rate"]), f"${v['total_pnl']:,.2f}"]
                     for cat, v in sorted(breakdown.items(), key=lambda kv: -kv[1]["total_pnl"])]
        lines.append(tabulate(cat_table, headers=["category", "signals", "win rate", "PnL"],
                              tablefmt="github"))
    lines.append("\nCategories that appear with positive PnL across all three cells are the "
                 "consistent earners; categories negative in every cell drag returns and are "
                 "candidates for exclusion in paper mode.")

    # 5. Exit strategy A vs B
    lines.append("\n\n## 5. Hold-to-resolution vs copy-exits (top 3 N/W/F/size combos)\n")
    ab_table = []
    seen = set()
    for c in top3:
        key = (c[0], c[1], c[2], c[4])  # N, W, F, size
        if key in seen:
            continue
        seen.add(key)
        va_a = rows.get((c[0], c[1], c[2], "hold_to_resolution", c[4], "validate"), {})
        va_b = rows.get((c[0], c[1], c[2], "copy_exits", c[4], "validate"), {})
        pa, pb = va_a.get("total_pnl"), va_b.get("total_pnl")
        winner = "—"
        if pa is not None and pb is not None:
            winner = f"hold (+${pa - pb:,.2f})" if pa > pb else f"copy (+${pb - pa:,.2f})"
        ab_table.append([f"N={c[0]} W={c[1]:g}h F=${c[2]:.0f} ${c[4]:.0f}",
                         fmt(pa, ",.2f"), fmt(pb, ",.2f"), winner])
    lines.append(tabulate(ab_table, headers=["combo", "hold PnL(val)", "copy PnL(val)", "winner"],
                          tablefmt="github"))

    # 6. Equity curves CSV (validate period, top 3 cells)
    curves = []
    for c in top3:
        pnl_col = "pnl_20" if c[4] == 20 else "pnl_50"
        sig_rows = conn.execute(
            f"""SELECT signal_time, exit_time, {pnl_col} pnl FROM signals
                WHERE n_traders=? AND window_hours=? AND size_floor=? AND exit_type=?
                  AND split='validate' AND {pnl_col} IS NOT NULL
                ORDER BY COALESCE(exit_time, signal_time)""",
            (c[0], c[1], c[2], c[3])).fetchall()
        cum, curve = 0.0, []
        for r in sig_rows:
            cum += r["pnl"]
            curve.append((r["exit_time"] or r["signal_time"], cum))
        curves.append(curve)
    eq_path = os.path.join(REPORTS_DIR, "equity_curve_top3.csv")
    with open(eq_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["trade_number", "timestamp_cell1", "cumulative_pnl_cell1",
                    "timestamp_cell2", "cumulative_pnl_cell2",
                    "timestamp_cell3", "cumulative_pnl_cell3"])
        for i in range(max((len(c) for c in curves), default=0)):
            row = [i + 1]
            for curve in curves:
                row += list(curve[i]) if i < len(curve) else ["", ""]
            w.writerow(row)
    lines.append(f"\n\n## 6. Equity curves\n\nValidate-period cumulative PnL for the top 3 cells: "
                 f"`reports/equity_curve_top3.csv` ({max((len(c) for c in curves), default=0)} rows).")

    # 7. Trade log for the best cell
    pnl_col = "pnl_20" if best[4] == 20 else "pnl_50"
    best_trades = conn.execute(
        f"""SELECT s.signal_time, s.entry_price, s.exit_price, s.exit_time, s.exit_type,
                   s.{pnl_col} pnl, s.category, s.resolved, m.question
            FROM signals s LEFT JOIN markets m ON m.condition_id = s.condition_id
            WHERE s.n_traders=? AND s.window_hours=? AND s.size_floor=? AND s.exit_type=?
              AND s.split='validate'
            ORDER BY s.signal_time""", (best[0], best[1], best[2], best[3])).fetchall()
    log_path = os.path.join(REPORTS_DIR, "best_cell_trades.csv")
    with open(log_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["market", "signal_time_utc", "entry_price", "exit_price", "exit_type", "pnl", "category"])
        for r in best_trades:
            w.writerow([r["question"],
                        datetime.fromtimestamp(r["signal_time"], tz=timezone.utc).isoformat(),
                        r["entry_price"], r["exit_price"], r["exit_type"],
                        None if r["pnl"] is None else round(r["pnl"], 2), r["category"]])
    lines.append(f"\n## 7. Best-cell trade log\n\nEvery simulated validate-period trade for "
                 f"**{cell_label(best_val)}**: `reports/best_cell_trades.csv` ({len(best_trades)} rows).")

    # 8. Unresolved positions
    lines.append("\n## 8. Unresolved positions (validate period, top 10 cells)\n")
    unres_table = [[cell_label(r_of(c, 'validate')), r_of(c, "validate").get("unresolved_count"),
                    f"${(r_of(c, 'validate').get('unresolved_count') or 0) * c[4]:,.0f}"]
                   for c in cells[:10]]
    lines.append(tabulate(unres_table, headers=["cell", "unresolved", "capital tied up"],
                          tablefmt="github"))

    # 9. Next steps
    lines.append("\n\n## 9. Recommended next steps\n")
    val_pnl = best_val.get("total_pnl") or 0
    if val_pnl > 0 and best in consistent:
        lines.append(
            f"- Validate-period returns are **positive and consistent with train**. Run paper mode "
            f"with N={best[0]}, window={best[1]:g}h, floor=${best[2]:.0f}, exit={best[3]} "
            f"(update the `paper:` block in config.yaml) and compare live alpha decay against the "
            f"backtest edge of ${fmt(best_val.get('avg_pnl'), ',.2f')}/trade.")
        lines.append("- Do NOT go live until the decision-gate checklist in PLAN.md passes.")
    elif val_pnl > 0:
        lines.append("- The best validate cell is positive but was **not** among the best on train "
                     "— likely noise. Keep paper mode on defaults and re-run the backtest with more "
                     "history before trusting it.")
    else:
        lines.append("- **No parameter set made money in the validate period.** Given that this "
                     "backtest already overstates returns (survivorship bias), the strategy as "
                     "specified shows no edge. Do not proceed toward live trading; revisit the "
                     "signal definition or the watchlist instead.")

    os.makedirs(REPORTS_DIR, exist_ok=True)
    out = os.path.join(REPORTS_DIR, "backtest_report.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"report written: {out}")
    print(f"equity curves:  {eq_path}")
    print(f"trade log:      {log_path}")


if __name__ == "__main__":
    main()
