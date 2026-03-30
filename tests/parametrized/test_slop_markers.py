"""Parametrized LLM marker detection tests using shared params."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from filters.llm_detect import count_llm_markers

def test_each_llm_phrase_detected(llm_phrases):
    for phrase in llm_phrases:
        text = f"Some intro text. {phrase}. More text here."
        count, _ = count_llm_markers(text)
        assert count >= 1, f"'{phrase}' not detected"

def test_combined_markers(llm_phrases):
    text = ". ".join(llm_phrases)
    count, _ = count_llm_markers(text)
    assert count >= len(llm_phrases) // 2, f"Expected many, got {count}"
