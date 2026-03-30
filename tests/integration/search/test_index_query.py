"""Integration: build Lunr index from sample docs and search it."""
import sys
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent.parent)
sys.path.insert(0, _PROJECT_ROOT)

from lunr import lunr


def _make_docs():
    return [
        {"id": "0", "title": "Container networking on Linux",
         "snippet": "veth pairs and network namespaces",
         "author": "Alice", "tags_text": "linux containers", "source": "blog"},
        {"id": "1", "title": "Debugging memory leaks in Python",
         "snippet": "tracemalloc and objgraph tools",
         "author": "Bob", "tags_text": "python debugging", "source": "blog"},
    ]


def _build_index(docs):
    return lunr(
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


def test_search_finds_matching_doc():
    idx = _build_index(_make_docs())
    results = idx.search("container")
    refs = [r["ref"] for r in results]
    assert "0" in refs


def test_search_no_false_positives():
    idx = _build_index(_make_docs())
    results = idx.search("kubernetes")
    assert len(results) == 0
