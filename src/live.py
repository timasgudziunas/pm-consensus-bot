"""Phase 6: live execution — STUB ONLY. Nothing here is implemented, by design.

Per CLAUDE.md non-negotiable #1: no order placement, no wallet interaction,
no key management, no code that moves real money. Do not implement anything
in this file until the owner explicitly says go, with both backtest and
paper-trading results in hand and the PLAN.md decision gate fully passed.

Notes for when that day comes (from OVERVIEW.md / PLAN.md):

VENUE
- The owner is in the US. The main Polymarket CLOB blocks US order placement.
- Live trading goes through Polymarket US (polymarket.us) — a separate,
  CFTC-regulated venue with its own API (Ed25519 request signing) and
  mandatory KYC via the iOS app.
- Signal source stays the GLOBAL Polymarket Data API (that's where the
  watchlist trades); execution happens on the US venue. These are different
  books with different markets.

MUST VERIFY BEFORE ANY ORDER CODE
- Market overlap: how many signal markets actually exist on Polymarket US?
  The decision gate requires at least 5 paper-mode signal markets present.
- Price tracking between the global book (signal prices) and the US book
  (execution prices) — divergence eats the edge measured in paper mode.

RISK CONTROLS (config.yaml `live:` block, already present)
- Position size: $20 fixed initially. Hard cap read from config only —
  never adjustable from code or CLI flags.
- Kill switch: if cumulative realized loss exceeds live.max_loss_usd
  (currently -$200), halt ALL new entries and alert the owner.

DECISION GATE (PLAN.md) — all must be true before writing a line here:
1. >= 1 parameter set profitable in the backtest validate period.
2. Same parameter set positive/neutral in paper trading.
3. Average alpha decay < 50% of average backtest PnL per trade.
4. Polymarket US KYC complete, API keys generated (keys NEVER in this repo).
5. >= 5 paper-signal markets available on Polymarket US.
"""

raise SystemExit("live.py is a stub — live trading is not built yet, on purpose.")
