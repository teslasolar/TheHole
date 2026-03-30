#!/usr/bin/env python3
"""
score.py -- CLI to run the slop filter + ranker on crawled documents.

Useful for debugging and inspecting individual document scores.

Usage:
    python scripts/score.py                            # score all crawled docs
    python scripts/score.py --file data/crawled/arxiv.jsonl
    python scripts/score.py --url "https://example.com/article"  # score single doc by URL
    python scripts/score.py --top 20                   # show top 20
    python scripts/score.py --bottom 20                # show worst 20
    python scripts/score.py --verbose                  # show all sub-scores
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

# Ensure project root is on the path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from filters.slop_filter import SlopFilter
from rankers.ranker import HoleRanker


def load_docs(data_dir: Path, file_path: Path | None = None) -> List[Dict[str, Any]]:
    """Load documents from crawled data."""
    docs: List[Dict[str, Any]] = []

    if file_path:
        paths = [file_path]
    else:
        if not data_dir.exists():
            return docs
        paths = sorted(data_dir.glob("*.jsonl")) + sorted(data_dir.glob("*.json"))

    for p in paths:
        if p.suffix == ".jsonl":
            with open(p) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        docs.append(json.loads(line))
        elif p.suffix == ".json" and p.name not in ("meta.json",):
            with open(p) as f:
                obj = json.load(f)
            if isinstance(obj, list):
                docs.extend(obj)
            elif isinstance(obj, dict) and "url" in obj:
                docs.append(obj)

    return docs


def format_score_line(
    doc: Dict[str, Any],
    slop_score: int,
    slop_rules: list,
    rank_info: Dict[str, Any],
    verbose: bool = False,
) -> str:
    """Format a single document's score for display."""
    title = doc.get("title", "(no title)")[:60]
    url = doc.get("url", "")[:80]
    composite = rank_info["composite"]
    passed = "PASS" if slop_score >= -30 else "FAIL"

    line = f"  [{passed}] composite={composite:6.2f}  slop={slop_score:4d}  {title}"
    if verbose:
        line += f"\n         url: {url}"
        line += f"\n         rules: {', '.join(slop_rules) if slop_rules else '(none)'}"
        scores = rank_info["scores"]
        line += (
            f"\n         sub-scores: "
            f"slop={scores['slop']:.0f} prac={scores['practitioner']:.0f} "
            f"cite={scores['citation']:.0f} fresh={scores['freshness']:.0f} "
            f"depth={scores['depth']:.0f} tier={scores['source_tier']:.0f}"
        )
    return line


def main() -> None:
    parser = argparse.ArgumentParser(description="Score documents with slop filter + ranker")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=_PROJECT_ROOT / "data" / "crawled",
        help="Directory with crawled docs",
    )
    parser.add_argument("--file", type=Path, default=None, help="Score a specific file")
    parser.add_argument("--url", type=str, default=None, help="Score a single document by URL")
    parser.add_argument("--top", type=int, default=0, help="Show top N docs")
    parser.add_argument("--bottom", type=int, default=0, help="Show bottom N docs")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed sub-scores")
    parser.add_argument("--threshold", type=int, default=-30, help="Slop threshold")
    args = parser.parse_args()

    docs = load_docs(args.data_dir, args.file)
    if not docs:
        print("[score] No documents found.")
        return

    if args.url:
        docs = [d for d in docs if d.get("url") == args.url]
        if not docs:
            print(f"[score] No document found with URL: {args.url}")
            return

    slop_filter = SlopFilter(threshold=args.threshold)
    ranker = HoleRanker(slop_filter=slop_filter)

    results = []
    pass_count = 0
    fail_count = 0

    for doc in docs:
        slop_score, slop_rules = slop_filter.score(doc)
        rank_info = ranker.rank(doc)
        results.append((doc, slop_score, slop_rules, rank_info))
        if slop_score >= args.threshold:
            pass_count += 1
        else:
            fail_count += 1

    # Sort by composite score
    results.sort(key=lambda x: x[3]["composite"], reverse=True)

    print(f"[score] Scored {len(results)} documents: {pass_count} pass, {fail_count} fail")
    print()

    if args.top:
        print(f"--- Top {args.top} ---")
        for doc, ss, sr, ri in results[: args.top]:
            print(format_score_line(doc, ss, sr, ri, args.verbose))
        print()

    if args.bottom:
        print(f"--- Bottom {args.bottom} ---")
        for doc, ss, sr, ri in results[-args.bottom :]:
            print(format_score_line(doc, ss, sr, ri, args.verbose))
        print()

    if not args.top and not args.bottom:
        for doc, ss, sr, ri in results:
            print(format_score_line(doc, ss, sr, ri, args.verbose))


if __name__ == "__main__":
    main()
