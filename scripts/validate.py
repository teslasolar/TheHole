#!/usr/bin/env python3
"""
validate.py -- Check index integrity for THE HOLE.

Validates:
  - All output files exist and are valid JSON
  - documents.json has required fields on every entry
  - index.json is non-empty
  - meta.json has expected keys
  - Per-source files reference valid document IDs
  - No broken references between index and documents

Usage:
    python scripts/validate.py
    python scripts/validate.py --index-dir frontend/index
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Set

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

# Required fields in every document entry
REQUIRED_DOC_FIELDS = [
    "id", "url", "title", "source", "date", "snippet", "composite_score",
]


class ValidationError:
    def __init__(self, file: str, message: str, severity: str = "error"):
        self.file = file
        self.message = message
        self.severity = severity

    def __str__(self) -> str:
        icon = "ERROR" if self.severity == "error" else "WARN"
        return f"  [{icon}] {self.file}: {self.message}"


def validate_json_file(path: Path) -> tuple[Any | None, list[ValidationError]]:
    """Load and validate a JSON file. Returns (data, errors)."""
    errors: list[ValidationError] = []
    if not path.exists():
        errors.append(ValidationError(path.name, "File does not exist"))
        return None, errors
    try:
        with open(path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        errors.append(ValidationError(path.name, f"Invalid JSON: {e}"))
        return None, errors
    return data, errors


def validate_documents(docs: list[dict]) -> list[ValidationError]:
    """Validate documents.json entries."""
    errors: list[ValidationError] = []
    seen_ids: set[str] = set()
    seen_urls: set[str] = set()

    for i, doc in enumerate(docs):
        for field in REQUIRED_DOC_FIELDS:
            if field not in doc:
                errors.append(
                    ValidationError("documents.json", f"Entry {i} missing field '{field}'")
                )

        doc_id = doc.get("id", "")
        if doc_id in seen_ids:
            errors.append(
                ValidationError("documents.json", f"Duplicate id '{doc_id}'")
            )
        seen_ids.add(doc_id)

        url = doc.get("url", "")
        if not url:
            errors.append(
                ValidationError("documents.json", f"Entry {i} has empty URL")
            )
        if url in seen_urls:
            errors.append(
                ValidationError(
                    "documents.json",
                    f"Duplicate URL at entry {i}: {url[:80]}",
                    severity="warn",
                )
            )
        seen_urls.add(url)

        # Validate composite_score is a number
        score = doc.get("composite_score")
        if score is not None and not isinstance(score, (int, float)):
            errors.append(
                ValidationError("documents.json", f"Entry {i}: composite_score is not numeric")
            )

    return errors


def validate_meta(meta: dict, docs: list[dict]) -> list[ValidationError]:
    """Validate meta.json."""
    errors: list[ValidationError] = []
    required_meta_keys = ["built_at", "total_crawled", "total_indexed", "total_rejected", "sources"]

    for key in required_meta_keys:
        if key not in meta:
            errors.append(ValidationError("meta.json", f"Missing key '{key}'"))

    if "total_indexed" in meta and meta["total_indexed"] != len(docs):
        errors.append(
            ValidationError(
                "meta.json",
                f"total_indexed ({meta['total_indexed']}) != documents.json length ({len(docs)})",
            )
        )

    return errors


def validate_source_files(
    index_dir: Path, docs: list[dict]
) -> list[ValidationError]:
    """Validate per-source split files."""
    errors: list[ValidationError] = []
    valid_ids: set[str] = {d.get("id", "") for d in docs}

    for source_file in sorted(index_dir.glob("source_*.json")):
        data, file_errors = validate_json_file(source_file)
        errors.extend(file_errors)
        if data is None:
            continue
        if not isinstance(data, list):
            errors.append(
                ValidationError(source_file.name, "Expected a JSON array")
            )
            continue
        for entry in data:
            eid = entry.get("id", "")
            if eid not in valid_ids:
                errors.append(
                    ValidationError(
                        source_file.name,
                        f"References unknown document id '{eid}'",
                    )
                )

    return errors


def validate_index(index_dir: Path) -> list[ValidationError]:
    """Validate index.json is present and non-empty."""
    errors: list[ValidationError] = []
    path = index_dir / "index.json"
    data, file_errors = validate_json_file(path)
    errors.extend(file_errors)
    if data is not None:
        if isinstance(data, dict) and len(data) == 0:
            errors.append(
                ValidationError("index.json", "Index is empty", severity="warn")
            )
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate THE HOLE search index")
    parser.add_argument(
        "--index-dir",
        type=Path,
        default=_PROJECT_ROOT / "frontend" / "index",
        help="Path to index directory",
    )
    args = parser.parse_args()

    index_dir: Path = args.index_dir
    all_errors: list[ValidationError] = []

    print(f"[validate] Checking index at: {index_dir}")
    print()

    # 1. documents.json
    docs_data, errs = validate_json_file(index_dir / "documents.json")
    all_errors.extend(errs)
    if docs_data is not None:
        if not isinstance(docs_data, list):
            all_errors.append(ValidationError("documents.json", "Expected a JSON array"))
            docs_data = []
        else:
            all_errors.extend(validate_documents(docs_data))
            print(f"  documents.json: {len(docs_data)} entries")
    else:
        docs_data = []

    # 2. index.json
    all_errors.extend(validate_index(index_dir))

    # 3. meta.json
    meta_data, errs = validate_json_file(index_dir / "meta.json")
    all_errors.extend(errs)
    if meta_data is not None and isinstance(meta_data, dict):
        all_errors.extend(validate_meta(meta_data, docs_data))

    # 4. source files
    all_errors.extend(validate_source_files(index_dir, docs_data))

    # Report
    print()
    error_count = sum(1 for e in all_errors if e.severity == "error")
    warn_count = sum(1 for e in all_errors if e.severity == "warn")

    if all_errors:
        print(f"[validate] Found {error_count} error(s), {warn_count} warning(s):")
        for err in all_errors:
            print(str(err))
    else:
        print("[validate] All checks passed.")

    print()
    if error_count > 0:
        print(f"[validate] FAILED ({error_count} errors)")
        sys.exit(1)
    else:
        print(f"[validate] OK ({warn_count} warnings)")
        sys.exit(0)


if __name__ == "__main__":
    main()
