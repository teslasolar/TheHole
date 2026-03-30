import sys
sys.path.insert(0, "/home/user/TheHole")
from spiders.fediverse import FediverseSpider

SAMPLE = {
    "content": "<p>This is a longer post about programming and Rust lang topics.</p>",
    "url": "https://mastodon.social/@user/123",
    "account": {"display_name": "Alice", "username": "alice", "acct": "alice"},
    "_instance": "mastodon.social",
    "created_at": "2023-01-01T00:00:00Z",
    "tags": [{"name": "rust"}],
    "language": "en",
}


def test_parse_basic():
    spider = FediverseSpider.__new__(FediverseSpider)
    doc = spider.parse(SAMPLE)
    assert doc["source"] == "fediverse"
    assert "fediverse" in doc["tags"]
    assert doc["author"] == "Alice"


def test_parse_skip_reblog():
    item = {**SAMPLE, "reblog": {"id": 1}}
    spider = FediverseSpider.__new__(FediverseSpider)
    assert spider.parse(item) is None


def test_parse_skip_short():
    item = {**SAMPLE, "content": "<p>Hi</p>"}
    spider = FediverseSpider.__new__(FediverseSpider)
    assert spider.parse(item) is None
