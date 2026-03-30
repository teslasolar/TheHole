"""Parametrized end-to-end ranking using shared fixtures."""
import copy

def test_clean_outranks_slop(ranker, clean_doc, slop_doc, practitioner_author):
    d1 = copy.deepcopy(clean_doc)
    d1["author_meta"] = practitioner_author
    r1 = ranker.rank(d1)
    r2 = ranker.rank(copy.deepcopy(slop_doc))
    assert r1["composite"] > r2["composite"]

def test_clean_with_author_outranks_clean_without(ranker, clean_doc, practitioner_author, empty_author):
    d1 = copy.deepcopy(clean_doc)
    d1["author_meta"] = practitioner_author
    d2 = copy.deepcopy(clean_doc)
    d2["author_meta"] = empty_author
    r1 = ranker.rank(d1)
    r2 = ranker.rank(d2)
    assert r1["composite"] > r2["composite"]
