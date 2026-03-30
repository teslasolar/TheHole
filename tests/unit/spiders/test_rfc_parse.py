import sys
sys.path.insert(0, "/home/user/TheHole")
from xml.etree import ElementTree as ET
from spiders.rfc import RfcSpider

NS = "http://www.rfc-editor.org/rfc-index"
SAMPLE_XML = f"""<rfc-entry xmlns="{NS}">
  <doc-id>RFC9110</doc-id>
  <title>HTTP Semantics</title>
  <abstract><p>This document defines HTTP semantics [RFC7230].</p></abstract>
  <author><name>R. Fielding</name></author>
  <date><year>2022</year><month>June</month></date>
</rfc-entry>"""


def test_parse_basic():
    spider = RfcSpider.__new__(RfcSpider)
    spider.fetch_full_text = False
    el = ET.fromstring(SAMPLE_XML)
    doc = spider.parse(el)
    assert doc["title"] == "RFC 9110: HTTP Semantics"
    assert doc["source"] == "rfc"
    assert doc["source_tier"] == 1
    assert doc["has_citations"] is True
    assert "rfc" in doc["tags"]
