import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from filters.slop_filter import SlopFilter


def test_empty_author_penalized():
    doc = {"title": "Some post", "snippet": "", "author": ""}
    _, rules = SlopFilter().score(doc)
    assert "no_real_author" in rules


def test_generic_author_penalized():
    doc = {"title": "Some post", "snippet": "", "author": "admin"}
    _, rules = SlopFilter().score(doc)
    assert "no_real_author" in rules


def test_real_author_passes():
    doc = {"title": "Some post", "snippet": "", "author": "Jane Doe"}
    _, rules = SlopFilter().score(doc)
    assert "no_real_author" not in rules
