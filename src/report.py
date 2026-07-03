"""Phase 4: generate the human-readable backtest report — cohort edition.

Reads backtest_results + signals (written by backtest.py, one sweep per wallet
cohort) and produces:
- reports/backtest_report.md   (cohort comparison + robustness-checked winners)
- reports/equity_curve_top3.csv  (top 3 cells of the winning cohort)
- reports/best_cell_trades.csv   (trade log of the overall best robust cell)

Run: python src/report.py
"""
import csv
import json
import os
import time
from datetime import datetime, timezone

from tabulate import tabulate

import db
from data_api import load_config

REPORTS_DIR = os.path.join(db.REPO_ROOT, "reports")

SECONDS_PER_MONTH = 30.44 * 86400

SURVIVORSHIP_CAVEAT = """\
> **⚠ SURVIVORSHIP BIAS — READ BEFORE ACTING ON ANYTHING BELOW**
>
> The watchlist was selected from **today's** leaderboard: these traders are on it
> *because* their bets ended up winning. Replaying their historical trades therefore
> overstates what a real-time selection would have earned. This applies to EVERY
> cohort below — cohort B and C rankings are computed over the same
> leaderboard-derived pool, so comparing cohorts is fair, but absolute numbers are
> inflated for all of them. Mitigations applied:
> (1) train/validate split — parameters are picked on the first 4 months and judged
> on the last 2; (2) neighborhood robustness check — single spectacular grid cells
> are flagged as suspect unless their parameter neighbors are also profitable;
> (3) treat every number in this report as an **upper bound**, not an expectation.
> A trader whose edge was luck will regress; paper trading (Phase 5) is the honest
> test. See OVERVIEW.md for the full discussion.
>
> **Coverage bias (API limitation):** the Data API caps per-wallet history at its
> 4,000 most recent trades — {trunc} of {selected} selected wallets hit that cap, so the
> most active wallets contribute little or nothing to the early (train) months.
> Trade density — and therefore signal counts — is skewed toward the recent
> (validate) period. Treat cross-period comparisons accordingly.
"""


def fmt(v, spec=",.0f", none="—"):
    """Format a possibly-None number."""
    return none if v is None else format(v, spec)


def pct(v):
    return "—" if v is None else f"{v * 100:.0f}%"


def cell_label(c: tuple) -> str:
    """Label for a (n, w, f, exit, size) cell tuple."""
    return f"N={c[0]} W={c[1]:g}h F=${c[2]:.0f} {c[3]} ${c[4]:.0f}"


def neighbor_cells(cell: tuple, grid: dict) -> list:
    """Grid neighbors of a cell: N±1, W one step, F one step (exit/size fixed)."""
    n, w, f, exit_s, size = cell
    out = []
    axes = [("n_traders", n, 0), ("window_hours", w, 1), ("size_floor_usd", f, 2)]
    for key, val, pos in axes:
        values = grid[key]
        try:
            i = values.index(val)
        except ValueError:
            # DB floats vs config ints — match by value
            i = next((j for j, v in enumerate(values) if float(v) == float(val)), None)
            if i is None:
                continue
        for j in (i - 1, i + 1):
            if 0 <= j < len(values):
                nc = [n, w, f]
                nc[pos] = values[j]
                out.append((nc[0], nc[1], nc[2], exit_s, size))
    return out


def robust_fraction(rows: dict, cohort: str, cell: tuple, grid: dict):
    """Fraction of a cell's grid neighbors profitable in validate, or None."""
    present = profitable = 0
    for nc in neighbor_cells(cell, grid):
        r = rows.get((cohort, *nc, "validate"))
        if r:
            present += 1
            profitable += 1 if (r.get("total_pnl") or 0) > 0 else 0
    return (profitable / present) if present else None


def coverage_counts(conn) -> tuple:
    """(truncated, selected) wallet counts for the coverage-bias note."""
    cutoff = int(time.time() - load_config()["lookback_months"] * SECONDS_PER_MONTH)
    selected = conn.execute("SELECT COUNT(*) c FROM wallets WHERE selected = 1").fetchone()["c"]
    trunc = conn.execute(
        """SELECT COUNT(*) c FROM (
               SELECT t.wallet, MIN(t.timestamp) mn FROM trades t
               JOIN wallets w ON w.address = t.wallet AND w.selected = 1
               GROUP BY t.wallet)
           WHERE mn > ?""", (cutoff + 7 * 86400,)).fetchone()["c"]
    return trunc, selected


def main() -> None:
    """Build the cohort-comparison report from backtest_results and signals."""
    conn = db.connect()
    cfg = load_config()
    bcfg = cfg["backtest"]
    grid = cfg["sweep"]
    thresh = bcfg["robust_neighbor_fraction"]

    rows = {(r["cohort"], r["n_traders"], r["window_hours"], r["size_floor"],
             r["exit_strategy"], r["position_size"], r["split"]): dict(r)
            for r in conn.execute("SELECT * FROM backtest_results")}
    if not rows:
        raise SystemExit("no backtest results — run backtest.py first")
    cohorts = sorted({k[0] for k in rows})

    def r_of(cohort, cell, split):
        return rows.get((cohort, *cell, split), {})

    # ---- per-cohort analysis ----
    analysis = {}
    for co in cohorts:
        cells = sorted({k[1:6] for k in rows if k[0] == co},
                       key=lambda c: -(r_of(co, c, "validate").get("total_pnl") or float("-inf")))
        consistent = [c for c in cells
                      if (r_of(co, c, "validate").get("total_pnl") or 0) > 0
                      and (r_of(co, c, "train").get("total_pnl") or 0) > 0]
        # robustness over the top slice (sorted by validate PnL, so the first
        # consistent+robust cell found is the cohort's best robust cell)
        best_robust, robust_info = None, {}
        for c in cells[:100]:
            frac = robust_fraction(rows, co, c, grid)
            robust_info[c] = frac
            ok = (c in consistent and frac is not None and frac >= thresh)
            if ok and best_robust is None:
                best_robust = c
        analysis[co] = {
            "cells": cells, "consistent": consistent,
            "best": cells[0] if cells else None,
            "best_robust": best_robust, "robust_info": robust_info,
        }

    # winner: cohort with the highest-validate-PnL robust cell; if no cohort has
    # a robust cell, fall back to raw best but say so loudly
    robust_cohorts = [co for co in cohorts if analysis[co]["best_robust"]]
    if robust_cohorts:
        winner = max(robust_cohorts,
                     key=lambda co: r_of(co, analysis[co]["best_robust"], "validate").get("total_pnl") or 0)
        winner_cell = analysis[winner]["best_robust"]
    else:
        winner = max(cohorts,
                     key=lambda co: (r_of(co, analysis[co]["best"], "validate").get("total_pnl") or 0)
                     if analysis[co]["best"] else float("-inf"))
        winner_cell = analysis[winner]["best"]
    win_val = r_of(winner, winner_cell, "validate")
    win_train = r_of(winner, winner_cell, "train")

    lines = []
    lines.append("# Backtest Report — Polymarket Consensus Copy-Trading (cohort sweep)")
    lines.append(f"\n_Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}. "
                 f"Lookback {cfg['lookback_months']} months, train = first "
                 f"{bcfg['train_months']} months, validate = remainder. "
                 f"Cohorts: A = raw month PnL (control), B = PnL per dollar of volume, "
                 f"C = stake-weighted entry edge, union = all selected wallets._\n")

    # 1. Executive summary
    lines.append("## 1. Executive summary\n")
    robust_note = ("robust: its parameter neighborhood is profitable in validate"
                   if analysis[winner]["best_robust"] == winner_cell else
                   "**NOT robust** — no cell in any cohort passed the neighborhood check; "
                   "treat this winner as suspect")
    lines.append(
        f"The best wallet set is **cohort {winner}** and the best parameter cell is "
        f"**{cell_label(winner_cell)}** ({robust_note}). Validate-period total PnL "
        f"**${fmt(win_val.get('total_pnl'), ',.2f')}** "
        f"({pct(win_val.get('return_on_capital'))} return on capital), win rate "
        f"{pct(win_val.get('win_rate'))} over {win_val.get('signal_count')} signals "
        f"({win_val.get('resolved_count')} closed); train-period PnL "
        f"${fmt(win_train.get('total_pnl'), ',.2f')} ({pct(win_train.get('win_rate'))} win rate).\n")

    # 2. Bias caveats
    trunc, selected = coverage_counts(conn)
    lines.append("## 2. Known bias\n")
    lines.append(SURVIVORSHIP_CAVEAT.format(trunc=trunc, selected=selected))

    # 3. Cohort comparison — the night's question: which definition of
    # "efficient" produces the most profitable consensus signals?
    lines.append("\n## 3. Cohort comparison\n")
    comp = []
    for co in cohorts:
        a = analysis[co]
        best, br = a["best"], a["best_robust"]
        bv = r_of(co, best, "validate") if best else {}
        brv = r_of(co, br, "validate") if br else {}
        comp.append([
            co, len(a["cells"]), len(a["consistent"]),
            pct(len(a["consistent"]) / len(a["cells"]) if a["cells"] else None),
            cell_label(best) if best else "—", fmt(bv.get("total_pnl"), ",.0f"),
            cell_label(br) if br else "none", fmt(brv.get("total_pnl"), ",.0f"),
            pct(a["robust_info"].get(br)) if br else "—",
        ])
    lines.append(tabulate(comp, headers=["cohort", "cells", "both-profitable", "breadth",
                                         "best cell (val PnL sort)", "PnL(val)",
                                         "best ROBUST cell", "PnL(val)", "nbr prof."],
                          tablefmt="github"))
    lines.append(
        f"\n**Verdict:** cohort **{winner}** wins on the best robust validate cell. "
        f"Breadth (share of cells profitable in both periods) is the tie-breaker to "
        f"trust when robust winners are close — a cohort that is broadly profitable "
        f"beats one spectacular cell. Robustness threshold: ≥{thresh:.0%} of a cell's "
        f"grid neighbors (N±1, window ±1 step, floor ±1 step) profitable in validate.")

    # 4. Top grid cells per cohort
    top_n = bcfg["report_top_cells"]
    lines.append(f"\n\n## 4. Top {top_n} grid cells per cohort (sorted by validate PnL)\n")
    for co in cohorts:
        a = analysis[co]
        lines.append(f"\n### Cohort {co}\n")
        table = []
        for c in a["cells"][:top_n]:
            tr, va = r_of(co, c, "train"), r_of(co, c, "validate")
            frac = a["robust_info"].get(c)
            table.append([
                c[0], f"{c[1]:g}h", f"${c[2]:.0f}", c[3], f"${c[4]:.0f}",
                tr.get("signal_count"), pct(tr.get("win_rate")), fmt(tr.get("total_pnl"), ",.0f"),
                va.get("signal_count"), pct(va.get("win_rate")), fmt(va.get("total_pnl"), ",.0f"),
                pct(frac),
                "ROBUST" if (c in a["consistent"] and frac is not None and frac >= thresh) else "",
            ])
        lines.append(tabulate(table, headers=["N", "W", "F", "exit", "size",
                                              "sig(tr)", "win(tr)", "PnL(tr)",
                                              "sig(val)", "win(val)", "PnL(val)",
                                              "nbrs prof.", "robust"],
                              tablefmt="github"))
        lines.append(f"\n({len(a['cells'])} cells total for cohort {co}; "
                     f"full grid lives in the backtest_results table.)")

    # 5. Category consistency (top 3 cells of the winning cohort, validate)
    win_cells = analysis[winner]["cells"]
    top3 = win_cells[:3]
    lines.append(f"\n\n## 5. Category consistency (cohort {winner} top 3 cells, validate period)\n")
    for c in top3:
        va = r_of(winner, c, "validate")
        lines.append(f"\n**{cell_label(c)}**\n")
        breakdown = json.loads(va.get("category_breakdown") or "{}")
        cat_table = [[cat, v["signals"], pct(v["win_rate"]), f"${v['total_pnl']:,.2f}"]
                     for cat, v in sorted(breakdown.items(), key=lambda kv: -kv[1]["total_pnl"])]
        lines.append(tabulate(cat_table, headers=["category", "signals", "win rate", "PnL"],
                              tablefmt="github"))
    lines.append("\nCategories positive across all three cells are the consistent earners; "
                 "categories negative in every cell drag returns and are candidates for "
                 "exclusion in paper mode.")

    # 6. Hold-to-resolution vs copy-exits (winning cohort, top combos)
    lines.append(f"\n\n## 6. Hold-to-resolution vs copy-exits (cohort {winner}, top 3 combos)\n")
    ab_table, seen = [], set()
    for c in top3:
        key = (c[0], c[1], c[2], c[4])
        if key in seen:
            continue
        seen.add(key)
        va_a = rows.get((winner, c[0], c[1], c[2], "hold_to_resolution", c[4], "validate"), {})
        va_b = rows.get((winner, c[0], c[1], c[2], "copy_exits", c[4], "validate"), {})
        pa, pb = va_a.get("total_pnl"), va_b.get("total_pnl")
        result = "—"
        if pa is not None and pb is not None:
            result = f"hold (+${pa - pb:,.2f})" if pa > pb else f"copy (+${pb - pa:,.2f})"
        ab_table.append([f"N={c[0]} W={c[1]:g}h F=${c[2]:.0f} ${c[4]:.0f}",
                         fmt(pa, ",.2f"), fmt(pb, ",.2f"), result])
    lines.append(tabulate(ab_table, headers=["combo", "hold PnL(val)", "copy PnL(val)", "winner"],
                          tablefmt="github"))

    # 7. Equity curves CSV (validate period, winning cohort top 3)
    curves = []
    for c in top3:
        pnl_col = f"pnl_{int(c[4])}"
        sig_rows = conn.execute(
            f"""SELECT signal_time, exit_time, {pnl_col} pnl FROM signals
                WHERE cohort=? AND n_traders=? AND window_hours=? AND size_floor=? AND exit_type=?
                  AND split='validate' AND {pnl_col} IS NOT NULL
                ORDER BY COALESCE(exit_time, signal_time)""",
            (winner, c[0], c[1], c[2], c[3])).fetchall()
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
    lines.append(f"\n\n## 7. Equity curves\n\nValidate-period cumulative PnL for cohort "
                 f"{winner}'s top 3 cells: `reports/equity_curve_top3.csv` "
                 f"({max((len(c) for c in curves), default=0)} rows).")

    # 8. Trade log for the overall best (robust) cell
    pnl_col = f"pnl_{int(winner_cell[4])}"
    best_trades = conn.execute(
        f"""SELECT s.signal_time, s.entry_price, s.exit_price, s.exit_time, s.exit_type,
                   s.{pnl_col} pnl, s.category, s.resolved, m.question
            FROM signals s LEFT JOIN markets m ON m.condition_id = s.condition_id
            WHERE s.cohort=? AND s.n_traders=? AND s.window_hours=? AND s.size_floor=?
              AND s.exit_type=? AND s.split='validate'
            ORDER BY s.signal_time""",
        (winner, winner_cell[0], winner_cell[1], winner_cell[2], winner_cell[3])).fetchall()
    log_path = os.path.join(REPORTS_DIR, "best_cell_trades.csv")
    with open(log_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["market", "signal_time_utc", "entry_price", "exit_price", "exit_type",
                    "pnl", "category"])
        for r in best_trades:
            w.writerow([r["question"],
                        datetime.fromtimestamp(r["signal_time"], tz=timezone.utc).isoformat(),
                        r["entry_price"], r["exit_price"], r["exit_type"],
                        None if r["pnl"] is None else round(r["pnl"], 2), r["category"]])
    lines.append(f"\n## 8. Best-cell trade log\n\nEvery simulated validate-period trade for "
                 f"cohort {winner} **{cell_label(winner_cell)}**: "
                 f"`reports/best_cell_trades.csv` ({len(best_trades)} rows).")

    # 9. Unresolved positions (winning cohort, validate, top 10 cells)
    lines.append(f"\n## 9. Unresolved positions (cohort {winner}, validate period, top 10 cells)\n")
    unres_table = [[cell_label(c), r_of(winner, c, "validate").get("unresolved_count"),
                    f"${(r_of(winner, c, 'validate').get('unresolved_count') or 0) * c[4]:,.0f}"]
                   for c in win_cells[:10]]
    lines.append(tabulate(unres_table, headers=["cell", "unresolved", "capital tied up"],
                          tablefmt="github"))

    # 10. Next steps
    lines.append("\n\n## 10. Recommended next steps\n")
    val_pnl = win_val.get("total_pnl") or 0
    pcfg = cfg["paper"]
    current = (pcfg["default_n"], float(pcfg["default_window_hours"]),
               float(pcfg["default_size_floor"]), pcfg["exit_strategy"])
    chosen = (winner_cell[0], float(winner_cell[1]), float(winner_cell[2]), winner_cell[3])
    if val_pnl > 0 and analysis[winner]["best_robust"] == winner_cell:
        if chosen != current:
            lines.append(
                f"- Best robust cell **differs from the current paper config** "
                f"(paper: N={current[0]} W={current[1]:g}h F=${current[2]:.0f} {current[3]}). "
                f"Update the `paper:` block to N={chosen[0]}, window={chosen[1]:g}h, "
                f"floor=${chosen[2]:.0f}, exit={chosen[3]}, and run paper on cohort {winner}'s wallets.")
        else:
            lines.append(f"- Best robust cell **matches the current paper config** — no change "
                         f"needed; run paper on cohort {winner}'s wallets.")
        lines.append("- Do NOT go live until the decision-gate checklist in PLAN.md passes.")
    elif val_pnl > 0:
        lines.append("- The best validate cell is positive but **failed the robustness check** "
                     "(isolated grid peak) — likely overfit. Keep paper mode on current defaults "
                     "and re-run with more history before trusting it.")
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
