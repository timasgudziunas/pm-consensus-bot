"""Render wallet-quality analysis outputs (2026-07-07 overnight task).

Reads the scratch DB produced by wallet_quality.py (positions + per-wallet
test batteries + gate payload) plus the live wallets table (read-only), and
writes:
  reports/wallet_quality_analysis.md   — findings document
  reports/wallet_quality_scores.csv    — full per-wallet table, machine-readable

Verdict taxonomy (fixed before results):
  CONSISTENT            time-split replicates + bootstrap CI > 0 + edge survives
                        removing top-k winners
  REPLICATES_WEAK       both time halves positive, but CI includes 0 or edge
                        concentrated in few winners
  ONE_PERIOD            positive overall but only one time half positive
  NO_EDGE               copyable edge <= 0 overall
  *_YOUNG variants      wallet too young to time-split (sports cohort mostly):
                        same tests on a market-hash split within its window —
                        consistency evidence, NOT persistence evidence
  UNTESTABLE            fewer resolved positions than min_resolved_markets_any

Run: python src/wallet_quality_report.py
"""
import csv
import json
import logging
import os
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone

import db
from data_api import load_config
from wallet_quality import SCRATCH_PATH, connect_ro, spearman

log = logging.getLogger("wq_report")

REPORT_MD = os.path.join(db.REPO_ROOT, "reports", "wallet_quality_analysis.md")
SCORES_CSV = os.path.join(db.REPO_ROOT, "reports", "wallet_quality_scores.csv")


def fmt(v, spec, na="-"):
    return format(v, spec) if v is not None else na


def classify(t: dict) -> str:
    """Apply the pre-registered verdict taxonomy to one wallet battery."""
    if t["verdict"] == "UNTESTABLE":
        return "UNTESTABLE"
    if t["edge"] is None or t["edge"] <= 0:
        return "NO_EDGE"
    ts, ms = t.get("time_split"), t.get("market_split") or {}
    ci_pos = bool(t.get("ci_excludes_zero"))
    broad = bool((t.get("concentration") or {}).get("broad"))
    if ts:
        if ts["replicates"] and ci_pos and broad:
            return "CONSISTENT"
        if ts["replicates"]:
            return "REPLICATES_WEAK"
        return "ONE_PERIOD"
    if ms.get("replicates") and ci_pos and broad:
        return "CONSISTENT_YOUNG"
    if ms.get("replicates"):
        return "REPLICATES_WEAK_YOUNG"
    return "LUCKY_FEW_MARKETS"


def load_all(size_floor: float):
    scratch = sqlite3.connect(f"file:{SCRATCH_PATH}?mode=ro", uri=True)
    scratch.row_factory = sqlite3.Row
    tests = {r["wallet"]: json.loads(r["payload"])
             for r in scratch.execute("SELECT * FROM wallet_tests")}
    payload = json.loads(scratch.execute(
        "SELECT value FROM meta WHERE key='score_payload'").fetchone()["value"])
    built = {r["key"]: r["value"] for r in scratch.execute(
        "SELECT * FROM meta WHERE key LIKE '%built_at'")}

    # per-wallet structural stats from positions (resolved only)
    struct = {}
    for r in scratch.execute("""
            SELECT wallet, SUM(stake_usd) stake, SUM(shares_bought) shares,
                   COUNT(*) n, MIN(first_buy_ts) first_ts, MAX(first_buy_ts) last_ts,
                   AVG(stake_usd) mean_stake,
                   SUM(CASE WHEN max_buy_usd >= :floor THEN 1 ELSE 0 END) n_eligible,
                   SUM(CASE WHEN max_buy_usd >= :floor THEN pnl_hold_usd ELSE 0 END) p_eligible,
                   SUM(CASE WHEN max_buy_usd >= :floor THEN stake_usd ELSE 0 END) s_eligible
            FROM positions WHERE status='RESOLVED' GROUP BY wallet""",
            {"floor": size_floor}):
        struct[r["wallet"]] = dict(r)
    # medians need per-row values
    vols, stakes, holds = defaultdict(list), defaultdict(list), defaultdict(list)
    for r in scratch.execute("""SELECT wallet, stake_usd, volume, first_buy_ts, end_ts
                                FROM positions WHERE status='RESOLVED'"""):
        stakes[r["wallet"]].append(r["stake_usd"])
        if r["volume"] is not None:
            vols[r["wallet"]].append(r["volume"])
        if r["end_ts"] and r["first_buy_ts"] and r["end_ts"] > r["first_buy_ts"]:
            holds[r["wallet"]].append((r["end_ts"] - r["first_buy_ts"]) / 86400)

    def med(xs):
        xs = sorted(xs)
        return xs[len(xs) // 2] if xs else None
    for w, s in struct.items():
        s["med_stake"] = med(stakes[w])
        s["med_volume"] = med(vols[w])
        s["med_hold_days"] = med(holds[w])
        s["avg_entry_price"] = (s["stake"] / s["shares"]) if s["shares"] else None
    maker = {r["wallet"]: r["maker_share"] for r in scratch.execute(
        "SELECT wallet, maker_share FROM wallet_maker_share")}
    for w, s in struct.items():
        s["maker_share"] = maker.get(w)
    scratch.close()

    live = connect_ro()
    wallets = {r["address"]: dict(r) for r in live.execute(
        "SELECT * FROM wallets WHERE selected=1 AND (','||cohorts||',') LIKE '%,B,%'")}
    live.close()
    return tests, payload, struct, wallets, built


def build_rows(tests, payload, struct, wallets):
    scores = payload["scores"]
    rows = []
    for w, t in tests.items():
        wt = wallets.get(w, {})
        st = struct.get(w, {})
        sc = scores.get(w, {})
        ts = t.get("time_split") or {}
        ms = t.get("market_split") or {}
        wf = t.get("walk_forward") or {}
        conc = t.get("concentration") or {}
        ci = t.get("edge_ci") or (None, None)
        rows.append({
            "wallet": w, "username": (wt.get("username") or "")[:40],
            "categories": wt.get("category"), "cohorts": wt.get("cohorts"),
            "verdict": classify(t),
            "n_resolved": t.get("n_resolved"), "stake_usd": round(t.get("stake_total") or 0),
            "edge": t.get("edge"), "edge_per_share": t.get("edge_per_share"),
            "edge_cash": t.get("edge_cash"), "cash_ok_frac": t.get("cash_ok_frac"),
            "ci_lo": ci[0], "ci_hi": ci[1], "win_rate": t.get("win_rate"),
            "h1_edge": (ts.get("h1") or {}).get("edge"), "h2_edge": (ts.get("h2") or {}).get("edge"),
            "time_replicates": ts.get("replicates"),
            "mkt_a_edge": (ms.get("a") or {}).get("edge"), "mkt_b_edge": (ms.get("b") or {}).get("edge"),
            "mkt_replicates": ms.get("replicates"),
            "wf_positive": wf.get("positive"), "wf_judged": wf.get("judged"),
            "top3_win_share": conc.get("top_k_share_of_gross_wins"),
            "edge_wo_top3": conc.get("edge_without_top_k"),
            "span_days": t.get("span_days"),
            "score": sc.get("score"),
            "stake_resolved_frac": (t.get("coverage") or {}).get("stake_resolved_frac"),
            "avg_entry_price": st.get("avg_entry_price"),
            "med_stake": st.get("med_stake"), "med_volume": st.get("med_volume"),
            "med_hold_days": st.get("med_hold_days"), "maker_share": st.get("maker_share"),
            "n_eligible": st.get("n_eligible"),
            "edge_eligible": (st["p_eligible"] / st["s_eligible"])
                             if st.get("s_eligible") else None,
            "first_trade": datetime.fromtimestamp(st["first_ts"], tz=timezone.utc).date().isoformat()
                           if st.get("first_ts") else None,
        })
    rows.sort(key=lambda r: -(r["score"] if r["score"] is not None else -1))
    return rows


def correlates(rows) -> list:
    """Spearman of structural features vs copyable edge (full window)."""
    feats = ["avg_entry_price", "med_stake", "med_volume", "med_hold_days",
             "n_resolved", "span_days", "win_rate", "maker_share"]
    out = []
    for f in feats:
        pairs = [(r[f], r["edge"]) for r in rows
                 if r[f] is not None and r["edge"] is not None]
        out.append((f, len(pairs), spearman([p[0] for p in pairs], [p[1] for p in pairs])))
    return out


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cfg = load_config()
    wq = cfg["analysis"]["wallet_quality"]
    tests, payload, struct, wallets, built = load_all(float(cfg['paper']['default_size_floor']))
    rows = build_rows(tests, payload, struct, wallets)
    gates = payload["gates"]

    with open(SCORES_CSV, "w", encoding="utf-8", newline="") as f:
        wcsv = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        wcsv.writeheader()
        for r in rows:
            wcsv.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})
    log.info("wrote %s (%d rows)", SCORES_CSV, len(rows))

    by_verdict = defaultdict(list)
    for r in rows:
        by_verdict[r["verdict"]].append(r)
    # per-discovery-category verdict counts
    cats = sorted({c for r in rows for c in (r["categories"] or "").split(",") if c})
    verdict_order = ["CONSISTENT", "REPLICATES_WEAK", "ONE_PERIOD", "NO_EDGE",
                     "CONSISTENT_YOUNG", "REPLICATES_WEAK_YOUNG", "LUCKY_FEW_MARKETS",
                     "UNTESTABLE"]

    L = ["# Wallet-level skill verification — cohort B (250 wallets)",
         "",
         f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} "
         "(autonomous overnight session; owner-directed). Engine: "
         "`src/wallet_quality.py`; full per-wallet table: "
         "`reports/wallet_quality_scores.csv`; chronology & dead-ends: "
         "`reports/autonomous_log_2026-07-07.md`.",
         "",
         "## 0. Read this first — what the numbers can and cannot say",
         "",
         "- **Metric**: per-wallet *copyable entry edge* = stake-weighted "
         "(resolution payout − entry price) per dollar over the wallet's "
         "visible taker BUYs, aggregated to (wallet, market) positions. This "
         "is exactly what copying the wallet's buys and holding to resolution "
         "earns — it matches the live strategy and is immune to the "
         "taker-only feed hole (below).",
         "- **The /trades feed is TAKER-ONLY** (discovered tonight; "
         "`takerOnly=true` is the API default and all ingested history used "
         "it). Maker fills are invisible. Cash-flow PnL is therefore "
         "unreliable for passive-exit wallets and is reported only as a "
         "flagged secondary column. This also means paper's copy-exit "
         "detection is partially blind to maker exits — standing caveat, "
         "affects the copy_exits backtests too.",
         "- **Survivorship**: all 250 wallets were selected on this very "
         "window (June leaderboard). Edge LEVELS are inflated by "
         "construction; only cross-wallet separation, splits, and held-out "
         "tests are informative. Any persistence test whose outcome half "
         "includes June is collider-biased — the clean test excludes June "
         "from the outcome side.",
         "- **Price-level confound**: PnL/$ is not comparable across wallets "
         "with different entry-price habits (a 0.90-buyer can at most make "
         "+0.11/$; a 0.10-buyer up to +9/$). Per-share edge is reported "
         "alongside; correlate section quantifies the confound.",
         ""]

    # 1. coverage
    n_res = sum(r["n_resolved"] or 0 for r in rows)
    L += ["## 1. Data basis",
          "",
          f"- 250 cohort-B wallets, verified-full taker-trade history, trades "
          f"before {cfg['analysis']['window_end_utc']}.",
          f"- {n_res:,} resolved (wallet, market) positions; positions built "
          f"{built.get('positions_built_at', '?')[:16]}.",
          f"- Missing-market resolution fetch (wallet_quality_fetch.py) filled "
          "the market table for everything the cohort ever traded (see log); "
          "per-wallet resolved-stake coverage is in the CSV "
          "(`stake_resolved_frac`).",
          ""]

    # 2. verdicts
    L += ["## 2. Per-wallet consistency verdicts (P1)", "",
          "| verdict | wallets | median edge | median n | total stake $M |",
          "|---|---|---|---|---|"]
    for v in verdict_order:
        rs = by_verdict.get(v, [])
        if not rs:
            continue
        es = sorted(r["edge"] for r in rs if r["edge"] is not None)
        ns = sorted(r["n_resolved"] for r in rs)
        L.append(f"| {v} | {len(rs)} | "
                 f"{fmt(es[len(es)//2] if es else None, '+.3f')} | {ns[len(ns)//2]} | "
                 f"{sum(r['stake_usd'] for r in rs)/1e6:,.1f} |")
    L += ["",
          "`*_YOUNG` = too young to split by time (mostly the World-Cup-era "
          "sports cohort): market-split consistency within their single window "
          "is evidence of *breadth*, NOT of persistence across periods — "
          "explicitly per the task brief, no test was forced where data is "
          "insufficient.", ""]

    # 3. gates
    L += ["## 3. Is the quality signal real? The validation gates (P4 verdict)",
          "",
          "Design: score each wallet on half its data, test its edge on the "
          "held-out half, across wallets. Composite score = equal-weight "
          "percentile ranks of {worst-split edge, bootstrap CI lower bound, "
          "edge without top-3 winners, walk-forward positive fraction, win "
          "rate}. Raw edge = plain PnL/$ on the training half.",
          "",
          "| gate | n | composite→edge ρ (perm p) | raw edge ρ (perm p) | raw per-share ρ (p) | top−bottom quintile gap |",
          "|---|---|---|---|---|---|"]
    for name, g in gates.items():
        L.append(
            f"| {name} | {g.get('n')} | "
            f"{fmt(g.get('spearman_rho'), '+.3f')} (p={fmt(g.get('perm_p_one_sided'), '.3f')}) | "
            f"{fmt(g.get('raw_edge_spearman'), '+.3f')} (p={fmt(g.get('raw_edge_perm_p_one_sided'), '.3f')}) | "
            f"{fmt(g.get('raw_edge_per_share_spearman'), '+.3f')} (p={fmt(g.get('raw_edge_per_share_perm_p_one_sided'), '.3f')}) | "
            f"{fmt(g.get('quintile_gap'), '+.3f')}/$ |")
    import math
    L += ["", "Detectable effect at this sample size (80% power, 5% one-sided, "
          "Fisher approximation): " +
          "; ".join(f"{name} n={g.get('n')} → ρ ≥ {math.tanh(2.486 / math.sqrt(max(g.get('n', 4) - 3, 1))):.2f}"
                    for name, g in gates.items()) +
          ". Observed correlations below these thresholds are INDISTINGUISHABLE "
          "from zero — treat them as 'cannot tell', not as 'no effect'.", ""]
    L += ["",
          "- `persistence_full`: time halves over the whole window — "
          "**collider-biased** (June selection sits in the outcome half), "
          "shown for completeness only.",
          "- `persistence_preselect`: time halves over pre-June data only — "
          "the clean persistence test.",
          "- `reliability_market`: market-hash halves, same period — measures "
          "whether the edge is even measurable, ignoring persistence.", ""]

    # 4. rankings
    def table(rs, title, cols=14):
        T = [f"### {title}", "",
             "| # | wallet | user | cats | verdict | n | edge/$ | CI | wo-top3 | h1/h2 |",
             "|---|---|---|---|---|---|---|---|---|---|"]
        for i, r in enumerate(rs[:cols], 1):
            T.append(
                f"| {i} | {r['wallet'][:10]}… | {r['username'][:16]} | "
                f"{r['categories'] or '-'} | {r['verdict']} | {r['n_resolved']} | "
                f"{fmt(r['edge'], '+.3f')} | "
                f"[{fmt(r['ci_lo'], '+.2f')},{fmt(r['ci_hi'], '+.2f')}] | "
                f"{fmt(r['edge_wo_top3'], '+.3f')} | "
                f"{fmt(r['h1_edge'], '+.2f')}/{fmt(r['h2_edge'], '+.2f')} |")
        return T + [""]

    scored = [r for r in rows if r["score"] is not None]
    L += ["## 4. Rankings (P2) — with the §3 caveat that the composite score "
          "FAILED out-of-sample validation; ranks describe the past, they do "
          "not predict", ""]
    L += table(scored, "Top of composite score")
    L += table(sorted(scored, key=lambda r: (r["score"] or 0)), "Bottom of composite score")

    # 5. vs current cohort, per category
    L += ["## 5. Quality view vs current category-based cohort (P3)", ""]
    for cat in cats:
        crs = [r for r in rows if cat in (r["categories"] or "")]
        if not crs:
            continue
        vc = defaultdict(int)
        for r in crs:
            vc[r["verdict"]] += 1
        strong = [r for r in crs if r["verdict"] in ("CONSISTENT", "CONSISTENT_YOUNG")]
        L.append(f"- **{cat}** ({len(crs)} wallets): " +
                 ", ".join(f"{v} {vc[v]}" for v in verdict_order if vc.get(v)) +
                 (f". Individually consistent: " +
                  ", ".join(f"{r['username'] or r['wallet'][:8]} ({fmt(r['edge'], '+.2f')}/$, n={r['n_resolved']})"
                            for r in sorted(strong, key=lambda x: -(x['edge'] or 0))[:6])
                  if strong else ". **No individually consistent wallet.**"))
    L += [""]

    # 5b. which verdicts are actually driving live paper signals?
    live = connect_ro()
    contrib = defaultdict(lambda: {"signals": 0, "pnl": 0.0})
    for r in live.execute("""SELECT wallets, pnl_20, status FROM paper_trades
                             WHERE status IN ('OPEN','CLOSED')"""):
        try:
            ws = json.loads(r["wallets"])
        except (TypeError, ValueError):
            continue
        for w in ws:
            contrib[w]["signals"] += 1
            contrib[w]["pnl"] += (r["pnl_20"] or 0) / len(ws)
    live.close()
    verdict_of = {r["wallet"]: r["verdict"] for r in rows}
    agg = defaultdict(lambda: {"wallets": 0, "signals": 0, "pnl": 0.0})
    for w, c in contrib.items():
        v = verdict_of.get(w, "NOT_IN_COHORT_B")
        agg[v]["wallets"] += 1
        agg[v]["signals"] += c["signals"]
        agg[v]["pnl"] += c["pnl"]
    L += ["### Which verdict buckets drive the LIVE paper signals so far",
          "",
          "(participation-weighted attribution over filled paper positions; "
          "tiny n — descriptive only)", "",
          "| verdict | wallets contributing | signal participations | attributed PnL $ |",
          "|---|---|---|---|"]
    for v, a in sorted(agg.items(), key=lambda kv: -kv[1]["signals"]):
        L.append(f"| {v} | {a['wallets']} | {a['signals']} | {a['pnl']:+.2f} |")
    L += [""]

    # 6. correlates
    L += ["## 6. Structural correlates of edge (P4)", "",
          "| feature | n | Spearman vs edge/$ |", "|---|---|---|"]
    for f_, n_, rho in correlates(rows):
        L.append(f"| {f_} | {n_} | {fmt(rho, '+.3f')} |")
    L += [""]

    # 6b. price-level confound: pooled position PnL/$ by entry-price bucket
    scratch = sqlite3.connect(f"file:{SCRATCH_PATH}?mode=ro", uri=True)
    scratch.row_factory = sqlite3.Row
    L += ["### Entry-price bucket baseline (pooled positions — the confound itself)", "",
          "| avg entry price | positions | stake $M | pooled PnL/$ | pooled per-share |",
          "|---|---|---|---|---|"]
    for lo, hi in [(0, .1), (.1, .3), (.3, .5), (.5, .7), (.7, .9), (.9, 1.01)]:
        r = scratch.execute(
            """SELECT COUNT(*) n, SUM(stake_usd) s, SUM(pnl_hold_usd) p, SUM(shares_bought) sh
               FROM positions WHERE status='RESOLVED' AND shares_bought > 0
                 AND stake_usd/shares_bought >= ? AND stake_usd/shares_bought < ?""",
            (lo, hi)).fetchone()
        L.append(f"| {lo:.1f}–{hi:.1f} | {r['n'] or 0:,} | {(r['s'] or 0)/1e6:,.1f} | "
                 f"{fmt((r['p']/r['s']) if r['s'] else None, '+.3f')} | "
                 f"{fmt((r['p']/r['sh']) if r['sh'] else None, '+.3f')} |")
    scratch.close()
    L += [""]

    # 6c. per-category gates from stored per-wallet train/test halves
    wallet_cats = {r["wallet"]: (r["categories"] or "") for r in rows}
    L += ["### Gates sliced by discovery category (raw copyable edge, train→test ρ)", "",
          "| category | " + " | ".join(gates.keys()) + " |",
          "|---|" + "---|" * len(gates)]
    for cat in cats:
        cells = []
        for g in gates.values():
            pw = g.get("per_wallet") or {}
            pairs = [(v["train"], v["test"]) for w, v in pw.items()
                     if cat in wallet_cats.get(w, "")
                     and v["train"] is not None and v["test"] is not None]
            rho = spearman([p[0] for p in pairs], [p[1] for p in pairs])
            cells.append(f"{fmt(rho, '+.3f')} (n={len(pairs)})")
        L.append(f"| {cat} | " + " | ".join(cells) + " |")
    L += [""]

    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    log.info("wrote %s", REPORT_MD)


if __name__ == "__main__":
    main()
