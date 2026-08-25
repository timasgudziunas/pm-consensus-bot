"""Pre-registered wallet-edge persistence checkpoint (owner-directed, 2026-08-17).

Overdue Aug 5-11 main checkpoint from `reports/proposals/
quality_weighted_cohort_proposal.md` (§C.3 + Amendment). Question: does each
cohort-B wallet's PAST raw copyable edge predict its edge on the held-out
JULY+ forward window? Methodology is fixed and pre-registered as "exactly as
implemented in src/wallet_quality.py" -- this script reuses that module's
position-building and gate machinery, it does not reimplement it.

Pipeline:
  1. build_positions(cutoff=persistence_checkpoint.window_end_utc) into its
     own scratch DB (data/pc_positions.sqlite, NOT wq_positions.sqlite).
  2. Split each wallet's RESOLVED positions into PAST (first_buy before
     past_end_utc) / FORWARD (first_buy >= forward_start_utc); drop
     June-initiated positions entirely (collider risk from June-leaderboard
     cohort selection).
  3. Eligible wallets: >= min_resolved_past AND >= min_resolved_forward.
  4. Pre-registered PASS requires all three: (a) Spearman(past edge, forward
     edge) > 0, permutation p < 0.05; (b) top-vs-bottom quintile forward-edge
     gap > 0; (c) same Spearman test on the per-share edge variant. Anything
     less is INCONCLUSIVE (the expected outcome under weak persistence, see
     the report's quoted expected-outcome clause -- never call it FAIL).

Run: python src/persistence_checkpoint.py
Writes: reports/persistence_checkpoint.md, reports/persistence_checkpoint_wallets.csv
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
import wallet_quality as wq
from data_api import load_config

log = logging.getLogger("persistence_checkpoint")

PC_SCRATCH_PATH = os.path.join(db.REPO_ROOT, "data", "pc_positions.sqlite")
REPORT_MD = os.path.join(db.REPO_ROOT, "reports", "persistence_checkpoint.md")
CSV_PATH = os.path.join(db.REPO_ROOT, "reports", "persistence_checkpoint_wallets.csv")

# power-model reference rows (reports/proposals/persistence_power_and_strict45_analysis.md)
POWER_TABLE = [
    ("Aug 11", 218, 84, "83%"),
    ("Aug 18", 222, 91, "84%"),
]


def _ts(iso: str) -> int:
    """Parse a config ISO-8601 UTC timestamp ('...Z') to epoch seconds."""
    return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp())


def fmt(v, spec, na="-"):
    return format(v, spec) if v is not None else na


def median(xs: list):
    xs = sorted(xs)
    n = len(xs)
    if n == 0:
        return None
    mid = n // 2
    return xs[mid] if n % 2 else (xs[mid - 1] + xs[mid]) / 2


# ---------- split PAST / FORWARD / dropped ----------

def load_split(pc: dict) -> tuple:
    """Load RESOLVED positions from the scratch DB and split by first_buy_ts.

    Returns (by_wallet, robustness) where by_wallet[w] = {"past": [...],
    "forward": [...], "dropped": [...]} (each a list of position dicts)."""
    past_end = _ts(pc["past_end_utc"])
    forward_start = _ts(pc["forward_start_utc"])
    scratch = sqlite3.connect(f"file:{PC_SCRATCH_PATH}?mode=ro", uri=True)
    scratch.row_factory = sqlite3.Row
    rows = scratch.execute("SELECT * FROM positions WHERE status='RESOLVED'").fetchall()
    scratch.close()

    by_wallet: dict = defaultdict(lambda: {"past": [], "forward": [], "dropped": []})
    for r in rows:
        p = dict(r)
        fb = p["first_buy_ts"]
        if fb is None:
            continue  # RESOLVED positions always have a first buy; guard only
        if fb < past_end:
            by_wallet[p["wallet"]]["past"].append(p)
        elif fb >= forward_start:
            by_wallet[p["wallet"]]["forward"].append(p)
        else:
            by_wallet[p["wallet"]]["dropped"].append(p)

    total_past = sum(len(d["past"]) for d in by_wallet.values())
    addon_past = sum(1 for d in by_wallet.values() for p in d["past"]
                     if p["last_ts"] and p["last_ts"] >= past_end)
    total_dropped = sum(len(d["dropped"]) for d in by_wallet.values())
    robustness = {"total_past": total_past, "addon_past": addon_past,
                  "total_dropped_june": total_dropped, "past_end": past_end,
                  "forward_start": forward_start}
    log.info("split: %d past (%d with post-%s add-on trades), %d forward, %d dropped (June)",
             total_past, addon_past, pc["past_end_utc"][:10],
             sum(len(d["forward"]) for d in by_wallet.values()), total_dropped)
    return dict(by_wallet), robustness


def eligible_wallets(by_wallet: dict, min_past: int, min_forward: int) -> dict:
    return {w: d for w, d in by_wallet.items()
            if len(d["past"]) >= min_past and len(d["forward"]) >= min_forward}


def edge_dicts(elig: dict) -> tuple:
    """wallet -> raw edge and per-share edge, past and forward sides."""
    ep = {w: wq.edge(d["past"]) for w, d in elig.items()}
    ef = {w: wq.edge(d["forward"]) for w, d in elig.items()}
    epsp = {w: wq.edge_per_share(d["past"]) for w, d in elig.items()}
    epsf = {w: wq.edge_per_share(d["forward"]) for w, d in elig.items()}
    return ep, ef, epsp, epsf


def load_categories(wallets: list) -> dict:
    """wallet -> first tag of its wallets.category comma-list, or None."""
    live = wq.connect_ro()
    ph = ",".join("?" * len(wallets))
    out = {}
    for r in live.execute(f"SELECT address, category FROM wallets WHERE address IN ({ph})", wallets):
        cat = (r["category"] or "").split(",")[0].strip()
        out[r["address"]] = cat or None
    live.close()
    return out


# ---------- verification ----------

def spot_check(cutoff_ts: int, wallet: str, condition_id: str, stored: dict) -> dict:
    """Recompute pnl_hold/stake for one (wallet, condition_id) straight from
    raw trades + market outcome_prices, independent of build_positions, and
    diff against the scratch DB's stored value."""
    live = wq.connect_ro()
    rows = live.execute(
        """SELECT side, outcome_index, size_usd, price FROM trades
           WHERE wallet=? AND condition_id=? AND timestamp<? AND outcome_index>=0 AND price>0""",
        (wallet, condition_id, cutoff_ts)).fetchall()
    m = live.execute("SELECT outcome_prices FROM markets WHERE condition_id=?",
                     (condition_id,)).fetchone()
    live.close()
    buy_usd, buy_sh = 0.0, defaultdict(float)
    for r in rows:
        if r["side"] == "BUY":
            buy_usd += r["size_usd"]
            buy_sh[r["outcome_index"]] += r["size_usd"] / r["price"]
    payouts = [float(x) for x in json.loads(m["outcome_prices"])]
    pnl_hold = sum(bsh * payouts[oi] for oi, bsh in buy_sh.items() if oi < len(payouts)) - buy_usd
    diff = pnl_hold - stored["pnl_hold_usd"]
    return {"recomputed_pnl_hold": pnl_hold, "stored_pnl_hold": stored["pnl_hold_usd"],
            "diff": diff, "matches_to_cent": abs(diff) < 0.005}


def rerun_stability_check(edge_past: dict, edge_forward: dict, seed: int, iters: int) -> bool:
    """Run the primary gate twice with the same seed; verify identical output
    (permutation test determinism -- required for reruns to reproduce)."""
    g1 = wq.predictive_gate(edge_past, edge_forward, seed, iters=iters)
    g2 = wq.predictive_gate(edge_past, edge_forward, seed, iters=iters)
    stable = (g1.get("spearman_rho") == g2.get("spearman_rho")
              and g1.get("perm_p_one_sided") == g2.get("perm_p_one_sided"))
    log.info("rerun-stability check (same seed twice): %s", "PASS" if stable else "FAIL")
    return stable


def coverage_stats(cfg: dict, cutoff_ts: int) -> tuple:
    """(n_misses_recorded, pct_missing_excl_misses) for cohort-B markets up to
    cutoff_ts -- the verification stat the fetch step is supposed to have
    driven near zero."""
    misses_path = os.path.join(
        db.REPO_ROOT, *cfg["analysis"]["wallet_quality"]["fetch"]["misses_file"].split("/"))
    misses: set = set()
    if os.path.exists(misses_path):
        with open(misses_path, encoding="utf-8") as f:
            misses = set(json.load(f))
    live = wq.connect_ro()
    wset = sorted(db.get_cohort_wallets(live, cfg["paper"]["watchlist_cohort"]))
    ph = ",".join("?" * len(wset))
    total = live.execute(
        f"""SELECT COUNT(DISTINCT t.condition_id) FROM trades t
            WHERE t.wallet IN ({ph}) AND t.timestamp < ?
              AND t.condition_id IS NOT NULL AND t.condition_id != ''""",
        [*wset, cutoff_ts]).fetchone()[0]
    missing_ids = [r[0] for r in live.execute(
        f"""SELECT DISTINCT t.condition_id FROM trades t
            WHERE t.wallet IN ({ph}) AND t.timestamp < ?
              AND t.condition_id IS NOT NULL AND t.condition_id != ''
              AND NOT EXISTS (SELECT 1 FROM markets m WHERE m.condition_id = t.condition_id)""",
        [*wset, cutoff_ts]).fetchall()]
    live.close()
    missing_excl_misses = [c for c in missing_ids if c not in misses]
    pct = (len(missing_excl_misses) / total * 100) if total else 0.0
    log.info("coverage: %d/%d condition_ids still missing (excl. %d recorded misses) = %.3f%%",
             len(missing_excl_misses), total, len(misses), pct)
    return len(misses), pct


# ---------- report ----------

def build_report(pc: dict, by_wallet: dict, robustness: dict, elig: dict,
                 gate_raw: dict, gate_share: dict, verdict: str,
                 sens: dict, per_cat: list, spot: list, stable: bool,
                 crit_a: bool, crit_b: bool, crit_c: bool, n_misses: int,
                 coverage_missing_pct: float) -> list:
    n = len(elig)
    fwd_ks = sorted(len(d["forward"]) for d in elig.values())
    med_k = median(fwd_ks)

    L = ["# Pre-registered wallet-edge persistence checkpoint (Aug 2026, overdue Aug 5-11)",
         "",
         f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}. "
         "Engine: `src/persistence_checkpoint.py` (reuses `src/wallet_quality.py` "
         "position-building and gate machinery). Full per-wallet table: "
         "`reports/persistence_checkpoint_wallets.csv`. Pre-registration: "
         "`reports/proposals/quality_weighted_cohort_proposal.md` §C.3 + Amendment.",
         "",
         "## Question",
         "",
         "Does each cohort-B wallet's PAST raw copyable edge (per-(wallet, "
         "market) net position, pnl_hold = buy_shares×payout − buy_usd, "
         "edge = pnl/stake) predict its edge on the held-out JULY+ forward "
         "window? This is the pre-registered re-validation gate for whether "
         "wallet-level quality is a selectable signal at all — it decides "
         "nothing about live trading directly (see proposal §C.4-5 for what a "
         "PASS/INCONCLUSIVE implies).",
         "",
         "## Executive summary",
         "",
         f"**Verdict: {verdict}**",
         "",
         f"- (a) Spearman(past edge, forward edge) = {fmt(gate_raw.get('spearman_rho'), '+.3f')}, "
         f"one-sided permutation p = {fmt(gate_raw.get('perm_p_one_sided'), '.4f')} (n={gate_raw.get('n')}) "
         f"-> {'MET' if crit_a else 'not met'}",
         f"- (b) top-vs-bottom quintile forward-edge gap = {fmt(gate_raw.get('quintile_gap'), '+.3f')}/$ "
         f"-> {'MET' if crit_b else 'not met'}",
         f"- (c) per-share Spearman = {fmt(gate_share.get('spearman_rho'), '+.3f')}, "
         f"p = {fmt(gate_share.get('perm_p_one_sided'), '.4f')} (n={gate_share.get('n')}) "
         f"-> {'MET' if crit_c else 'not met'}",
         f"- Achieved sample: n={n} eligible wallets, median forward k={med_k} resolved "
         "positions (see Power section below for how this compares to the design target).",
         ""]

    if verdict != "PASS":
        L += ["**\"Cannot distinguish from noise\" is the EXPECTED outcome under weak-but-real "
              "persistence, not a failed experiment or a failed strategy** (pre-registration "
              "Amendment, clause 2). It keeps the status quo (cohort B, category-based "
              "selection, unchanged) and justifies neither a quality tilt (proposal §C.4) "
              "nor a cohort cut (proposal §B). Do not re-shop metrics or re-run this test "
              "with different criteria based on this result.", ""]

    L += ["## Pre-registered pass criteria (quoted, before results)",
          "",
          "> Pre-registered pass criteria (all three):",
          "> - raw-edge persistence Spearman > 0 with permutation p < 0.05;",
          "> - top-vs-bottom quintile held-out edge gap > 0;",
          "> - result survives the per-share (price-controlled) variant.",
          "",
          "> \"Cannot distinguish from noise\" is an EXPECTED outcome, not a failed "
          "experiment or a failed strategy ... An inconclusive result keeps option A "
          "(status quo) and does NOT justify either a quality tilt (§C.4) or a "
          "cohort cut (§B).",
          "",
          "— `reports/proposals/quality_weighted_cohort_proposal.md` §C.3 + Amendment clause 2.",
          ""]

    L += ["## Results",
          "",
          "| criterion | value | threshold | met? |",
          "|---|---|---|---|",
          f"| (a) raw edge Spearman rho | {fmt(gate_raw.get('spearman_rho'), '+.4f')} | > 0 | {'yes' if (gate_raw.get('spearman_rho') or 0) > 0 else 'no'} |",
          f"| (a) raw edge permutation p (one-sided, {pc['permutation_iterations']:,} perms) | {fmt(gate_raw.get('perm_p_one_sided'), '.4f')} | < 0.05 | {'yes' if crit_a else 'no'} |",
          f"| (b) top-bottom quintile forward-edge gap | {fmt(gate_raw.get('quintile_gap'), '+.4f')}/$ | > 0 | {'yes' if crit_b else 'no'} |",
          f"|   top quintile mean forward edge | {fmt(gate_raw.get('top_quintile_h2_edge'), '+.4f')}/$ | - | - |",
          f"|   bottom quintile mean forward edge | {fmt(gate_raw.get('bottom_quintile_h2_edge'), '+.4f')}/$ | - | - |",
          f"| (c) per-share Spearman rho | {fmt(gate_share.get('spearman_rho'), '+.4f')} | > 0 | {'yes' if (gate_share.get('spearman_rho') or 0) > 0 else 'no'} |",
          f"| (c) per-share permutation p | {fmt(gate_share.get('perm_p_one_sided'), '.4f')} | < 0.05 | {'yes' if crit_c else 'no'} |",
          "",
          f"Sample: n={n} eligible wallets (>= {pc['min_resolved_past']} resolved PAST positions "
          f"AND >= {pc['min_resolved_forward']} resolved FORWARD positions). "
          f"Seed {pc['seed']} (config `analysis.persistence_checkpoint.seed`) — rerun-stability "
          f"check (same seed twice): **{'PASS' if stable else 'FAIL — investigate before trusting p-values'}**.",
          ""]

    L += ["## Achieved sample vs. the power model's design target",
          "",
          "From `reports/proposals/persistence_power_and_strict45_analysis.md` "
          "(Monte-Carlo power model, calibrated to the observed sigma_T=0.048 "
          "same-period reliability):",
          "",
          "| date | design n | design median forward k | best-case power (rho_true=1.0) |",
          "|---|---|---|---|"]
    for label, dn, dk, dp in POWER_TABLE:
        L.append(f"| {label} | {dn} | {dk} | {dp} |")
    L += ["",
          f"**Actual (this run, window end {pc['window_end_utc'][:10]}): n={n}, median forward k={med_k}.**",
          f"{'At or above' if n >= 218 and (med_k or 0) >= 84 else 'Below'} the Aug 11-18 design "
          "range, so the test ran " +
          ("at approximately designed power (~83-84% IF true persistence is strong, "
           "rho_true~=1.0; only ~54-61% if rho_true~=0.7; ~27-31% if rho_true~=0.4, the level "
           "implied by the original +0.08 point estimate)."
           if n >= 200 else
           "below designed power — treat a non-pass as even less informative than the "
           "pre-registered expected-outcome clause already assumes."),
          "",
          "This is a power statement, not a hedge on the verdict above: the pre-registered "
          "criteria and their thresholds are exactly as stated regardless of achieved power. "
          "It only calibrates how much weight an INCONCLUSIVE result should carry.",
          ""]

    L += ["## Secondary analyses (NOT decision criteria)", ""]
    L += ["### Per-category Spearman slices (wallets.category, first tag)", "",
          "| category | n | Spearman rho (raw edge) | permutation p |",
          "|---|---|---|---|"]
    for cat, cn, crho, cp in per_cat:
        L.append(f"| {cat} | {cn} | {fmt(crho, '+.3f')} | {fmt(cp, '.4f')} |")
    L += ["", "Sample sizes per category are small; these are descriptive slices, not "
          "independent tests.", ""]

    L += ["### Sensitivity: rerun at min_resolved_forward=20", "",
          f"n={sens.get('n')}, Spearman rho={fmt(sens.get('spearman_rho'), '+.4f')}, "
          f"p={fmt(sens.get('perm_p_one_sided'), '.4f')}, "
          f"quintile gap={fmt(sens.get('quintile_gap'), '+.4f')}/$.",
          ""]

    L += ["### Quintile gap on the per-share metric", "",
          f"top quintile mean forward edge_per_share={fmt(gate_share.get('top_quintile_h2_edge'), '+.4f')}, "
          f"bottom quintile={fmt(gate_share.get('bottom_quintile_h2_edge'), '+.4f')}, "
          f"gap={fmt(gate_share.get('quintile_gap'), '+.4f')} (n={gate_share.get('n')}).",
          ""]

    L += ["## Verification", "", "Spot-checked accounting (independent recomputation from raw "
          "trades + outcome_prices vs the scratch DB's stored value):", ""]
    for s in spot:
        L.append(f"- wallet `{s['wallet'][:10]}...`, market `{s['condition_id'][:10]}...`: "
                 f"recomputed pnl_hold={s['recomputed_pnl_hold']:.4f}, stored={s['stored_pnl_hold']:.4f}, "
                 f"diff={s['diff']:.6f} -> {'matches to the cent' if s['matches_to_cent'] else '**MISMATCH**'}")
    L += ["", f"Rerun-stability (same seed twice, identical rho/p): "
          f"**{'confirmed' if stable else 'FAILED — see above'}**.", ""]

    L += ["## Robustness footnote: PAST positions with post-window add-on trades", "",
          f"{robustness['addon_past']} of {robustness['total_past']} PAST positions "
          f"(first buy before {pc['past_end_utc'][:10]}) have a most-recent trade on or after "
          f"{pc['past_end_utc'][:10]} — i.e. the wallet added to that position after the PAST "
          "window nominally ended (positions are aggregated over their whole trade history up "
          f"to {pc['window_end_utc'][:10]}, not truncated at past_end_utc, per spec). "
          f"{robustness['total_dropped_june']} June-initiated positions were dropped entirely "
          "(first buy in June — collider risk from June-leaderboard cohort selection).", ""]

    L += ["## Standing caveats (do not paper over these)", "",
          "- **WC-era sports composition of the first ~2.5 weeks of the forward window.** "
          "The forward window opens 2026-07-01; the World Cup ran through ~Jul 19 (handoff "
          "§0a). Forward-side sports positions opened before ~Jul 19 are WC-inflated, not "
          "steady-state — any per-category sports read above inherits that.",
          "- **~24.5h ingestion outage, 2026-07-16 02:52 UTC → 2026-07-17 03:27 UTC**, "
          "recovered only about half that window's trades (~10.2k captured vs ~20k/day "
          "typical, per handoff §0b). Forward positions with a first buy on 2026-07-16 may "
          "be undercounted or missing entirely — this is a coverage gap, not a signal.",
          "- **The trades feed is TAKER-ONLY** (median cohort wallet ~84% maker). The "
          "copyable-edge metric used here (pnl_hold over visible taker BUYs) is immune by "
          "construction — it is exactly what the bot could copy — but \"wallet activity\" "
          "in this data is not the wallet's full activity.",
          "- **Survivorship bias**: cohort B was selected on the June leaderboard. PAST-side "
          "edge levels for June-and-earlier are inflated by that selection; June-initiated "
          "positions are dropped entirely from both sides for exactly this reason, but the "
          "PAST window itself (pre-June) still describes wallets that went on to be selected, "
          "not a random sample.",
          "- **Recently-opened forward positions are disproportionately unresolved** — a "
          "position opened days before window_end_utc has not had time to resolve, and slow "
          "categories (e.g. TECH, median resolution lag ~21 days per the July power-model "
          "analysis) are under-represented in the resolved forward set relative to fast "
          "categories (POLITICS/SPORTS). The per-category slice above should be read with "
          "this skew in mind, not as representative category composition.",
          f"- **Markets Gamma no longer serves** are recorded in `data/wq_fetch_misses.json` "
          f"({n_misses:,} condition_ids as of this run) and excluded from both position-"
          f"building and the coverage denominator below — they are neither PAST nor FORWARD "
          "data, they simply cannot be priced.",
          f"- **Market-metadata coverage**: after the extended fetch/refresh pass, "
          f"{coverage_missing_pct:.2f}% of condition_ids traded by cohort-B wallets up to "
          f"{pc['window_end_utc'][:10]} still have no markets row (excluding recorded "
          "misses). See the fetch log for the run that produced this.",
          ""]

    return L


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    cfg = load_config()
    pc = cfg["analysis"]["persistence_checkpoint"]
    cutoff_ts = _ts(pc["window_end_utc"])
    seed = int(pc["seed"])
    iters = int(pc["permutation_iterations"])
    min_past = int(pc["min_resolved_past"])
    min_fwd = int(pc["min_resolved_forward"])

    log.info("building positions (cutoff=%s) into %s ...", pc["window_end_utc"], PC_SCRATCH_PATH)
    wq.build_positions(cutoff_ts=cutoff_ts, scratch_path=PC_SCRATCH_PATH)

    by_wallet, robustness = load_split(pc)
    elig = eligible_wallets(by_wallet, min_past, min_fwd)
    log.info("eligible wallets (>=%d past, >=%d forward): %d / %d cohort-B wallets with any "
             "resolved positions", min_past, min_fwd, len(elig), len(by_wallet))

    edge_past, edge_forward, eps_past, eps_forward = edge_dicts(elig)

    gate_raw = wq.predictive_gate(edge_past, edge_forward, seed ^ 0xA5A5A5, iters=iters)
    gate_share = wq.predictive_gate(eps_past, eps_forward, seed ^ 0x5A5A5A, iters=iters)

    def _crit(gate: dict) -> bool:
        rho, p = gate.get("spearman_rho"), gate.get("perm_p_one_sided")
        return rho is not None and rho > 0 and p is not None and p < 0.05

    crit_a = _crit(gate_raw)
    crit_b = (gate_raw.get("quintile_gap") or 0) > 0
    crit_c = _crit(gate_share)
    verdict = "PASS" if (crit_a and crit_b and crit_c) else "INCONCLUSIVE"
    log.info("VERDICT: %s (a=%s b=%s c=%s)", verdict, crit_a, crit_b, crit_c)

    stable = rerun_stability_check(edge_past, edge_forward, seed ^ 0xA5A5A5, iters)

    # secondary: per-category slices
    cats = load_categories(list(elig.keys()))
    by_cat = defaultdict(list)
    for w in elig:
        by_cat[cats.get(w) or "UNTAGGED"].append(w)
    per_cat = []
    for cat, ws in sorted(by_cat.items(), key=lambda kv: -len(kv[1])):
        pairs = [(edge_past[w], edge_forward[w]) for w in ws]
        if len(pairs) >= 3:
            rho = wq.spearman([p[0] for p in pairs], [p[1] for p in pairs])
            # deterministic per-category seed offset (builtin hash() is
            # randomized per-process by default -- would break rerun-stability)
            cat_offset = sum(ord(c) for c in cat) & 0x7FFFFFFF
            g = wq.raw_gate(pairs, seed ^ cat_offset, "cat", iters=iters)
            per_cat.append((cat, len(pairs), rho, g.get("cat_perm_p_one_sided")))
        else:
            per_cat.append((cat, len(pairs), None, None))

    # secondary: sensitivity rerun at min_resolved_forward=20
    elig20 = eligible_wallets(by_wallet, min_past, 20)
    ep20, ef20, _, _ = edge_dicts(elig20)
    sens = wq.predictive_gate(ep20, ef20, seed ^ 0xC3C3C3, iters=iters)

    # verification: spot-check 2 positions independently
    spot = []
    if elig:
        w_list = sorted(elig.keys())
        picks = [(w_list[0], by_wallet[w_list[0]]["past"][0]),
                 (w_list[-1], by_wallet[w_list[-1]]["forward"][0])]
        for w, pos in picks:
            spot.append(dict(wallet=w, condition_id=pos["condition_id"],
                             **spot_check(cutoff_ts, w, pos["condition_id"], pos)))
            log.info("spot check %s / %s: %s", w[:10], pos["condition_id"][:10],
                     "OK" if spot[-1]["matches_to_cent"] else "MISMATCH")

    n_misses, coverage_missing_pct = coverage_stats(cfg, cutoff_ts)

    lines = build_report(pc, by_wallet, robustness, elig, gate_raw, gate_share, verdict,
                         sens, per_cat, spot, stable, crit_a, crit_b, crit_c,
                         n_misses, coverage_missing_pct)
    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    log.info("wrote %s", REPORT_MD)

    with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
        wcsv = csv.writer(f)
        wcsv.writerow(["wallet", "category", "n_past", "n_forward", "stake_past", "stake_forward",
                       "edge_past", "edge_forward", "edge_per_share_past", "edge_per_share_forward"])
        for w in sorted(elig.keys()):
            d = elig[w]
            wcsv.writerow([
                w, cats.get(w) or "", len(d["past"]), len(d["forward"]),
                round(sum(p["stake_usd"] for p in d["past"]), 2),
                round(sum(p["stake_usd"] for p in d["forward"]), 2),
                round(edge_past[w], 6) if edge_past[w] is not None else "",
                round(edge_forward[w], 6) if edge_forward[w] is not None else "",
                round(eps_past[w], 6) if eps_past[w] is not None else "",
                round(eps_forward[w], 6) if eps_forward[w] is not None else "",
            ])
    log.info("wrote %s (%d rows)", CSV_PATH, len(elig))


if __name__ == "__main__":
    main()
