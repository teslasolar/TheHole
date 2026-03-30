"""Parametrized affiliate link detection using shared params."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from filters.affiliate_detect import count_affiliate_links

def test_each_affiliate_url_detected(affiliate_urls):
    for url in affiliate_urls:
        text = f'Visit <a href="{url}">link</a> for details.'
        assert count_affiliate_links(text) >= 1, f"'{url}' not detected"

def test_all_affiliates_combined(affiliate_urls):
    text = " ".join(f'<a href="{u}">link</a>' for u in affiliate_urls)
    count = count_affiliate_links(text)
    assert count >= len(affiliate_urls) - 1, f"Expected {len(affiliate_urls)}, got {count}"
