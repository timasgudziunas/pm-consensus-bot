"""Data API client (leaderboard, trades, positions, activity).

Also home of BaseClient, the shared throttled/retrying HTTP core used by
gamma_api.py and clob_api.py (kept here so the repo layout stays exactly as
specified in OVERVIEW.md).

Phase 0 findings (2026-07-02), verified against live responses:
- Field casing is camelCase exactly as OVERVIEW.md says (proxyWallet,
  conditionId, transactionHash, ...). Clients normalize all keys to
  snake_case before returning.
- /trades 'size' is in SHARES, not USD. USD value = size * price
  (cross-checked against /activity's usdcSize). OVERVIEW's filterAmount
  is a dollar filter, but the returned size field is shares.
- The GLOBAL /trades feed (no user param) returns outcomeIndex=999 —
  unreliable. Map the 'asset' field (outcome token id) to an index via the
  market's clobTokenIds instead. User-filtered /trades has correct indexes.
- Leaderboard accepts only OVERALL, POLITICS, SPORTS, CRYPTO, FINANCE,
  CULTURE, TECH as categories; everything else in OVERVIEW's example list
  returns HTTP 400.
"""
import logging
import os
import re
import time
from typing import Any, Optional

import requests
import yaml

log = logging.getLogger(__name__)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(REPO_ROOT, "config.yaml")

_config_cache: Optional[dict] = None


def load_config() -> dict:
    """Load and cache config.yaml. Missing keys are bugs — let KeyError crash."""
    global _config_cache
    if _config_cache is None:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            _config_cache = yaml.safe_load(f)
    return _config_cache


_CAMEL_RE = re.compile(r"(?<!^)(?=[A-Z])")


def _snake(key: str) -> str:
    return _CAMEL_RE.sub("_", key).lower()


def normalize_keys(obj: Any) -> Any:
    """Recursively convert dict keys from camelCase to snake_case."""
    if isinstance(obj, dict):
        return {_snake(k): normalize_keys(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [normalize_keys(x) for x in obj]
    return obj


class ApiError(Exception):
    """Raised when a request fails after all retries."""


# One shared throttle across every client instance in the process, so the
# combined request rate stays under the config ceiling.
_last_request_at = 0.0


class BaseClient:
    """Throttled, retrying GET client. Subclasses set base_url."""

    base_url = ""

    def __init__(self) -> None:
        cfg = load_config()["api"]
        self.throttle = float(cfg["throttle_seconds"])
        self.backoff_base = float(cfg["backoff_base_seconds"])
        self.max_retries = int(cfg["max_retries"])
        self.timeout = float(cfg["timeout_seconds"])
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "pm-consensus-bot/0.1"

    def _get(self, path: str, params: Optional[dict] = None) -> Any:
        """GET base_url+path with throttle and exponential backoff on 429/5xx.

        Returns parsed JSON with all keys snake_cased. Raises ApiError after
        max_retries transient failures, or immediately on 4xx (except 429)."""
        global _last_request_at
        url = self.base_url + path
        attempt = 0
        while True:
            wait = self.throttle - (time.monotonic() - _last_request_at)
            if wait > 0:
                time.sleep(wait)
            _last_request_at = time.monotonic()
            try:
                resp = self.session.get(url, params=params, timeout=self.timeout)
            except requests.RequestException as e:
                resp = None
                err = f"network error: {e}"
            if resp is not None:
                if resp.status_code == 200:
                    try:
                        return normalize_keys(resp.json())
                    except ValueError as e:
                        err = f"bad JSON: {e}"
                elif resp.status_code == 429 or resp.status_code >= 500:
                    err = f"HTTP {resp.status_code}"
                else:
                    raise ApiError(f"GET {url} params={params} -> HTTP {resp.status_code}: {resp.text[:200]}")
            attempt += 1
            if attempt > self.max_retries:
                raise ApiError(f"GET {url} failed after {self.max_retries} retries ({err})")
            delay = self.backoff_base * (2 ** (attempt - 1))
            log.warning("GET %s %s — retry %d/%d in %.1fs", url, err, attempt, self.max_retries, delay)
            time.sleep(delay)


class DataApi(BaseClient):
    """Client for https://data-api.polymarket.com."""

    base_url = "https://data-api.polymarket.com"

    def get_leaderboard(self, category: str = "OVERALL", time_period: str = "MONTH",
                        order_by: str = "PNL", limit: int = 50, offset: int = 0) -> list:
        """Leaderboard page; rows have proxy_wallet, user_name, pnl, vol, rank."""
        return self._get("/v1/leaderboard", {
            "category": category, "timePeriod": time_period,
            "orderBy": order_by, "limit": limit, "offset": offset,
        })

    def get_trades(self, user: Optional[str] = None, limit: int = 100, offset: int = 0,
                   side: Optional[str] = None, taker_only: bool = True,
                   filter_type: Optional[str] = None, filter_amount: Optional[float] = None) -> list:
        """Trades, newest first. No user -> global feed (outcome_index unreliable there)."""
        params: dict = {"limit": limit, "offset": offset, "takerOnly": str(taker_only).lower()}
        if user:
            params["user"] = user
        if side:
            params["side"] = side
        if filter_type:
            params["filterType"] = filter_type
        if filter_amount is not None:
            params["filterAmount"] = filter_amount
        return self._get("/trades", params)

    def get_positions(self, user: str) -> list:
        """Current open positions with cost basis for a wallet."""
        return self._get("/positions", {"user": user})

    def get_activity(self, user: str, limit: int = 100, offset: int = 0) -> list:
        """Per-user activity feed (TRADE / REDEEM rows, has usdc_size)."""
        return self._get("/activity", {"user": user, "limit": limit, "offset": offset})
