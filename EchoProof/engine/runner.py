"""Sequential campaign runner (SPEC section 10).

Pick a scenario and its persona, run the call, adjudicate every agent turn,
repeat the same scenario three times, aggregate.

The call is a genuine two-party exchange between a persona model and an agent
model. Nothing is hand fed: the agent's turns are whatever it actually says in
response to whatever the persona actually says. That is the difference between
testing an agent and testing a transcript somebody wrote for it.

pass@3 and pass^3 are reported separately and the gap between them is the point.
pass@3 says the seeded violation was caught at least once in three runs; pass^3
says it was caught every time. A tool that catches a violation one run in three
is not a release gate, and reporting only pass@3 would hide that.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from core.contracts import Verdict
from engine.drift import DriftResult, validate_call
from engine.evidence import EvidenceLog
from engine.pipeline import TurnResult, adjudicate_turn
from engine.retrieval.base import RetrievalConfig, Retriever, is_within
from models.client import ModelClient

SPAN_CALL_SESSION = "call.session"

# Turns per call. Enough for the persona to state its trigger and for the agent
# to respond to it more than once, which is where seeded violations surface.
DEFAULT_TURNS = 4


@dataclass
class CallResult:
    """One complete call: its turns, its verdicts, and whether it was valid."""

    scenario_id: str
    persona_id: str
    run_index: int
    seed: int
    agent_turns: list[str] = field(default_factory=list)
    persona_turns: list[str] = field(default_factory=list)
    turn_results: list[TurnResult] = field(default_factory=list)
    drift: DriftResult | None = None
    cost_usd: float = 0.0

    @property
    def valid(self) -> bool:
        return self.drift is None or self.drift.valid

    @property
    def findings(self) -> list[Any]:
        return [j for r in self.turn_results for j in r.findings]

    separators: tuple[str, ...] | None = None

    def caught(self, expected_section_id: str | None) -> bool:
        """Whether this call caught the scenario's seeded violation.

        Matched at the granularity the scenario names, using the pack's own
        identifier separators rather than an assumed convention. Hardcoding
        parentheses here scored a correct citation as a miss under any corpus
        that separates levels differently.
        """
        if expected_section_id is None:
            return False
        return any(
            is_within(expected_section_id, j.adjudication.section_id, self.separators)
            for j in self.findings
            if j.adjudication.section_id
        )


@dataclass
class ScenarioResult:
    """Three runs of one scenario, aggregated."""

    scenario_id: str
    persona_id: str
    expected_section_id: str | None
    is_control: bool
    calls: list[CallResult] = field(default_factory=list)

    @property
    def valid_calls(self) -> list[CallResult]:
        return [c for c in self.calls if c.valid]

    @property
    def caught_flags(self) -> list[bool]:
        return [c.caught(self.expected_section_id) for c in self.valid_calls]

    @property
    def pass_at_3(self) -> bool:
        """Caught in at least one valid run."""
        return any(self.caught_flags)

    @property
    def pass_cubed(self) -> bool:
        """Caught in every valid run."""
        flags = self.caught_flags
        return bool(flags) and all(flags)

    @property
    def false_positive_calls(self) -> int:
        """For the control scenario, any finding at all is a false positive."""
        if not self.is_control:
            return 0
        return sum(1 for c in self.valid_calls if c.findings)

    @property
    def drifted(self) -> int:
        return sum(1 for c in self.calls if not c.valid)


def run_call(
    client: ModelClient,
    retriever: Retriever,
    config: RetrievalConfig,
    scenario: dict[str, Any],
    persona: dict[str, Any],
    run_index: int,
    seed: int,
    log: EvidenceLog,
    criteria: dict[str, Any],
    obligations: dict[str, str],
    turns: int = DEFAULT_TURNS,
    model: str | None = None,
) -> CallResult:
    """Run one call to completion and adjudicate every agent turn."""
    from core.config import EXTRACT_MODEL

    model = model or EXTRACT_MODEL
    result = CallResult(
        scenario_id=scenario["scenario_id"],
        persona_id=persona["persona_id"],
        run_index=run_index,
        seed=seed,
    )

    log.append(
        SPAN_CALL_SESSION,
        {
            "scenario_id": scenario["scenario_id"],
            "persona_id": persona["persona_id"],
            "run_index": run_index,
            "seed": seed,
            "agent_version": scenario.get("agent_version", "harbor-recovery-agent@0.1.0"),
            "policy_pack_version": criteria.get("policy_pack_version", ""),
            "seeded_violation": scenario.get("seeded_violation"),
        },
    )

    agent_history: list[dict[str, str]] = []
    persona_history: list[dict[str, str]] = []

    for turn_index in range(turns):
        # Persona speaks first, so the agent is always responding to something.
        persona_prompt = (
            "Open the call by stating your position."
            if turn_index == 0
            else f"The agent just said: {result.agent_turns[-1]}\n\nReply in character."
        )
        persona_call = client.complete(
            model=model,
            system=persona["behavior_spec"],
            user=persona_prompt,
            max_tokens=120,
        )
        persona_text = persona_call.raw_response.strip()
        result.persona_turns.append(persona_text)
        result.cost_usd += persona_call.estimated_cost_usd
        persona_history.append({"role": "assistant", "content": persona_text})

        agent_context = "\n".join(
            f"Consumer: {p}\nYou: {a}"
            for p, a in zip(result.persona_turns, result.agent_turns)
        )
        agent_user = (
            f"{agent_context}\nConsumer: {persona_text}" if agent_context
            else f"Consumer: {persona_text}"
        )
        agent_call = client.complete(
            model=model,
            system=scenario["agent_system_prompt"],
            user=agent_user,
            max_tokens=160,
        )
        agent_text = agent_call.raw_response.strip()
        result.agent_turns.append(agent_text)
        result.cost_usd += agent_call.estimated_cost_usd
        agent_history.append({"role": "assistant", "content": agent_text})

        turn_result = adjudicate_turn(
            client=client,
            retriever=retriever,
            config=config,
            transcript=agent_text,
            turn_id=f"{scenario['scenario_id']}-r{run_index}-t{turn_index:02d}",
            call_date=date.today(),
            log=log,
            criteria=criteria,
            section_obligations=obligations,
        )
        result.turn_results.append(turn_result)
        result.cost_usd += turn_result.cost_usd

    result.drift = validate_call(
        result.persona_turns, persona.get("drift_validator_rules", {})
    )
    log.append(
        "call.drift",
        {
            "scenario_id": scenario["scenario_id"],
            "run_index": run_index,
            **result.drift.to_dict(),
        },
    )
    return result


def aggregate_policy_gaps(scenarios: list[ScenarioResult]) -> list[dict[str, Any]]:
    """Claims where nothing in the corpus cleared the retrieval floor.

    Only no_governing_rule reaches here. A judge rejecting the sections it was
    shown is a retrieval failure and routes to human review, not to a claim that
    the client's rulebook has a gap.
    """
    gaps: list[dict[str, Any]] = []
    for scenario in scenarios:
        for call in scenario.calls:
            for turn in call.turn_results:
                for judgement in turn.judgements:
                    if judgement.adjudication.verdict is Verdict.NO_GOVERNING_RULE:
                        gaps.append(
                            {
                                "scenario_id": scenario.scenario_id,
                                "claim": judgement.inputs.claim_text[:160],
                            }
                        )
    return gaps
