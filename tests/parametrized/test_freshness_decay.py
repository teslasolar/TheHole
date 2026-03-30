"""Parametrized freshness scoring using doc fixtures."""

def test_fresh_beats_old(ranker, clean_doc, old_doc):
    s1 = ranker.score_freshness(clean_doc)
    s2 = ranker.score_freshness(old_doc)
    assert s1 > s2, f"Fresh {s1} should beat old {s2}"

def test_clean_doc_near_100(ranker, clean_doc):
    score = ranker.score_freshness(clean_doc)
    assert score >= 90, f"Today's doc should be near 100, got {score}"

def test_old_doc_decayed(ranker, old_doc):
    score = ranker.score_freshness(old_doc)
    assert score < 60, f"Year-old doc should decay below 60, got {score}"
