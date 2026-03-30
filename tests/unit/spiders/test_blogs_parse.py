import sys
sys.path.insert(0, "/home/user/TheHole")
from spiders.blogs import BlogSpider


class FakeEntry(dict):
    def __init__(self):
        super().__init__(
            link="https://blog.example.com/post1",
            title="My Post",
            summary="<p>Hello world</p>",
            author="Alice",
            published="2023-01-01",
            tags=[],
        )


def test_parse_basic():
    spider = BlogSpider.__new__(BlogSpider)
    item = {
        "entry": FakeEntry(),
        "blog_meta": {"author": "Alice", "id": "b1", "tier": 2, "tags": ["tech"]},
    }
    doc = spider.parse(item)
    assert doc["title"] == "My Post"
    assert doc["source"] == "blog"
    assert "tech" in doc["tags"]


def test_parse_missing_url():
    spider = BlogSpider.__new__(BlogSpider)
    entry = FakeEntry()
    entry.get = lambda k, d="": "" if k in ("link", "title") else d
    doc = spider.parse({"entry": entry, "blog_meta": {}})
    assert doc is None
