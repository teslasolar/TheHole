"""
Hacker News spider -- uses the Firebase/Algolia API.

Endpoints:
  * https://hacker-news.firebaseio.com/v0/topstories.json
  * https://hacker-news.firebaseio.com/v0/item/{id}.json
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterator, List, Optional

from .base import HoleSpider, make_document

_HN_BASE = "https://hacker-news.firebaseio.com/v0"
_CODE_RE = re.compile(r"```|<code>|<pre>")


class HackerNewsSpider(HoleSpider):
    """Crawl Hacker News top and best stories."""

    name = "hn"

    def __init__(
        self,
        feeds: Optional[List[str]] = None,
        max_stories: int = 200,
        **kwargs: Any,
    ):
        super().__init__(rate=2.0, burst=10, **kwargs)
        self.feeds = feeds or ["topstories", "beststories"]
        self.max_stories = max_stories

    # ------------------------------------------------------------------

    def _get_item(self, item_id: int) -> Optional[Dict[str, Any]]:
        try:
            return self.get_json(f"{_HN_BASE}/item/{item_id}.json")
        except Exception:
            return None

    def fetch_items(self) -> Iterator[Dict[str, Any]]:
        cursor = self.load_cursor()
        seen: set = set(cursor.get("seen_ids", []))
        new_seen: List[int] = []

        for feed in self.feeds:
            ids: List[int] = self.get_json(f"{_HN_BASE}/{feed}.json") or []
            count = 0
            for story_id in ids:
                if story_id in seen:
                    continue
                if count >= self.max_stories:
                    break
                item = self._get_item(story_id)
                if item and item.get("type") == "story" and not item.get("deleted"):
                    yield item
                    new_seen.append(story_id)
                    count += 1

        # Keep last 5000 IDs to avoid infinite growth
        all_seen = list(seen | set(new_seen))[-5000:]
        self.save_cursor({"seen_ids": all_seen})

    def parse(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        title = item.get("title", "")
        url = item.get("url", "")
        if not url:
            # self-posts link to HN
            url = f"https://news.ycombinator.com/item?id={item.get('id', '')}"

        body = item.get("text", "") or ""
        author = item.get("by", "")
        ts = item.get("time", 0)
        from datetime import datetime, timezone
        date = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if ts else ""

        score = item.get("score", 0)
        descendants = item.get("descendants", 0)

        tags: List[str] = ["hn"]
        if score >= 100:
            tags.append("popular")

        has_code = bool(_CODE_RE.search(body))

        return make_document(
            url=url,
            title=title,
            body=body,
            author=author,
            author_id=author,
            source="hackernews",
            source_tier=2,
            date=date,
            tags=tags,
            lang="en",
            has_code=has_code,
            has_citations=False,
            has_data=False,
            outlinks=[item["url"]] if item.get("url") else [],
        )
