"""
IndexBuilder -- builds the static search index for THE HOLE frontend.

Produces:
  frontend/index/documents.json   -- all documents sorted by composite score
  frontend/index/index.json       -- Lunr search index (serialized)
  frontend/index/meta.json        -- build metadata
  frontend/index/source_*.json    -- per-source document splits
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from lunr import lunr

from filters.slop_filter import SlopFilter
from rankers.ranker import HoleRanker

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_OUTPUT_DIR = _PROJECT_ROOT / "frontend" / "index"


class IndexBuilder:
    """
    Takes scored documents and builds a static Lunr-based search index.
    """

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        ranker: Optional[HoleRanker] = None,
        slop_filter: Optional[SlopFilter] = None,
    ):
        self.output_dir = Path(output_dir) if output_dir else _DEFAULT_OUTPUT_DIR
        self.slop_filter = slop_filter or SlopFilter()
        self.ranker = ranker or HoleRanker(slop_filter=self.slop_filter)

    def build_static(
        self, docs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Build the full static index from a list of document dicts.

        Steps:
          1. Filter out slop (below threshold).
          2. Rank remaining documents.
          3. Sort by composite score descending.
          4. Build Lunr index JSON.
          5. Write documents.json, per-source splits, and meta.json.

        Returns the meta dict.
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # --- Step 1: filter ---
        accepted: List[Dict[str, Any]] = []
        rejected_count = 0
        for doc in docs:
            if self.slop_filter.should_index(doc):
                accepted.append(doc)
            else:
                rejected_count += 1

        # --- Step 2 & 3: rank and sort ---
        ranked: List[Tuple[Dict[str, Any], Dict[str, Any]]] = self.ranker.rank_many(accepted)

        # Build final document list with ranking info embedded
        indexed_docs: List[Dict[str, Any]] = []
        for i, (doc, rank_info) in enumerate(ranked):
            entry = {
                "id": str(i),
                "url": doc.get("url", ""),
                "title": doc.get("title", ""),
                "author": doc.get("author", ""),
                "source": doc.get("source", ""),
                "source_tier": doc.get("source_tier", 3),
                "date": doc.get("date", ""),
                "snippet": doc.get("snippet", ""),
                "word_count": doc.get("word_count", 0),
                "tags": doc.get("tags", []),
                "has_code": doc.get("has_code", False),
                "has_citations": doc.get("has_citations", False),
                "has_data": doc.get("has_data", False),
                "composite_score": rank_info["composite"],
                "scores": rank_info["scores"],
            }
            indexed_docs.append(entry)

        # --- Step 4: build Lunr index ---
        lunr_index = self._build_lunr_index(indexed_docs)

        # --- Step 5: write outputs ---
        self._write_json(self.output_dir / "documents.json", indexed_docs)
        self._write_json(self.output_dir / "index.json", lunr_index)

        # Per-source splits
        source_groups: Dict[str, List[Dict[str, Any]]] = {}
        for entry in indexed_docs:
            src = entry.get("source", "unknown")
            source_groups.setdefault(src, []).append(entry)

        for source_name, source_docs in source_groups.items():
            safe_name = source_name.replace("/", "_").replace(" ", "_").lower()
            self._write_json(
                self.output_dir / f"source_{safe_name}.json", source_docs
            )

        # Meta
        meta = {
            "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "total_crawled": len(docs),
            "total_indexed": len(indexed_docs),
            "total_rejected": rejected_count,
            "sources": {
                name: len(sdocs) for name, sdocs in source_groups.items()
            },
        }
        self._write_json(self.output_dir / "meta.json", meta)

        return meta

    # -------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------

    def _build_lunr_index(self, docs: List[Dict[str, Any]]) -> dict:
        """Build a serialized Lunr index from indexed documents."""
        if not docs:
            return {}

        # Build the lunr index
        idx = lunr(
            ref="id",
            fields=[
                {"field_name": "title", "boost": 10},
                {"field_name": "snippet", "boost": 2},
                {"field_name": "author", "boost": 3},
                {"field_name": "tags_text", "boost": 5},
                {"field_name": "source", "boost": 1},
            ],
            documents=[
                {
                    "id": doc["id"],
                    "title": doc.get("title", ""),
                    "snippet": doc.get("snippet", ""),
                    "author": doc.get("author", ""),
                    "tags_text": " ".join(doc.get("tags", [])),
                    "source": doc.get("source", ""),
                }
                for doc in docs
            ],
        )

        return idx.serialize()

    @staticmethod
    def _write_json(path: Path, data: Any) -> None:
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)
