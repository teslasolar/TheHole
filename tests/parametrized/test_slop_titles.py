"""Parametrized slop filter title tests using shared params."""
import pytest

def test_listicle_titles_penalized(slop_filter, listicle_titles, slop_doc):
    for title in listicle_titles:
        slop_doc["title"] = title
        score, rules = slop_filter.score(slop_doc)
        assert score < -15, f"{title} should be penalized"

def test_clean_titles_pass(slop_filter, clean_titles, clean_doc):
    for title in clean_titles:
        clean_doc["title"] = title
        score, rules = slop_filter.score(clean_doc)
        assert not any("listicle" in r for r in rules), f"{title} should pass"
