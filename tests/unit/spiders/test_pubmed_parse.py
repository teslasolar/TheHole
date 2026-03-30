import sys
sys.path.insert(0, "/home/user/TheHole")
from xml.etree import ElementTree as ET
from spiders.pubmed import PubmedSpider

SAMPLE_XML = """<PubmedArticle>
  <MedlineCitation>
    <PMID>12345678</PMID>
    <Article>
      <ArticleTitle>Test Study</ArticleTitle>
      <Abstract><AbstractText>Results about algorithm.</AbstractText></Abstract>
      <AuthorList><Author><LastName>Smith</LastName><ForeName>John</ForeName></Author></AuthorList>
      <Journal><JournalIssue><PubDate><Year>2023</Year><Month>06</Month></PubDate></JournalIssue></Journal>
    </Article>
  </MedlineCitation>
</PubmedArticle>"""


def test_parse_basic():
    spider = PubmedSpider.__new__(PubmedSpider)
    el = ET.fromstring(SAMPLE_XML)
    doc = spider.parse(el)
    assert doc["title"] == "Test Study"
    assert doc["source"] == "pubmed"
    assert "12345678" in doc["url"]
    assert doc["has_code"] is True
