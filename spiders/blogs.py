"""
Blog spider -- fetches posts from curated practitioner blogs via RSS/Atom feeds.

Uses feedparser to handle the variety of feed formats.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

import feedparser

from .base import HoleSpider, make_document

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_CODE_RE = re.compile(r"<code|<pre|```")
_CITATION_RE = re.compile(r"\[\d+\]|<a\s+href=")
_TAG_STRIP = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return _TAG_STRIP.sub("", text).strip()


class BlogSpider(HoleSpider):
    """Crawl practitioner blogs via RSS/Atom feeds."""

    name = "blogs"

    def __init__(self, blogs_file: Optional[str] = None, **kwargs: Any):
        super().__init__(rate=2.0, burst=5, **kwargs)
        path = Path(blogs_file) if blogs_file else _DATA_DIR / "blogs.json"
        with open(path, "r") as f:
            self.blogs: List[Dict[str, Any]] = json.load(f)

    # ------------------------------------------------------------------

    def fetch_items(self) -> Iterator[Dict[str, Any]]:
        cursor = self.load_cursor()
        seen_hashes: set = set(cursor.get("seen_hashes", []))
        new_hashes: List[str] = []

        for blog in self.blogs:
            feed_url = blog.get("rss") or blog.get("feed_url", "")
            if not feed_url:
                continue
            try:
                text = self.get_text(feed_url)
            except Exception:
                continue

            feed = feedparser.parse(text)
            for entry in feed.entries:
                link = entry.get("link", "")
                entry_hash = hashlib.md5(link.encode()).hexdigest()
                if entry_hash in seen_hashes:
                    continue
                new_hashes.append(entry_hash)
                yield {
                    "entry": entry,
                    "blog_meta": blog,
                }

        # keep last 10 000 hashes
        all_hashes = list(seen_hashes | set(new_hashes))[-10000:]
        self.save_cursor({"seen_hashes": all_hashes})

    def parse(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        entry = item["entry"]
        blog_meta = item["blog_meta"]

        url = entry.get("link", "")
        title = entry.get("title", "")
        if not url or not title:
            return None

        # Body: prefer content, fall back to summary
        body_html = ""
        if entry.get("content"):
            body_html = entry["content"][0].get("value", "")
        elif entry.get("summary"):
            body_html = entry["summary"]
        body = _strip_html(body_html)

        author = entry.get("author", "") or blog_meta.get("author", "")
        author_id = blog_meta.get("id", "")
        source_tier = blog_meta.get("tier", 2)

        # Date
        date = ""
        for field in ("published", "updated"):
            val = entry.get(field, "")
            if val:
                date = val
                break

        tags: List[str] = [t.get("term", "") for t in entry.get("tags", []) if t.get("term")]
        blog_tags = blog_meta.get("tags", [])
        tags.extend(blog_tags)

        has_code = bool(_CODE_RE.search(body_html))
        has_citations = bool(_CITATION_RE.search(body_html))

        outlinks: List[str] = re.findall(r'href="(https?://[^"]+)"', body_html)

        return make_document(
            url=url,
            title=title,
            body=body,
            author=author,
            author_id=author_id,
            source="blog",
            source_tier=source_tier,
            date=date,
            tags=tags,
            lang=blog_meta.get("lang", "en"),
            has_code=has_code,
            has_citations=has_citations,
            has_data=False,
            outlinks=outlinks,
        )
