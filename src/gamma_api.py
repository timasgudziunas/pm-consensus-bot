"""Gamma API client (market metadata, events, resolution data).

Phase 0 findings (2026-07-02):
- market.category and market.tags are null on /markets responses; the
  embedded events objects carry NO tags either. Category must be resolved
  via GET /events?slug=<event_slug> -> tags[].label, then mapped through
  config category_tag_map.
- outcomePrices and clobTokenIds come back as JSON-encoded STRINGS
  (e.g. '["1","0"]'), not arrays. Callers must json.loads them.
- condition_ids accepts repeated query params for batch lookup.
- DISCREPANCY vs OVERVIEW.md: /markets returns only OPEN markets unless
  closed=true is passed (a condition_ids lookup for a resolved market comes
  back empty, HTTP 200). Callers needing resolved markets must query twice:
  once with no closed param (open) and once with closed=True.
"""
import logging
from typing import Optional

from data_api import BaseClient, load_config

log = logging.getLogger(__name__)


class GammaApi(BaseClient):
    """Client for https://gamma-api.polymarket.com."""

    base_url = "https://gamma-api.polymarket.com"

    def get_markets(self, condition_ids: Optional[list] = None, slug: Optional[str] = None,
                    limit: int = 100, offset: int = 0, closed: Optional[bool] = None) -> list:
        """Market metadata dicts. condition_ids may be a list (batched lookup)."""
        params: dict = {"limit": limit, "offset": offset}
        if condition_ids:
            params["condition_ids"] = condition_ids  # requests encodes repeats
        if slug:
            params["slug"] = slug
        if closed is not None:
            params["closed"] = str(closed).lower()
        return self._get("/markets", params)

    def get_events(self, slug: Optional[str] = None, tag: Optional[str] = None,
                   limit: int = 20, offset: int = 0) -> list:
        """Event dicts; the slug-filtered form is how we get category tags."""
        params: dict = {"limit": limit, "offset": offset}
        if slug:
            params["slug"] = slug
        if tag:
            params["tag"] = tag
        return self._get("/events", params)

    def resolve_category(self, event_slug: str) -> tuple:
        """Map an event's tags to one of our categories via config category_tag_map.

        Returns (category or '', [tag labels]). '' = fetched but unmapped."""
        try:
            events = self.get_events(slug=event_slug)
        except Exception as e:
            log.warning("events lookup failed for %s: %s", event_slug, e)
            return "", []
        if not events:
            return "", []
        labels = [str(t.get("label", "")).strip() for t in (events[0].get("tags") or [])]
        lowered = {l.lower() for l in labels}
        for category, tag_names in load_config()["category_tag_map"].items():
            if lowered & {t.lower() for t in tag_names}:
                return category, labels
        return "", labels
