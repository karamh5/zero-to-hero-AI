"""Reranking: top 50 candidates down to the governing section (SPEC section 5).

Why this stage exists, measured rather than assumed. On the 54 query/section
pairs, hybrid fusion alone gave precision@1 0.574 with recall@50 of 1.000. The
governing paragraph was retrieved every single time and then ranked below
something else. That is a ranking problem, not a recall problem, and it is the
exact problem a cross-encoder solves: bi-encoders score a query and a passage
independently, so they cannot represent the interaction between them, while a
cross-encoder reads both together.

The reranker also supplies better-calibrated confidence than cosine similarity.
Cosine over bge embeddings compresses everything into roughly 0.70 to 0.90, so
the floor and ceiling thresholds had almost no room to separate real matches
from near misses. A cross-encoder's sigmoid output spreads across the range,
which is what makes the two thresholds in SPEC section 5 meaningful instead of
nominal.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod

from core.contracts import RetrievalCandidate

RERANK_MODEL = "BAAI/bge-reranker-base"
RERANK_REVISION = "main"


class Reranker(ABC):
    """Rescores an already-retrieved candidate list."""

    @abstractmethod
    def rerank(
        self, query: str, candidates: list[RetrievalCandidate]
    ) -> list[RetrievalCandidate]:
        """Return the candidates reordered, with `score` replaced."""

    @abstractmethod
    def fingerprint(self) -> dict[str, object]:
        """Identity of this reranker, pinned into the retrieve.rule span."""


class CrossEncoderReranker(Reranker):
    """Cross-encoder reranking with a locally pinned model.

    Local for the same reason the embeddings are local: an API-side model can
    change underneath a scored run, and CLAUDE.md decision 9 requires the
    backend that produced a run's numbers to stay fixed for that run.
    """

    def __init__(self, batch_size: int = 32) -> None:
        self._model = None
        self._batch_size = batch_size

    @property
    def model(self):  # type: ignore[no-untyped-def]
        """Load lazily so tests that never rerank do not pay the model load."""
        if self._model is None:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(RERANK_MODEL, revision=RERANK_REVISION)
        return self._model

    def rerank(
        self, query: str, candidates: list[RetrievalCandidate]
    ) -> list[RetrievalCandidate]:
        if not candidates:
            return []

        # The heading goes in alongside the body. A paragraph reading "More than
        # seven times within seven consecutive days; nor" cannot be judged
        # relevant to a call frequency question without the provision it sits
        # under, and that is true for the cross-encoder just as it was for the
        # embedding model.
        pairs = [
            (query, f"{c.heading} {c.text}".strip() if c.heading else f"{c.section_id} {c.text}")
            for c in candidates
        ]
        raw = self.model.predict(
            pairs, batch_size=self._batch_size, show_progress_bar=False
        )

        rescored = [
            RetrievalCandidate(
                section_id=candidate.section_id,
                chunk_id=candidate.chunk_id,
                text=candidate.text,
                score=_sigmoid(float(logit)),
                bm25_rank=candidate.bm25_rank,
                dense_rank=candidate.dense_rank,
            )
            for candidate, logit in zip(candidates, raw)
        ]
        # Tie-break on chunk_id so the ordering is total and reproducible.
        rescored.sort(key=lambda c: (-c.score, c.chunk_id))
        return rescored

    def fingerprint(self) -> dict[str, object]:
        return {
            "reranker": "cross_encoder",
            "model": RERANK_MODEL,
            "revision": RERANK_REVISION,
            "score_transform": "sigmoid",
        }


def _sigmoid(value: float) -> float:
    """Map a cross-encoder logit into [0, 1] so thresholds are interpretable."""
    if value >= 0:
        return 1.0 / (1.0 + math.exp(-value))
    exp_value = math.exp(value)
    return exp_value / (1.0 + exp_value)
