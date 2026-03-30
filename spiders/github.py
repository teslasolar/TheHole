"""
GitHub spider -- fetches trending/recently-updated repos via the REST API.

Uses the search/repositories endpoint and optionally fetches README content.
"""

from __future__ import annotations

import base64
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterator, List, Optional

from .base import HoleSpider, make_document

_CODE_RE = re.compile(r"```")


class GithubSpider(HoleSpider):
    """Crawl GitHub repositories and their READMEs."""

    name = "github"

    def __init__(
        self,
        query: str = "stars:>50 pushed:>{since}",
        max_results: int = 200,
        fetch_readme: bool = True,
        **kwargs: Any,
    ):
        token = os.environ.get("GITHUB_TOKEN", "")
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        headers["Accept"] = "application/vnd.github+json"
        super().__init__(rate=1.0, burst=5, headers=headers, **kwargs)
        self.api_url = "https://api.github.com/search/repositories"
        self.query_template = query
        self.max_results = max_results
        self.fetch_readme = fetch_readme

    # ------------------------------------------------------------------

    def _since_date(self) -> str:
        cursor = self.load_cursor()
        last = cursor.get("last_date", "")
        if last:
            return last
        return (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")

    def fetch_items(self) -> Iterator[Dict[str, Any]]:
        since = self._since_date()
        query = self.query_template.replace("{since}", since)
        page_size = 100
        fetched = 0

        for page in range(1, (self.max_results // page_size) + 2):
            if fetched >= self.max_results:
                break
            params = {
                "q": query,
                "sort": "updated",
                "order": "desc",
                "per_page": min(page_size, self.max_results - fetched),
                "page": page,
            }
            data = self.get_json(self.api_url, params=params)
            items = data.get("items", [])
            if not items:
                break
            for repo in items:
                yield repo
                fetched += 1

        self.save_cursor({"last_date": datetime.now(timezone.utc).strftime("%Y-%m-%d")})

    def _fetch_readme(self, full_name: str) -> str:
        """Try to fetch the decoded README for a repo."""
        if not self.fetch_readme:
            return ""
        try:
            url = f"https://api.github.com/repos/{full_name}/readme"
            data = self.get_json(url)
            content = data.get("content", "")
            encoding = data.get("encoding", "base64")
            if encoding == "base64" and content:
                return base64.b64decode(content).decode("utf-8", errors="replace")
            return content
        except Exception:
            return ""

    def parse(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        full_name = item.get("full_name", "")
        url = item.get("html_url", "")
        title = full_name
        description = item.get("description") or ""

        readme = self._fetch_readme(full_name)
        body = f"{description}\n\n{readme}".strip()

        owner = item.get("owner", {})
        author = owner.get("login", "")
        author_id = str(owner.get("id", ""))

        date = item.get("pushed_at") or item.get("updated_at") or ""

        tags: List[str] = item.get("topics", []) or []
        language = item.get("language")
        if language:
            tags.append(language.lower())

        has_code = True  # it's a code repository
        has_citations = bool(re.search(r"cite|citation|bibtex", body, re.I))

        outlinks: List[str] = []
        homepage = item.get("homepage")
        if homepage:
            outlinks.append(homepage)

        return make_document(
            url=url,
            title=title,
            body=body,
            author=author,
            author_id=author_id,
            source="github",
            source_tier=2,
            date=date,
            tags=tags,
            lang="en",
            has_code=has_code,
            has_citations=has_citations,
            has_data=False,
            outlinks=outlinks,
        )
