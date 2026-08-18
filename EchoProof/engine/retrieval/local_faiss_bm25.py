"""Local hybrid retriever: BM25 plus dense vectors, fused.

This is the MVP backend. It sits behind `Retriever` so the Production
OpenSearch swap replaces this file and nothing else.

Two design points worth stating, because both look like arbitrary choices and
are not:

**Ranking and confidence come from different signals.** Reciprocal rank fusion
decides the ORDER, because it is robust when BM25 and dense scores live on
incompatible scales. But RRF scores are not calibrated: a top RRF score of
0.032 says nothing about whether the match is any good, so it cannot drive the
floor and ceiling thresholds SPEC section 5 depends on. Cosine similarity from
a normalised embedding model is calibrated and interpretable, so it supplies the
`score` used for confidence. Order from fusion, confidence from cosine.

**Embeddings run locally.** An API-side embedding model can change underneath a
scored evaluation run with no change on our side, which is what ARCHITECTURE.md
decision 9 forbids. A pinned local model makes precision@1 exactly reproducible
and makes re-indexing during threshold calibration free.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import faiss
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

from core.config import EMBEDDING_MODEL, EMBEDDING_REVISION
from core.contracts import Chunk, RetrievalCandidate
from engine.retrieval.base import RetrievalConfig, Retriever
from engine.retrieval.rerank import Reranker

# bge models are trained with an asymmetric prefix on the query side only.
# Omitting it measurably degrades retrieval, and applying it to passages as well
# degrades it differently, so it goes on exactly one side.
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

# Reciprocal rank fusion constant. 60 is the value from the original RRF paper
# and is deliberately not tuned here: tuning it against the same pairs used to
# report precision@1 would inflate the reported number.
RRF_K = 60

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:\.[a-z0-9]+)*")


def tokenize(text: str) -> list[str]:
    """Lowercase word tokens, keeping section numbers like 1006.14 intact."""
    return _TOKEN_RE.findall(text.lower())


class LocalHybridRetriever(Retriever):
    """BM25 and FAISS over the same chunk set, fused by reciprocal rank."""

    def __init__(
        self,
        cache_dir: Path | None = None,
        batch_size: int = 64,
        reranker: Reranker | None = None,
    ) -> None:
        self._chunks: list[Chunk] = []
        self._bm25: BM25Okapi | None = None
        self._faiss: faiss.Index | None = None
        self._model: SentenceTransformer | None = None
        self._cache_dir = cache_dir
        self._batch_size = batch_size
        self._reranker = reranker

    # -- model ------------------------------------------------------------

    @property
    def model(self) -> SentenceTransformer:
        """Load the embedding model lazily.

        Lazy because the deterministic-check tests and the chunking tests have
        no business paying a model load, and because a missing model should fail
        when retrieval is actually attempted rather than at import time.
        """
        if self._model is None:
            self._model = SentenceTransformer(
                EMBEDDING_MODEL, revision=EMBEDDING_REVISION
            )
        return self._model

    # -- indexing ---------------------------------------------------------

    def index(self, chunks: list[Chunk]) -> None:
        if not chunks:
            raise ValueError("cannot index an empty chunk set")
        self._chunks = list(chunks)
        self._bm25 = BM25Okapi([tokenize(c.embed_text) for c in self._chunks])

        vectors = self._load_cached_vectors()
        if vectors is None:
            vectors = self._embed([c.embed_text for c in self._chunks])
            self._save_cached_vectors(vectors)

        dimension = vectors.shape[1]
        # Inner product over L2-normalised vectors is cosine similarity, which
        # is what makes `score` interpretable against the thresholds.
        index = faiss.IndexFlatIP(dimension)
        index.add(vectors)
        self._faiss = index

    def _embed(self, texts: list[str]) -> np.ndarray:
        raw = self.model.encode(
            texts,
            batch_size=self._batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        return np.asarray(raw, dtype="float32")

    def _cache_paths(self) -> tuple[Path, Path] | None:
        if self._cache_dir is None:
            return None
        return (
            self._cache_dir / "vectors.npy",
            self._cache_dir / "vectors.meta.json",
        )

    def _cache_signature(self) -> dict[str, Any]:
        # Keyed on the exact text embedded, not just the chunk identifiers.
        # Chunk ids are stable across changes to how a chunk's context is built,
        # so an id-only key would happily serve vectors computed for the old
        # text against the new text and silently corrupt every retrieval number.
        digest = hashlib.sha256()
        for chunk in self._chunks:
            digest.update(chunk.chunk_id.encode("utf-8"))
            digest.update(b"\0")
            digest.update(chunk.embed_text.encode("utf-8"))
            digest.update(b"\0")
        return {
            "model": EMBEDDING_MODEL,
            "revision": EMBEDDING_REVISION,
            "chunk_count": len(self._chunks),
            "embed_text_digest": digest.hexdigest(),
        }

    def _load_cached_vectors(self) -> np.ndarray | None:
        paths = self._cache_paths()
        if paths is None:
            return None
        vectors_path, meta_path = paths
        if not (vectors_path.exists() and meta_path.exists()):
            return None
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
        # The cache is keyed on the exact chunk set and model. Any change to
        # either invalidates it, because a stale vector silently paired with a
        # new chunk would corrupt every retrieval number downstream.
        if meta != self._cache_signature():
            return None
        return np.load(vectors_path)

    def _save_cached_vectors(self, vectors: np.ndarray) -> None:
        paths = self._cache_paths()
        if paths is None:
            return
        vectors_path, meta_path = paths
        vectors_path.parent.mkdir(parents=True, exist_ok=True)
        np.save(vectors_path, vectors)
        meta_path.write_text(
            json.dumps(self._cache_signature(), sort_keys=True), encoding="utf-8"
        )

    # -- search -----------------------------------------------------------

    def search(self, query: str, config: RetrievalConfig) -> list[RetrievalCandidate]:
        if self._bm25 is None or self._faiss is None:
            raise RuntimeError("index() must be called before search()")

        # Depth pulled from each first-stage retriever independently. Wider than
        # the number of candidates finally reranked, so the union is genuinely
        # covered rather than silently truncated.
        pool = min(config.first_stage_k, len(self._chunks))

        bm25_scores = self._bm25.get_scores(tokenize(query))
        bm25_order = np.argsort(bm25_scores)[::-1][:pool]

        query_vector = self._embed([QUERY_PREFIX + query])
        cosine, dense_order = self._faiss.search(query_vector, pool)
        cosine = cosine[0]
        dense_order = dense_order[0]

        bm25_rank = {int(idx): rank for rank, idx in enumerate(bm25_order)}
        dense_rank = {int(idx): rank for rank, idx in enumerate(dense_order)}
        cosine_by_index = {
            int(idx): float(score) for idx, score in zip(dense_order, cosine)
        }

        fused: dict[int, float] = {}
        for ranks in (bm25_rank, dense_rank):
            for idx, rank in ranks.items():
                fused[idx] = fused.get(idx, 0.0) + 1.0 / (RRF_K + rank + 1)

        # Order by fusion over the FULL union of both retrievers, then cap at
        # rerank_k rather than at the per-retriever pool depth. Capping here at
        # `pool` was the bug: it threw away up to half the union before the
        # reranker could look at it.
        ordered = sorted(
            fused.items(),
            key=lambda item: (item[1], cosine_by_index.get(item[0], 0.0)),
            reverse=True,
        )[: min(config.rerank_k, len(self._chunks))]

        candidates: list[RetrievalCandidate] = []
        for idx, _fused_score in ordered:
            chunk = self._chunks[idx]
            score = cosine_by_index.get(idx)
            if score is None:
                # BM25 surfaced a chunk the dense side did not return, so its
                # cosine is unknown. Compute it rather than guessing, or this
                # chunk could never clear a threshold no matter how good it is.
                score = float(
                    np.dot(
                        self._embed([QUERY_PREFIX + query])[0],
                        self._embed([chunk.embed_text])[0],
                    )
                )
            candidates.append(
                RetrievalCandidate(
                    section_id=chunk.section_id,
                    chunk_id=chunk.chunk_id,
                    text=chunk.text,
                    score=score,
                    bm25_rank=bm25_rank.get(idx),
                    dense_rank=dense_rank.get(idx),
                    heading=chunk.parent_heading,
                )
            )

        # Fusion has done the recall work; the reranker decides the order and
        # supplies the calibrated score the thresholds are applied to.
        if self._reranker is not None:
            return self._reranker.rerank(query, candidates)

        # Without a reranker, confidence must still be monotone with rank or the
        # thresholds do not mean what they say.
        candidates.sort(key=lambda c: (-c.score, c.chunk_id))
        return candidates

    def config_fingerprint(self) -> dict[str, object]:
        fingerprint: dict[str, object] = {
            "retriever": "local_faiss_bm25",
            "embedding_model": EMBEDDING_MODEL,
            "embedding_revision": EMBEDDING_REVISION,
            "fusion": "rrf",
            "rrf_k": RRF_K,
            "query_prefix": QUERY_PREFIX,
            "chunk_count": len(self._chunks),
        }
        fingerprint.update(
            self._reranker.fingerprint()
            if self._reranker is not None
            else {"reranker": "none"}
        )
        return fingerprint
