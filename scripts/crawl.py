#!/usr/bin/env python3
"""
crawl.py -- CLI to run individual spiders for THE HOLE.

Usage:
    python scripts/crawl.py --source=arxiv
    python scripts/crawl.py --source=arxiv --test --limit=5
    python scripts/crawl.py --source=all
    python scripts/crawl.py --list
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Type

# Ensure project root is on the path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from spiders.base import HoleSpider

# ---------------------------------------------------------------------------
# Spider registry -- maps source name to module path
# ---------------------------------------------------------------------------
_SPIDER_MODULES: Dict[str, str] = {
    # Add spider modules here as they are created:
    # "arxiv": "spiders.arxiv",
    # "hackernews": "spiders.hackernews",
    # "github": "spiders.github_spider",
    # "lobsters": "spiders.lobsters",
}

_OUTPUT_DIR = _PROJECT_ROOT / "data" / "crawled"


def _discover_spiders() -> Dict[str, Type[HoleSpider]]:
    """Import and return all registered spider classes."""
    spiders: Dict[str, Type[HoleSpider]] = {}
    for name, module_path in _SPIDER_MODULES.items():
        try:
            mod = importlib.import_module(module_path)
            # Convention: the module exposes a class named Spider
            cls = getattr(mod, "Spider", None)
            if cls and issubclass(cls, HoleSpider):
                spiders[name] = cls
            else:
                print(f"[crawl] Warning: {module_path} has no Spider class", file=sys.stderr)
        except ImportError as e:
            print(f"[crawl] Warning: could not import {module_path}: {e}", file=sys.stderr)
    return spiders


def run_spider(
    spider_cls: Type[HoleSpider],
    limit: int = 0,
    test: bool = False,
) -> List[Dict[str, Any]]:
    """Instantiate and run a spider, return the documents."""
    spider = spider_cls()
    if test:
        limit = limit or 5
        print(f"[crawl] Running {spider.name} in test mode (limit={limit})")
    else:
        print(f"[crawl] Running {spider.name} (limit={limit or 'unlimited'})")

    docs = spider.crawl(limit=limit)
    print(f"[crawl] {spider.name}: fetched {len(docs)} documents")
    return docs


def save_docs(source: str, docs: List[Dict[str, Any]]) -> Path:
    """Save crawled documents to a JSONL file."""
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = _OUTPUT_DIR / f"{source}.jsonl"
    with open(out_path, "w") as f:
        for doc in docs:
            f.write(json.dumps(doc, default=str) + "\n")
    print(f"[crawl] Saved {len(docs)} docs to {out_path}")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run THE HOLE spiders")
    parser.add_argument(
        "--source",
        type=str,
        default="",
        help="Spider name to run (or 'all')",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test mode: fetch a small number of documents",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Maximum number of documents to fetch",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        dest="list_spiders",
        help="List available spiders and exit",
    )
    args = parser.parse_args()

    spiders = _discover_spiders()

    if args.list_spiders:
        if not spiders:
            print("[crawl] No spiders registered yet. Add them to _SPIDER_MODULES in crawl.py")
        else:
            print("[crawl] Available spiders:")
            for name in sorted(spiders):
                print(f"  - {name}")
        return

    if not args.source:
        parser.print_help()
        return

    if args.source == "all":
        if not spiders:
            print("[crawl] No spiders registered. Nothing to crawl.")
            return
        for name, cls in sorted(spiders.items()):
            docs = run_spider(cls, limit=args.limit, test=args.test)
            if docs:
                save_docs(name, docs)
    else:
        if args.source not in spiders:
            print(
                f"[crawl] Unknown source '{args.source}'. "
                f"Available: {', '.join(sorted(spiders)) or '(none registered)'}",
                file=sys.stderr,
            )
            sys.exit(1)
        docs = run_spider(spiders[args.source], limit=args.limit, test=args.test)
        if docs:
            save_docs(args.source, docs)


if __name__ == "__main__":
    main()
