"""Tests for the HoleRanker."""

from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rankers.ranker import HoleRanker, FRESHNESS_HALF_LIFE_DAYS, TIER_SCORES

_FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _load_fixture(name: str) -> dict:
    with open(_FIXTURES / name) as f:
        return json.load(f)


@pytest.fixture
def ranker():
    return HoleRanker()


@pytest.fixture
def clean_doc():
    return _load_fixture("sample_clean_doc.json")


# ---------------------------------------------------------------------------
# Practitioner scoring
# ---------------------------------------------------------------------------


class TestPractitionerScoring:
    def test_github_repos_boost(self, ranker):
        doc = {"author_meta": {"github_repos": 50, "github_commits": 0, "papers": 0}}
        score = ranker.score_practitioner(doc)
        assert score >= 45  # 20 + 15 + 10

    def test_github_commits_boost(self, ranker):
        doc = {"author_meta": {"github_repos": 0, "github_commits": 600, "papers": 0}}
        score = ranker.score_practitioner(doc)
        assert score >= 25  # 10 + 10 + 5

    def test_papers_boost(self, ranker):
        doc = {"author_meta": {"github_repos": 0, "github_commits": 0, "papers": 25}}
        score = ranker.score_practitioner(doc)
        assert score >= 30  # 15 + 10 + 5

    def test_has_code_boost(self, ranker):
        doc_with = {"has_code": True, "author_meta": {}}
        doc_without = {"has_code": False, "author_meta": {}}
        assert ranker.score_practitioner(doc_with) > ranker.score_practitioner(doc_without)

    def test_author_id_boost(self, ranker):
        doc = {"author_id": "jvns", "author_meta": {}}
        score = ranker.score_practitioner(doc)
        assert score >= 10

    def test_no_signals_scores_zero(self, ranker):
        doc = {"author_meta": {}}
        assert ranker.score_practitioner(doc) == 0.0

    def test_full_practitioner(self, ranker, clean_doc):
        score = ranker.score_practitioner(clean_doc)
        # jvns: 45 repos, 1200 commits, has_code, valid author_id
        assert score >= 60

    def test_capped_at_100(self, ranker):
        doc = {
            "author_meta": {"github_repos": 100, "github_commits": 1000, "papers": 50},
            "has_code": True,
            "author_id": "superdev",
        }
        assert ranker.score_practitioner(doc) == 100.0


# ---------------------------------------------------------------------------
# Citation scoring
# ---------------------------------------------------------------------------


class TestCitationScoring:
    def test_tier1_inlinks(self, ranker):
        doc = {"inlinks": {"tier1": 5, "tier2": 0}}
        assert ranker.score_citation(doc) == 75.0  # 5 * 15

    def test_tier2_inlinks(self, ranker):
        doc = {"inlinks": {"tier1": 0, "tier2": 10}}
        assert ranker.score_citation(doc) == 50.0  # 10 * 5

    def test_combined_inlinks(self, ranker):
        doc = {"inlinks": {"tier1": 3, "tier2": 5}}
        assert ranker.score_citation(doc) == 70.0  # 3*15 + 5*5

    def test_capped_at_100(self, ranker):
        doc = {"inlinks": {"tier1": 10, "tier2": 20}}
        assert ranker.score_citation(doc) == 100.0

    def test_no_inlinks(self, ranker):
        doc = {}
        assert ranker.score_citation(doc) == 0.0

    def test_clean_doc_citation(self, ranker, clean_doc):
        # tier1=3, tier2=8 => 3*15 + 8*5 = 85
        assert ranker.score_citation(clean_doc) == 85.0


# ---------------------------------------------------------------------------
# Freshness scoring
# ---------------------------------------------------------------------------


class TestFreshnessScoring:
    def test_today_scores_100(self, ranker):
        now = datetime(2024, 6, 1, tzinfo=timezone.utc)
        doc = {"date": "2024-06-01T00:00:00Z"}
        score = ranker.score_freshness(doc, now=now)
        assert abs(score - 100.0) < 0.1

    def test_half_life_decay(self, ranker):
        now = datetime(2024, 6, 1, tzinfo=timezone.utc)
        past = now - timedelta(days=FRESHNESS_HALF_LIFE_DAYS)
        doc = {"date": past.strftime("%Y-%m-%dT%H:%M:%SZ")}
        score = ranker.score_freshness(doc, now=now)
        assert abs(score - 50.0) < 1.0

    def test_double_half_life(self, ranker):
        now = datetime(2024, 6, 1, tzinfo=timezone.utc)
        past = now - timedelta(days=FRESHNESS_HALF_LIFE_DAYS * 2)
        doc = {"date": past.strftime("%Y-%m-%dT%H:%M:%SZ")}
        score = ranker.score_freshness(doc, now=now)
        assert abs(score - 25.0) < 1.0

    def test_no_date_gets_default(self, ranker):
        doc = {"date": ""}
        assert ranker.score_freshness(doc) == 25.0

    def test_invalid_date_gets_default(self, ranker):
        doc = {"date": "not-a-date"}
        assert ranker.score_freshness(doc) == 25.0

    def test_very_old_approaches_zero(self, ranker):
        now = datetime(2024, 6, 1, tzinfo=timezone.utc)
        doc = {"date": "2010-01-01T00:00:00Z"}
        score = ranker.score_freshness(doc, now=now)
        assert score < 1.0


# ---------------------------------------------------------------------------
# Depth scoring
# ---------------------------------------------------------------------------


class TestDepthScoring:
    def test_short_content(self, ranker):
        doc = {"word_count": 100}
        assert ranker.score_depth(doc) == 0.0

    def test_medium_content(self, ranker):
        doc = {"word_count": 900}
        score = ranker.score_depth(doc)
        assert score == 25.0  # 10 + 15

    def test_long_content_with_extras(self, ranker):
        doc = {
            "word_count": 3500,
            "has_code": True,
            "has_citations": True,
            "has_data": True,
            "heading_depth": 3,
        }
        score = ranker.score_depth(doc)
        # 10 + 15 + 15 + 10 + 15 + 15 + 10 + 10 = 100
        assert score == 100.0

    def test_heading_depth(self, ranker):
        doc2 = {"word_count": 0, "heading_depth": 2}
        doc3 = {"word_count": 0, "heading_depth": 3}
        assert ranker.score_depth(doc2) == 5.0
        assert ranker.score_depth(doc3) == 10.0


# ---------------------------------------------------------------------------
# Source tier scoring
# ---------------------------------------------------------------------------


class TestSourceTierScoring:
    def test_all_tiers(self, ranker):
        for tier, expected in TIER_SCORES.items():
            doc = {"source_tier": tier}
            assert ranker.score_source_tier(doc) == float(expected)

    def test_default_tier(self, ranker):
        doc = {}
        assert ranker.score_source_tier(doc) == 40.0  # defaults to T3


# ---------------------------------------------------------------------------
# Composite ranking
# ---------------------------------------------------------------------------


class TestCompositeRanking:
    def test_rank_returns_all_keys(self, ranker, clean_doc):
        result = ranker.rank(clean_doc)
        assert "composite" in result
        assert "scores" in result
        for key in ("slop", "practitioner", "citation", "freshness", "depth", "source_tier"):
            assert key in result["scores"]

    def test_composite_is_weighted_sum(self, ranker):
        # Create a doc where we can predict sub-scores
        doc = {
            "title": "Test",
            "snippet": "Content",
            "author": "Dev",
            "author_id": "devuser",
            "source_tier": 1,
            "date": "",
            "word_count": 0,
            "has_code": False,
            "has_citations": False,
            "has_data": False,
        }
        result = ranker.rank(doc)
        scores = result["scores"]
        weights = ranker.weights
        expected = sum(scores[k] * weights[k] for k in weights)
        assert abs(result["composite"] - round(expected, 2)) < 0.01

    def test_rank_many_sorted(self, ranker):
        docs = [
            {"title": "Bad", "snippet": "", "source_tier": 4, "date": "2020-01-01T00:00:00Z"},
            {"title": "Good", "snippet": "", "source_tier": 1, "author": "Dev", "author_id": "devuser",
             "has_code": True, "has_citations": True, "word_count": 2000, "date": "2024-01-01T00:00:00Z"},
        ]
        ranked = ranker.rank_many(docs)
        assert ranked[0][0]["title"] == "Good"
        assert ranked[1][0]["title"] == "Bad"
        assert ranked[0][1]["composite"] >= ranked[1][1]["composite"]

    def test_clean_doc_scores_high(self, ranker, clean_doc):
        result = ranker.rank(clean_doc)
        assert result["composite"] > 50
