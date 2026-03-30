"""
Shared test fixtures and params for the entire test suite.
Loads params.json and provides pytest fixtures for all test files.
"""
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PARAMS = json.loads((Path(__file__).parent / "params.json").read_text())


# ═══ DOCUMENT FIXTURES ═══

@pytest.fixture
def clean_doc():
    d = dict(PARAMS["clean_doc"])
    d["date"] = datetime.now().isoformat()
    d["snippet"] = d["body"][:200]
    d["body_hash"] = "a" * 64
    d["lang"] = "en"
    d["outlinks"] = []
    d["inlinks"] = {"tier1": 2, "tier2": 3}
    d["scores"] = {"slop": -5}
    d["author_meta"] = {}
    return d


@pytest.fixture
def slop_doc():
    d = dict(PARAMS["slop_doc"])
    d["date"] = datetime.now().isoformat()
    d["snippet"] = d["body"][:200]
    d["body_hash"] = "b" * 64
    d["lang"] = "en"
    d["outlinks"] = PARAMS["slop_markers"]["affiliate_urls"]
    d["inlinks"] = {"tier1": 0, "tier2": 0}
    d["scores"] = {"slop": -70}
    d["author_meta"] = {}
    return d


@pytest.fixture
def old_doc(clean_doc):
    clean_doc["date"] = (datetime.now() - timedelta(days=365)).isoformat()
    return clean_doc


# ═══ AUTHOR FIXTURES ═══

@pytest.fixture
def practitioner_author():
    return dict(PARAMS["practitioner_author"])


@pytest.fixture
def empty_author():
    return dict(PARAMS["empty_author"])


@pytest.fixture
def academic_author():
    return dict(PARAMS["academic_author"])


# ═══ INLINK FIXTURES ═══

@pytest.fixture
def t1_inlinks():
    return list(PARAMS["t1_inlinks"])


@pytest.fixture
def t2_inlinks():
    return list(PARAMS["t2_inlinks"])


# ═══ SLOP MARKER FIXTURES ═══

@pytest.fixture
def affiliate_urls():
    return list(PARAMS["slop_markers"]["affiliate_urls"])


@pytest.fixture
def llm_phrases():
    return list(PARAMS["slop_markers"]["llm_phrases"])


@pytest.fixture
def cta_phrases():
    return list(PARAMS["slop_markers"]["cta_phrases"])


@pytest.fixture
def listicle_titles():
    return list(PARAMS["slop_markers"]["listicle_titles"])


@pytest.fixture
def clean_titles():
    return list(PARAMS["slop_markers"]["clean_titles"])


# ═══ SOURCE TIER FIXTURES ═══

@pytest.fixture
def source_tiers():
    return dict(PARAMS["source_tiers"])


# ═══ MODULE INSTANCES ═══

@pytest.fixture
def slop_filter():
    from filters.slop_filter import SlopFilter
    return SlopFilter()


@pytest.fixture
def ranker():
    from rankers.ranker import HoleRanker
    return HoleRanker()
