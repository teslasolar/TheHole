#!/usr/bin/env python3
"""
build_index.py -- Main build pipeline for THE HOLE search engine.

Loads crawled documents, runs the slop filter, ranks them, and
builds the static Lunr index for the frontend.

Usage:
    python scripts/build_index.py
    python scripts/build_index.py --data-dir data/crawled --output-dir frontend/index
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

# Ensure project root is on the path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from filters.slop_filter import SlopFilter
from index.builder import IndexBuilder
from rankers.ranker import HoleRanker


def load_crawled_docs(data_dir: Path) -> list[dict]:
    """
    Load all crawled document JSON files from *data_dir*.

    Supports:
      - A single documents.json array file
      - A directory of individual .json files
      - JSONL (one JSON object per line) files ending in .jsonl
    """
    docs: list[dict] = []

    if not data_dir.exists():
        print(f"[build] Data directory does not exist: {data_dir}", file=sys.stderr)
        return docs

    # Single array file
    single = data_dir / "documents.json"
    if single.exists():
        with open(single) as f:
            loaded = json.load(f)
        if isinstance(loaded, list):
            docs.extend(loaded)
            print(f"[build] Loaded {len(loaded)} docs from {single}")
            return docs

    # JSONL files
    for jsonl_path in sorted(data_dir.glob("*.jsonl")):
        count = 0
        with open(jsonl_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    docs.append(json.loads(line))
                    count += 1
        print(f"[build] Loaded {count} docs from {jsonl_path}")

    # Individual JSON files (not documents.json, not meta.json)
    for json_path in sorted(data_dir.glob("*.json")):
        if json_path.name in ("documents.json", "meta.json"):
            continue
        try:
            with open(json_path) as f:
                obj = json.load(f)
            if isinstance(obj, dict) and "url" in obj:
                docs.append(obj)
            elif isinstance(obj, list):
                docs.extend(obj)
        except (json.JSONDecodeError, KeyError):
            print(f"[build] Skipping invalid file: {json_path}", file=sys.stderr)

    print(f"[build] Total documents loaded: {len(docs)}")
    return docs


def main() -> None:
    parser = argparse.ArgumentParser(description="Build THE HOLE search index")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=_PROJECT_ROOT / "data" / "crawled",
        help="Directory containing crawled document files",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=_PROJECT_ROOT / "frontend" / "index",
        help="Output directory for index files",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=-30,
        help="Slop filter threshold (default: -30)",
    )
    args = parser.parse_args()

    # Load documents
    docs = load_crawled_docs(args.data_dir)
    if not docs:
        print("[build] No documents found. Nothing to index.")
        return

    # Initialize components
    slop_filter = SlopFilter(threshold=args.threshold)
    ranker = HoleRanker(slop_filter=slop_filter)
    builder = IndexBuilder(
        output_dir=args.output_dir, ranker=ranker, slop_filter=slop_filter
    )

    # Build the index
    print(f"[build] Running slop filter + ranker on {len(docs)} documents...")
    meta = builder.build_static(docs)

    print(f"[build] Index built successfully!")
    print(f"[build]   Crawled:  {meta['total_crawled']}")
    print(f"[build]   Indexed:  {meta['total_indexed']}")
    print(f"[build]   Rejected: {meta['total_rejected']}")
    print(f"[build]   Sources:  {meta['sources']}")
    print(f"[build]   Output:   {args.output_dir}")


if __name__ == "__main__":
    main()
