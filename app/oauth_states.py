"""Bounded, single-use OAuth state; no I/O under its private lock."""
import math
import threading
import time

DEFAULT_TTL_SECONDS = 600
DEFAULT_CAPACITY = 10


class OAuthStates:
    def __init__(self, *, ttl_seconds=DEFAULT_TTL_SECONDS, capacity=DEFAULT_CAPACITY, clock=None):
        if (isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, (int, float))
                or not math.isfinite(ttl_seconds) or ttl_seconds <= 0
                or isinstance(capacity, bool) or not isinstance(capacity, int) or capacity <= 0):
            raise ValueError("invalid OAuth state bounds")
        self._ttl = ttl_seconds
        self._capacity = capacity
        self._clock = time.monotonic if clock is None else clock
        self._values = {}
        self._deadlines = {}
        self._lock = threading.Lock()

    def _discard(self, key):
        self._values.pop(key, None)
        self._deadlines.pop(key, None)

    def _expire(self, now):
        for key, deadline in tuple(self._deadlines.items()):
            if now >= deadline:
                self._discard(key)

    def __setitem__(self, key, value):
        with self._lock:
            now = self._clock()
            self._expire(now)
            if key in self._values:
                self._discard(key)
            elif len(self._values) >= self._capacity:
                self._discard(next(iter(self._values)))
            self._values[key] = value
            self._deadlines[key] = now + self._ttl

    def pop(self, key, *default):
        if len(default) > 1:
            raise TypeError(f"pop expected at most 2 arguments, got {len(default) + 1}")
        with self._lock:
            self._expire(self._clock())
            value = self._values.pop(key, *default)
            self._deadlines.pop(key, None)
            return value
