"""Wallet-level skill verification (owner-directed overnight task, 2026-07-07).

Question: for each cohort-B watchlist wallet INDIVIDUALLY, is there evidence of
a consistent, persistent edge — or is inclusion driven by a lucky run/period?

Pipeline (all read-only against the live DB; scratch cache in its own file):
  stage positions  — per-(wallet, market) NET position PnL over resolved
                     markets, cached to data/wq_positions.sqlite
  stage tests      — per-wallet consistency battery: time split-half,
                     walk-forward windows, market-split, bootstrap CI on the
                     wallet's own positions, concentration/breadth, win rate
  stage score      — composite quality score + the H1-score->H2-edge
                     predictive-validity gate (decides whether the score is
                     distinguishable from noise at this sample size)

Method decisions fixed BEFORE results (see reports/autonomous_log_2026-07-07.md):
unit of observation = market-level net position, not trade; edge = PnL per
dollar of buy stake; positions timestamped at first buy; markets with negative
net inventory beyond tolerance (pre-history positions) excluded as dirty.

Run: python src/wallet_quality.py [positions|tests|score|all]
"""
import json
import logging
import math
import os
import random
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone

import db
from data_api import load_config

log = logging.getLogger("wallet_quality")

SCRATCH_PATH = os.path.join(db.REPO_ROOT, "data", "wq_positions.sqlite")

SCRATCH_SCHEMA = """
CREATE TABLE IF NOT EXISTS positions (
    wallet        TEXT,
    condition_id  TEXT,
    first_buy_ts  INTEGER,
    last_ts       INTEGER,
    stake_usd     REAL,     -- total buy stake
    max_buy_usd   REAL,     -- largest single buy (signal-eligibility vs size floor)
    shares_bought REAL,     -- total shares bought (for per-share edge: pnl_hold/shares)
    pnl_hold_usd  REAL,     -- PRIMARY: copyable edge = buy_shares*payout - buy_usd
                            -- (what following this wallet's visible taker buys to
                            -- resolution would have earned; immune to the
                            -- taker-only feed hole because the bot can only
                            -- ever copy visible buys)
    pnl_cash_usd  REAL,     -- SECONDARY: sells - buys + net_shares*payout;
                            -- systematically wrong for maker-exit wallets
                            -- (the /trades feed is taker-only) — NULL when
                            -- inventory accounting is inconsistent (cash_dirty)
    n_trades      INTEGER,
    status        TEXT,     -- RESOLVED / UNRESOLVED / UNKNOWN_MARKET / NO_BUYS
    cash_dirty    INTEGER,  -- 1 = cash accounting inconsistent (pre-history or maker inventory)
    volume        REAL,     -- market lifetime volume (proxy, fetch-time snapshot)
    category      TEXT,     -- market category if known, else NULL
    end_ts        INTEGER,  -- market end date epoch if parseable
    PRIMARY KEY (wallet, condition_id)
);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS wallet_tests (
    wallet TEXT PRIMARY KEY,
    payload TEXT              -- JSON blob of the full test battery
);
"""


def connect_ro() -> sqlite3.Connection:
    """Read-only connection to the live DB (never blocks paper.py's writer)."""
    conn = sqlite3.connect(f"file:{db.DB_PATH}?mode=ro", uri=True, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def connect_scratch() -> sqlite3.Connection:
    conn = sqlite3.connect(SCRATCH_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCRATCH_SCHEMA)
    return conn


def market_end_ts(m: dict):
    """Epoch of market end_date, or None (mirrors backtest.market_end_ts intent)."""
    ed = m.get("end_date")
    if not ed:
        return None
    try:
        return int(datetime.fromisoformat(ed.replace("Z", "+00:00")).timestamp())
    except ValueError:
        return None


# ---------- stage: positions ----------

def build_positions() -> None:
    """Aggregate trades into per-(wallet, market) net positions and price them."""
    cfg = load_config()
    wq = cfg["analysis"]["wallet_quality"]
    cutoff = int(datetime.fromisoformat(
        cfg["analysis"]["window_end_utc"].replace("Z", "+00:00")).timestamp())
    live = connect_ro()
    wset = sorted(db.get_cohort_wallets(live, cfg["paper"]["watchlist_cohort"]))
    ph = ",".join("?" * len(wset))

    log.info("aggregating trades for %d wallets (cutoff %s)...", len(wset),
             cfg["analysis"]["window_end_utc"])
    # one pass: per (wallet, condition, outcome, side) sums; shares = usd/price
    agg: dict = defaultdict(lambda: {"buy_usd": 0.0, "sell_usd": 0.0, "max_buy": 0.0,
                                     "buy_sh": defaultdict(float), "sell_sh": defaultdict(float),
                                     "first_buy": None, "last": 0, "n": 0})
    n_rows = 0
    for r in live.execute(
            f"""SELECT wallet, condition_id, outcome_index, side, size_usd, price, timestamp
                FROM trades WHERE wallet IN ({ph}) AND timestamp < ? AND outcome_index >= 0
                  AND price > 0""",
            [*wset, cutoff]):
        a = agg[(r["wallet"], r["condition_id"])]
        sh = r["size_usd"] / r["price"]
        if r["side"] == "BUY":
            a["buy_usd"] += r["size_usd"]
            a["max_buy"] = max(a["max_buy"], r["size_usd"])
            a["buy_sh"][r["outcome_index"]] += sh
            if a["first_buy"] is None or r["timestamp"] < a["first_buy"]:
                a["first_buy"] = r["timestamp"]
        else:
            a["sell_usd"] += r["size_usd"]
            a["sell_sh"][r["outcome_index"]] += sh
        a["last"] = max(a["last"], r["timestamp"])
        a["n"] += 1
        n_rows += 1
        if n_rows % 500000 == 0:
            log.info("  ...%dM trades aggregated, %d positions", n_rows // 1000000, len(agg))
    log.info("aggregated %d trades into %d (wallet, market) positions", n_rows, len(agg))

    markets = {r["condition_id"]: dict(r) for r in live.execute(
        "SELECT condition_id, closed, outcome_prices, volume, category, end_date FROM markets")}
    live.close()

    tol = float(wq["negative_inventory_tolerance"])
    out_rows = []
    for (wallet, cid), a in agg.items():
        m = markets.get(cid)
        stake = a["buy_usd"]
        status, pnl_hold, pnl_cash, cash_dirty = "RESOLVED", None, None, 0
        vol = cat = ets = None
        if m:
            vol, cat, ets = m.get("volume"), m.get("category"), market_end_ts(m)
        if stake <= 0:
            status = "NO_BUYS"        # sells only = pre-history/maker inventory; nothing copyable
        elif not m:
            status = "UNKNOWN_MARKET"
        elif not m.get("closed"):
            status = "UNRESOLVED"
        else:
            try:
                payouts = [float(x) for x in json.loads(m["outcome_prices"])]
            except (TypeError, ValueError):
                payouts = None
            if payouts is None or any(oi >= len(payouts) for oi in a["buy_sh"]):
                status = "UNRESOLVED"
            else:
                # PRIMARY: copyable edge — buys held to resolution, sells ignored
                pnl_hold = sum(bsh * payouts[oi] for oi, bsh in a["buy_sh"].items()) - a["buy_usd"]
                # SECONDARY: cash-flow PnL, only when inventory is consistent
                pnl_cash = a["sell_usd"] - a["buy_usd"]
                for oi, bsh in a["buy_sh"].items():
                    net = bsh - a["sell_sh"].get(oi, 0.0)
                    if net < -tol * max(bsh, 1e-9):
                        cash_dirty = 1
                        break
                    pnl_cash += max(net, 0.0) * payouts[oi]
                total_bought = sum(a["buy_sh"].values())
                if any(oi not in a["buy_sh"] and ssh > tol * max(total_bought, 1e-9)
                       for oi, ssh in a["sell_sh"].items()):
                    cash_dirty = 1
                if cash_dirty:
                    pnl_cash = None
        out_rows.append((wallet, cid, a["first_buy"], a["last"], stake, a["max_buy"],
                         sum(a["buy_sh"].values()), pnl_hold, pnl_cash,
                         a["n"], status, cash_dirty, vol, cat, ets))

    scratch = connect_scratch()
    scratch.execute("DROP TABLE IF EXISTS positions")
    scratch.executescript(SCRATCH_SCHEMA)
    scratch.executemany(
        "INSERT INTO positions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", out_rows)
    scratch.execute("INSERT OR REPLACE INTO meta VALUES ('positions_built_at', ?)",
                    (datetime.now(timezone.utc).isoformat(),))
    scratch.commit()
    by_status = scratch.execute(
        "SELECT status, COUNT(*), SUM(stake_usd) FROM positions GROUP BY status").fetchall()
    for r in by_status:
        log.info("positions %s: n=%d stake=$%.0f", r[0], r[1], r[2] or 0)
    scratch.close()


# ---------- stage: tests ----------

def edge(ps: list) -> float:
    """Copyable-edge PnL per dollar of buy stake; None if no stake."""
    stake = sum(p["stake_usd"] for p in ps)
    return (sum(p["pnl_hold_usd"] for p in ps) / stake) if stake > 0 else None


def edge_per_share(ps: list):
    """Stake-weighted per-share edge (payout - price); price-level comparable."""
    sh = sum(p["shares_bought"] for p in ps)
    return (sum(p["pnl_hold_usd"] for p in ps) / sh) if sh > 0 else None


def cash_edge(ps: list):
    """Cash-flow PnL/$ over positions with consistent accounting only."""
    ok = [p for p in ps if p["pnl_cash_usd"] is not None]
    stake = sum(p["stake_usd"] for p in ok)
    return (sum(p["pnl_cash_usd"] for p in ok) / stake) if stake > 0 else None


def win_rate(ps: list):
    return (sum(1 for p in ps if p["pnl_hold_usd"] > 0) / len(ps)) if ps else None


def bootstrap_edge_ci(ps: list, iters: int, seed: int):
    """Seeded percentile bootstrap CI on PnL/$ over positions."""
    n = len(ps)
    if n < 3:
        return None
    rng = random.Random(seed)
    vals = []
    pnl = [p["pnl_hold_usd"] for p in ps]
    stk = [p["stake_usd"] for p in ps]
    for _ in range(iters):
        s_pnl = s_stk = 0.0
        for _ in range(n):
            i = rng.randrange(n)
            s_pnl += pnl[i]
            s_stk += stk[i]
        if s_stk > 0:
            vals.append(s_pnl / s_stk)
    if not vals:
        return None
    vals.sort()
    return (vals[int(0.025 * len(vals))], vals[int(0.975 * len(vals)) - 1])


def wallet_battery(ps: list, wq: dict, seed: int) -> dict:
    """Full consistency battery for one wallet's resolved positions."""
    ps = sorted(ps, key=lambda p: p["first_buy_ts"] or 0)
    n = len(ps)
    out: dict = {"n_resolved": n,
                 "stake_total": sum(p["stake_usd"] for p in ps),
                 "pnl_total": sum(p["pnl_hold_usd"] for p in ps),
                 "edge": edge(ps), "edge_per_share": edge_per_share(ps),
                 "win_rate": win_rate(ps),
                 "edge_cash": cash_edge(ps),
                 "cash_ok_frac": (sum(1 for p in ps if p["pnl_cash_usd"] is not None) / len(ps))
                                 if ps else None}
    if n < int(wq["min_resolved_markets_any"]):
        out["verdict"] = "UNTESTABLE"
        return out

    span_days = ((ps[-1]["first_buy_ts"] or 0) - (ps[0]["first_buy_ts"] or 0)) / 86400
    out["span_days"] = round(span_days, 1)

    # time split-half at the median position (equal-n halves)
    can_time_split = (n >= int(wq["min_resolved_markets_split"])
                      and span_days >= float(wq["min_span_days_split"]))
    out["time_split_attempted"] = can_time_split
    if can_time_split:
        h1, h2 = ps[:n // 2], ps[n // 2:]
        out["time_split"] = {
            "h1": {"n": len(h1), "edge": edge(h1), "win_rate": win_rate(h1),
                   "end": datetime.fromtimestamp(h1[-1]["first_buy_ts"], tz=timezone.utc).date().isoformat()},
            "h2": {"n": len(h2), "edge": edge(h2), "win_rate": win_rate(h2)},
            "replicates": (edge(h1) or 0) > 0 and (edge(h2) or 0) > 0,
        }

    # walk-forward: equal time windows over the wallet's own span
    nw = int(wq["walk_forward_windows"])
    t0, t1 = ps[0]["first_buy_ts"], ps[-1]["first_buy_ts"] + 1
    wf = []
    if span_days >= float(wq["min_span_days_split"]):
        step = max((t1 - t0) // nw, 1)
        for wi in range(nw):
            chunk = [p for p in ps if t0 + wi * step <= p["first_buy_ts"] < t0 + (wi + 1) * step]
            wf.append({"n": len(chunk), "edge": edge(chunk)})
        judged = [w for w in wf if w["n"] >= 5]
        out["walk_forward"] = {
            "windows": wf, "judged": len(judged),
            "positive": sum(1 for w in judged if (w["edge"] or 0) > 0),
        }

    # market-split (time-independent): alternate positions by condition_id hash
    a = [p for p in ps if int(p["condition_id"][-4:], 16) % 2 == 0]
    b = [p for p in ps if int(p["condition_id"][-4:], 16) % 2 == 1]
    out["market_split"] = {
        "a": {"n": len(a), "edge": edge(a)}, "b": {"n": len(b), "edge": edge(b)},
        "replicates": (edge(a) or 0) > 0 and (edge(b) or 0) > 0,
    }

    # bootstrap CI on the wallet's own positions
    ci = bootstrap_edge_ci(ps, int(wq["bootstrap_iterations"]), seed)
    out["edge_ci"] = ci
    out["ci_excludes_zero"] = bool(ci and ci[0] > 0)

    # concentration / breadth: does the edge survive removing the top winners?
    k = int(wq["concentration_top_k"])
    winners = sorted(ps, key=lambda p: -p["pnl_hold_usd"])
    pos_pnl = sum(p["pnl_hold_usd"] for p in ps if p["pnl_hold_usd"] > 0)
    top_k = winners[:k]
    rest = winners[k:]
    out["concentration"] = {
        "top_k_share_of_gross_wins": (sum(p["pnl_hold_usd"] for p in top_k if p["pnl_hold_usd"] > 0) / pos_pnl)
                                     if pos_pnl > 0 else None,
        "edge_without_top_k": edge(rest),
        "broad": (edge(rest) or 0) > 0,
    }
    out["verdict"] = "TESTED"
    return out


def run_tests() -> None:
    """Run the battery for every wallet; store JSON blobs in the scratch DB."""
    cfg = load_config()
    wq = cfg["analysis"]["wallet_quality"]
    scratch = connect_scratch()
    rows = scratch.execute(
        "SELECT * FROM positions WHERE status='RESOLVED' ORDER BY wallet").fetchall()
    by_wallet: dict = defaultdict(list)
    for r in rows:
        by_wallet[r["wallet"]].append(dict(r))
    # coverage denominators (all statuses)
    cov = {r["wallet"]: dict(r) for r in scratch.execute(
        """SELECT wallet, COUNT(*) n_all, SUM(stake_usd) stake_all,
                  SUM(CASE WHEN status='RESOLVED' THEN stake_usd ELSE 0 END) stake_res,
                  SUM(CASE WHEN status='UNKNOWN_MARKET' THEN stake_usd ELSE 0 END) stake_unk
           FROM positions GROUP BY wallet""")}
    base_seed = int(wq["bootstrap_seed"])
    scratch.execute("DELETE FROM wallet_tests")
    done = 0
    for wallet, ps in sorted(by_wallet.items()):
        seed = base_seed ^ (int(wallet[-8:], 16) & 0x7FFFFFFF)
        battery = wallet_battery(ps, wq, seed)
        c = cov.get(wallet, {})
        battery["coverage"] = {
            "markets_any": c.get("n_all"),
            "stake_resolved_frac": (c["stake_res"] / c["stake_all"]) if c.get("stake_all") else None,
            "stake_unknown_frac": (c["stake_unk"] / c["stake_all"]) if c.get("stake_all") else None,
        }
        scratch.execute("INSERT OR REPLACE INTO wallet_tests VALUES (?, ?)",
                        (wallet, json.dumps(battery)))
        done += 1
        if done % 50 == 0:
            log.info("tested %d/%d wallets", done, len(by_wallet))
    scratch.execute("INSERT OR REPLACE INTO meta VALUES ('tests_built_at', ?)",
                    (datetime.now(timezone.utc).isoformat(),))
    scratch.commit()
    log.info("battery done for %d wallets", done)
    scratch.close()


# ---------- stage: score ----------

def percentile_ranks(values: dict) -> dict:
    """Map key->value to key->rank in [0,1] (None values get no rank)."""
    keyed = [(k, v) for k, v in values.items() if v is not None]
    keyed.sort(key=lambda kv: kv[1])
    n = len(keyed)
    return {k: (i + 0.5) / n for i, (k, v) in enumerate(keyed)}


def component_scores(t: dict) -> dict:
    """Raw component values for one wallet's battery (higher = better)."""
    comp = {}
    ts = t.get("time_split")
    ms = t.get("market_split")
    # worst-half edge: the weakest link across whichever split was possible
    halves = []
    if ts:
        halves += [ts["h1"]["edge"], ts["h2"]["edge"]]
    if ms and ms["a"]["n"] >= 5 and ms["b"]["n"] >= 5:
        halves += [ms["a"]["edge"], ms["b"]["edge"]]
    comp["worst_split_edge"] = min([h for h in halves if h is not None], default=None)
    ci = t.get("edge_ci")
    comp["ci_lower"] = ci[0] if ci else None
    conc = t.get("concentration") or {}
    comp["edge_without_winners"] = conc.get("edge_without_top_k")
    wf = t.get("walk_forward")
    comp["wf_positive_frac"] = (wf["positive"] / wf["judged"]) if wf and wf["judged"] >= 3 else None
    comp["win_rate"] = t.get("win_rate")
    return comp


def run_score() -> dict:
    """Composite score + the predictive-validity gate. Returns summary dict."""
    cfg = load_config()
    wq = cfg["analysis"]["wallet_quality"]
    scratch = connect_scratch()
    tests = {r["wallet"]: json.loads(r["payload"])
             for r in scratch.execute("SELECT * FROM wallet_tests")}
    pos_rows = scratch.execute(
        "SELECT * FROM positions WHERE status='RESOLVED'").fetchall()
    by_wallet: dict = defaultdict(list)
    for r in pos_rows:
        by_wallet[r["wallet"]].append(dict(r))

    # composite score over full-history batteries
    comps = {w: component_scores(t) for w, t in tests.items() if t["verdict"] == "TESTED"}
    names = ["worst_split_edge", "ci_lower", "edge_without_winners", "wf_positive_frac", "win_rate"]
    ranks = {nm: percentile_ranks({w: c[nm] for w, c in comps.items()}) for nm in names}
    scores = {}
    for w, c in comps.items():
        rs = [ranks[nm][w] for nm in names if w in ranks[nm]]
        scores[w] = {"score": sum(rs) / len(rs) if rs else None,
                     "n_components": len(rs), **c}

    # predictive gates: score each wallet on one data half, test its edge on
    # the held-out half. Three designs:
    #   persistence_full      — time halves over the full window (collider-
    #                           biased by June cohort selection; kept for
    #                           comparison, labeled as such)
    #   persistence_preselect — time halves over PRE-June data only (clean
    #                           persistence test)
    #   reliability_market    — market-hash halves, same period (is the edge
    #                           even measurable, ignoring persistence?)
    base_seed = int(wq["bootstrap_seed"])
    presel_ts = int(datetime.fromisoformat(
        wq["selection_window_start_utc"].replace("Z", "+00:00")).timestamp())
    min_n = int(wq["min_resolved_markets_split"])
    min_span = float(wq["min_span_days_split"])

    def split_pairs(mode: str, cutoff_ts=None) -> dict:
        """wallet -> (train_positions, test_positions) under a split design."""
        out = {}
        for w, ps in by_wallet.items():
            ps = sorted(ps, key=lambda p: p["first_buy_ts"] or 0)
            if cutoff_ts is not None:
                ps = [p for p in ps if p["first_buy_ts"] and p["first_buy_ts"] < cutoff_ts]
            if len(ps) < min_n:
                continue
            if mode == "time":
                span = (ps[-1]["first_buy_ts"] - ps[0]["first_buy_ts"]) / 86400
                if span < min_span:
                    continue
                out[w] = (ps[:len(ps) // 2], ps[len(ps) // 2:])
            else:  # market-hash split
                a = [p for p in ps if int(p["condition_id"][-4:], 16) % 2 == 0]
                b = [p for p in ps if int(p["condition_id"][-4:], 16) % 2 == 1]
                if len(a) >= min_n // 2 and len(b) >= min_n // 2:
                    out[w] = (a, b)
        return out

    def gate_for(pairs: dict, tag: int) -> dict:
        h1_comps, test_edge, train_edge = {}, {}, {}
        for w, (tr, te) in pairs.items():
            seed = base_seed ^ (int(w[-8:], 16) & 0x7FFFFFFF) ^ tag
            b1 = wallet_battery(tr, wq, seed)
            if b1["verdict"] != "TESTED":
                continue
            h1_comps[w] = component_scores(b1)
            train_edge[w] = edge(tr)
            test_edge[w] = edge(te)
        h1_ranks = {nm: percentile_ranks({w: c[nm] for w, c in h1_comps.items()})
                    for nm in names}
        h1_score = {}
        for w, c in h1_comps.items():
            rs = [h1_ranks[nm][w] for nm in names if w in h1_ranks[nm]]
            if rs:
                h1_score[w] = sum(rs) / len(rs)
        g = predictive_gate(h1_score, test_edge, base_seed)
        raw = [(train_edge[w], test_edge[w]) for w in h1_score
               if test_edge.get(w) is not None and train_edge.get(w) is not None]
        g.update(raw_gate(raw, base_seed, "raw_edge"))
        raw_ps = [(edge_per_share(pairs[w][0]), edge_per_share(pairs[w][1]))
                  for w in h1_score
                  if edge_per_share(pairs[w][0]) is not None
                  and edge_per_share(pairs[w][1]) is not None]
        g.update(raw_gate(raw_ps, base_seed, "raw_edge_per_share"))
        # per-wallet halves so the report can slice by category / draw scatters
        g["per_wallet"] = {w: {"train": train_edge.get(w), "test": test_edge.get(w),
                               "score": h1_score.get(w)} for w in h1_score}
        return g

    gates = {
        "persistence_full": gate_for(split_pairs("time"), 0x5A5A5A),
        "persistence_preselect": gate_for(split_pairs("time", cutoff_ts=presel_ts), 0x3C3C3C),
        "reliability_market": gate_for(split_pairs("market"), 0x0F0F0F),
    }
    payload = {"scores": scores, "gates": gates}
    scratch.execute("INSERT OR REPLACE INTO meta VALUES ('score_payload', ?)",
                    (json.dumps(payload),))
    scratch.commit()
    scratch.close()
    log.info("gates: %s", json.dumps({k: {kk: vv for kk, vv in g.items() if kk != "per_wallet"}
                                      for k, g in gates.items()}))
    return payload


def spearman(xs: list, ys: list):
    """Spearman rank correlation (ties -> average ranks)."""
    n = len(xs)
    if n < 3:
        return None
    def ranks(vals):
        order = sorted(range(n), key=lambda i: vals[i])
        rk = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and vals[order[j + 1]] == vals[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for t in range(i, j + 1):
                rk[order[t]] = avg
            i = j + 1
        return rk
    rx, ry = ranks(xs), ranks(ys)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((rx[i] - mx) * (ry[i] - my) for i in range(n))
    den = (sum((r - mx) ** 2 for r in rx) * sum((r - my) ** 2 for r in ry)) ** 0.5
    return num / den if den else None


def raw_gate(pairs: list, seed: int, prefix: str) -> dict:
    """Spearman + permutation p for raw train->test edge pairs."""
    if len(pairs) < 3:
        return {prefix + "_spearman": None}
    xs, ys = [p[0] for p in pairs], [p[1] for p in pairs]
    rho = spearman(xs, ys)
    rng = random.Random(seed)
    ys_p = ys[:]
    hits = 0
    iters = 10000
    for _ in range(iters):
        rng.shuffle(ys_p)
        r = spearman(xs, ys_p)
        if r is not None and r >= rho:
            hits += 1
    return {prefix + "_spearman": rho, prefix + "_perm_p_one_sided": hits / iters,
            prefix + "_n": len(pairs)}


def predictive_gate(h1_score: dict, h2_edge: dict, seed: int) -> dict:
    """Does the H1-only score predict H2 edge across wallets?

    Reports Spearman rho with a permutation p-value (seeded) and the
    top-vs-bottom-quintile H2 edge gap. This is the decision input for
    whether wallet discovery on this metric is justified at all."""
    ws = [w for w in h1_score if h2_edge.get(w) is not None]
    xs = [h1_score[w] for w in ws]
    ys = [h2_edge[w] for w in ws]
    rho = spearman(xs, ys)
    if rho is None:
        return {"n": len(ws), "verdict": "INSUFFICIENT"}
    rng = random.Random(seed)
    perm = 0
    iters = 10000
    ys_p = ys[:]
    for _ in range(iters):
        rng.shuffle(ys_p)
        r = spearman(xs, ys_p)
        if r is not None and r >= rho:
            perm += 1
    p = perm / iters
    order = sorted(ws, key=lambda w: h1_score[w])
    q = max(len(ws) // 5, 1)
    bot, top = order[:q], order[-q:]
    top_e = sum(h2_edge[w] for w in top) / len(top)
    bot_e = sum(h2_edge[w] for w in bot) / len(bot)
    return {"n": len(ws), "spearman_rho": rho, "perm_p_one_sided": p,
            "top_quintile_h2_edge": top_e, "bottom_quintile_h2_edge": bot_e,
            "quintile_gap": top_e - bot_e}


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    if stage in ("positions", "all"):
        build_positions()
    if stage in ("tests", "all"):
        run_tests()
    if stage in ("score", "all"):
        run_score()


if __name__ == "__main__":
    main()
