"""Monte-Carlo power analysis for the persistence re-validation checkpoint.

Produced the tables in reports/proposals/persistence_power_and_strict45_analysis.md
(2026-07-07). Analysis-only: read-only on the DBs, touches nothing live.
Needs numpy (present in the miniconda env; deliberately NOT added to
requirements.txt — this is not part of the bot).

Model: wallet i has true copyable edge T_i, cross-wallet SD sigma_T. An edge
measured over k positions carries noise SE_i * sqrt(n_i / k), with SE_i from
the wallet's bootstrap CI in reports/wallet_quality_scores.csv. The forward
window's true edge correlates with the past true edge at rho_true. Test =
one-sided Spearman > 0 at p < 0.05 (Fisher z), the pre-registered criterion.
sigma_T is calibrated so that a half-vs-half simulation reproduces the
OBSERVED same-period market-split reliability (rho ~ +0.22, n=221), then held
fixed. Forward accrual: each wallet's own Jun-15-30 weekly position rate
until the WC ends (2026-07-19), sports-tagged wallets reverting to their May
rate afterwards; discounted by the empirical resolution-lag CDF.

The constants below are frozen documentation of the published analysis, not
tunables — hence not in config.yaml.

Run: python src/persistence_power_mc.py
"""
import csv
import math
import os
import sqlite3
from datetime import datetime, timezone

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCORES_CSV = os.path.join(REPO_ROOT, "reports", "wallet_quality_scores.csv")
WQ_DB = os.path.join(REPO_ROOT, "data", "wq_positions.sqlite")

SIGMA_T = 0.048          # calibrated: reproduces observed half-split rho ~ 0.22
SIGMA_T_BRACKET = (0.040, 0.048, 0.060)
RHO_TRUE_SCENARIOS = (1.0, 0.7, 0.4)   # 0.4 = de-attenuated current point estimate
K_MIN = 10               # min resolved forward positions to enter the test
N_SIMS = 1500
ALPHA_Z = 1.645          # one-sided 5%
FWD_START = datetime(2026, 7, 2, tzinfo=timezone.utc)   # post-history-cutoff
WC_END = datetime(2026, 7, 19, tzinfo=timezone.utc)
RERUN_DATES = ("2026-07-21", "2026-07-28", "2026-08-04", "2026-08-11",
               "2026-08-18", "2026-09-01", "2026-09-15", "2026-10-01")

rng = np.random.default_rng(20260707)


def _ts(s: str) -> int:
    return int(datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp())


def load_wallets() -> list[dict]:
    """Per-wallet edge estimate, bootstrap SE, n, and sports tag from the scores CSV."""
    out = []
    for r in csv.DictReader(open(SCORES_CSV, encoding="utf-8")):
        try:
            edge, lo, hi, n = float(r["edge"]), float(r["ci_lo"]), float(r["ci_hi"]), int(r["n_resolved"])
        except ValueError:
            continue
        if n < 4 or hi <= lo:
            continue
        out.append({"w": r["wallet"], "edge": edge, "se": (hi - lo) / 3.92, "n": n,
                    "sports": "SPORTS" in r["categories"]})
    return out


def load_rates_and_lags(conn: sqlite3.Connection) -> tuple[dict, dict, np.ndarray]:
    """Weekly accrual rates (May, Jun-15-30) per wallet + June resolution-lag sample."""
    def rates(lo: int, hi: int) -> dict:
        weeks = (hi - lo) / 604800
        return {w: n / weeks for w, n in conn.execute(
            "SELECT wallet, COUNT(*) FROM positions WHERE first_buy_ts>=? AND first_buy_ts<? GROUP BY wallet",
            (lo, hi))}
    r_may = rates(_ts("2026-05-01"), _ts("2026-06-01"))
    r_jun = rates(_ts("2026-06-15"), _ts("2026-07-01"))
    lags = np.array([max(0.0, x) for (x,) in conn.execute(
        "SELECT (end_ts-first_buy_ts)/86400.0 FROM positions "
        "WHERE status='RESOLVED' AND end_ts IS NOT NULL AND first_buy_ts>=? AND first_buy_ts<?",
        (_ts("2026-06-01"), _ts("2026-07-01")))])
    return r_may, r_jun, lags


def projected_k(wobj: dict, d_end: datetime, r_may: dict, r_jun: dict,
                lags: np.ndarray) -> float:
    """Expected RESOLVED forward positions for a wallet by d_end."""
    rj = r_jun.get(wobj["w"], 0.0)
    rp = r_may.get(wobj["w"], 0.0) if wobj["sports"] else rj
    wc_wk = max(0.0, (min(d_end, WC_END) - FWD_START).days / 7)
    post_wk = max(0.0, (d_end - max(FWD_START, WC_END)).days / 7)
    k = rj * wc_wk + rp * post_wk
    total_days = (d_end - FWD_START).days
    if total_days <= 0 or k == 0:
        return 0.0
    ages = np.linspace(0, total_days, 24)
    frac = float(np.mean([np.mean(lags <= a) for a in ages]))
    return k * frac


def spearman_power(wallets: list[dict], k_map: dict, rho_true: float,
                   sigma_t: float, n_sims: int = N_SIMS,
                   k_min: int = K_MIN) -> tuple[float, float, int]:
    """(power, mean observed Spearman rho, n included) for one scenario."""
    sel = [w for w in wallets if k_map[w["w"]] >= k_min]
    if len(sel) < 10:
        return 0.0, 0.0, len(sel)
    se_past = np.array([w["se"] for w in sel])
    se_fwd = np.array([w["se"] * math.sqrt(w["n"] / k_map[w["w"]]) for w in sel])
    n = len(sel)
    rejects, rhos = 0, []
    for _ in range(n_sims):
        t_past = rng.normal(0, sigma_t, n)
        t_fwd = rho_true * t_past + math.sqrt(max(0.0, 1 - rho_true ** 2)) * rng.normal(0, sigma_t, n)
        past = t_past + rng.normal(0, se_past)
        fwd = t_fwd + rng.normal(0, se_fwd)
        rp = np.argsort(np.argsort(past)).astype(float)
        rf = np.argsort(np.argsort(fwd)).astype(float)
        rho = float(np.corrcoef(rp, rf)[0, 1])
        rhos.append(rho)
        if 0.5 * math.log((1 + rho) / (1 - rho)) * math.sqrt(n - 3) > ALPHA_Z:
            rejects += 1
    return rejects / n_sims, float(np.mean(rhos)), n


def main() -> None:
    """Calibration check, power-by-date sweep, and sigma_T sensitivity bracket."""
    wallets = load_wallets()
    conn = sqlite3.connect(f"file:{WQ_DB.replace(os.sep, '/')}?mode=ro", uri=True)
    r_may, r_jun, lags = load_rates_and_lags(conn)
    conn.close()
    print(f"wallets with usable edge+CI: {len(wallets)}")

    half_k = {w["w"]: w["n"] / 2 for w in wallets}
    p, rho, n = spearman_power(wallets, half_k, 1.0, SIGMA_T, n_sims=400, k_min=8)
    print(f"calibration (half-vs-half, rho_true=1, sigma_T={SIGMA_T}): "
          f"model rho={rho:+.3f} vs observed +0.22 (n={n})\n")

    print(f"{'date':<11} {'wk':>4} {'n':>4} {'floor':>6} | power "
          + "  ".join(f"rt={rt}" for rt in RHO_TRUE_SCENARIOS))
    for ds in RERUN_DATES:
        d = datetime.fromisoformat(ds).replace(tzinfo=timezone.utc)
        k_map = {w["w"]: projected_k(w, d, r_may, r_jun, lags) for w in wallets}
        n_inc = sum(1 for w in wallets if k_map[w["w"]] >= K_MIN)
        floor = 2.486 / math.sqrt(max(n_inc - 3, 1))
        cells = []
        for rt in RHO_TRUE_SCENARIOS:
            p, rho, _ = spearman_power(wallets, k_map, rt, SIGMA_T)
            cells.append(f"{p:.2f}(rho{rho:+.2f})")
        wk = (d - FWD_START).days / 7
        print(f"{ds:<11} {wk:4.1f} {n_inc:4d} {floor:6.3f} | " + "  ".join(cells))

    print("\nsigma_T sensitivity at 2026-08-04:")
    d = datetime(2026, 8, 4, tzinfo=timezone.utc)
    k_map = {w["w"]: projected_k(w, d, r_may, r_jun, lags) for w in wallets}
    for sig in SIGMA_T_BRACKET:
        for rt in (1.0, 0.4):
            p, rho, n = spearman_power(wallets, k_map, rt, sig)
            print(f"  sigma={sig:.3f} rho_true={rt}: power={p:.2f}, E[obs rho]={rho:+.3f}, n={n}")


if __name__ == "__main__":
    main()
