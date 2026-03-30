import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from filters.slop_filter import SlopFilter


def test_clean_doc_passes():
    doc = {"title": "Understanding eBPF", "snippet": "A deep look at eBPF.", "author": "Alice", "has_code": True, "has_citations": True}
    assert SlopFilter().should_index(doc) is True


def test_slop_doc_rejected():
    doc = {
        "title": "10 Best VPNs You Must Have",
        "snippet": "",
        "url": "https://www.buzzfeed.com/vpns",
        "author": "",
        "body": "Buy now! " * 20,
    }
    assert SlopFilter().should_index(doc) is False
