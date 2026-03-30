import sys, os, json, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from pathlib import Path
from index.builder import IndexBuilder


def test_build_static_creates_files():
    docs = [
        {"title": "Good Post", "snippet": "Useful content", "url": "https://example.com/1", "author": "Alice", "source": "blog", "date": "2026-01-01"},
    ]
    with tempfile.TemporaryDirectory() as tmpdir:
        builder = IndexBuilder(output_dir=Path(tmpdir))
        meta = builder.build_static(docs)
        assert (Path(tmpdir) / "documents.json").exists()
        assert (Path(tmpdir) / "meta.json").exists()
        assert meta["total_indexed"] >= 1
