from tessera.api.discovery.cache import DiscoveryCache
from tessera.api.discovery.types import DiscoveredModel, SourceResult


def _collect_factory(counter):
    def collect():
        counter.append(1)
        model = DiscoveredModel(f"ollama/m{len(counter)}", "m", "ollama", "ready", "ollama")
        return [model], [SourceResult("ollama", (model,), "ok")]
    return collect


def test_a_second_read_inside_the_ttl_does_not_recollect():
    calls, now = [], [1000.0]
    cache = DiscoveryCache(ttl_seconds=60.0, clock=lambda: now[0], collect=_collect_factory(calls))
    first, _ = cache.get()
    now[0] += 30.0
    second, _ = cache.get()
    assert len(calls) == 1
    assert [m.id for m in first] == [m.id for m in second]


def test_a_read_after_the_ttl_expires_recollects():
    calls, now = [], [1000.0]
    cache = DiscoveryCache(ttl_seconds=60.0, clock=lambda: now[0], collect=_collect_factory(calls))
    cache.get()
    now[0] += 61.0
    cache.get()
    assert len(calls) == 2


def test_invalidate_forces_the_next_read_to_recollect():
    calls, now = [], [1000.0]
    cache = DiscoveryCache(ttl_seconds=3600.0, clock=lambda: now[0], collect=_collect_factory(calls))
    cache.get()
    cache.invalidate()
    cache.get()
    assert len(calls) == 2


def test_a_collect_that_raises_serves_the_previous_value_rather_than_failing_the_read():
    # A launcher that renders stale rows beats a launcher that 500s.
    calls, now = [], [1000.0]
    collect = _collect_factory(calls)
    cache = DiscoveryCache(ttl_seconds=1.0, clock=lambda: now[0], collect=collect)
    warm, _ = cache.get()

    def boom():
        raise RuntimeError("sources exploded")

    cache._collect = boom            # noqa: SLF001 — exercising the degradation path
    now[0] += 10.0
    served, _ = cache.get()
    assert [m.id for m in served] == [m.id for m in warm]


def test_the_first_ever_collect_failing_yields_an_empty_result_not_an_exception():
    def boom():
        raise RuntimeError("sources exploded")

    models, statuses = DiscoveryCache(ttl_seconds=1.0, clock=lambda: 0.0, collect=boom).get()
    assert (models, statuses) == ([], [])
