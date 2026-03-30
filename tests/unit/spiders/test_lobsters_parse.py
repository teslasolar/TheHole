import sys
sys.path.insert(0, "/home/user/TheHole")
from spiders.lobsters import LobstersSpider

SAMPLE = {
    "short_id": "abc123",
    "url": "https://example.com/article",
    "title": "Cool Article",
    "description": "A neat description",
    "submitter_user": "bob",
    "created_at": "2023-01-01T00:00:00Z",
    "tags": ["programming"],
    "score": 25,
    "comments_url": "https://lobste.rs/s/abc123",
}


def test_parse_basic():
    spider = LobstersSpider.__new__(LobstersSpider)
    doc = spider.parse(SAMPLE)
    assert doc["title"] == "Cool Article"
    assert doc["source"] == "lobsters"
    assert "popular" in doc["tags"]
    assert "lobsters" in doc["tags"]


def test_parse_missing_url():
    item = {**SAMPLE, "url": "", "title": "", "comments_url": ""}
    spider = LobstersSpider.__new__(LobstersSpider)
    assert spider.parse(item) is None
