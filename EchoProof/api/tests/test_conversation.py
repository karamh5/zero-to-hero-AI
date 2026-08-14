"""The agent-only guarantee, tested rather than asserted.

An audit found that "only agent turns are adjudicated" held by convention at
the proxy and the campaign runner, was unenforceable in the engine, and did
not hold at all for the rig, which accepted any pasted text. These tests pin
the fix so it cannot quietly regress.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from engine.conversation import (  # noqa: E402
    ConversationError,
    Turn,
    adjudicate_conversation,
    format_context,
    parse_turns,
)


def test_roles_are_recognised() -> None:
    turns = parse_turns(
        [
            {"role": "customer", "text": "I disputed this in writing."},
            {"role": "agent", "text": "The balance is still due today."},
        ]
    )
    assert [t.is_agent for t in turns] == [False, True]
    assert turns[0].is_customer


def test_agent_synonyms_are_agents() -> None:
    # A pack using "assistant" must not have its agent turns silently
    # reclassified as context and skipped.
    for role in ("agent", "assistant", "bot"):
        turns = parse_turns([{"role": role, "text": "hello"}])
        assert turns[0].is_agent, role


def test_unlabelled_turn_is_refused() -> None:
    with pytest.raises(ConversationError):
        parse_turns([{"text": "who said this?"}])


def test_unknown_role_is_refused_not_defaulted() -> None:
    # Defaulting either way is worse than refusing: to customer drops agent
    # turns from adjudication, to agent scores the consumer.
    with pytest.raises(ConversationError) as excinfo:
        parse_turns([{"role": "narrator", "text": "meanwhile"}])
    assert "narrator" in str(excinfo.value)


def test_conversation_without_an_agent_turn_is_refused() -> None:
    with pytest.raises(ConversationError):
        parse_turns([{"role": "customer", "text": "hello?"}])


def test_context_labels_both_speakers() -> None:
    context = format_context(
        [
            Turn(role="customer", text="I disputed this."),
            Turn(role="agent", text="Noted."),
        ]
    )
    assert "CONSUMER: I disputed this." in context
    assert "AGENT: Noted." in context


def test_only_agent_turns_reach_the_pipeline(monkeypatch) -> None:
    """The load-bearing test: customer text must never be adjudicated."""
    adjudicated: list[str] = []
    contexts: list[str | None] = []

    class StubTurnResult:
        claims: list[str] = []
        judgements: list[str] = []
        cost_usd = 0.0
        findings: list[str] = []
        abstentions: list[str] = []

    def fake_adjudicate_turn(**kwargs):  # type: ignore[no-untyped-def]
        adjudicated.append(kwargs["transcript"])
        contexts.append(kwargs.get("context"))
        return StubTurnResult()

    import engine.conversation as conversation_module

    monkeypatch.setattr(conversation_module, "adjudicate_turn", fake_adjudicate_turn)

    turns = parse_turns(
        [
            {"role": "customer", "text": "I already disputed this debt in writing."},
            {"role": "agent", "text": "The balance of $4,500 is still due today."},
            {"role": "customer", "text": "Even while it is disputed?"},
            {"role": "agent", "text": "Yes, I will take a card payment now."},
        ]
    )

    result = adjudicate_conversation(
        client=None,  # type: ignore[arg-type]
        retriever=None,  # type: ignore[arg-type]
        config=None,  # type: ignore[arg-type]
        turns=turns,
        conversation_id="test",
        title="Test",
    )

    assert adjudicated == [
        "The balance of $4,500 is still due today.",
        "Yes, I will take a card payment now.",
    ]
    # No consumer utterance was ever passed as a transcript.
    for text in adjudicated:
        assert "disputed this debt in writing" not in text
        assert "Even while it is disputed" not in text

    assert result.agent_turn_count == 2
    assert result.customer_turn_count == 2

    # The consumer's words did travel as context, which is what lets the judge
    # tell whether the agent responded correctly to a dispute.
    assert contexts[0] is not None
    assert "I already disputed this debt in writing." in contexts[0]
    assert contexts[1] is not None
    assert "Even while it is disputed?" in contexts[1]


def test_context_accumulates_in_order(monkeypatch) -> None:
    seen: list[str | None] = []

    class StubTurnResult:
        claims: list[str] = []
        judgements: list[str] = []
        cost_usd = 0.0
        findings: list[str] = []
        abstentions: list[str] = []

    def fake_adjudicate_turn(**kwargs):  # type: ignore[no-untyped-def]
        seen.append(kwargs.get("context"))
        return StubTurnResult()

    import engine.conversation as conversation_module

    monkeypatch.setattr(conversation_module, "adjudicate_turn", fake_adjudicate_turn)

    adjudicate_conversation(
        client=None,  # type: ignore[arg-type]
        retriever=None,  # type: ignore[arg-type]
        config=None,  # type: ignore[arg-type]
        turns=parse_turns(
            [
                {"role": "agent", "text": "First agent turn."},
                {"role": "customer", "text": "A reply."},
                {"role": "agent", "text": "Second agent turn."},
            ]
        ),
        conversation_id="test",
        title="Test",
    )

    # The first agent turn has nothing before it.
    assert seen[0] is None
    # The second sees both earlier turns, in order.
    assert seen[1] is not None
    assert seen[1].index("AGENT: First agent turn.") < seen[1].index("CONSUMER: A reply.")
