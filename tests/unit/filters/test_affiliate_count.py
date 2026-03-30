import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from filters.affiliate_detect import count_affiliate_links


def test_amazon_tag_detected():
    text = "Check this https://amazon.com/dp/B08?tag=myblog-20"
    assert count_affiliate_links(text) >= 1


def test_multiple_patterns():
    text = "Visit https://amzn.to/abc and https://go.skimresources.com/foo"
    assert count_affiliate_links(text) >= 2


def test_clean_text():
    text = "How to configure DNS on Linux using systemd-resolved."
    assert count_affiliate_links(text) == 0
