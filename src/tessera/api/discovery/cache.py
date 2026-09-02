"""TTL cache between the sources and the request path.

`GET /api/eval-setup` must never probe: a stopped daemon would otherwise add its
timeout to every page load. The cache is the boundary that guarantees it.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

from .types import DiscoveredModel, SourceResult

Collected = tuple[list[DiscoveredModel], list[SourceResult]]


class DiscoveryCache:
    def __init__(
        self,
        *,
        ttl_seconds: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
        collect: Callable[[], Collected],
    ) -> None:
        self._ttl = ttl_seconds
        self._clock = clock
        self._collect = collect
        self._lock = threading.Lock()
        self._value: Collected | None = None
        self._stamp: float = 0.0

    def get(self) -> Collected:
        with self._lock:
            fresh = self._value is not None and (self._clock() - self._stamp) < self._ttl
            if fresh:
                return self._value            # type: ignore[return-value]
            try:
                self._value = self._collect()
                self._stamp = self._clock()
            except Exception:  # noqa: BLE001 — stale rows beat a failed page load
                if self._value is None:
                    return [], []
            return self._value                # type: ignore[return-value]

    def invalidate(self) -> None:
        with self._lock:
            self._value = None
