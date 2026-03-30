import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from filters.slop_filter import SlopFilter


def test_cta_flood_detected():
    ctas = "Buy now! Click here! Sign up now! Subscribe now! Act now! Hurry! Free trial! Don't miss out! Limited time offer!"
    doc = {"title": "Sale", "snippet": "", "body": ctas}
    score, rules = SlopFilter().score(doc)
    assert "cta_flood" in rules


def test_no_cta_clean():
    doc = {"title": "TCP internals", "snippet": "Explains SYN handshake", "body": "The SYN packet initiates a connection.", "author": "jdoe"}
    _, rules = SlopFilter().score(doc)
    assert "cta_flood" not in rules
    assert "cta_heavy" not in rules
