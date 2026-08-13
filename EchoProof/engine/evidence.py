"""Append-only, hash-chained evidence log (SPEC section 7).

Entry N's hash covers entry N-1's hash, so editing anything in the middle
invalidates every hash after it. That is what makes the log tamper-evident and
what lets the report seal break visibly when the agent version or policy pack
version changes.

Built in Phase 1 rather than Phase 3 on purpose. CLAUDE.md decision 7 requires
every model call, retrieval call and finding to write a span before the feature
is considered done, and retrofitting instrumentation into finished code reliably
misses the calls that matter.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from core.contracts import Span
from core.hashing import HASH_SCHEME, chain_hash

# The span types SPEC section 7 defines. Phase 1 emits the middle four; the
# others arrive with audio capture and the report. Declaring all of them here
# keeps the vocabulary in one place rather than as string literals at call sites.
SPAN_CALL_SESSION = "call.session"
SPAN_AGENT_TURN = "agent.turn"
SPAN_EXTRACT_CLAIMS = "extract.claims"
SPAN_CHECK_DETERMINISTIC = "check.deterministic"
SPAN_RETRIEVE_RULE = "retrieve.rule"
SPAN_JUDGE_RULE = "judge.rule"
SPAN_FINDING_EMIT = "finding.emit"

GENESIS_HASH = ""


class ChainError(RuntimeError):
    """Raised when the evidence chain does not verify."""


@dataclass
class EvidenceLog:
    """An append-only chain of spans for one run."""

    run_id: str
    spans: list[Span] = field(default_factory=list)

    @property
    def head(self) -> str:
        """The hash of the most recent entry, or the genesis value."""
        return self.spans[-1].entry_hash if self.spans else GENESIS_HASH

    def append(self, span_type: str, payload: dict[str, Any]) -> Span:
        """Add a span. The only way to write to the log."""
        span_id = f"{self.run_id}-{len(self.spans):04d}"
        entry = {"span_type": span_type, "span_id": span_id, "payload": payload}
        span = Span(
            span_type=span_type,
            span_id=span_id,
            payload=payload,
            prev_hash=self.head,
            entry_hash=chain_hash(self.head, entry),
        )
        self.spans.append(span)
        return span

    def verify(self) -> bool:
        """Recompute the whole chain and compare.

        This is the mechanism behind SPEC section 11's reproducibility-by-hash
        diagnostic: a stored run replays to the same chain, or it does not.
        """
        previous = GENESIS_HASH
        for span in self.spans:
            if span.prev_hash != previous:
                return False
            entry = {
                "span_type": span.span_type,
                "span_id": span.span_id,
                "payload": span.payload,
            }
            if span.entry_hash != chain_hash(previous, entry):
                return False
            previous = span.entry_hash
        return True

    def of_type(self, span_type: str) -> Iterator[Span]:
        return (s for s in self.spans if s.span_type == span_type)

    def write(self, path: Path) -> Path:
        """Persist the log as JSON Lines, header first."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {
                        "run_id": self.run_id,
                        "hash_scheme": HASH_SCHEME,
                        "span_count": len(self.spans),
                        "head": self.head,
                    },
                    sort_keys=True,
                )
                + "\n"
            )
            for span in self.spans:
                handle.write(json.dumps(span.to_dict(), sort_keys=True) + "\n")
        return path

    @classmethod
    def read(cls, path: Path) -> "EvidenceLog":
        """Load a log and verify its chain before returning it.

        Verification on read rather than on demand: a caller who forgets to
        verify would otherwise be handed a tampered log that looks fine.
        """
        lines = [
            line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
        ]
        if not lines:
            raise ChainError(f"{path} is empty")

        header = json.loads(lines[0])
        log = cls(run_id=header["run_id"])
        for line in lines[1:]:
            record = json.loads(line)
            log.spans.append(
                Span(
                    span_type=record["span_type"],
                    span_id=record["span_id"],
                    payload=record["payload"],
                    prev_hash=record["prev_hash"],
                    entry_hash=record["entry_hash"],
                )
            )
        if not log.verify():
            raise ChainError(f"evidence chain in {path} does not verify")
        if log.head != header["head"]:
            raise ChainError(f"head hash in {path} does not match the chain")
        return log
