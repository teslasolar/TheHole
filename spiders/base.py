"""
HoleSpider -- universal base class for THE HOLE crawlers.

Provides:
  * Token-bucket rate limiting
  * Automatic retries with exponential backoff
  * Cursor (checkpoint) persistence to JSON files
  * Pagination helpers
  * A standard document schema every spider must produce
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_CURSOR_DIR = _DATA_DIR / "cursors"
_CURSOR_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Document schema (matches Document_UDT)
# ---------------------------------------------------------------------------
DOCUMENT_FIELDS = [
    "url", "title", "author", "author_id", "source", "source_tier",
    "date", "snippet", "body_hash", "word_count", "tags", "lang",
    "has_code", "has_citations", "has_data", "outlinks",
]


def make_document(
    url: str,
    title: str,
    body: str,
    *,
    author: str = "",
    author_id: str = "",
    source: str = "",
    source_tier: int = 3,
    date: str = "",
    tags: Optional[List[str]] = None,
    lang: str = "en",
    has_code: bool = False,
    has_citations: bool = False,
    has_data: bool = False,
    outlinks: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Build a document dict that conforms to the Document_UDT shape."""
    snippet = body[:300].replace("\n", " ").strip() if body else ""
    body_hash = hashlib.sha256(body.encode("utf-8", errors="replace")).hexdigest() if body else ""
    word_count = len(body.split()) if body else 0
    return {
        "url": url,
        "title": title,
        "author": author,
        "author_id": author_id,
        "source": source,
        "source_tier": source_tier,
        "date": date or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "snippet": snippet,
        "body_hash": body_hash,
        "word_count": word_count,
        "tags": tags or [],
        "lang": lang,
        "has_code": has_code,
        "has_citations": has_citations,
        "has_data": has_data,
        "outlinks": outlinks or [],
    }


# ---------------------------------------------------------------------------
# Token-bucket rate limiter
# ---------------------------------------------------------------------------
class _TokenBucket:
    """Simple token-bucket rate limiter."""

    def __init__(self, rate: float, burst: int = 1):
        self.rate = rate          # tokens per second
        self.burst = burst
        self.tokens = float(burst)
        self._last = time.monotonic()

    def acquire(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last
        self._last = now
        self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
        if self.tokens < 1.0:
            wait = (1.0 - self.tokens) / self.rate
            time.sleep(wait)
            self.tokens = 0.0
        else:
            self.tokens -= 1.0


# ---------------------------------------------------------------------------
# HoleSpider base
# ---------------------------------------------------------------------------
class HoleSpider(ABC):
    """
    Base spider.  Subclasses must implement:
        name          -- unique string identifier
        fetch_items() -- yields raw items from the upstream source
        parse(item)   -- converts one raw item into a Document dict, or None
    """

    name: str = "base"

    def __init__(
        self,
        rate: float = 1.0,
        burst: int = 3,
        max_retries: int = 4,
        backoff_factor: float = 1.0,
        timeout: float = 30.0,
        headers: Optional[Dict[str, str]] = None,
    ):
        self.timeout = timeout
        self._bucket = _TokenBucket(rate=rate, burst=burst)

        # Build a requests.Session with retry logic
        self.session = requests.Session()
        retry = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        default_headers = {
            "User-Agent": "TheHole/1.0 (search engine crawler; +https://thehole.dev)",
        }
        if headers:
            default_headers.update(headers)
        self.session.headers.update(default_headers)

    # -- cursor management --------------------------------------------------

    def _cursor_path(self) -> Path:
        return _CURSOR_DIR / f"{self.name}.json"

    def load_cursor(self) -> Dict[str, Any]:
        """Load the last-saved cursor, or return an empty dict."""
        p = self._cursor_path()
        if p.exists():
            with open(p, "r") as f:
                return json.load(f)
        return {}

    def save_cursor(self, cursor: Dict[str, Any]) -> None:
        """Persist a cursor dict to disk."""
        p = self._cursor_path()
        with open(p, "w") as f:
            json.dump(cursor, f, indent=2)

    # -- HTTP helpers -------------------------------------------------------

    def get(self, url: str, **kwargs: Any) -> requests.Response:
        """Rate-limited GET request."""
        self._bucket.acquire()
        kwargs.setdefault("timeout", self.timeout)
        return self.session.get(url, **kwargs)

    def get_json(self, url: str, **kwargs: Any) -> Any:
        """Rate-limited GET that returns parsed JSON."""
        resp = self.get(url, **kwargs)
        resp.raise_for_status()
        return resp.json()

    def get_text(self, url: str, **kwargs: Any) -> str:
        """Rate-limited GET that returns response text."""
        resp = self.get(url, **kwargs)
        resp.raise_for_status()
        return resp.text

    # -- pagination helper --------------------------------------------------

    def paginate(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        page_key: str = "page",
        max_pages: int = 50,
        results_key: Optional[str] = None,
    ) -> Iterator[Any]:
        """
        Generic page-number pagination.  Yields individual items.
        Stops when a page returns zero results or max_pages is reached.
        """
        params = dict(params or {})
        for page_num in range(1, max_pages + 1):
            params[page_key] = page_num
            data = self.get_json(url, params=params)
            items = data[results_key] if results_key and isinstance(data, dict) else data
            if not items:
                break
            for item in items:
                yield item

    # -- abstract interface -------------------------------------------------

    @abstractmethod
    def fetch_items(self) -> Iterator[Any]:
        """Yield raw items from the data source."""
        ...

    @abstractmethod
    def parse(self, item: Any) -> Optional[Dict[str, Any]]:
        """
        Convert a raw item into a Document_UDT-shaped dict.
        Return None to skip the item.
        """
        ...

    # -- main entry point ---------------------------------------------------

    def crawl(self, limit: int = 0) -> List[Dict[str, Any]]:
        """
        Run a full crawl.  Returns a list of document dicts.
        If *limit* is >0, stop after that many documents.
        """
        docs: List[Dict[str, Any]] = []
        for item in self.fetch_items():
            doc = self.parse(item)
            if doc is not None:
                docs.append(doc)
                if limit and len(docs) >= limit:
                    break
        return docs
