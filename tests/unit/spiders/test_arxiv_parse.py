import sys
sys.path.insert(0, "/home/user/TheHole")
from xml.etree import ElementTree as ET
from spiders.arxiv import ArxivSpider

SAMPLE_XML = """<entry xmlns="http://www.w3.org/2005/Atom">
  <id>http://arxiv.org/abs/2301.00001v1</id>
  <title>Test Paper</title>
  <summary>A sample abstract about algorithm implementation.</summary>
  <published>2023-01-01T00:00:00Z</published>
  <author><name>Alice</name></author>
  <category term="cs.AI"/>
</entry>"""


def test_parse_basic():
    spider = ArxivSpider.__new__(ArxivSpider)
    entry = ET.fromstring(SAMPLE_XML)
    doc = spider.parse(entry)
    assert doc["title"] == "Test Paper"
    assert doc["source"] == "arxiv"
    assert doc["source_tier"] == 1
    assert "cs.AI" in doc["tags"]
    assert doc["has_code"] is True
