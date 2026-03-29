"""
Lobsters spider -- fetches stories via the JSON API.

API docs: https://lobste.rs/about
Endpoints:
  * https://lobste.rs/hottest.json
  * https://lobste.rs/newest.json
  * https://lobste.rs/page/{n}.json
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, Iterator, List, Optional

from .base import HoleSpider, make_document


class LobstersSpider(HoleSpider):
    """Crawl Lobste.rs stories."""

    name = "lobsters"

    def __init__(
        self,
        feeds: Optional[List[str]] = None,
        max_pages: int = 5,
        **kwargs: Any,
    ):
        super().__init__(rate=1.0, burst=3, **kwargs)
        self.feeds = feeds or ["hottest", "newest"]
        self.max_pages = max_pages

    # ------------------------------------------------------------------

    def fetch_items(self) -> Iterator[Dict[str, Any]]:
        cursor = self.load_cursor()
        seen: set = set(cursor.get("seen_ids", []))
        new_ids: List[str] = []

        for feed in self.feeds:
            for page in range(1, self.max_pages + 1):
                url = f"https://lobste.rs/{feed}/page/{page}.json"
                try:
                    items = self.get_json(url)
                except Exception:
                    break
                if not items:
                    break
                for story in items:
                    sid = story.get("short_id", "")
                    if sid in seen:
                        continue
                    new_ids.append(sid)
                    yield story

        all_seen = list(seen | set(new_ids))[-5000:]
        self.save_cursor({"seen_ids": all_seen})

    def parse(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        url = item.get("url") or item.get("comments_url", "")
        title = item.get("title", "")
        if not url or not title:
            return None

        body = item.get("description", "") or ""
        author = item.get("submitter_user", {}).get("username", "") if isinstance(item.get("submitter_user"), dict) else item.get("submitter_user", "")
        date = item.get("created_at", "")

        tags: List[str] = item.get("tags", []) or []
        tags.append("lobsters")

        score = item.get("score", 0)
        if score >= 20:
            tags.append("popular")

        comments_url = item.get("comments_url", "")
        outlinks: List[str] = []
        if comments_url:
            outlinks.append(comments_url)
        if item.get("url") and item.get("url") != url:
            outlinks.append(item["url"])

        return make_document(
            url=url,
            title=title,
            body=body,
            author=author,
            author_id=author,
            source="lobsters",
            source_tier=2,
            date=date,
            tags=tags,
            lang="en",
            has_code=False,
            has_citations=False,
            has_data=False,
            outlinks=outlinks,
        )
