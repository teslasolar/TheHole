"""Integration: DummySpider -> filter -> rank -> IndexBuilder."""
import json
import sys
import tempfile
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent.parent)
sys.path.insert(0, _PROJECT_ROOT)

from spiders.base import HoleSpider, make_document
from index.builder import IndexBuilder

_FIXTURES = Path(__file__).resolve().parent.parent.parent / "fixtures" / "docs"


class DummySpider(HoleSpider):
    name = "dummy_full"
    def __init__(self, items):
        self._items = items
    def fetch_items(self):
        return iter(self._items)
    def parse(self, item):
        return item


def test_full_pipeline_produces_output():
    with open(_FIXTURES / "sample_clean_doc.json") as f:
        clean = json.load(f)
    with open(_FIXTURES / "sample_slop_doc.json") as f:
        slop = json.load(f)

    spider = DummySpider([clean, slop])
    docs = spider.crawl()

    with tempfile.TemporaryDirectory() as td:
        outdir = Path(td)
        builder = IndexBuilder(output_dir=outdir)
        meta = builder.build_static(docs)

        assert (outdir / "documents.json").exists()
        assert (outdir / "index.json").exists()
        assert (outdir / "meta.json").exists()
        assert meta["total_indexed"] >= 1
        assert meta["total_rejected"] >= 1
