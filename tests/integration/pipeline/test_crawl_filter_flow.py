"""Integration: DummySpider -> SlopFilter flow."""
import json
import sys
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent.parent)
sys.path.insert(0, _PROJECT_ROOT)

from spiders.base import HoleSpider, make_document
from filters.slop_filter import SlopFilter

_FIXTURES = Path(__file__).resolve().parent.parent.parent / "fixtures" / "docs"


class DummySpider(HoleSpider):
    name = "dummy"
    def __init__(self, items):
        self._items = items
    def fetch_items(self):
        return iter(self._items)
    def parse(self, item):
        return item


def _load(name):
    with open(_FIXTURES / name) as f:
        return json.load(f)


def test_clean_doc_passes_filter():
    doc = _load("sample_clean_doc.json")
    spider = DummySpider([doc])
    docs = spider.crawl()
    filt = SlopFilter()
    assert filt.should_index(docs[0])


def test_slop_doc_fails_filter():
    doc = _load("sample_slop_doc.json")
    spider = DummySpider([doc])
    docs = spider.crawl()
    filt = SlopFilter()
    assert not filt.should_index(docs[0])
