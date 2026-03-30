import sys
sys.path.insert(0, "/home/user/TheHole")
from spiders.hn import HackerNewsSpider

SAMPLE = {
    "id": 123,
    "title": "Show HN: My Project",
    "url": "https://example.com/proj",
    "text": "",
    "by": "alice",
    "time": 1672531200,
    "score": 150,
    "descendants": 42,
}


def test_parse_basic():
    spider = HackerNewsSpider.__new__(HackerNewsSpider)
    doc = spider.parse(SAMPLE)
    assert doc["title"] == "Show HN: My Project"
    assert doc["source"] == "hackernews"
    assert "popular" in doc["tags"]
    assert doc["url"] == "https://example.com/proj"


def test_parse_self_post():
    item = {**SAMPLE, "url": "", "score": 5}
    spider = HackerNewsSpider.__new__(HackerNewsSpider)
    doc = spider.parse(item)
    assert "news.ycombinator.com" in doc["url"]
