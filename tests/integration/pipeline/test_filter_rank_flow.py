"""Integration: filter docs then rank, verify ordering."""
import json
import sys
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent.parent)
sys.path.insert(0, _PROJECT_ROOT)

from filters.slop_filter import SlopFilter
from rankers.ranker import HoleRanker

_FIXTURES = Path(__file__).resolve().parent.parent.parent / "fixtures" / "docs"


def _load(name):
    with open(_FIXTURES / name) as f:
        return json.load(f)


def test_filtered_then_ranked():
    clean = _load("sample_clean_doc.json")
    slop = _load("sample_slop_doc.json")
    filt = SlopFilter()
    accepted = [d for d in [clean, slop] if filt.should_index(d)]
    assert len(accepted) == 1
    assert accepted[0]["author_id"] == "jvns"

    ranker = HoleRanker(slop_filter=filt)
    ranked = ranker.rank_many(accepted)
    assert len(ranked) == 1
    assert ranked[0][1]["composite"] > 0


def test_rank_order_correct():
    clean = _load("sample_clean_doc.json")
    mediocre = dict(clean, author="", author_id="",
                    has_code=False, has_citations=False,
                    source_tier=3, inlinks={})
    filt = SlopFilter()
    ranker = HoleRanker(slop_filter=filt)
    ranked = ranker.rank_many([mediocre, clean])
    assert ranked[0][0]["author_id"] == "jvns"
