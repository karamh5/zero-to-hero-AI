"""On-disk retrieval cache.

A campaign runs the same scenario three times with the same seed, so the same
claims recur and the same retrieval queries are issued repeatedly. Reranking is
the dominant cost in the pipeline: fifty cross-encoder passes per query, times
two or three questions per claim, on CPU.

This is a correctness-preserving optimisation, not a shortcut. The cache stores
the exact candidate list a query produced and returns it unchanged, so a cached
run and an uncached run are byte identical. It also strengthens the
reproducibility property SPEC section 7 defines: identical stored inputs return
an identical ranking by construction, rather than by trusting that the reranker
is deterministic across processes.

The key includes the retriever's own configuration fingerprint, so changing the
embedding model, the reranker, the fusion constant or the pool depths
invalidates every entry. That is the same discipline the embedding vector cache
already uses, and it exists because a stale entry silently paired with new
config would corrupt every number downstream without any visible failure.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.contracts import Chunk, RetrievalCandidate
from core.hashing import hash_object
from engine.retrieval.base import RetrievalConfig, Retriever


class CachingRetriever(Retriever):
    """Wraps a retriever and memoises `search` results on disk."""

    def __init__(
        self,
        inner: Retriever,
        cache_dir: Path,
        pack_version: str,
        enabled: bool = True,
    ) -> None:
        self._inner = inner
        self._dir = cache_dir
        self._pack_version = pack_version
        self._enabled = enabled
        self.hits = 0
        self.misses = 0

    def index(self, chunks: list[Chunk]) -> None:
        self._inner.index(chunks)

    def config_fingerprint(self) -> dict[str, object]:
        return self._inner.config_fingerprint()

    def _key(self, query: str, config: RetrievalConfig) -> str:
        return hash_object(
            {
                "query": query,
                "pack_version": self._pack_version,
                "retriever": self._inner.config_fingerprint(),
                # Only the depths affect which candidates come back. The floor
                # and ceiling are applied after search and must not be part of
                # the key, or recalibrating thresholds would needlessly discard
                # a cache that is still perfectly valid.
                "first_stage_k": config.first_stage_k,
                "rerank_k": config.rerank_k,
            }
        )

    def _path(self, key: str) -> Path:
        return self._dir / key[:2] / f"{key}.json"

    def search(self, query: str, config: RetrievalConfig) -> list[RetrievalCandidate]:
        if not self._enabled:
            return self._inner.search(query, config)

        key = self._key(query, config)
        path = self._path(key)

        if path.exists():
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                self.hits += 1
                return [
                    RetrievalCandidate(
                        section_id=c["section_id"],
                        chunk_id=c["chunk_id"],
                        text=c["text"],
                        score=float(c["score"]),
                        bm25_rank=c.get("bm25_rank"),
                        dense_rank=c.get("dense_rank"),
                        heading=c.get("heading", ""),
                    )
                    for c in payload["candidates"]
                ]
            except (json.JSONDecodeError, KeyError, TypeError):
                # A corrupt entry is recomputed rather than raised on. The cache
                # is an accelerator and must never be able to fail a run.
                pass

        candidates = self._inner.search(query, config)
        self.misses += 1

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "query": query,
                    "candidates": [
                        {
                            "section_id": c.section_id,
                            "chunk_id": c.chunk_id,
                            "text": c.text,
                            "score": c.score,
                            "bm25_rank": c.bm25_rank,
                            "dense_rank": c.dense_rank,
                            "heading": c.heading,
                        }
                        for c in candidates
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return candidates

    def stats(self) -> dict[str, int | float]:
        total = self.hits + self.misses
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(self.hits / total, 4) if total else 0.0,
        }
