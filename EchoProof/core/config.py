"""Configuration and credential loading.

Secrets come from EchoProof/.env and nowhere else. Nothing in this repository
may contain a key literal: the repository is public, and a key that reaches a
commit is a key that has to be rotated.

The model and embedding identifiers below are pinned to dated snapshots rather
than `-latest` aliases. This is not stylistic. As of 2026-08-12 the Mistral API
reports `mistral-small-latest` as an alias of both `mistral-small-2603` and
`magistral-small-latest`, which is a reasoning model. A `-latest` string can
therefore change model class underneath a scored evaluation run with no change
on our side, which is exactly what ARCHITECTURE.md decision 9 forbids.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"

# Pinned identities. Changing either of these invalidates comparison against
# any previously scored run, so both are recorded into every evidence span.
JUDGE_MODEL = "mistral-large-2512"
EXTRACT_MODEL = "mistral-large-2512"
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_REVISION = "main"

# Temperature is zero everywhere and is not configurable. A nonzero temperature
# would make the same stored inputs regenerate a different verdict, which breaks
# the reproducibility property SPEC section 7 defines.
TEMPERATURE = 0.0

# Speech. Both identifiers were read from Deepgram's live /v1/models rather than
# copied from the brief, and the check was worth making: the brief says
# "Aura-2", but there is no bare aura-2 model. TTS requires a specific voice, so
# the identifier below names one. STT reports canonically as nova-3-general and
# the API accepts nova-3 as its alias.
DEEPGRAM_BASE_URL = "https://api.deepgram.com/v1"
STT_MODEL = "nova-3"
TTS_MODEL = "aura-2-asteria-en"

# Word-level confidence floor. SPEC section 8 routes a numeric token below this
# to abstention rather than to a finding: a misheard digit is the difference
# between a correct amount and a fabricated allegation about one.
STT_NUMERIC_CONFIDENCE_FLOOR = 0.75


class ConfigError(RuntimeError):
    """Raised when a required credential or setting is absent."""


@dataclass(frozen=True)
class Settings:
    """Resolved runtime settings. Built once by `load_settings`."""

    mistral_api_key: str
    mistral_base_url: str
    supabase_url: str | None
    supabase_key: str | None
    deepgram_api_key: str | None

    @property
    def has_supabase(self) -> bool:
        return bool(self.supabase_url and self.supabase_key)

    @property
    def has_deepgram(self) -> bool:
        return bool(self.deepgram_api_key)


def load_settings(require_model: bool = True) -> Settings:
    """Read .env and return settings.

    Only the model credential is required by default. Supabase and Deepgram are
    optional here because Phase 1 does not use them, and failing a retrieval
    evaluation because an unrelated key is absent would be a bad trade.
    """
    if ENV_PATH.exists():
        load_dotenv(ENV_PATH, override=False)

    api_key = os.environ.get("MISTRAL_API_KEY", "").strip()
    if require_model and not api_key:
        raise ConfigError(
            f"MISTRAL_API_KEY is not set. Expected it in {ENV_PATH}. "
            "Never pass it on the command line or hardcode it."
        )

    return Settings(
        mistral_api_key=api_key,
        mistral_base_url=os.environ.get(
            "MISTRAL_BASE_URL", "https://api.mistral.ai/v1"
        ).strip(),
        supabase_url=_optional("SUPABASE_URL"),
        supabase_key=_optional("SUPABASE_KEY"),
        deepgram_api_key=_optional("DEEPGRAM_API_KEY"),
    )


def _optional(name: str) -> str | None:
    value = os.environ.get(name, "").strip()
    return value or None


# Filesystem layout. Kept here so no other module hardcodes a path.
PACKS_DIR = PROJECT_ROOT / "packs"
POLICY_DIR = PACKS_DIR / "policy"
CRITERIA_DIR = PACKS_DIR / "criteria"
FIXTURES_DIR = PROJECT_ROOT / "fixtures"
RUNS_DIR = PROJECT_ROOT / "runs"
