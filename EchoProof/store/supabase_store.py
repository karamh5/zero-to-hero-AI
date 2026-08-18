"""Run and findings metadata in Supabase (brief audit gap 2).

**Metadata only. Evidence content never leaves the local content-addressed
store.** ARCHITECTURE.md decision 11 is explicit: Supabase holds run and findings
metadata, never evidence content. So this module writes identifiers, verdicts,
section numbers, severities and hashes. It does not write transcripts, rule
text, rationales, audio, or prompts.

That boundary is a security posture, not tidiness. The brief's deployment story
is that EchoProof runs inside the client's own account precisely so call content
and policy text never transit a vendor's infrastructure. Pushing a transcript
into a hosted database would quietly undo the answer InfoSec was given.

Everything degrades to a warning when credentials are absent. A campaign must
never fail because an optional index is unreachable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.config import Settings

# The two tables this module expects. Creating them is a one-time operation the
# client performs in their own project; this module never issues DDL, because a
# tool that silently alters a client's schema is a tool their DBA will remove.
SCHEMA_SQL = """
create table if not exists echoproof_runs (
  run_id text primary key,
  created_at timestamptz default now(),
  agent_version text,
  policy_pack_version text,
  chain_head text,
  span_count int,
  scenario_count int,
  call_count int,
  drifted_calls int,
  cost_usd numeric
);

create table if not exists echoproof_findings (
  id bigserial primary key,
  run_id text references echoproof_runs(run_id),
  claim_id text,
  scenario_id text,
  verdict text,
  severity text,
  section_id text,
  selected_score numeric,
  entry_hash text,
  audio_clip_ref text
);
"""


@dataclass
class StoreResult:
    """What actually happened, so a caller can report it honestly."""

    enabled: bool
    runs_written: int = 0
    findings_written: int = 0
    error: str | None = None

    def describe(self) -> str:
        if not self.enabled:
            return "supabase disabled (no credentials); metadata not indexed"
        if self.error:
            return f"supabase write failed, run is unaffected: {self.error}"
        return (
            f"supabase indexed 1 run and {self.findings_written} finding(s), "
            "metadata only"
        )


class SupabaseStore:
    """Thin metadata writer. Optional by construction."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: Any = None

    @property
    def enabled(self) -> bool:
        return self._settings.has_supabase

    def _connect(self) -> Any:
        if self._client is None:
            from supabase import create_client

            self._client = create_client(
                self._settings.supabase_url, self._settings.supabase_key
            )
        return self._client

    def write_run(
        self, run_meta: dict[str, Any], findings: list[dict[str, Any]]
    ) -> StoreResult:
        """Upsert one run and its findings. Never raises."""
        if not self.enabled:
            return StoreResult(enabled=False)

        try:
            client = self._connect()
            client.table("echoproof_runs").upsert(run_meta).execute()

            rows = [_metadata_only(f, run_meta["run_id"]) for f in findings]
            if rows:
                client.table("echoproof_findings").insert(rows).execute()
            return StoreResult(
                enabled=True, runs_written=1, findings_written=len(rows)
            )
        except Exception as exc:  # noqa: BLE001 - optional index, never fatal
            return StoreResult(enabled=True, error=str(exc)[:200])


def _metadata_only(finding: dict[str, Any], run_id: str) -> dict[str, Any]:
    """Project a finding down to metadata.

    Written as an explicit allowlist rather than a denylist. A denylist silently
    starts leaking the moment a new field is added to a finding, and the field
    most likely to be added to a compliance finding is more content.
    """
    return {
        "run_id": run_id,
        "claim_id": finding.get("claim_id"),
        "scenario_id": finding.get("scenario_id"),
        "verdict": finding.get("verdict"),
        "severity": finding.get("severity"),
        "section_id": finding.get("section_id"),
        "selected_score": finding.get("selected_score"),
        "entry_hash": finding.get("entry_hash"),
        "audio_clip_ref": finding.get("audio_clip_ref"),
    }
