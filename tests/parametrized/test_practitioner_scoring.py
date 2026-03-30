"""Parametrized practitioner scoring using shared author fixtures."""

def _doc_with_author(clean_doc, author):
    d = dict(clean_doc)
    d["author_meta"] = author
    return d

def test_practitioner_beats_empty(ranker, clean_doc, practitioner_author, empty_author):
    d1 = _doc_with_author(clean_doc, practitioner_author)
    d2 = _doc_with_author(clean_doc, empty_author)
    assert ranker.score_practitioner(d1) > ranker.score_practitioner(d2)

def test_academic_has_paper_signal(ranker, clean_doc, academic_author):
    d = _doc_with_author(clean_doc, academic_author)
    assert ranker.score_practitioner(d) > 0

def test_practitioner_vs_academic(ranker, clean_doc, practitioner_author, academic_author):
    d1 = _doc_with_author(clean_doc, practitioner_author)
    d2 = _doc_with_author(clean_doc, academic_author)
    assert ranker.score_practitioner(d1) > ranker.score_practitioner(d2)
