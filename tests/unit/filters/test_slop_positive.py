import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from filters.slop_filter import SlopFilter


def test_has_code_bonus():
    doc = {"title": "Post", "snippet": "", "has_code": True, "author": "dev"}
    _, rules = SlopFilter().score(doc)
    assert "+has_code" in rules


def test_has_citations_bonus():
    doc = {"title": "Post", "snippet": "", "has_citations": True, "author": "dev"}
    _, rules = SlopFilter().score(doc)
    assert "+cites_papers" in rules


def test_documents_failure_bonus():
    doc = {"title": "Our postmortem on the outage", "snippet": "what went wrong", "author": "dev"}
    _, rules = SlopFilter().score(doc)
    assert "+documents_failure" in rules
