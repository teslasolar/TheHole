import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from datetime import datetime, timezone, timedelta
from rankers.ranker import HoleRanker


def test_today_near_100():
    now = datetime(2026, 3, 29, tzinfo=timezone.utc)
    doc = {"date": "2026-03-29T00:00:00Z"}
    score = HoleRanker().score_freshness(doc, now=now)
    assert score > 95


def test_180_days_about_50():
    now = datetime(2026, 3, 29, tzinfo=timezone.utc)
    past = now - timedelta(days=180)
    doc = {"date": past.strftime("%Y-%m-%dT%H:%M:%SZ")}
    score = HoleRanker().score_freshness(doc, now=now)
    assert 45 < score < 55
