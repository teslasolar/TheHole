import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from rankers.ranker import HoleRanker


def test_tier1():
    assert HoleRanker().score_source_tier({"source_tier": 1}) == 100.0

def test_tier2():
    assert HoleRanker().score_source_tier({"source_tier": 2}) == 70.0

def test_tier3():
    assert HoleRanker().score_source_tier({"source_tier": 3}) == 40.0

def test_tier4():
    assert HoleRanker().score_source_tier({"source_tier": 4}) == 10.0
