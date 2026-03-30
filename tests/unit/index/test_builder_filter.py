import sys, os, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from pathlib import Path
from index.builder import IndexBuilder


def test_rejects_slop():
    slop_doc = {
        "title": "10 Best VPNs Must Have",
        "snippet": "",
        "url": "https://www.buzzfeed.com/vpns",
        "author": "",
        "body": "Buy now! " * 20,
        "source": "farm",
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        meta = IndexBuilder(output_dir=Path(tmpdir)).build_static([slop_doc])
        assert meta["total_rejected"] == 1
        assert meta["total_indexed"] == 0


def test_accepts_clean():
    doc = {"title": "eBPF Guide", "snippet": "Deep dive.", "author": "Alice", "url": "https://example.com/ebpf", "source": "blog", "has_code": True}
    with tempfile.TemporaryDirectory() as tmpdir:
        meta = IndexBuilder(output_dir=Path(tmpdir)).build_static([doc])
        assert meta["total_indexed"] == 1
