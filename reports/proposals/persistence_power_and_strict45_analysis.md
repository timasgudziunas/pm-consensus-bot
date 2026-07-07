# Analysis: persistence-test power by date + strict-45 cohort paper preview

> **Owner decisions 2026-07-07 based on this doc:** (a) strict-45 paper cohort
> **DROPPED** — confirmed dead by replay (0–1 signals/month at live consensus
> settings); no further work unless the underlying wallet pool grows
> substantially. (b) Persistence pre-registration amended with a Jul 21–28
> early peek + expected-outcome clause (see
> `quality_weighted_cohort_proposal.md`). (c) New tracked checkpoints in
> PLAN.md: WC cliff ~Jul 19, post-WC steady-state read ~Jul 26–31.
>
> Written 2026-07-07 (owner-directed, analysis only — nothing live touched).
> Q1: what is the minimum new data to get the persistence test out of
> "undetectable" territory, and is the pre-registered ~Aug 5 checkpoint real?
> Q2: what would paper-trading the 45 strict-consistency wallets look like?
> Scripts: session scratchpad (power MC + signals.py replay); inputs:
> `reports/wallet_quality_scores.csv`, `data/wq_positions.sqlite`,
> `data/copybot.db`. All queries read-only.

## Q1. Power of the persistence re-validation, by calendar date

### Setup

The pre-registered test (quality_weighted_cohort_proposal.md): Spearman
correlation between each wallet's past raw copyable edge and its edge over the
July+ forward window, one-sided p<0.05. Current clean result: ρ=+0.08, p=0.15,
n=166, detectability floor ρ≈0.19.

### The binding constraint is NOT days of data

- **Resolution lag is a non-issue**: June-opened positions resolve at median
  0.7 days; 89% were resolved within the week. (TECH is the slow tail, median
  ~21d.)
- **Accrual is fast**: median cohort-B wallet opens ~14 positions/week now
  (WC era) and ~8/week pre-WC. Sports wallets: 25/wk during WC → ~3/wk after
  (May rate). By Aug 4 the median wallet already has ~73 resolved forward
  positions — the forward-side measurement is then nearly as reliable as it
  will ever get.
- **The real ceiling is the wallet count (≈250) plus noise on the *past*
  side.** The Fisher floor at n=230 is ρ≈0.165 and no amount of forward data
  lowers it. Past-side edge estimates are fixed forever at their current
  reliability.

### Monte-Carlo power model (show-your-work)

Per wallet: true edge T_i with cross-wallet SD σ_T; any k-position edge
measurement adds noise SE_i·√(n_i/k) using each wallet's bootstrap CI from the
scores CSV. Forward true edge correlates with past true edge at ρ_true.
Projected forward k per wallet: its own Jun-15–30 weekly rate until Jul 19,
then May rate for sports wallets (post-WC), discounted by the empirical
resolution-lag CDF. Test = one-sided Spearman p<0.05, power over 1,500 sims.

**Calibration**: σ_T=0.048 reproduces the *observed* same-period market-split
reliability (model ρ=0.23 vs observed +0.22, n=221). Held fixed thereafter.
Implication: de-attenuating the observed persistence point estimate (+0.08)
against the ~0.20–0.22 reliability ceiling implies **true persistence
ρ_true ≈ 0.4** if the point estimate is taken at face value.

### Results (n = wallets with ≥10 resolved forward positions)

| rerun date | fwd weeks | n | median k | Fisher floor | power if ρ_true=1.0 | ρ_true=0.7 | ρ_true=0.4 |
|---|---|---|---|---|---|---|---|
| Jul 21 | 2.7 | 199 | 48 | 0.178 | 64% (E ρ +0.14) | 44% | 24% |
| Jul 28 | 3.7 | 207 | 61 | 0.174 | 73% (+0.16) | 50% | 26% |
| **Aug 4** | 4.7 | 212 | 73 | 0.172 | **77% (+0.17)** | 54% | 28% |
| Aug 11 | 5.7 | 218 | 84 | 0.170 | 83% (+0.18) | 56% | 30% |
| Aug 18 | 6.7 | 222 | 91 | 0.168 | 84% (+0.19) | 61% | 31% |
| Sep 1 | 8.7 | 230 | 106 | 0.165 | 90% (+0.20) | 66% | 33% |
| Oct 1 | 13.0 | 233 | 145 | 0.164 | 94% (+0.22) | 71% | 39% |

Calibration sensitivity at Aug 4: best-case power 62–94% across σ_T
0.040–0.060; the ρ_true=0.4 row stays 22–38% everywhere.

### Answers

1. **Aug 5 is not a placeholder — it sits near the knee.** 80% best-case
   power is crossed ~Aug 8–11; Aug 4–5 gives ~77%. Reading 2–3 weeks earlier
   (Jul 21–28) still yields 64–73% best-case power — partially useful, but a
   pre-Jul-19 read is dominated by WC-era sports data, which the
   pre-registration deliberately excludes from interpretation. Practical
   earliest *useful* checkpoint: **~Jul 28 as a peek (73% best-case), Aug 8–11
   as the honest 80% date.** Waiting past mid-August buys little (84→94% from
   Aug 18 to Oct 1).
2. **The test is only powered against STRONG persistence.** If true
   persistence is what the current point estimate implies (ρ_true≈0.4),
   power is ~27% at Aug 4 and only ~39% by October — the expected observable
   ρ (~+0.07) sits below the n≈250 floor at *any* feasible date. Detecting
   that scenario needs ~750–1,000 wallets or a materially more efficient
   estimator (precision-weighted/shrunk correlation), not more weeks.
3. So the honest reading of the Aug 5 rerun: **a pass means persistence is
   strong; a "cannot tell" is the expected outcome under weak-but-real
   persistence and must not be read as absence** — same asymmetry as tonight's
   original result, now quantified.

## Q2. Paper-trading the strict-45 cohort: what it would look like

### Composition

45 wallets = 38 CONSISTENT + 7 CONSISTENT_YOUNG. Category split
(multi-tagged wallets counted per category): POLITICS 14, SPORTS 10,
FINANCE 8, CRYPTO 7, TECH 7, CULTURE 7. Signal-eligibility: 42/45 have at
least one $1000+ single buy in six months; median 67 eligible positions
(~2.6 eligible buys/week/wallet).

### Signal frequency — replay through the real `signals.detect_signals`

Method check: the 250-wallet replay over the live gate window (Jul 5–7)
produces 23 signals vs ~30 the paper loop actually recorded — same order,
method valid.

| cohort / params | May (pre-WC) | June (WC era) | Jul 5–7 (live window) |
|---|---|---|---|
| 250, live params N=5 W=12h F=$1000 | 1.0/day | 6.9/day | 10.6/day |
| **45, live params N=5 W=12h F=$1000** | **0.0/day (0 signals)** | **0.03/day (1 signal)** | **0.0/day** |
| 45, N=4 F=$1000 | 0.1/day | 0.2/day | 0.5/day |
| 45, N=3 F=$1000 | 0.2/day | 0.6/day | 1.4/day |
| 45, N=3 F=$500 | 0.3/day | 0.9/day | — |
| 45, N=2 F=$1000 | 2.5/day | 3.9/day | — |

### Answers

1. **At live parameters the 45-wallet cohort is dead on arrival**: one signal
   in two replayed months, zero in the live window. Five-of-45 consensus
   within 12h at a $1000 floor essentially never happens — the median strict
   wallet makes ~2.6 eligible buys/week spread across many markets.
2. **To keep it "meaningfully active" you must relax to N=3 (± lower floor)
   → ~0.3–0.9 signals/day (≈10–27/month), or N=2 → ~2.5–4/day.** N=2 is
   barely a consensus signal (it abandons most of the luck-cancelling the
   strategy is built on); N=3/F=$500 is the defensible floor, but at
   ~0.3/day post-WC a 3-day-gate-style evaluation is meaningless — evaluating
   such a book takes **months**, which collides with Q1's timeline anyway.
3. Category mix of what would fire (N=3 replays): roughly half
   POLITICS, half SPORTS, occasional CRYPTO — FINANCE/TECH/CULTURE strict
   wallets almost never coincide.
4. **Side-finding that outranks the question: the World-Cup cliff.** The
   *current* 250-wallet bot at live params ran at ~1.0 signal/day in May
   (pre-WC) vs ~7–11/day now. After Jul 19, expect the live paper loop to
   drop by roughly an order of magnitude. Tomorrow's day-3 gate verdict is
   measured on WC-era flow and will NOT extrapolate to August volumes.

### Caveats

- All rates from the taker-only feed (median wallet ~84% maker) — invisible
  maker buys can't form signals live either, so replay matches the bot's
  reality, but "wallet activity" here ≠ full wallet activity.
- May is used as the post-WC proxy for sports rates; `end_ts` is the market's
  scheduled end (in-play buys clamped to lag 0) — both approximations.
- The MC model assumes normal true-edge distribution and 1/√k SE scaling of
  the bootstrap CIs; Spearman on ranks softens (not removes) heavy tails.
- Replay counts signals, not fills (no order-book depth simulation); the live
  gate window suggests signal→fill is currently near 1:1.
