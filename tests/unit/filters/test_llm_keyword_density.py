import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from filters.llm_detect import max_keyword_density


def test_empty_returns_zero():
    assert max_keyword_density("") == 0.0


def test_normal_text_low_density():
    text = "The server handles requests from clients using TCP connections over the network stack while balancing load across multiple backend instances running different services behind a reverse proxy layer."
    density = max_keyword_density(text)
    assert density < 0.05


def test_stuffed_text_high_density():
    text = " ".join(["vpn"] * 20 + ["the"] * 5 + ["good"] * 2)
    density = max_keyword_density(text)
    assert density > 0.08
