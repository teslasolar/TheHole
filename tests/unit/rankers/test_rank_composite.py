import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from rankers.ranker import HoleRanker, WEIGHTS


def test_returns_all_keys():
    doc = {"title": "Test", "snippet": "", "author": "dev", "date": "2026-01-01T00:00:00Z"}
    result = HoleRanker().rank(doc)
    assert "composite" in result
    assert "scores" in result
    for key in WEIGHTS:
        assert key in result["scores"]


def test_weighted_sum_correct():
    doc = {"title": "Test", "snippet": "", "author": "dev"}
    result = HoleRanker().rank(doc)
    expected = sum(result["scores"][k] * WEIGHTS[k] for k in WEIGHTS)
    assert abs(result["composite"] - round(expected, 2)) < 0.01
