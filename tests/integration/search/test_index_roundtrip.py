"""Integration: write index to disk, reload, and verify search."""
import json
import sys
import tempfile
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent.parent)
sys.path.insert(0, _PROJECT_ROOT)

from lunr import lunr
from lunr.index import Index


def _build_and_serialize():
    docs = [
        {"id": "0", "title": "Rust borrow checker explained",
         "snippet": "ownership and lifetimes", "author": "Carol",
         "tags_text": "rust", "source": "blog"},
    ]
    idx = lunr(
        ref="id",
        fields=[
            {"field_name": "title", "boost": 10},
            {"field_name": "snippet", "boost": 2},
            {"field_name": "author", "boost": 3},
            {"field_name": "tags_text", "boost": 5},
            {"field_name": "source", "boost": 1},
        ],
        documents=docs,
    )
    return idx.serialize()


def test_roundtrip_via_disk():
    data = _build_and_serialize()
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "index.json"
        with open(path, "w") as f:
            json.dump(data, f)
        with open(path) as f:
            loaded = json.load(f)

    idx = Index.load(loaded)
    results = idx.search("rust")
    assert len(results) >= 1
    assert results[0]["ref"] == "0"
