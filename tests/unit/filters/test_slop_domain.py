import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from filters.slop_filter import SlopFilter


def test_blacklisted_domain_detected():
    doc = {"title": "X", "snippet": "", "url": "https://www.buzzfeed.com/article/123"}
    score, rules = SlopFilter().score(doc)
    assert any("known_farm" in r for r in rules)
    assert score <= -50


def test_clean_domain_passes():
    doc = {"title": "X", "snippet": "", "url": "https://jvns.ca/blog/post", "author": "Julia"}
    _, rules = SlopFilter().score(doc)
    assert not any("known_farm" in r for r in rules)
