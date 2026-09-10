"""Thin Microsoft Graph client: app-only auth (client secret), read-only calls.
Handles 429 throttling by honoring Retry-After exactly, per request (plan §6).
"""
import time

import requests
import msal

from app.config import GraphConfig
from app.logging_config import get_logger

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
SCOPE = ["https://graph.microsoft.com/.default"]
MAX_RETRIES = 5


class GraphClient:
    def __init__(self, logger=None):
        self.logger = logger or get_logger()
        authority = f"https://login.microsoftonline.com/{GraphConfig.tenant_id}"
        self._app = msal.ConfidentialClientApplication(
            GraphConfig.client_id, authority=authority,
            client_credential=GraphConfig.client_secret,
        )

    def _get_token(self) -> str:
        result = self._app.acquire_token_silent(SCOPE, account=None)
        if not result:
            result = self._app.acquire_token_for_client(scopes=SCOPE)
        if "access_token" not in result:
            raise RuntimeError(f"Graph auth failed: {result.get('error_description')}")
        return result["access_token"]

    def _request(self, method: str, url: str, params: dict | None = None) -> requests.Response:
        if not url.startswith("http"):
            url = f"{GRAPH_BASE}{url}"
        for attempt in range(MAX_RETRIES):
            resp = requests.request(
                method, url, params=params,
                headers={"Authorization": f"Bearer {self._get_token()}"},
            )
            if resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", "5"))
                self.logger.warning(
                    "graph_retry status=429 attempt=%s wait_seconds=%s path=%s",
                    attempt + 1,
                    wait,
                    url.split("?", 1)[0],
                )
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp
        raise RuntimeError(f"Graph request throttled past {MAX_RETRIES} retries: {url}")

    def get(self, url: str, params: dict | None = None) -> dict:
        return self._request("GET", url, params).json()

    def paged_get(self, url: str, params: dict | None = None):
        """Yield items across @odata.nextLink pages."""
        next_url, next_params = url, params
        while next_url:
            page = self.get(next_url, next_params)
            for item in page.get("value", []):
                yield item
            next_url, next_params = page.get("@odata.nextLink"), None

    def run_delta(self, start_url: str):
        """Walk all pages of a /delta call, yielding each item, and return the final deltaLink."""
        next_url = start_url
        delta_link = None
        while next_url:
            page = self.get(next_url)
            for item in page.get("value", []):
                yield item
            next_url = page.get("@odata.nextLink")
            if not next_url:
                delta_link = page.get("@odata.deltaLink")
        self.last_delta_link = delta_link
