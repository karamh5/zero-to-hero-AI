"""The retrieval cache must not change results.

A faster cache that returns anything different from an uncached search is not an
optimisation, it is a silent corruption of every retrieval number downstream.
These use a stub retriever so the property is tested without loading models.
"""

from __future__ import annotations

from core.contracts import Chunk, RetrievalCandidate
from engine.retrieval.base import RetrievalConfig, Retriever
from engine.retrieval.cache import CachingRetriever

CONFIG = RetrievalConfig(floor=0.4, ceiling=0.6)


class StubRetriever(Retriever):
    """Counts calls, so a cache hit is observable."""

    def __init__(self, fingerprint: dict | None = None) -> None:
        self.calls = 0
        self._fingerprint = fingerprint or {"retriever": "stub", "v": 1}

    def index(self, chunks: list[Chunk]) -> None:
        return None

    def search(self, query: str, config: RetrievalConfig) -> list[RetrievalCandidate]:
        self.calls += 1
        return [
            RetrievalCandidate(
                section_id="1006.14(g)",
                chunk_id="1006.14(g)",
                text=f"text for {query}",
                score=0.6123456789,
                bm25_rank=0,
                dense_rank=1,
                heading="heading",
            )
        ]

    def config_fingerprint(self) -> dict:
        return self._fingerprint


def test_a_cached_search_returns_identical_candidates(tmp_path) -> None:  # type: ignore[no-untyped-def]
    inner = StubRetriever()
    cache = CachingRetriever(inner, tmp_path, "pack-v1")

    cold = cache.search("a query", CONFIG)
    warm = cache.search("a query", CONFIG)

    assert inner.calls == 1
    assert len(cold) == len(warm)
    for a, b in zip(cold, warm):
        assert a.section_id == b.section_id
        assert a.chunk_id == b.chunk_id
        assert a.text == b.text
        assert a.score == b.score
        assert a.bm25_rank == b.bm25_rank
        assert a.dense_rank == b.dense_rank
        assert a.heading == b.heading


def test_score_precision_survives_the_round_trip(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Thresholds compare against this, so a rounded score is a changed result."""
    inner = StubRetriever()
    cache = CachingRetriever(inner, tmp_path, "pack-v1")
    cold = cache.search("q", CONFIG)
    warm = cache.search("q", CONFIG)
    assert cold[0].score == warm[0].score == 0.6123456789


def test_a_different_query_is_a_different_entry(tmp_path) -> None:  # type: ignore[no-untyped-def]
    inner = StubRetriever()
    cache = CachingRetriever(inner, tmp_path, "pack-v1")
    cache.search("first", CONFIG)
    cache.search("second", CONFIG)
    assert inner.calls == 2


def test_a_changed_retriever_fingerprint_invalidates_the_cache(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """A stale entry paired with new config would corrupt every number."""
    first = StubRetriever({"retriever": "stub", "v": 1})
    CachingRetriever(first, tmp_path, "pack-v1").search("q", CONFIG)

    second = StubRetriever({"retriever": "stub", "v": 2})
    CachingRetriever(second, tmp_path, "pack-v1").search("q", CONFIG)
    assert second.calls == 1


def test_a_changed_pack_version_invalidates_the_cache(tmp_path) -> None:  # type: ignore[no-untyped-def]
    first = StubRetriever()
    CachingRetriever(first, tmp_path, "pack-v1").search("q", CONFIG)

    second = StubRetriever()
    CachingRetriever(second, tmp_path, "pack-v2").search("q", CONFIG)
    assert second.calls == 1


def test_changing_a_threshold_does_not_invalidate_the_cache(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Floor and ceiling are applied after search, so they are not in the key.

    Recalibrating thresholds must not throw away a cache that is still correct.
    """
    inner = StubRetriever()
    cache = CachingRetriever(inner, tmp_path, "pack-v1")
    cache.search("q", RetrievalConfig(floor=0.4, ceiling=0.6))
    cache.search("q", RetrievalConfig(floor=0.1, ceiling=0.9))
    assert inner.calls == 1


def test_a_changed_pool_depth_does_invalidate_the_cache(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Depths change which candidates come back, so they are in the key."""
    inner = StubRetriever()
    cache = CachingRetriever(inner, tmp_path, "pack-v1")
    cache.search("q", RetrievalConfig(floor=0.4, ceiling=0.6, rerank_k=50))
    cache.search("q", RetrievalConfig(floor=0.4, ceiling=0.6, rerank_k=100))
    assert inner.calls == 2


def test_a_corrupt_entry_is_recomputed_rather_than_raised(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """The cache is an accelerator and must never be able to fail a run."""
    inner = StubRetriever()
    cache = CachingRetriever(inner, tmp_path, "pack-v1")
    cache.search("q", CONFIG)

    for path in tmp_path.rglob("*.json"):
        path.write_text("{ this is not valid json", encoding="utf-8")

    result = cache.search("q", CONFIG)
    assert inner.calls == 2
    assert result[0].section_id == "1006.14(g)"


def test_disabled_cache_always_calls_through(tmp_path) -> None:  # type: ignore[no-untyped-def]
    inner = StubRetriever()
    cache = CachingRetriever(inner, tmp_path, "pack-v1", enabled=False)
    cache.search("q", CONFIG)
    cache.search("q", CONFIG)
    assert inner.calls == 2


def test_stats_report_hits_and_misses(tmp_path) -> None:  # type: ignore[no-untyped-def]
    cache = CachingRetriever(StubRetriever(), tmp_path, "pack-v1")
    cache.search("q", CONFIG)
    cache.search("q", CONFIG)
    stats = cache.stats()
    assert stats["hits"] == 1 and stats["misses"] == 1
    assert stats["hit_rate"] == 0.5
