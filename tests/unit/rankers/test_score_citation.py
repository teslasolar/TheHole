import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from rankers.ranker import HoleRanker


def test_t1_inlinks():
    doc = {"inlinks": {"tier1": 5, "tier2": 0}}
    score = HoleRanker().score_citation(doc)
    assert score == 75.0


def test_mixed_inlinks():
    doc = {"inlinks": {"tier1": 2, "tier2": 4}}
    score = HoleRanker().score_citation(doc)
    assert score == 50.0


def test_no_inlinks():
    doc = {}
    score = HoleRanker().score_citation(doc)
    assert score == 0.0
