"""
Stack Overflow spider -- fetches highly-voted answers via the SE API v2.3.

API docs: https://api.stackexchange.com/docs
"""

from __future__ import annotations

import html
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List, Optional

from .base import HoleSpider, make_document

_SE_API = "https://api.stackexchange.com/2.3"
_CODE_RE = re.compile(r"<code>|<pre>")
_CITATION_RE = re.compile(r"https?://\S+|RFC\s*\d+", re.I)
_TAG_STRIP = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    """Rough HTML tag removal."""
    return html.unescape(_TAG_STRIP.sub("", text))


class StackOverflowSpider(HoleSpider):
    """Crawl top Stack Overflow answers."""

    name = "stackoverflow"

    def __init__(
        self,
        tagged: str = "",
        min_score: int = 10,
        max_results: int = 200,
        **kwargs: Any,
    ):
        super().__init__(rate=1.0, burst=5, **kwargs)
        self.tagged = tagged
        self.min_score = min_score
        self.max_results = max_results
        self.api_key = os.environ.get("SE_API_KEY", "")

    # ------------------------------------------------------------------

    def fetch_items(self) -> Iterator[Dict[str, Any]]:
        cursor = self.load_cursor()
        last_date = cursor.get("last_activity_date", 0)
        fetched = 0

        for page in range(1, (self.max_results // 100) + 2):
            if fetched >= self.max_results:
                break
            params: Dict[str, Any] = {
                "order": "desc",
                "sort": "votes",
                "site": "stackoverflow",
                "filter": "withbody",
                "pagesize": min(100, self.max_results - fetched),
                "page": page,
                "min": self.min_score,
            }
            if self.tagged:
                params["tagged"] = self.tagged
            if self.api_key:
                params["key"] = self.api_key
            if last_date:
                params["fromdate"] = last_date

            data = self.get_json(f"{_SE_API}/answers", params=params)
            items = data.get("items", [])
            if not items:
                break
            max_date = last_date
            for item in items:
                yield item
                fetched += 1
                act = item.get("last_activity_date", 0)
                if act > max_date:
                    max_date = act

            self.save_cursor({"last_activity_date": max_date})

            if not data.get("has_more", False):
                break
            # respect backoff header
            backoff = data.get("backoff")
            if backoff:
                import time
                time.sleep(int(backoff))

    def parse(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        answer_id = item.get("answer_id", "")
        question_id = item.get("question_id", "")
        url = f"https://stackoverflow.com/a/{answer_id}"

        body_html = item.get("body", "")
        body = _strip_html(body_html)
        title = f"SO Answer #{answer_id} (Q#{question_id})"

        owner = item.get("owner", {})
        author = owner.get("display_name", "")
        author_id = str(owner.get("user_id", ""))

        ts = item.get("last_activity_date") or item.get("creation_date", 0)
        date = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if ts else ""

        tags: List[str] = item.get("tags", []) or []
        has_code = bool(_CODE_RE.search(body_html))
        has_citations = bool(_CITATION_RE.search(body_html))

        outlinks: List[str] = re.findall(r'href="(https?://[^"]+)"', body_html)

        return make_document(
            url=url,
            title=title,
            body=body,
            author=author,
            author_id=author_id,
            source="stackoverflow",
            source_tier=2,
            date=date,
            tags=tags,
            lang="en",
            has_code=has_code,
            has_citations=has_citations,
            has_data=False,
            outlinks=outlinks,
        )
