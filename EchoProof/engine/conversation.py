"""Role-aware conversation adjudication.

**Only agent turns are ever adjudicated.** Customer turns are context and
nothing else: they are never extracted from, never given a verdict, never
scored, and never counted. This module is where that rule stops being a
convention held by careful callers and becomes something the code enforces.

Before this existed, `adjudicate_turn` took a bare string with no notion of
who was speaking. Agent-only held because the campaign runner and the proxy
happened to pass agent text, and it did not hold at all for the transcript
ingest route or the rig, where any pasted text was extracted from and judged.
An audit found no active case of a customer turn being scored, but nothing
prevented one.

The second thing this fixes: the judge could not see what the customer said,
so it could not tell whether an agent responded correctly to a written
dispute, a cease-contact request or a wrong-party statement. Those are exactly
the obligations a collections agent is judged on. Customer turns now travel to
the judge as context, clearly labelled as context, with the instruction that
only the agent's claim is under adjudication.

ARCHITECTURE.md decision 9 note: passing context changes what the judge sees, so it
would invalidate comparison against previously scored runs. It is therefore
opt-in. `context_turns` defaults to empty and every existing caller keeps its
exact prior behaviour; only conversations built through this module supply it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Callable

from core.contracts import Verdict
from engine.evidence import EvidenceLog
from engine.pipeline import TurnResult, adjudicate_turn
from engine.retrieval.base import RetrievalConfig, Retriever
from models.client import ModelClient

# The two roles this engine understands. `agent` is the system under test;
# everything else is context. Kept as a frozenset rather than a bare string
# compare so a pack using "assistant" or "bot" is accepted rather than
# silently treated as a customer and skipped.
AGENT_ROLES = frozenset({"agent", "assistant", "bot"})
CUSTOMER_ROLES = frozenset({"customer", "consumer", "user", "caller"})


class ConversationError(ValueError):
    """Raised when a conversation is malformed or unlabelled."""


@dataclass(frozen=True)
class Turn:
    """One utterance with an explicit speaker."""

    role: str
    text: str
    audio_ref: str | None = None

    @property
    def is_agent(self) -> bool:
        return self.role.strip().lower() in AGENT_ROLES

    @property
    def is_customer(self) -> bool:
        return self.role.strip().lower() in CUSTOMER_ROLES

    def to_dict(self) -> dict[str, Any]:
        return {"role": self.role, "text": self.text, "audio_ref": self.audio_ref}


def parse_turns(raw: list[dict[str, Any]]) -> list[Turn]:
    """Build turns from pack data, rejecting anything unlabelled.

    An unrecognised role is an error rather than a default. Defaulting to
    `customer` would silently drop agent turns from adjudication, and
    defaulting to `agent` would score the consumer. Both are worse than
    refusing to run.
    """
    turns: list[Turn] = []
    for index, item in enumerate(raw):
        role = str(item.get("role", "")).strip().lower()
        if not role:
            raise ConversationError(f"turn {index} has no role")
        if role not in AGENT_ROLES and role not in CUSTOMER_ROLES:
            raise ConversationError(
                f"turn {index} has unrecognised role {role!r}. "
                f"Agent roles: {sorted(AGENT_ROLES)}. "
                f"Customer roles: {sorted(CUSTOMER_ROLES)}."
            )
        text = str(item.get("text", "")).strip()
        if not text:
            raise ConversationError(f"turn {index} has no text")
        turns.append(Turn(role=role, text=text, audio_ref=item.get("audio_ref")))
    if not any(turn.is_agent for turn in turns):
        raise ConversationError(
            "conversation contains no agent turn, so there is nothing to adjudicate"
        )
    return turns


def format_context(turns: list[Turn]) -> str:
    """Render preceding turns as labelled context for the judge.

    Explicitly labelled by speaker, so the judge can tell what the consumer
    said without any chance of treating it as the claim under adjudication.
    """
    lines: list[str] = []
    for turn in turns:
        speaker = "AGENT" if turn.is_agent else "CONSUMER"
        lines.append(f"{speaker}: {turn.text}")
    return "\n".join(lines)


@dataclass
class ConversationResult:
    """Everything one conversation produced, with the skipped turns recorded."""

    conversation_id: str
    title: str
    turn_results: list[TurnResult] = field(default_factory=list)
    agent_turn_count: int = 0
    customer_turn_count: int = 0
    cost_usd: float = 0.0

    @property
    def findings(self) -> list[Any]:
        return [j for r in self.turn_results for j in r.findings]

    @property
    def abstentions(self) -> list[Any]:
        return [j for r in self.turn_results for j in r.abstentions]

    @property
    def supported(self) -> list[Any]:
        return [
            j
            for r in self.turn_results
            for j in r.judgements
            if j.adjudication.verdict is Verdict.SUPPORTED
        ]

    @property
    def claim_count(self) -> int:
        return sum(len(r.claims) for r in self.turn_results)


def adjudicate_conversation(
    client: ModelClient,
    retriever: Retriever,
    config: RetrievalConfig,
    turns: list[Turn],
    conversation_id: str,
    title: str,
    call_date: date | None = None,
    log: EvidenceLog | None = None,
    criteria: dict[str, Any] | None = None,
    section_obligations: dict[str, str] | None = None,
    expectations: dict[str, Any] | None = None,
    on_progress: Callable[[str, dict[str, Any]], None] | None = None,
) -> ConversationResult:
    """Adjudicate every AGENT turn in a conversation, in order.

    Customer turns are counted, recorded in the evidence log as context, and
    then skipped. They are never passed to the extractor, so no claim can ever
    originate from one.
    """
    result = ConversationResult(
        conversation_id=conversation_id,
        title=title,
        agent_turn_count=sum(1 for t in turns if t.is_agent),
        customer_turn_count=sum(1 for t in turns if not t.is_agent),
    )

    if log is not None:
        log.append(
            "conversation.start",
            {
                "conversation_id": conversation_id,
                "title": title,
                "turn_count": len(turns),
                "agent_turns": result.agent_turn_count,
                "customer_turns": result.customer_turn_count,
                "rule": "only agent turns are adjudicated; customer turns are "
                "context and are never extracted from or given a verdict",
            },
        )

    agent_index = 0
    for position, turn in enumerate(turns):
        if not turn.is_agent:
            if on_progress is not None:
                on_progress(
                    "turn.skipped",
                    {
                        "position": position,
                        "role": turn.role,
                        "reason": "customer turn, used as context only",
                        "text": turn.text[:90],
                    },
                )
            if log is not None:
                log.append(
                    "conversation.context",
                    {
                        "conversation_id": conversation_id,
                        "position": position,
                        "role": turn.role,
                        "text": turn.text,
                        "adjudicated": False,
                    },
                )
            continue

        # Everything said before this agent turn, both sides, as context.
        context = format_context(turns[:position])
        if on_progress is not None:
            on_progress(
                "turn.agent",
                {
                    "position": position,
                    "index": agent_index + 1,
                    "of": result.agent_turn_count,
                    "text": turn.text[:90],
                    "context_turns": position,
                },
            )

        turn_result = adjudicate_turn(
            client=client,
            retriever=retriever,
            config=config,
            transcript=turn.text,
            turn_id=f"{conversation_id}-t{agent_index:02d}",
            call_date=call_date,
            log=log,
            criteria=criteria,
            section_obligations=section_obligations,
            audio_ref=turn.audio_ref,
            expectations=expectations or {},
            on_progress=on_progress,
            context=context or None,
        )
        result.turn_results.append(turn_result)
        result.cost_usd += turn_result.cost_usd
        agent_index += 1

    return result
