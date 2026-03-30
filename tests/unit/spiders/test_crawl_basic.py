import sys
sys.path.insert(0, "/home/user/TheHole")
from spiders.base import HoleSpider, make_document


class DummySpider(HoleSpider):
    name = "dummy"

    def __init__(self):
        super().__init__(rate=100.0, burst=10)
        self.items = [{"id": 1}, {"id": 2}, {"id": 3}]

    def fetch_items(self):
        return iter(self.items)

    def parse(self, item):
        return make_document(url=f"http://x/{item['id']}", title="T", body="b")


def test_crawl_returns_all():
    docs = DummySpider().crawl()
    assert len(docs) == 3


def test_crawl_with_limit():
    docs = DummySpider().crawl(limit=2)
    assert len(docs) == 2
