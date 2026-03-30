import sys
sys.path.insert(0, "/home/user/TheHole")
from spiders.base import make_document


def test_tags_default_empty_list():
    doc = make_document(url="http://x", title="T", body="w")
    assert doc["tags"] == []


def test_lang_default_en():
    doc = make_document(url="http://x", title="T", body="w")
    assert doc["lang"] == "en"


def test_source_tier_default():
    doc = make_document(url="http://x", title="T", body="w")
    assert doc["source_tier"] == 3


def test_outlinks_default_empty():
    doc = make_document(url="http://x", title="T", body="w")
    assert doc["outlinks"] == []
