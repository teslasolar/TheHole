import sys, time
sys.path.insert(0, "/home/user/TheHole")
from spiders.base import _TokenBucket


def test_initial_burst_no_wait():
    bucket = _TokenBucket(rate=1.0, burst=3)
    t0 = time.monotonic()
    for _ in range(3):
        bucket.acquire()
    elapsed = time.monotonic() - t0
    assert elapsed < 0.5


def test_tokens_deplete():
    bucket = _TokenBucket(rate=10.0, burst=1)
    bucket.acquire()
    # After burst is used, next acquire should briefly wait
    t0 = time.monotonic()
    bucket.acquire()
    elapsed = time.monotonic() - t0
    assert elapsed >= 0.05
