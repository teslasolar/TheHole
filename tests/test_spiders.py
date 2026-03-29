"""Tests for the HoleSpider base class."""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional
from unittest.mock import MagicMock, patch

import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from spiders.base import HoleSpider, _TokenBucket, make_document


# ---------------------------------------------------------------------------
# Concrete test spider
# ---------------------------------------------------------------------------


class DummySpider(HoleSpider):
    name = "dummy"

    def __init__(self, items: List[Any] | None = None, **kwargs):
        super().__init__(**kwargs)
        self._items = items or []

    def fetch_items(self) -> Iterator[Any]:
        for item in self._items:
            yield item

    def parse(self, item: Any) -> Optional[Dict[str, Any]]:
        if item is None:
            return None
        return make_document(
            url=item.get("url", "https://example.com"),
            title=item.get("title", "Test"),
            body=item.get("body", "Test body content here."),
            author=item.get("author", "Test Author"),
            source="dummy",
        )


# ---------------------------------------------------------------------------
# Token bucket / rate limiting
# ---------------------------------------------------------------------------


class TestTokenBucket:
    def test_burst_allows_immediate(self):
        bucket = _TokenBucket(rate=1.0, burst=3)
        # Should be able to acquire 3 times without delay
        start = time.monotonic()
        for _ in range(3):
            bucket.acquire()
        elapsed = time.monotonic() - start
        assert elapsed < 0.5  # should be near-instant

    def test_rate_limiting_delays(self):
        bucket = _TokenBucket(rate=10.0, burst=1)
        # First acquire is instant (burst=1)
        bucket.acquire()
        # Second should wait ~0.1s
        start = time.monotonic()
        bucket.acquire()
        elapsed = time.monotonic() - start
        assert elapsed >= 0.05  # at least some delay
        assert elapsed < 0.5   # but not too long

    def test_tokens_refill(self):
        bucket = _TokenBucket(rate=100.0, burst=2)
        bucket.acquire()
        bucket.acquire()
        # Tokens exhausted, wait for refill
        time.sleep(0.05)
        start = time.monotonic()
        bucket.acquire()
        elapsed = time.monotonic() - start
        # Should be fast since tokens refilled at 100/s
        assert elapsed < 0.2


# ---------------------------------------------------------------------------
# Cursor management
# ---------------------------------------------------------------------------


class TestCursorManagement:
    def test_save_and_load_cursor(self, tmp_path):
        with patch("spiders.base._CURSOR_DIR", tmp_path):
            spider = DummySpider()
            cursor = {"last_page": 5, "last_id": "abc123"}
            spider.save_cursor(cursor)

            loaded = spider.load_cursor()
            assert loaded == cursor

    def test_load_empty_cursor(self, tmp_path):
        with patch("spiders.base._CURSOR_DIR", tmp_path):
            spider = DummySpider()
            cursor = spider.load_cursor()
            assert cursor == {}

    def test_cursor_persistence(self, tmp_path):
        with patch("spiders.base._CURSOR_DIR", tmp_path):
            spider1 = DummySpider()
            spider1.save_cursor({"page": 10})

            # New instance should load same cursor
            spider2 = DummySpider()
            assert spider2.load_cursor() == {"page": 10}


# ---------------------------------------------------------------------------
# Crawl and parse
# ---------------------------------------------------------------------------


class TestCrawl:
    def test_crawl_returns_docs(self):
        items = [
            {"url": "https://example.com/1", "title": "Post 1", "body": "Body 1"},
            {"url": "https://example.com/2", "title": "Post 2", "body": "Body 2"},
        ]
        spider = DummySpider(items=items)
        docs = spider.crawl()
        assert len(docs) == 2
        assert docs[0]["url"] == "https://example.com/1"
        assert docs[1]["title"] == "Post 2"

    def test_crawl_with_limit(self):
        items = [
            {"url": f"https://example.com/{i}", "title": f"Post {i}", "body": f"Body {i}"}
            for i in range(10)
        ]
        spider = DummySpider(items=items)
        docs = spider.crawl(limit=3)
        assert len(docs) == 3

    def test_crawl_skips_none(self):
        items = [
            {"url": "https://example.com/1", "title": "Post 1", "body": "Body 1"},
            None,  # parse returns None for this
            {"url": "https://example.com/3", "title": "Post 3", "body": "Body 3"},
        ]
        spider = DummySpider(items=items)
        docs = spider.crawl()
        assert len(docs) == 2


# ---------------------------------------------------------------------------
# make_document helper
# ---------------------------------------------------------------------------


class TestMakeDocument:
    def test_required_fields(self):
        doc = make_document(
            url="https://example.com/test",
            title="Test Title",
            body="This is the body text.",
        )
        assert doc["url"] == "https://example.com/test"
        assert doc["title"] == "Test Title"
        assert doc["word_count"] == 5
        assert doc["body_hash"] != ""
        assert doc["snippet"] == "This is the body text."

    def test_optional_fields(self):
        doc = make_document(
            url="https://example.com/test",
            title="Test",
            body="Body",
            author="Julia Evans",
            source="blog",
            source_tier=1,
            has_code=True,
            tags=["python", "debugging"],
        )
        assert doc["author"] == "Julia Evans"
        assert doc["source"] == "blog"
        assert doc["source_tier"] == 1
        assert doc["has_code"] is True
        assert doc["tags"] == ["python", "debugging"]

    def test_empty_body(self):
        doc = make_document(url="https://example.com", title="Test", body="")
        assert doc["word_count"] == 0
        assert doc["body_hash"] == ""
        assert doc["snippet"] == ""

    def test_snippet_truncation(self):
        long_body = "word " * 200  # 1000 chars
        doc = make_document(url="https://example.com", title="Test", body=long_body)
        assert len(doc["snippet"]) <= 300


# ---------------------------------------------------------------------------
# Pagination helper
# ---------------------------------------------------------------------------


class TestPagination:
    def test_paginate_stops_on_empty(self):
        spider = DummySpider()
        # Mock get_json to return items then empty
        responses = [
            [{"id": 1}, {"id": 2}],
            [{"id": 3}],
            [],  # empty => stop
        ]
        call_count = 0

        def mock_get_json(url, **kwargs):
            nonlocal call_count
            result = responses[call_count] if call_count < len(responses) else []
            call_count += 1
            return result

        spider.get_json = mock_get_json
        items = list(spider.paginate("https://api.example.com/items", max_pages=10))
        assert len(items) == 3
        assert call_count == 3

    def test_paginate_respects_max_pages(self):
        spider = DummySpider()
        call_count = 0

        def mock_get_json(url, **kwargs):
            nonlocal call_count
            call_count += 1
            return [{"id": call_count}]

        spider.get_json = mock_get_json
        items = list(spider.paginate("https://api.example.com/items", max_pages=3))
        assert len(items) == 3
        assert call_count == 3

    def test_paginate_with_results_key(self):
        spider = DummySpider()
        call_count = 0

        def mock_get_json(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return {"data": [{"id": call_count}], "total": 2}
            return {"data": [], "total": 2}

        spider.get_json = mock_get_json
        items = list(spider.paginate(
            "https://api.example.com/items",
            results_key="data",
            max_pages=5,
        ))
        assert len(items) == 2
