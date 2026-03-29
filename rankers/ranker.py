"""
HoleRanker -- composite ranking engine for THE HOLE search engine.

Combines multiple quality signals into a single composite score used
for ordering search results.
"""

from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from filters.slop_filter import SlopFilter

# ---------------------------------------------------------------------------
# Weight configuration
# ---------------------------------------------------------------------------
WEIGHTS = {
    "slop": 0.25,
    "practitioner": 0.25,
    "citation": 0.20,
    "freshness": 0.15,
    "depth": 0.10,
    "source_tier": 0.05,
}

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
FRESHNESS_HALF_LIFE_DAYS = 180
TIER_SCORES = {1: 100, 2: 70, 3: 40, 4: 10}


class HoleRanker:
    """
    Computes a composite quality score for each document.

    Sub-scores are normalized to 0-100 and combined with weights.
    """

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        slop_filter: Optional[SlopFilter] = None,
    ):
        self.weights = weights or dict(WEIGHTS)
        self.slop_filter = slop_filter or SlopFilter()

    # -------------------------------------------------------------------
    # Sub-score: slop (inverse -- higher = cleaner)
    # -------------------------------------------------------------------

    def score_slop(self, doc: Dict[str, Any]) -> float:
        """
        Convert slop filter score to a 0-100 quality signal.
        A slop score of 0 => 100 (perfectly clean).
        A slop score of -100 => 0 (maximum slop).
        Positive bonuses can push above 100 (capped at 100).
        """
        raw, _ = self.slop_filter.score(doc)
        # Map: raw 0 -> 100, raw -100 -> 0, allow positive bonuses
        value = 100 + raw
        return max(0.0, min(100.0, value))

    # -------------------------------------------------------------------
    # Sub-score: practitioner signal
    # -------------------------------------------------------------------

    def score_practitioner(self, doc: Dict[str, Any]) -> float:
        """
        Score how likely the author is a practitioner vs content writer.

        Signals:
        - github_repos: number of public repos
        - github_commits: recent commit activity
        - papers: academic publications
        - has_code: the document contains code
        """
        score = 0.0
        author_meta = doc.get("author_meta", {})

        # GitHub presence
        repos = author_meta.get("github_repos", 0)
        if repos > 0:
            score += 20
        if repos >= 10:
            score += 15
        if repos >= 50:
            score += 10

        # Commit activity
        commits = author_meta.get("github_commits", 0)
        if commits > 0:
            score += 10
        if commits >= 100:
            score += 10
        if commits >= 500:
            score += 5

        # Academic papers
        papers = author_meta.get("papers", 0)
        if papers > 0:
            score += 15
        if papers >= 5:
            score += 10
        if papers >= 20:
            score += 5

        # Code in the document itself
        if doc.get("has_code"):
            score += 10

        # Author has a plausible GitHub identity
        author_id = doc.get("author_id", "")
        if author_id and re.match(r"^[a-zA-Z][a-zA-Z0-9_-]{2,38}$", author_id):
            score += 10

        return min(100.0, score)

    # -------------------------------------------------------------------
    # Sub-score: citation / inlink quality
    # -------------------------------------------------------------------

    def score_citation(self, doc: Dict[str, Any]) -> float:
        """
        Score based on inbound links from tiered sources.
        T1 inlinks * 15 + T2 inlinks * 5, capped at 100.
        """
        inlinks = doc.get("inlinks", {})
        t1 = inlinks.get("tier1", 0)
        t2 = inlinks.get("tier2", 0)
        raw = t1 * 15 + t2 * 5
        return min(100.0, float(raw))

    # -------------------------------------------------------------------
    # Sub-score: freshness (exponential decay)
    # -------------------------------------------------------------------

    def score_freshness(self, doc: Dict[str, Any], now: Optional[datetime] = None) -> float:
        """
        Exponential decay with a half-life of 180 days.
        A document published today scores 100; at 180 days it scores 50;
        at 360 days it scores 25; etc.
        """
        date_str = doc.get("date", "")
        if not date_str:
            return 25.0  # unknown date gets a low-but-nonzero score

        try:
            pub_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return 25.0

        if now is None:
            now = datetime.now(timezone.utc)
        if pub_date.tzinfo is None:
            pub_date = pub_date.replace(tzinfo=timezone.utc)

        age_days = max(0, (now - pub_date).total_seconds() / 86400)
        decay = math.pow(0.5, age_days / FRESHNESS_HALF_LIFE_DAYS)
        return 100.0 * decay

    # -------------------------------------------------------------------
    # Sub-score: depth / substance
    # -------------------------------------------------------------------

    def score_depth(self, doc: Dict[str, Any]) -> float:
        """
        Measures content depth based on:
        - word_count: longer content scores higher (diminishing returns)
        - has_code: code examples add depth
        - has_citations: references add depth
        - has_data: data/tables add depth
        - heading_depth: deep heading structure (h3+) adds depth
        """
        score = 0.0

        wc = doc.get("word_count", 0)
        if wc >= 300:
            score += 10
        if wc >= 800:
            score += 15
        if wc >= 1500:
            score += 15
        if wc >= 3000:
            score += 10

        if doc.get("has_code"):
            score += 15

        if doc.get("has_citations"):
            score += 15

        if doc.get("has_data"):
            score += 10

        heading_depth = doc.get("heading_depth", 0)
        if heading_depth >= 3:
            score += 10
        elif heading_depth >= 2:
            score += 5

        return min(100.0, score)

    # -------------------------------------------------------------------
    # Sub-score: source tier
    # -------------------------------------------------------------------

    def score_source_tier(self, doc: Dict[str, Any]) -> float:
        """
        T1=100, T2=70, T3=40, T4=10.
        """
        tier = doc.get("source_tier", 3)
        return float(TIER_SCORES.get(tier, 40))

    # -------------------------------------------------------------------
    # Composite ranking
    # -------------------------------------------------------------------

    def rank(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compute the composite score and return a dict with all sub-scores
        and the final composite.
        """
        scores = {
            "slop": self.score_slop(doc),
            "practitioner": self.score_practitioner(doc),
            "citation": self.score_citation(doc),
            "freshness": self.score_freshness(doc),
            "depth": self.score_depth(doc),
            "source_tier": self.score_source_tier(doc),
        }

        composite = sum(
            scores[key] * self.weights[key] for key in self.weights
        )

        return {
            "scores": scores,
            "composite": round(composite, 2),
        }

    def rank_many(self, docs: List[Dict[str, Any]]) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
        """
        Rank a list of documents. Returns list of (doc, rank_info) tuples
        sorted by composite score descending.
        """
        ranked = [(doc, self.rank(doc)) for doc in docs]
        ranked.sort(key=lambda x: x[1]["composite"], reverse=True)
        return ranked
