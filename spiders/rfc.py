"""
RFC spider -- parses IETF RFC index and fetches RFC text.

Uses the rfc-index.xml maintained by IETF and fetches individual RFCs
from https://www.rfc-editor.org/rfc/rfcNNNN.txt
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterator, List, Optional
from xml.etree import ElementTree as ET

from .base import HoleSpider, make_document

_RFC_INDEX_URL = "https://www.rfc-editor.org/rfc-index.xml"
_RFC_TEXT_URL = "https://www.rfc-editor.org/rfc/rfc{number}.txt"
_NS = {"": "http://www.rfc-editor.org/rfc-index"}
_CODE_RE = re.compile(r"ABNF|pseudo-?code|algorithm|implementation", re.I)
_CITATION_RE = re.compile(r"\[RFC\d+\]|\[[\w-]+\]")


class RfcSpider(HoleSpider):
    """Crawl IETF RFCs."""

    name = "rfc"

    def __init__(
        self,
        max_results: int = 200,
        fetch_full_text: bool = False,
        **kwargs: Any,
    ):
        super().__init__(rate=2.0, burst=5, **kwargs)
        self.max_results = max_results
        self.fetch_full_text = fetch_full_text

    # ------------------------------------------------------------------

    def fetch_items(self) -> Iterator[ET.Element]:
        cursor = self.load_cursor()
        last_rfc = cursor.get("last_rfc_number", 0)

        text = self.get_text(_RFC_INDEX_URL)
        root = ET.fromstring(text)

        entries = root.findall("{http://www.rfc-editor.org/rfc-index}rfc-entry")
        # Sort by doc-id number descending (newest first)
        def _rfc_num(el: ET.Element) -> int:
            doc_id = el.find("{http://www.rfc-editor.org/rfc-index}doc-id")
            if doc_id is not None and doc_id.text:
                m = re.search(r"\d+", doc_id.text)
                return int(m.group()) if m else 0
            return 0

        entries.sort(key=_rfc_num, reverse=True)

        count = 0
        max_num = last_rfc
        for entry in entries:
            num = _rfc_num(entry)
            if num <= last_rfc:
                continue
            if count >= self.max_results:
                break
            if num > max_num:
                max_num = num
            yield entry
            count += 1

        if max_num > last_rfc:
            self.save_cursor({"last_rfc_number": max_num})

    def parse(self, item: ET.Element) -> Optional[Dict[str, Any]]:
        ns = "{http://www.rfc-editor.org/rfc-index}"

        doc_id_el = item.find(f"{ns}doc-id")
        if doc_id_el is None or not doc_id_el.text:
            return None
        doc_id = doc_id_el.text.strip()
        m = re.search(r"\d+", doc_id)
        number = m.group() if m else ""

        title_el = item.find(f"{ns}title")
        title = (title_el.text or "").strip() if title_el is not None else ""

        # Abstract
        abstract_el = item.find(f"{ns}abstract")
        if abstract_el is not None:
            body = "".join(abstract_el.itertext()).strip()
        else:
            body = ""

        # Optionally fetch full text
        if self.fetch_full_text and number:
            try:
                full = self.get_text(_RFC_TEXT_URL.format(number=number))
                body = full
            except Exception:
                pass

        # Authors
        authors: List[str] = []
        for author_el in item.findall(f"{ns}author"):
            name = author_el.find(f"{ns}name")
            if name is not None and name.text:
                authors.append(name.text.strip())

        # Date
        date_el = item.find(f"{ns}date")
        date = ""
        if date_el is not None:
            y = date_el.find(f"{ns}year")
            mo = date_el.find(f"{ns}month")
            if y is not None and y.text:
                date = y.text
                if mo is not None and mo.text:
                    date = f"{y.text}-{mo.text}"

        url = f"https://www.rfc-editor.org/rfc/rfc{number}" if number else ""

        # Keywords as tags
        tags: List[str] = []
        for kw in item.findall(f"{ns}keywords/{ns}kw"):
            if kw.text and kw.text.strip():
                tags.append(kw.text.strip())
        tags.append("rfc")

        # Outlinks: obsoletes / updates
        outlinks: List[str] = []
        for rel in item.findall(f"{ns}obsoletes/{ns}doc-id") + item.findall(f"{ns}updates/{ns}doc-id"):
            if rel.text:
                rm = re.search(r"\d+", rel.text)
                if rm:
                    outlinks.append(f"https://www.rfc-editor.org/rfc/rfc{rm.group()}")

        has_code = bool(_CODE_RE.search(body))
        has_citations = bool(_CITATION_RE.search(body))

        return make_document(
            url=url,
            title=f"RFC {number}: {title}",
            body=body,
            author="; ".join(authors),
            author_id=authors[0] if authors else "",
            source="rfc",
            source_tier=1,
            date=date,
            tags=tags,
            lang="en",
            has_code=has_code,
            has_citations=has_citations,
            has_data=False,
            outlinks=outlinks,
        )
