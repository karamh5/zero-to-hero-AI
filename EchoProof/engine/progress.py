"""Live stage reporting for the demo (SPEC section 9's operator surface).

Adjudication takes up to 140 seconds. A room cannot watch a blank screen for
that long, and the fix is not to make the wait shorter by cutting work: it is to
make the wait legible.

Every line here reports **work that actually happened**. There is no timed
progress bar and no synthetic percentage, because a bar that advances on a timer
while nothing is happening is a lie an audience can usually detect, and this
product's entire argument is that its outputs are checkable.

The stage names double as the demo narration. When the screen says
`retrieve  query 2/3` the presenter has something true to say about why a claim
is being looked up three different ways.
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from typing import Any, TextIO

# Stage labels, kept short and fixed-width so the output aligns into a column a
# room can read from the back.
LABELS = {
    "extract.start": "extract   reading the turn",
    "extract.done": "extract   claims found",
    "claim.start": "claim     adjudicating",
    "deterministic.decided": "verify    decided in code",
    "retrieve.query": "retrieve  searching the corpus",
    "retrieve.done": "retrieve  candidates ranked",
    "judge.start": "judge     reading the rules",
    "judge.done": "judge     verdict",
    "evidence.written": "evidence  chain written",
}


@dataclass
class ProgressPrinter:
    """Prints pipeline stages with elapsed time, for a screen."""

    stream: TextIO = field(default_factory=lambda: sys.stdout)
    started: float = field(default_factory=time.perf_counter)
    verbose: bool = True
    events: list[tuple[float, str, dict[str, Any]]] = field(default_factory=list)

    def __call__(self, stage: str, detail: dict[str, Any]) -> None:
        elapsed = time.perf_counter() - self.started
        self.events.append((elapsed, stage, detail))
        if not self.verbose:
            return

        label = LABELS.get(stage, stage)
        note = self._describe(stage, detail)
        print(
            f"  [{elapsed:6.1f}s] {label:34} {note}",
            file=self.stream,
            flush=True,
        )

    def _describe(self, stage: str, d: dict[str, Any]) -> str:
        if stage == "extract.start":
            return f"{d.get('chars')} characters"
        if stage == "extract.done":
            rejected = d.get("rejected") or 0
            extra = f", {rejected} rejected" if rejected else ""
            return f"{d.get('claims')} claim(s){extra}"
        if stage == "claim.start":
            return (
                f"{d.get('index')}/{d.get('total')}  {d.get('claim_type')}  "
                f"{d.get('text', '')!r}"
            )
        if stage == "deterministic.decided":
            # Worth calling out on stage: this verdict involved no model at all.
            return f"{d.get('value')} -> {d.get('verdict')} (no model involved)"
        if stage == "retrieve.query":
            return f"query {d.get('number')}/{d.get('of')}  {d.get('query', '')!r}"
        if stage == "retrieve.done":
            return f"{d.get('candidates')} candidates, top {d.get('top')} @ {d.get('score')}"
        if stage == "judge.start":
            return f"{d.get('offered')} sections offered"
        if stage == "judge.done":
            section = d.get("section_id") or "-"
            return f"{d.get('verdict')} @ {section}"
        if stage == "evidence.written":
            return f"{d.get('spans')} spans, {d.get('findings')} finding(s)"
        return ", ".join(f"{k}={v}" for k, v in d.items())

    @property
    def elapsed(self) -> float:
        return time.perf_counter() - self.started

    def to_dict(self) -> dict[str, Any]:
        return {
            "elapsed_seconds": round(self.elapsed, 2),
            "events": [
                {"at": round(at, 2), "stage": stage, **detail}
                for at, stage, detail in self.events
            ],
        }
