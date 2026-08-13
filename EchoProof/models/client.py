"""The single model interface.

One OpenAI SDK client against an OpenAI-compatible base_url. Moving to Bedrock
is a base_url and model string change, which is the whole reason nothing else in
the codebase constructs a client or names a provider.

Every call returns its own provenance: the prompt hash, the resolved model
string, token usage, and the raw response. SPEC section 7 requires all of that
to reach the evidence log, and collecting it at the call site is the only place
it can be collected reliably.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

from openai import OpenAI

from core.config import TEMPERATURE, Settings
from core.hashing import hash_object

# Published Mistral pricing, USD per million tokens, for the pinned model.
# Used only to estimate cost per campaign, which the PoC brief tracks as a
# business metric. Wrong prices produce a wrong estimate and nothing else, so
# this is recorded as an assumption rather than treated as ground truth.
PRICE_PER_MTOK = {
    "mistral-large-2512": {"input": 2.00, "output": 6.00},
    "mistral-medium-2604": {"input": 0.40, "output": 2.00},
    "mistral-small-2603": {"input": 0.10, "output": 0.30},
}


@dataclass(frozen=True)
class ModelCall:
    """One model call and everything needed to reproduce or price it."""

    model: str
    prompt_hash: str
    raw_response: str
    tool_arguments: dict[str, Any] | None
    prompt_tokens: int
    completion_tokens: int
    finish_reason: str
    request: dict[str, Any] = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @property
    def estimated_cost_usd(self) -> float:
        prices = PRICE_PER_MTOK.get(self.model)
        if prices is None:
            return 0.0
        return round(
            (self.prompt_tokens / 1_000_000) * prices["input"]
            + (self.completion_tokens / 1_000_000) * prices["output"],
            6,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "prompt_hash": self.prompt_hash,
            "raw_response": self.raw_response,
            "tool_arguments": self.tool_arguments,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "estimated_cost_usd": self.estimated_cost_usd,
            "finish_reason": self.finish_reason,
        }


RETRY_ATTEMPTS = 6
RETRY_INITIAL_DELAY = 2.0
RETRY_MAX_DELAY = 30.0

# Substrings identifying failures worth retrying. Matched on the exception text
# rather than on SDK exception classes so the retry survives an SDK upgrade that
# renames them, which matters more here than precision does.
_TRANSIENT_MARKERS = (
    "rate limit",
    "rate_limit",
    "429",
    "timeout",
    "timed out",
    "connection",
    "temporarily unavailable",
    "service unavailable",
    "502",
    "503",
    "504",
    "overloaded",
    "capacity",
)


def _is_transient(exc: Exception) -> bool:
    text = f"{type(exc).__name__} {exc}".lower()
    return any(marker in text for marker in _TRANSIENT_MARKERS)


class ModelError(RuntimeError):
    """Raised when the backend fails or returns something unusable."""


class ModelClient:
    """Thin, provider-neutral wrapper. Temperature is always zero."""

    def __init__(self, settings: Settings) -> None:
        self._client = OpenAI(
            api_key=settings.mistral_api_key,
            base_url=settings.mistral_base_url,
        )
        self._base_url = settings.mistral_base_url

    def _create_with_retry(self, kwargs: dict[str, Any]) -> Any:
        """Call the backend, retrying transient failures with backoff.

        Rate limiting is the expected case, not an exceptional one: scoring 50
        fixtures issues hundreds of calls in a burst and the provider throttles
        them. Without this, a run dies partway through and the partial result is
        worthless. Retries are bounded and the final failure is still raised, so
        a genuinely broken backend does not turn into a silent hang.

        Only transient classes are retried. A malformed request or a bad key
        fails immediately, because retrying those just delays the error.
        """
        delay = RETRY_INITIAL_DELAY
        last_error: Exception | None = None

        for attempt in range(RETRY_ATTEMPTS):
            try:
                return self._client.chat.completions.create(**kwargs)
            except Exception as exc:  # noqa: BLE001 - re-raised as ModelError below
                last_error = exc
                if not _is_transient(exc) or attempt == RETRY_ATTEMPTS - 1:
                    break
                time.sleep(delay)
                delay = min(delay * 2, RETRY_MAX_DELAY)

        raise ModelError(
            f"model call failed against {self._base_url} after {RETRY_ATTEMPTS} "
            f"attempt(s): {last_error}"
        ) from last_error

    def complete(
        self,
        model: str,
        system: str,
        user: str,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: dict[str, Any] | str | None = None,
        max_tokens: int = 2048,
    ) -> ModelCall:
        """Issue one call and return it with its provenance attached."""
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        # The hash covers everything that determines the output. Temperature is
        # included even though it is constant, so that a future change to it is
        # visible as a hash change rather than an invisible drift in results.
        prompt_hash = hash_object(
            {
                "model": model,
                "messages": messages,
                "tools": tools,
                "tool_choice": tool_choice,
                "temperature": TEMPERATURE,
            }
        )

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": TEMPERATURE,
            "max_tokens": max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
        if tool_choice:
            kwargs["tool_choice"] = tool_choice

        response = self._create_with_retry(kwargs)

        choice = response.choices[0]
        message = choice.message
        content = message.content or ""

        tool_arguments: dict[str, Any] | None = None
        if getattr(message, "tool_calls", None):
            raw_arguments = message.tool_calls[0].function.arguments
            try:
                tool_arguments = json.loads(raw_arguments)
            except json.JSONDecodeError as exc:
                # A malformed tool payload is a failure of this call, not a
                # reason to fall back to free text. Falling back would let an
                # unvalidated response reach the judge.
                raise ModelError(f"tool arguments were not valid JSON: {exc}") from exc
            content = raw_arguments

        usage = response.usage
        return ModelCall(
            model=response.model or model,
            prompt_hash=prompt_hash,
            raw_response=content,
            tool_arguments=tool_arguments,
            prompt_tokens=getattr(usage, "prompt_tokens", 0) if usage else 0,
            completion_tokens=getattr(usage, "completion_tokens", 0) if usage else 0,
            finish_reason=choice.finish_reason or "",
        )
