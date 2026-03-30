"""
Affiliate link detection for THE HOLE slop filter.

Counts affiliate links / tracking URLs embedded in page content or outlinks.
"""

from __future__ import annotations

import re
from typing import List

# ---------------------------------------------------------------------------
# Patterns -- each tuple is (compiled regex, description)
# ---------------------------------------------------------------------------
_PATTERNS = [
    # Amazon Associates
    re.compile(r"[?&]tag=[A-Za-z0-9_-]+-20", re.IGNORECASE),
    re.compile(r"amzn\.to/", re.IGNORECASE),
    re.compile(r"amazon\.[a-z.]+/.*[?&]linkCode=", re.IGNORECASE),
    re.compile(r"amazon\.[a-z.]+/.*[?&]ascsubtag=", re.IGNORECASE),
    # ShareASale
    re.compile(r"shareasale\.com/[rmu]\.cfm", re.IGNORECASE),
    re.compile(r"shareasale\.com/.*[?&]afftrack=", re.IGNORECASE),
    # CJ Affiliate (Commission Junction)
    re.compile(r"anrdoezrs\.net/", re.IGNORECASE),
    re.compile(r"dpbolvw\.net/", re.IGNORECASE),
    re.compile(r"jdoqocy\.com/", re.IGNORECASE),
    re.compile(r"tkqlhce\.com/", re.IGNORECASE),
    re.compile(r"commission-junction\.com/", re.IGNORECASE),
    re.compile(r"cj\.com/", re.IGNORECASE),
    # Impact / Impact Radius
    re.compile(r"impact\.com/", re.IGNORECASE),
    re.compile(r"ojrq\.net/", re.IGNORECASE),
    re.compile(r"sjv\.io/", re.IGNORECASE),
    re.compile(r"7eer\.net/", re.IGNORECASE),
    re.compile(r"evyy\.net/", re.IGNORECASE),
    re.compile(r"pntra\.com/", re.IGNORECASE),
    re.compile(r"pjatr\.com/", re.IGNORECASE),
    re.compile(r"pntrs\.com/", re.IGNORECASE),
    re.compile(r"pntrac\.com/", re.IGNORECASE),
    # Rakuten / LinkShare
    re.compile(r"click\.linksynergy\.com/", re.IGNORECASE),
    re.compile(r"rakuten\.com/.*[?&]ranMID=", re.IGNORECASE),
    # SkimLinks
    re.compile(r"go\.skimresources\.com/", re.IGNORECASE),
    re.compile(r"go\.redirectingat\.com/", re.IGNORECASE),
    # Awin
    re.compile(r"awin1\.com/", re.IGNORECASE),
    re.compile(r"zenaps\.com/", re.IGNORECASE),
    # PartnerStack / other
    re.compile(r"partnerstack\.com/", re.IGNORECASE),
    # Generic affiliate query params
    re.compile(r"[?&]ref=[A-Za-z0-9_-]{4,}", re.IGNORECASE),
    re.compile(r"[?&]affiliate[_-]?id=", re.IGNORECASE),
    re.compile(r"[?&]aff[_-]?id=", re.IGNORECASE),
    re.compile(r"[?&]partner[_-]?id=", re.IGNORECASE),
    # Shortened URL services commonly used for affiliate cloaking
    re.compile(r"bit\.ly/", re.IGNORECASE),
    re.compile(r"tinyurl\.com/", re.IGNORECASE),
    re.compile(r"ow\.ly/", re.IGNORECASE),
    re.compile(r"buff\.ly/", re.IGNORECASE),
    re.compile(r"geni\.us/", re.IGNORECASE),
    re.compile(r"howl\.me/", re.IGNORECASE),
    re.compile(r"rstyle\.me/", re.IGNORECASE),
    re.compile(r"shopstyle\.it/", re.IGNORECASE),
]


def count_affiliate_links(text: str, outlinks: List[str] | None = None) -> int:
    """
    Count the number of affiliate / tracking links found in *text* and
    optional *outlinks* list.

    Returns an integer count (same URL matching multiple patterns still
    counts once per pattern match -- we intentionally over-count because
    multiple tracking layers are a stronger slop signal).
    """
    total = 0
    sources = [text] + (outlinks or [])
    combined = "\n".join(sources)
    for pat in _PATTERNS:
        total += len(pat.findall(combined))
    return total
