import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from filters.llm_detect import count_llm_markers


def test_detects_llm_phrases():
    text = "Let's dive into this comprehensive guide to unlock the full potential."
    count, matched = count_llm_markers(text)
    assert count >= 2
    assert any("dive into" in m for m in matched)


def test_clean_text_returns_zero():
    text = "The kernel uses cgroups to limit memory for each container."
    count, matched = count_llm_markers(text)
    assert count == 0
    assert matched == []
