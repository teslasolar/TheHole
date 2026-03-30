"""Parametrized should_index tests using shared fixtures."""

def test_clean_doc_indexed(slop_filter, clean_doc):
    assert slop_filter.should_index(clean_doc), "Clean doc should be indexed"

def test_slop_doc_rejected(slop_filter, slop_doc):
    assert not slop_filter.should_index(slop_doc), "Slop doc should be rejected"

def test_cta_phrases_penalize_score(slop_filter, slop_doc, cta_phrases):
    slop_doc["body"] = ". ".join(cta_phrases) * 5
    score, rules = slop_filter.score(slop_doc)
    assert any("cta" in r for r in rules), "CTA rules should trigger"
