import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from rankers.ranker import HoleRanker


def test_sorted_descending():
    docs = [
        {"title": "Low", "snippet": "", "word_count": 50},
        {"title": "High", "snippet": "", "word_count": 3000, "has_code": True, "has_citations": True, "author": "dev", "author_id": "ghuser", "author_meta": {"github_repos": 20}, "source_tier": 1, "date": "2026-03-01T00:00:00Z"},
    ]
    ranked = HoleRanker().rank_many(docs)
    assert len(ranked) == 2
    assert ranked[0][1]["composite"] >= ranked[1][1]["composite"]
    assert ranked[0][0]["title"] == "High"
