"""
LLM-generated content detection for THE HOLE slop filter.

Detects marker phrases characteristic of LLM output and measures
keyword stuffing via density analysis.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import List, Tuple

# ---------------------------------------------------------------------------
# Marker phrases -- phrases characteristic of LLM-generated text
# ---------------------------------------------------------------------------
LLM_MARKERS: List[str] = [
    # Classic ChatGPT hedging / filler
    "dive into",
    "delve into",
    "it's important to note",
    "it is important to note",
    "it's worth noting",
    "it is worth noting",
    "in today's digital landscape",
    "in today's fast-paced world",
    "in the ever-evolving",
    "in this comprehensive guide",
    "unlock the full potential",
    "unlock the power",
    "let's explore",
    "let's dive in",
    "navigating the landscape",
    "navigating the complexities",
    "the landscape of",
    "game-changer",
    "game changer",
    "paradigm shift",
    "revolutionize",
    "cutting-edge",
    "cutting edge",
    "leverage the power",
    "harness the power",
    "at the end of the day",
    "look no further",
    "without further ado",
    "in conclusion",
    "to sum up",
    "in summary",
    "as an AI language model",
    "as a large language model",
    "I don't have personal",
    "I cannot provide",
    "I'm unable to",
    "it depends on your specific",
    "there are several key",
    "here are some key",
    "there are many factors",
    "it's crucial to",
    "it is crucial to",
    "a myriad of",
    "a plethora of",
    "multifaceted",
    "holistic approach",
    "synergy",
    "elevate your",
    "streamline your",
    "optimize your",
    "maximize your",
    "take your .* to the next level",
    "empower you to",
    "empowers you to",
    "seamlessly integrate",
    "robust and scalable",
    "in the realm of",
    "tapestry of",
    "testament to",
    "embark on",
    "embarking on",
    "realm of possibilities",
    "not only .* but also",
    "whether you're a .* or a",
    "from .* to .*, we've got you covered",
    "stands out as",
    "boasts a wide range",
    "comprehensive overview",
    "key takeaways",
    "actionable insights",
    "data-driven",
    "best practices",
    "industry-leading",
    "state-of-the-art",
    "world-class",
    "top-notch",
    "first and foremost",
    "furthermore",
    "moreover",
    "additionally",
    "subsequently",
    "consequently",
    "in light of",
    "with that being said",
    "having said that",
    "it goes without saying",
    "needless to say",
    "rest assured",
    "by and large",
    "all things considered",
    "when it comes to",
    "in terms of",
    "on the other hand",
    "that said",
]

# Pre-compile patterns (some entries use .* so we compile as regex)
_COMPILED_MARKERS: List[re.Pattern] = []
for _phrase in LLM_MARKERS:
    if ".*" in _phrase:
        _COMPILED_MARKERS.append(re.compile(re.escape(_phrase).replace(r"\.\*", ".*"), re.IGNORECASE))
    else:
        _COMPILED_MARKERS.append(re.compile(re.escape(_phrase), re.IGNORECASE))


def count_llm_markers(text: str) -> Tuple[int, List[str]]:
    """
    Count how many distinct LLM marker phrases appear in *text*.

    Returns (count, list_of_matched_phrases).
    """
    matched: List[str] = []
    for marker, pattern in zip(LLM_MARKERS, _COMPILED_MARKERS):
        if pattern.search(text):
            matched.append(marker)
    return len(matched), matched


def max_keyword_density(text: str, top_n: int = 5) -> float:
    """
    Compute keyword density for the most frequent non-stop words.

    Returns the density (0.0-1.0) of the single most repeated word
    (excluding common English stop words), or 0.0 for empty text.
    """
    if not text:
        return 0.0

    stop_words = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
        "for", "of", "with", "by", "from", "is", "it", "this", "that",
        "was", "are", "were", "be", "been", "being", "have", "has", "had",
        "do", "does", "did", "will", "would", "could", "should", "may",
        "might", "shall", "can", "not", "no", "nor", "so", "if", "as",
        "its", "than", "then", "into", "about", "up", "out", "your",
        "you", "we", "they", "he", "she", "i", "me", "my", "our", "his",
        "her", "their", "them", "what", "which", "who", "whom", "when",
        "where", "how", "all", "each", "every", "both", "few", "more",
        "most", "other", "some", "such", "only", "own", "same", "just",
        "also", "very", "any", "these", "those", "here", "there",
    }

    words = re.findall(r"[a-z]{3,}", text.lower())
    if not words:
        return 0.0

    filtered = [w for w in words if w not in stop_words]
    if not filtered:
        return 0.0

    counts = Counter(filtered)
    most_common_count = counts.most_common(1)[0][1]
    return most_common_count / len(words)
