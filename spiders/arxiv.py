"""
arXiv spider -- fetches papers via the Atom/XML API.

API docs: https://info.arxiv.org/help/api/basics.html
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterator, List, Optional
from xml.etree import ElementTree as ET

from .base import HoleSpider, make_document

_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}

_CODE_INDICATORS = re.compile(
    r"(algorithm|implementation|code|github\.com|sourcecode)", re.I
)
_CITATION_INDICATORS = re.compile(r"\[\d+\]|\\cite\{|references", re.I)


class ArxivSpider(HoleSpider):
    """Crawl arXiv papers via the Atom API."""

    name = "arxiv"

    def __init__(
        self,
        query: str = "cat:cs.*",
        max_results: int = 200,
        sort_by: str = "submittedDate",
        sort_order: str = "descending",
        **kwargs: Any,
    ):
        super().__init__(rate=0.33, burst=1, **kwargs)  # 1 req / 3 s per arXiv policy
        self.api_url = "http://export.arxiv.org/api/query"
        self.query = query
        self.max_results = max_results
        self.sort_by = sort_by
        self.sort_order = sort_order

    # ------------------------------------------------------------------

    def fetch_items(self) -> Iterator[ET.Element]:
        cursor = self.load_cursor()
        start = cursor.get("start", 0)
        page_size = 100
        fetched = 0

        while fetched < self.max_results:
            count = min(page_size, self.max_results - fetched)
            params = {
                "search_query": self.query,
                "start": start + fetched,
                "max_results": count,
                "sortBy": self.sort_by,
                "sortOrder": self.sort_order,
            }
            text = self.get_text(self.api_url, params=params)
            root = ET.fromstring(text)
            entries = root.findall("atom:entry", _NS)
            if not entries:
                break
            for entry in entries:
                yield entry
                fetched += 1

        self.save_cursor({"start": start + fetched})

    def parse(self, item: ET.Element) -> Optional[Dict[str, Any]]:
        title_el = item.find("atom:title", _NS)
        summary_el = item.find("atom:summary", _NS)
        published_el = item.find("atom:published", _NS)
        link_el = item.find("atom:id", _NS)

        if title_el is None or link_el is None:
            return None

        title = " ".join((title_el.text or "").split())
        body = (summary_el.text or "").strip() if summary_el is not None else ""
        url = (link_el.text or "").strip()
        date = (published_el.text or "").strip() if published_el is not None else ""

        # Authors
        authors: List[str] = []
        for author_el in item.findall("atom:author", _NS):
            name_el = author_el.find("atom:name", _NS)
            if name_el is not None and name_el.text:
                authors.append(name_el.text.strip())

        # Categories as tags
        tags: List[str] = []
        for cat_el in item.findall("atom:category", _NS):
            term = cat_el.get("term", "")
            if term:
                tags.append(term)

        # Outlinks (PDF, DOI)
        outlinks: List[str] = []
        for link in item.findall("atom:link", _NS):
            href = link.get("href", "")
            if href and href != url:
                outlinks.append(href)

        doi_el = item.find("arxiv:doi", _NS)
        if doi_el is not None and doi_el.text:
            outlinks.append(f"https://doi.org/{doi_el.text.strip()}")

        has_code = bool(_CODE_INDICATORS.search(body))
        has_citations = bool(_CITATION_INDICATORS.search(body))

        return make_document(
            url=url,
            title=title,
            body=body,
            author="; ".join(authors),
            author_id=authors[0] if authors else "",
            source="arxiv",
            source_tier=1,
            date=date,
            tags=tags,
            lang="en",
            has_code=has_code,
            has_citations=has_citations,
            has_data=False,
            outlinks=outlinks,
        )
