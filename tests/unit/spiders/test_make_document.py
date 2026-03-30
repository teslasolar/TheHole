import sys, hashlib
sys.path.insert(0, "/home/user/TheHole")
from spiders.base import make_document


def test_snippet_truncated_to_300():
    body = "a" * 500
    doc = make_document(url="http://x", title="T", body=body)
    assert len(doc["snippet"]) == 300


def test_body_hash_is_sha256():
    body = "hello world"
    doc = make_document(url="http://x", title="T", body=body)
    expected = hashlib.sha256(body.encode("utf-8")).hexdigest()
    assert doc["body_hash"] == expected


def test_empty_body():
    doc = make_document(url="http://x", title="T", body="")
    assert doc["snippet"] == ""
    assert doc["body_hash"] == ""
    assert doc["word_count"] == 0
