import sys
sys.path.insert(0, "/home/user/TheHole")
from spiders.stackoverflow import StackOverflowSpider

SAMPLE = {
    "answer_id": 999,
    "question_id": 100,
    "body": "<p>Use <code>x = 1</code></p>",
    "owner": {"display_name": "Bob", "user_id": 42},
    "last_activity_date": 1672531200,
    "tags": ["python"],
}


def test_parse_basic():
    spider = StackOverflowSpider.__new__(StackOverflowSpider)
    doc = spider.parse(SAMPLE)
    assert doc["source"] == "stackoverflow"
    assert "999" in doc["url"]
    assert doc["has_code"] is True
    assert doc["author"] == "Bob"


def test_parse_tags():
    spider = StackOverflowSpider.__new__(StackOverflowSpider)
    doc = spider.parse(SAMPLE)
    assert "python" in doc["tags"]
