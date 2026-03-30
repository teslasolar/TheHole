import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from rankers.ranker import HoleRanker


def test_github_repos_boost():
    doc = {"author_meta": {"github_repos": 15}, "author_id": "devuser"}
    score = HoleRanker().score_practitioner(doc)
    assert score >= 35


def test_no_signals_zero():
    doc = {}
    score = HoleRanker().score_practitioner(doc)
    assert score == 0.0


def test_capped_at_100():
    doc = {
        "author_meta": {"github_repos": 100, "github_commits": 1000, "papers": 30},
        "has_code": True,
        "author_id": "superdev",
    }
    score = HoleRanker().score_practitioner(doc)
    assert score == 100.0
