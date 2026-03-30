import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from filters.slop_filter import SlopFilter


def test_listicle_title_penalized():
    doc = {"title": "10 Best VPNs for Privacy in 2026", "snippet": ""}
    score, rules = SlopFilter().score(doc)
    assert "listicle_title" in rules
    assert score < 0


def test_normal_title_passes():
    doc = {"title": "How DNS Works", "snippet": "", "author": "jsmith"}
    score, rules = SlopFilter().score(doc)
    assert "listicle_title" not in rules
