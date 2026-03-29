"""
Fediverse spider -- fetches public posts from Mastodon-compatible instances.

Uses the Mastodon public timeline API:
  GET /api/v1/timelines/public?local=false&limit=40
  GET /api/v1/timelines/tag/{hashtag}?limit=40
"""

from __future__ import annotations

import hashlib
import html
import re
from typing import Any, Dict, Iterator, List, Optional

from .base import HoleSpider, make_document

_TAG_STRIP = re.compile(r"<[^>]+>")
_CODE_RE = re.compile(r"<code|<pre|```")
_LINK_RE = re.compile(r'href="(https?://[^"]+)"')


def _strip_html(text: str) -> str:
    return html.unescape(_TAG_STRIP.sub("", text)).strip()


class FediverseSpider(HoleSpider):
    """Crawl Mastodon/Fediverse public timelines and hashtag feeds."""

    name = "fediverse"

    def __init__(
        self,
        instances: Optional[List[str]] = None,
        hashtags: Optional[List[str]] = None,
        max_per_instance: int = 200,
        **kwargs: Any,
    ):
        super().__init__(rate=1.0, burst=3, **kwargs)
        self.instances = instances or [
            "mastodon.social",
            "hachyderm.io",
            "fosstodon.org",
            "infosec.exchange",
            "sigmoid.social",
        ]
        self.hashtags = hashtags or [
            "programming", "rust", "python", "linux", "opensource",
            "infosec", "machinelearning", "compsci",
        ]
        self.max_per_instance = max_per_instance

    # ------------------------------------------------------------------

    def _fetch_timeline(self, instance: str, path: str) -> List[Dict[str, Any]]:
        """Paginate through a timeline endpoint."""
        results: List[Dict[str, Any]] = []
        url = f"https://{instance}{path}"
        params: Dict[str, Any] = {"limit": 40}

        while len(results) < self.max_per_instance:
            try:
                resp = self.get(url, params=params)
                resp.raise_for_status()
                statuses = resp.json()
            except Exception:
                break
            if not statuses:
                break
            results.extend(statuses)

            # Mastodon pagination via Link header
            link_header = resp.headers.get("Link", "")
            next_match = re.search(r'<([^>]+)>;\s*rel="next"', link_header)
            if next_match:
                url = next_match.group(1)
                params = {}
            else:
                break
        return results

    def fetch_items(self) -> Iterator[Dict[str, Any]]:
        cursor = self.load_cursor()
        seen: set = set(cursor.get("seen_ids", []))
        new_ids: List[str] = []

        for instance in self.instances:
            # Public timeline
            statuses = self._fetch_timeline(instance, "/api/v1/timelines/public?local=false")
            for status in statuses:
                sid = status.get("id", "")
                key = f"{instance}:{sid}"
                if key in seen:
                    continue
                new_ids.append(key)
                status["_instance"] = instance
                yield status

            # Hashtag timelines
            for tag in self.hashtags:
                statuses = self._fetch_timeline(instance, f"/api/v1/timelines/tag/{tag}")
                for status in statuses:
                    sid = status.get("id", "")
                    key = f"{instance}:{sid}"
                    if key in seen:
                        continue
                    new_ids.append(key)
                    status["_instance"] = instance
                    yield status

        all_seen = list(seen | set(new_ids))[-20000:]
        self.save_cursor({"seen_ids": all_seen})

    def parse(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        # Skip boosts (reblogs) and empty statuses
        if item.get("reblog"):
            return None
        content_html = item.get("content", "")
        if not content_html:
            return None

        body = _strip_html(content_html)
        if len(body) < 20:
            return None

        url = item.get("url") or item.get("uri", "")
        instance = item.get("_instance", "")

        account = item.get("account", {})
        author = account.get("display_name") or account.get("username", "")
        acct = account.get("acct", "")
        author_id = f"{acct}@{instance}" if "@" not in acct else acct

        date = item.get("created_at", "")

        # Tags from the status
        tags: List[str] = [t.get("name", "") for t in item.get("tags", []) if t.get("name")]
        tags.append("fediverse")

        has_code = bool(_CODE_RE.search(content_html))
        outlinks = _LINK_RE.findall(content_html)

        # Language
        lang = item.get("language") or "en"

        # Use first line or whole body as title
        first_line = body.split("\n")[0][:120]
        title = first_line if first_line else body[:120]

        return make_document(
            url=url,
            title=title,
            body=body,
            author=author,
            author_id=author_id,
            source="fediverse",
            source_tier=3,
            date=date,
            tags=tags,
            lang=lang,
            has_code=has_code,
            has_citations=False,
            has_data=False,
            outlinks=outlinks,
        )
