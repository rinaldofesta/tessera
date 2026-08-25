"""Thread-safe TTL cache; reads are pure snapshots and never perform discovery."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

from tessera.api.discovery.models import DiscoverySnapshot


class DiscoveryCache:
    def __init__(
        self,
        refresh: Callable[[], DiscoverySnapshot],
        initial: DiscoverySnapshot,
        *,
        ttl_seconds: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._refresh = refresh
        self._snapshot = initial
        self._ttl_seconds = max(0.1, ttl_seconds)
        self._clock = clock
        self._refreshed_at: float | None = None
        self._lock = threading.RLock()
        self._refresh_lock = threading.Lock()

    @property
    def ttl_seconds(self) -> float:
        return self._ttl_seconds

    def snapshot(self) -> DiscoverySnapshot:
        with self._lock:
            return self._snapshot

    def is_stale(self) -> bool:
        with self._lock:
            return (
                self._refreshed_at is None
                or self._clock() - self._refreshed_at >= self._ttl_seconds
            )

    def invalidate(self) -> None:
        with self._lock:
            self._refreshed_at = None

    def refresh(self) -> DiscoverySnapshot:
        # Do I/O outside the lock so normal GETs can keep reading the last good snapshot.
        with self._refresh_lock:
            return self._refresh_locked()

    def _refresh_locked(self) -> DiscoverySnapshot:
        snapshot = self._refresh()
        with self._lock:
            self._snapshot = snapshot
            self._refreshed_at = self._clock()
            return self._snapshot

    def refresh_if_stale(self) -> DiscoverySnapshot:
        if not self.is_stale():
            return self.snapshot()
        with self._refresh_lock:
            # Another refresher may have completed while this caller waited.
            if not self.is_stale():
                return self.snapshot()
            return self._refresh_locked()
