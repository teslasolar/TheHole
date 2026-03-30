"""Parametrized source tier scoring using shared params."""

def test_all_tiers_scored(ranker, source_tiers):
    expected = {1: 100, 2: 70, 3: 40, 4: 10}
    for source, tier in source_tiers.items():
        doc = {"source_tier": tier}
        score = ranker.score_source_tier(doc)
        assert score == expected[tier], f"{source} (T{tier}) scored {score}"

def test_tier_ordering(ranker, source_tiers):
    scores = {}
    for source, tier in source_tiers.items():
        scores[source] = ranker.score_source_tier({"source_tier": tier})
    assert scores["arxiv"] > scores["hn"]
    assert scores["hn"] > scores["web"]
