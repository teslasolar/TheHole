"""Tests for the SlopFilter."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from filters.slop_filter import SlopFilter

_FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _load_fixture(name: str) -> dict:
    with open(_FIXTURES / name) as f:
        return json.load(f)


@pytest.fixture
def filt():
    return SlopFilter()


@pytest.fixture
def clean_doc():
    return _load_fixture("sample_clean_doc.json")


@pytest.fixture
def slop_doc():
    return _load_fixture("sample_slop_doc.json")


# ---------------------------------------------------------------------------
# Basic scoring
# ---------------------------------------------------------------------------


class TestBasicScoring:
    def test_clean_doc_scores_near_zero_or_positive(self, filt, clean_doc):
        score, rules = filt.score(clean_doc)
        # Clean doc should have positive bonuses and no major penalties
        assert score >= -10, f"Clean doc scored {score}, rules: {rules}"

    def test_slop_doc_scores_below_threshold(self, filt, slop_doc):
        score, rules = filt.score(slop_doc)
        assert score < -30, f"Slop doc scored {score}, rules: {rules}"

    def test_clean_doc_should_index(self, filt, clean_doc):
        assert filt.should_index(clean_doc) is True

    def test_slop_doc_should_not_index(self, filt, slop_doc):
        assert filt.should_index(slop_doc) is False

    def test_empty_doc_scores_reasonably(self, filt):
        doc = {"url": "", "title": "", "snippet": ""}
        score, rules = filt.score(doc)
        # Empty doc gets a no_real_author penalty but not catastrophic
        assert isinstance(score, int)


# ---------------------------------------------------------------------------
# Individual rule triggers
# ---------------------------------------------------------------------------


class TestListicleDetection:
    def test_listicle_title_triggers(self, filt):
        doc = {"title": "10 Best Ways to Cook Pasta", "snippet": "Some content."}
        score, rules = filt.score(doc)
        assert "listicle_title" in rules

    def test_non_listicle_title_no_trigger(self, filt):
        doc = {"title": "How DNS Resolution Works", "snippet": "Some content."}
        _, rules = filt.score(doc)
        assert "listicle_title" not in rules

    def test_listicle_variants(self, filt):
        for title in [
            "15 Top Tools for DevOps",
            "7 Amazing JavaScript Libraries",
            "20 Must-Have Plugins",
            "5 Essential Tips for Python",
        ]:
            _, rules = filt.score({"title": title, "snippet": ""})
            assert "listicle_title" in rules, f"Should trigger for: {title}"


class TestAffiliateDensity:
    def test_heavy_affiliate_triggers(self, filt, slop_doc):
        _, rules = filt.score(slop_doc)
        assert any(r.startswith("affiliate") for r in rules)

    def test_no_affiliates_clean(self, filt):
        doc = {
            "title": "A guide",
            "snippet": "Content without affiliate links.",
            "body": "Just normal content here.",
            "outlinks": ["https://example.com", "https://docs.python.org"],
            "author": "Real Person",
        }
        _, rules = filt.score(doc)
        assert not any(r.startswith("affiliate") for r in rules)


class TestKeywordStuffing:
    def test_stuffed_content_triggers(self, filt):
        # Create content where one keyword dominates
        doc = {
            "title": "VPN Review",
            "snippet": "",
            "body": " ".join(["vpn"] * 50 + ["other"] * 10),
            "author": "Someone",
        }
        _, rules = filt.score(doc)
        assert "keyword_stuffing" in rules or "keyword_dense" in rules


class TestCTAFlood:
    def test_cta_flood_triggers(self, filt, slop_doc):
        _, rules = filt.score(slop_doc)
        assert "cta_flood" in rules or "cta_heavy" in rules

    def test_no_cta_in_clean_doc(self, filt, clean_doc):
        _, rules = filt.score(clean_doc)
        assert "cta_flood" not in rules
        assert "cta_heavy" not in rules


class TestAuthorSignals:
    def test_no_author_triggers(self, filt):
        doc = {"title": "Test", "snippet": "Content", "author": ""}
        _, rules = filt.score(doc)
        assert "no_real_author" in rules

    def test_generic_author_triggers(self, filt):
        for name in ["admin", "Staff", "Editor", "contributor", "Guest"]:
            doc = {"title": "Test", "snippet": "Content", "author": name}
            _, rules = filt.score(doc)
            assert "no_real_author" in rules, f"Should trigger for author='{name}'"

    def test_real_author_no_trigger(self, filt):
        doc = {"title": "Test", "snippet": "Content", "author": "Julia Evans"}
        _, rules = filt.score(doc)
        assert "no_real_author" not in rules

    def test_content_mill_numeric_id(self, filt):
        doc = {"title": "Test", "snippet": "Content", "author": "Writer", "author_id": "99281"}
        _, rules = filt.score(doc)
        assert "content_mill_author_id" in rules


class TestDomainSignals:
    def test_known_farm_triggers(self, filt):
        doc = {"url": "https://www.buzzdaily.com/article", "title": "Test", "snippet": ""}
        _, rules = filt.score(doc)
        assert any(r.startswith("known_farm") for r in rules)

    def test_clean_domain_no_trigger(self, filt):
        doc = {"url": "https://jvns.ca/blog/post", "title": "Test", "snippet": ""}
        _, rules = filt.score(doc)
        assert not any(r.startswith("known_farm") for r in rules)

    def test_subdomain_of_farm(self, filt):
        doc = {"url": "https://tech.ezinearticles.com/article", "title": "Test", "snippet": ""}
        _, rules = filt.score(doc)
        assert any(r.startswith("known_farm") for r in rules)

    def test_contributor_network_tag(self, filt):
        doc = {"url": "https://example.com/post", "title": "Test", "snippet": "", "tags": ["sponsored"]}
        _, rules = filt.score(doc)
        assert "contributor_network_tag" in rules

    def test_contributor_network_url(self, filt):
        doc = {"url": "https://example.com/sponsored/post", "title": "Test", "snippet": ""}
        _, rules = filt.score(doc)
        assert "contributor_network_url" in rules


class TestLLMDetection:
    def test_heavy_llm_markers(self, filt, slop_doc):
        _, rules = filt.score(slop_doc)
        assert any("llm_" in r for r in rules)

    def test_clean_doc_no_llm(self, filt, clean_doc):
        _, rules = filt.score(clean_doc)
        # Clean doc might trigger a few common words but shouldn't be "heavy"
        assert not any("llm_heavy" in r for r in rules)


class TestCommercialIntent:
    def test_pricing_page_triggers(self, filt):
        doc = {
            "title": "Pricing Plans",
            "snippet": "",
            "body": "Compare plans. $9.99/mo for Basic plan. $29.99/mo for Pro plan. Start your free trial. Money-back guarantee.",
            "url": "https://example.com/pricing",
            "author": "Company",
        }
        _, rules = filt.score(doc)
        assert "pricing_page" in rules or "pricing_url" in rules


# ---------------------------------------------------------------------------
# Positive signals
# ---------------------------------------------------------------------------


class TestPositiveSignals:
    def test_has_code_bonus(self, filt):
        doc = {"title": "Test", "snippet": "", "has_code": True, "author": "Dev"}
        score_with, rules_with = filt.score(doc)
        doc_without = {"title": "Test", "snippet": "", "has_code": False, "author": "Dev"}
        score_without, _ = filt.score(doc_without)
        assert score_with > score_without
        assert "+has_code" in rules_with

    def test_cites_papers_bonus(self, filt):
        doc = {"title": "Test", "snippet": "", "has_citations": True, "author": "Researcher"}
        _, rules = filt.score(doc)
        assert "+cites_papers" in rules

    def test_documents_failure_bonus(self, filt):
        doc = {"title": "Post-mortem: Our Database Outage", "snippet": "What went wrong with our deployment.", "author": "Engineer"}
        _, rules = filt.score(doc)
        assert "+documents_failure" in rules

    def test_author_has_repos_bonus(self, filt):
        doc = {"title": "Test", "snippet": "", "author": "Dev", "author_id": "jvns"}
        _, rules = filt.score(doc)
        assert "+author_has_repos" in rules

    def test_shows_data_bonus(self, filt):
        doc = {"title": "Test", "snippet": "", "has_data": True, "author": "Analyst"}
        _, rules = filt.score(doc)
        assert "+shows_data" in rules

    def test_all_positive_signals_stack(self, filt):
        doc = {
            "title": "Post-mortem: Production Failure",
            "snippet": "What went wrong and lessons learned.",
            "author": "Julia Evans",
            "author_id": "jvns",
            "has_code": True,
            "has_citations": True,
            "has_data": True,
        }
        score, rules = filt.score(doc)
        positive_rules = [r for r in rules if r.startswith("+")]
        assert len(positive_rules) >= 4
        # With all bonuses, score should be well positive
        assert score > 0


# ---------------------------------------------------------------------------
# Threshold configuration
# ---------------------------------------------------------------------------


class TestThreshold:
    def test_custom_threshold(self):
        strict = SlopFilter(threshold=0)
        lenient = SlopFilter(threshold=-100)
        doc = {"title": "Test", "snippet": "Meh content.", "author": ""}
        # no_real_author = -10, so score is around -10
        assert strict.should_index(doc) is False
        assert lenient.should_index(doc) is True
