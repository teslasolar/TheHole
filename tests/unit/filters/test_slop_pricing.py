import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from filters.slop_filter import SlopFilter


def test_pricing_page_detected():
    doc = {
        "title": "Pricing Plans",
        "snippet": "",
        "url": "https://example.com/pricing",
        "body": "Basic plan $9.99/mo. Pro plan $29.99/mo. Compare plans. Start your free trial.",
        "author": "sales",
    }
    score, rules = SlopFilter().score(doc)
    assert any("pricing" in r for r in rules)


def test_no_pricing_signals():
    doc = {"title": "How TCP Works", "snippet": "Networking basics.", "author": "dev"}
    _, rules = SlopFilter().score(doc)
    assert not any("pricing" in r for r in rules)
