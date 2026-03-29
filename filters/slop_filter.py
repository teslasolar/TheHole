"""
SlopFilter -- the core quality gate for THE HOLE search engine.

Every crawled document passes through this filter before indexing.
The filter accumulates penalty points (negative) and bonus points (positive).
A document with a composite score below the threshold is rejected.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple
from urllib.parse import urlparse

from .affiliate_detect import count_affiliate_links
from .llm_detect import count_llm_markers, max_keyword_density

# ---------------------------------------------------------------------------
# Default threshold -- documents scoring below this are excluded
# ---------------------------------------------------------------------------
DEFAULT_THRESHOLD = -30

# ---------------------------------------------------------------------------
# Load domain blacklist once at import time
# ---------------------------------------------------------------------------
_BLACKLIST_PATH = Path(__file__).resolve().parent / "blacklist.txt"


def _load_blacklist() -> Set[str]:
    domains: Set[str] = set()
    if not _BLACKLIST_PATH.exists():
        return domains
    with open(_BLACKLIST_PATH, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                domains.add(line.lower())
    return domains


_BLACKLISTED_DOMAINS: Set[str] = _load_blacklist()


class SlopFilter:
    """
    Scores a document for slop / low-quality signals.

    Usage::

        filt = SlopFilter()
        score, rules = filt.score(doc)
        if filt.should_index(doc):
            # keep it
    """

    def __init__(self, threshold: int = DEFAULT_THRESHOLD):
        self.threshold = threshold

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def score(self, doc: Dict[str, Any]) -> Tuple[int, List[str]]:
        """
        Evaluate *doc* and return ``(score, triggered_rules)``.

        Negative values = penalties.  Positive values = bonuses.
        """
        points = 0
        triggered: List[str] = []

        body = doc.get("snippet", "") + " " + doc.get("title", "")
        # If the full body is available, prefer it
        full_body = doc.get("body", body)
        title = doc.get("title", "")
        url = doc.get("url", "")
        outlinks = doc.get("outlinks", [])

        # -- Content structure signals ------------------------------------
        p, r = self._check_listicle(title)
        points += p
        triggered.extend(r)

        p, r = self._check_affiliate_density(full_body, outlinks)
        points += p
        triggered.extend(r)

        p, r = self._check_keyword_stuffing(full_body)
        points += p
        triggered.extend(r)

        p, r = self._check_cta_flood(full_body)
        points += p
        triggered.extend(r)

        # -- Author signals -----------------------------------------------
        p, r = self._check_no_author(doc)
        points += p
        triggered.extend(r)

        p, r = self._check_content_mill_rate(doc)
        points += p
        triggered.extend(r)

        # -- Domain signals -----------------------------------------------
        p, r = self._check_known_farm(url)
        points += p
        triggered.extend(r)

        p, r = self._check_contributor_network(doc)
        points += p
        triggered.extend(r)

        # -- LLM detection ------------------------------------------------
        p, r = self._check_llm_markers(full_body)
        points += p
        triggered.extend(r)

        # -- Commercial intent --------------------------------------------
        p, r = self._check_pricing_page(title, url, full_body)
        points += p
        triggered.extend(r)

        # -- Positive signals ---------------------------------------------
        p, r = self._positive_signals(doc)
        points += p
        triggered.extend(r)

        return points, triggered

    def should_index(self, doc: Dict[str, Any]) -> bool:
        """Return True if *doc* passes the quality gate."""
        score, _ = self.score(doc)
        return score >= self.threshold

    # -----------------------------------------------------------------------
    # Content structure checks
    # -----------------------------------------------------------------------

    _LISTICLE_RE = re.compile(
        r"^\s*\d+\s+(best|top|greatest|amazing|incredible|awesome|must-have|essential)",
        re.IGNORECASE,
    )

    def _check_listicle(self, title: str) -> Tuple[int, List[str]]:
        if self._LISTICLE_RE.search(title):
            return -15, ["listicle_title"]
        return 0, []

    def _check_affiliate_density(
        self, body: str, outlinks: List[str]
    ) -> Tuple[int, List[str]]:
        count = count_affiliate_links(body, outlinks)
        if count >= 10:
            return -25, ["affiliate_flood"]
        if count >= 5:
            return -15, ["affiliate_heavy"]
        if count >= 2:
            return -5, ["affiliate_present"]
        return 0, []

    def _check_keyword_stuffing(self, body: str) -> Tuple[int, List[str]]:
        density = max_keyword_density(body)
        if density > 0.08:
            return -20, ["keyword_stuffing"]
        if density > 0.05:
            return -10, ["keyword_dense"]
        return 0, []

    _CTA_PATTERNS = [
        re.compile(r"buy\s+now", re.IGNORECASE),
        re.compile(r"sign\s+up\s+(now|today|free)", re.IGNORECASE),
        re.compile(r"click\s+here", re.IGNORECASE),
        re.compile(r"subscribe\s+(now|today)", re.IGNORECASE),
        re.compile(r"don'?t\s+miss\s+out", re.IGNORECASE),
        re.compile(r"limited\s+time\s+offer", re.IGNORECASE),
        re.compile(r"act\s+now", re.IGNORECASE),
        re.compile(r"get\s+started\s+(now|today|free)", re.IGNORECASE),
        re.compile(r"order\s+(now|today)", re.IGNORECASE),
        re.compile(r"claim\s+your\s+(free|discount)", re.IGNORECASE),
        re.compile(r"exclusive\s+(deal|offer|discount)", re.IGNORECASE),
        re.compile(r"hurry", re.IGNORECASE),
        re.compile(r"free\s+trial", re.IGNORECASE),
    ]

    def _check_cta_flood(self, body: str) -> Tuple[int, List[str]]:
        count = 0
        for pat in self._CTA_PATTERNS:
            count += len(pat.findall(body))
        if count >= 8:
            return -20, ["cta_flood"]
        if count >= 4:
            return -10, ["cta_heavy"]
        return 0, []

    # -----------------------------------------------------------------------
    # Author signals
    # -----------------------------------------------------------------------

    def _check_no_author(self, doc: Dict[str, Any]) -> Tuple[int, List[str]]:
        author = doc.get("author", "").strip()
        if not author or author.lower() in ("admin", "staff", "editor", "contributor", "guest"):
            return -10, ["no_real_author"]
        return 0, []

    def _check_content_mill_rate(self, doc: Dict[str, Any]) -> Tuple[int, List[str]]:
        """
        If the author_id suggests a content-mill pattern (e.g. numeric ID,
        or known mill author format), penalize.
        """
        author_id = doc.get("author_id", "")
        if not author_id:
            return 0, []
        # Pure numeric author IDs often indicate mill-generated content
        if author_id.isdigit():
            return -10, ["content_mill_author_id"]
        # Extremely short or generic IDs
        if len(author_id) <= 2:
            return -5, ["generic_author_id"]
        return 0, []

    # -----------------------------------------------------------------------
    # Domain signals
    # -----------------------------------------------------------------------

    def _check_known_farm(self, url: str) -> Tuple[int, List[str]]:
        if not url:
            return 0, []
        try:
            domain = urlparse(url).hostname or ""
        except Exception:
            return 0, []
        domain = domain.lower()
        # Strip www. prefix
        if domain.startswith("www."):
            domain = domain[4:]
        if domain in _BLACKLISTED_DOMAINS:
            return -50, [f"known_farm:{domain}"]
        # Also check parent domain (e.g. sub.farm.com -> farm.com)
        parts = domain.split(".")
        if len(parts) > 2:
            parent = ".".join(parts[-2:])
            if parent in _BLACKLISTED_DOMAINS:
                return -50, [f"known_farm:{parent}"]
        return 0, []

    def _check_contributor_network(self, doc: Dict[str, Any]) -> Tuple[int, List[str]]:
        """
        Detects contributor / guest-post network patterns:
        - URL contains /contributor/ or /sponsored/
        - Tags contain 'sponsored' or 'partner'
        """
        url = doc.get("url", "").lower()
        tags = [t.lower() for t in doc.get("tags", [])]

        if "/sponsored/" in url or "/contributor/" in url or "/partner-content/" in url:
            return -15, ["contributor_network_url"]
        if "sponsored" in tags or "partner" in tags or "paid" in tags:
            return -15, ["contributor_network_tag"]
        return 0, []

    # -----------------------------------------------------------------------
    # LLM detection
    # -----------------------------------------------------------------------

    def _check_llm_markers(self, body: str) -> Tuple[int, List[str]]:
        count, matched = count_llm_markers(body)
        if count >= 8:
            return -25, [f"llm_heavy({count}_markers)"]
        if count >= 4:
            return -15, [f"llm_likely({count}_markers)"]
        if count >= 2:
            return -5, [f"llm_possible({count}_markers)"]
        return 0, []

    # -----------------------------------------------------------------------
    # Commercial intent
    # -----------------------------------------------------------------------

    _PRICING_SIGNALS = [
        re.compile(r"pricing\s+(plan|page|table)", re.IGNORECASE),
        re.compile(r"\$\d+(\.\d{2})?\s*/\s*(mo|month|yr|year)", re.IGNORECASE),
        re.compile(r"(free|basic|pro|premium|enterprise)\s+plan", re.IGNORECASE),
        re.compile(r"compare\s+plans", re.IGNORECASE),
        re.compile(r"start\s+your\s+free\s+trial", re.IGNORECASE),
        re.compile(r"money[- ]back\s+guarantee", re.IGNORECASE),
    ]

    def _check_pricing_page(
        self, title: str, url: str, body: str
    ) -> Tuple[int, List[str]]:
        combined = f"{title} {url} {body}"
        hits = sum(1 for pat in self._PRICING_SIGNALS if pat.search(combined))
        if hits >= 3:
            return -20, ["pricing_page"]
        if hits >= 1 and "/pricing" in url.lower():
            return -15, ["pricing_url"]
        return 0, []

    # -----------------------------------------------------------------------
    # Positive signals (bonuses)
    # -----------------------------------------------------------------------

    def _positive_signals(self, doc: Dict[str, Any]) -> Tuple[int, List[str]]:
        bonus = 0
        rules: List[str] = []

        if doc.get("has_code"):
            bonus += 15
            rules.append("+has_code")

        if doc.get("has_citations"):
            bonus += 20
            rules.append("+cites_papers")

        # documents_failure: the document discusses a failure / post-mortem
        title = doc.get("title", "").lower()
        snippet = doc.get("snippet", "").lower()
        failure_words = [
            "post-mortem", "postmortem", "failure", "outage", "incident report",
            "what went wrong", "lessons learned", "root cause",
            "we broke", "we failed", "debugging",
        ]
        if any(w in title or w in snippet for w in failure_words):
            bonus += 15
            rules.append("+documents_failure")

        # author_has_repos: author_id looks like a GitHub handle
        author_id = doc.get("author_id", "")
        if author_id and not author_id.isdigit() and len(author_id) >= 3:
            # Heuristic: if author_id is a plausible GitHub username
            if re.match(r"^[a-zA-Z][a-zA-Z0-9_-]{2,38}$", author_id):
                bonus += 15
                rules.append("+author_has_repos")

        if doc.get("has_data"):
            bonus += 10
            rules.append("+shows_data")

        return bonus, rules
