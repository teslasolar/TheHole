import sys
sys.path.insert(0, "/home/user/TheHole")
from spiders.github import GithubSpider

SAMPLE = {
    "full_name": "owner/repo",
    "html_url": "https://github.com/owner/repo",
    "description": "A cool project",
    "owner": {"login": "owner", "id": 123},
    "pushed_at": "2023-06-01T00:00:00Z",
    "topics": ["cli"],
    "language": "Python",
    "homepage": "https://example.com",
}


def test_parse_basic():
    spider = GithubSpider.__new__(GithubSpider)
    spider.fetch_readme = False
    doc = spider.parse(SAMPLE)
    assert doc["title"] == "owner/repo"
    assert doc["source"] == "github"
    assert doc["has_code"] is True
    assert "python" in doc["tags"]
    assert "https://example.com" in doc["outlinks"]
