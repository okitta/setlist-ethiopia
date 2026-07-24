"""A courteous HTTP client: identifies itself, obeys robots.txt, rate-limits per
host, and backs off on errors. Web scraping responsibly is a hard requirement here.
"""

from __future__ import annotations

import time
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import requests

DEFAULT_UA = (
    "SetlistEthiopiaScraper/0.1 "
    "(+https://github.com/okitta/setlist-ethiopia; community music archive)"
)


class FetchError(RuntimeError):
    """A request failed. Carries the HTTP status when there was a response."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class PoliteClient:
    def __init__(
        self,
        *,
        user_agent: str = DEFAULT_UA,
        contact: str | None = None,
        min_interval: float = 1.0,
        timeout: float = 20.0,
        obey_robots: bool = True,
        max_retries: int = 3,
    ) -> None:
        ua = user_agent
        if contact:
            ua = f"{user_agent} contact:{contact}"
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": ua})
        self.min_interval = min_interval
        self.timeout = timeout
        self.obey_robots = obey_robots
        self.max_retries = max_retries
        self._last_call: dict[str, float] = {}
        self._robots: dict[str, RobotFileParser | None] = {}

    # -- rate limiting -----------------------------------------------------
    def _throttle(self, host: str) -> None:
        last = self._last_call.get(host, 0.0)
        wait = self.min_interval - (time.monotonic() - last)
        if wait > 0:
            time.sleep(wait)
        self._last_call[host] = time.monotonic()

    # -- robots.txt --------------------------------------------------------
    def _allowed(self, url: str) -> bool:
        if not self.obey_robots:
            return True
        parts = urlsplit(url)
        host = parts.netloc
        if host not in self._robots:
            rp = RobotFileParser()
            rp.set_url(f"{parts.scheme}://{host}/robots.txt")
            try:
                rp.read()
            except Exception:
                rp = None  # unreachable robots.txt -> do not block, but be gentle
            self._robots[host] = rp
        rp = self._robots[host]
        if rp is None:
            return True
        return rp.can_fetch(self.session.headers["User-Agent"], url)

    # -- requests ----------------------------------------------------------
    def _request(self, url: str, *, headers: dict | None = None, params: dict | None = None):
        if not self._allowed(url):
            raise PermissionError(f"robots.txt disallows fetching {url}")
        host = urlsplit(url).netloc
        last_exc: Exception | None = None
        for attempt in range(self.max_retries):
            self._throttle(host)
            try:
                resp = self.session.get(
                    url, headers=headers, params=params, timeout=self.timeout
                )
            except requests.RequestException as exc:  # network hiccup -> retry
                last_exc = exc
                time.sleep(2**attempt)
                continue
            # Transient server errors / throttling -> back off and retry.
            if resp.status_code in (429, 500, 502, 503, 504):
                time.sleep(2**attempt)
                continue
            # Other client errors (401 bad key, 404 no data) are not retryable.
            if resp.status_code >= 400:
                raise FetchError(f"HTTP {resp.status_code} for {url}", status=resp.status_code)
            return resp
        raise FetchError(f"failed to fetch {url}: {last_exc}", status=None)

    def get_json(self, url: str, *, headers: dict | None = None, params: dict | None = None):
        resp = self._request(url, headers=headers, params=params)
        return resp.json()

    def get_text(self, url: str, *, headers: dict | None = None, params: dict | None = None) -> str:
        return self._request(url, headers=headers, params=params).text
