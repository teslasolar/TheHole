import sys, tempfile, json
sys.path.insert(0, "/home/user/TheHole")
from spiders.base import HoleSpider, make_document


class StubSpider(HoleSpider):
    name = "test_cursor_stub"
    def fetch_items(self):
        return iter([])
    def parse(self, item):
        return None


def test_cursor_roundtrip(tmp_path, monkeypatch):
    spider = StubSpider(rate=100.0, burst=1)
    cursor_file = tmp_path / "test_cursor_stub.json"
    monkeypatch.setattr(spider, "_cursor_path", lambda: cursor_file)
    spider.save_cursor({"page": 42, "key": "val"})
    loaded = spider.load_cursor()
    assert loaded == {"page": 42, "key": "val"}


def test_load_cursor_missing(tmp_path, monkeypatch):
    spider = StubSpider(rate=100.0, burst=1)
    monkeypatch.setattr(spider, "_cursor_path", lambda: tmp_path / "nope.json")
    assert spider.load_cursor() == {}
