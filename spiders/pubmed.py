"""
PubMed spider -- fetches biomedical literature via NCBI E-utilities.

API docs: https://www.ncbi.nlm.nih.gov/books/NBK25501/
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterator, List, Optional
from xml.etree import ElementTree as ET

from .base import HoleSpider, make_document

_EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
_CODE_RE = re.compile(r"algorithm|software|code|implementation", re.I)
_CITATION_RE = re.compile(r"\[\d+\]|PMID:\s*\d+|doi:", re.I)


class PubmedSpider(HoleSpider):
    """Crawl PubMed abstracts via NCBI E-utilities."""

    name = "pubmed"

    def __init__(
        self,
        query: str = "computer science[MeSH] OR bioinformatics[MeSH]",
        max_results: int = 200,
        **kwargs: Any,
    ):
        # NCBI requests max 3/sec without API key, 10/sec with
        super().__init__(rate=3.0, burst=3, **kwargs)
        self.query = query
        self.max_results = max_results
        import os
        self.api_key = os.environ.get("NCBI_API_KEY", "")

    # ------------------------------------------------------------------

    def _esearch(self) -> List[str]:
        """Return a list of PubMed IDs matching the query."""
        params: Dict[str, Any] = {
            "db": "pubmed",
            "term": self.query,
            "retmax": self.max_results,
            "retmode": "json",
            "sort": "date",
        }
        if self.api_key:
            params["api_key"] = self.api_key

        data = self.get_json(f"{_EUTILS}/esearch.fcgi", params=params)
        return data.get("esearchresult", {}).get("idlist", [])

    def _efetch(self, pmids: List[str]) -> str:
        """Fetch article XML for a batch of PMIDs."""
        params: Dict[str, Any] = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
        }
        if self.api_key:
            params["api_key"] = self.api_key
        return self.get_text(f"{_EUTILS}/efetch.fcgi", params=params)

    def fetch_items(self) -> Iterator[ET.Element]:
        cursor = self.load_cursor()
        seen_pmids: set = set(cursor.get("seen_pmids", []))
        new_pmids: List[str] = []

        pmids = self._esearch()
        pmids = [p for p in pmids if p not in seen_pmids]
        if not pmids:
            return

        # Fetch in batches of 200
        batch_size = 200
        for i in range(0, len(pmids), batch_size):
            batch = pmids[i : i + batch_size]
            xml_text = self._efetch(batch)
            root = ET.fromstring(xml_text)
            for article in root.findall(".//PubmedArticle"):
                pmid_el = article.find(".//PMID")
                if pmid_el is not None and pmid_el.text:
                    new_pmids.append(pmid_el.text)
                yield article

        all_seen = list(seen_pmids | set(new_pmids))[-10000:]
        self.save_cursor({"seen_pmids": all_seen})

    def parse(self, item: ET.Element) -> Optional[Dict[str, Any]]:
        article = item.find(".//Article")
        if article is None:
            return None

        # PMID
        pmid_el = item.find(".//PMID")
        pmid = pmid_el.text.strip() if pmid_el is not None and pmid_el.text else ""
        url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""

        # Title
        title_el = article.find(".//ArticleTitle")
        title = (title_el.text or "").strip() if title_el is not None else ""

        # Abstract
        abstract_parts: List[str] = []
        for abs_text in article.findall(".//AbstractText"):
            label = abs_text.get("Label", "")
            text = "".join(abs_text.itertext()).strip()
            if label:
                abstract_parts.append(f"{label}: {text}")
            else:
                abstract_parts.append(text)
        body = "\n".join(abstract_parts)

        # Authors
        authors: List[str] = []
        for auth in article.findall(".//Author"):
            last = auth.find("LastName")
            first = auth.find("ForeName")
            parts = []
            if last is not None and last.text:
                parts.append(last.text)
            if first is not None and first.text:
                parts.append(first.text)
            if parts:
                authors.append(" ".join(parts))

        # Date
        date = ""
        pub_date = article.find(".//PubDate")
        if pub_date is not None:
            year = pub_date.find("Year")
            month = pub_date.find("Month")
            day = pub_date.find("Day")
            parts = []
            if year is not None and year.text:
                parts.append(year.text)
            if month is not None and month.text:
                parts.append(month.text.zfill(2))
            if day is not None and day.text:
                parts.append(day.text.zfill(2))
            date = "-".join(parts)

        # MeSH terms as tags
        tags: List[str] = []
        for mesh in item.findall(".//MeshHeading/DescriptorName"):
            if mesh.text:
                tags.append(mesh.text.strip())

        # DOI
        outlinks: List[str] = []
        for eid in article.findall(".//ELocationID"):
            if eid.get("EIdType") == "doi" and eid.text:
                outlinks.append(f"https://doi.org/{eid.text.strip()}")

        has_code = bool(_CODE_RE.search(body))
        has_citations = bool(_CITATION_RE.search(body))

        return make_document(
            url=url,
            title=title,
            body=body,
            author="; ".join(authors),
            author_id=authors[0] if authors else "",
            source="pubmed",
            source_tier=1,
            date=date,
            tags=tags,
            lang="en",
            has_code=has_code,
            has_citations=has_citations,
            has_data=False,
            outlinks=outlinks,
        )
