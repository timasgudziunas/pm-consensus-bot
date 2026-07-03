"""CLOB API client (price history, order book, midpoint).

Phase 0 findings (2026-07-02):
- /prices-history returns {"history": [{"t": ts, "p": price}, ...]} — matches
  OVERVIEW.md. 'market' param is the outcome TOKEN id, not conditionId.
- /book returns bids/asks as lists of {"price": str, "size": str} sorted
  worst-to-best (best ask is the LAST element). We sort explicitly before use.
- /midpoint returns {"mid": "0.44"}.
"""
import logging
from typing import Optional

from data_api import BaseClient

log = logging.getLogger(__name__)


class ClobApi(BaseClient):
    """Client for https://clob.polymarket.com (public endpoints only)."""

    base_url = "https://clob.polymarket.com"

    def get_price_history(self, token_id: str, start_ts: int, end_ts: int,
                          fidelity: int = 60) -> list:
        """Historical prices as a list of (timestamp, price) tuples, ascending."""
        data = self._get("/prices-history", {
            "market": token_id, "startTs": start_ts, "endTs": end_ts, "fidelity": fidelity,
        })
        history = data.get("history", []) if isinstance(data, dict) else []
        return [(int(pt["t"]), float(pt["p"])) for pt in history]

    def get_book(self, token_id: str) -> Optional[dict]:
        """Order book with 'bids'/'asks' lists of {'price': float, 'size': float},
        asks sorted ascending by price, bids descending (best first)."""
        data = self._get("/book", {"token_id": token_id})
        if not isinstance(data, dict):
            return None
        def levels(side: str, reverse: bool) -> list:
            raw = data.get(side) or []
            lv = [{"price": float(l["price"]), "size": float(l["size"])} for l in raw]
            return sorted(lv, key=lambda l: l["price"], reverse=reverse)
        return {"bids": levels("bids", True), "asks": levels("asks", False)}

    def get_midpoint(self, token_id: str) -> Optional[float]:
        """Current midpoint price for a token, or None."""
        data = self._get("/midpoint", {"token_id": token_id})
        try:
            return float(data["mid"])
        except (TypeError, KeyError, ValueError):
            return None
