import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from rankers.ranker import HoleRanker


def test_short_doc_low():
    doc = {"word_count": 100}
    score = HoleRanker().score_depth(doc)
    assert score < 15


def test_long_with_code_and_citations():
    doc = {"word_count": 2000, "has_code": True, "has_citations": True, "heading_depth": 3}
    score = HoleRanker().score_depth(doc)
    assert score >= 70
