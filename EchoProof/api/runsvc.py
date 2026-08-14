"""Run discovery and read-only access to evidence artifacts.

Reads `runs/` from disk and joins spans through `engine.report`, which is the
same code path the filed HTML report uses. Nothing is recomputed: a verdict, a
score or a hash shown by the UI is the one written when the decision was made.

Chain verification happens on load because `EvidenceLog.read` verifies before
returning. A run whose chain does not verify is not hidden; it is reported as a
run in the `chain_failed` state, because a tampered or truncated log is exactly
the thing an evidence UI must surface rather than skip.
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.config import POLICY_DIR, RUNS_DIR
from core.hashing import hash_text
from core.packs import PackError, PolicyPack, load_policy_pack
from engine.evidence import (
    SPAN_AGENT_TURN,
    SPAN_CHECK_DETERMINISTIC,
    SPAN_EXTRACT_CLAIMS,
    SPAN_FINDING_EMIT,
    SPAN_JUDGE_RULE,
    SPAN_RETRIEVE_RULE,
    ChainError,
    EvidenceLog,
)
from engine.report import Finding, ReportData, extract_report_data

# The audio pipeline emits this alongside agent.turn; it carries word timings.
SPAN_AGENT_TURN_AUDIO = "agent.turn.audio"

# Fallback agent identity for runs whose log carries no call.session span.
# Same fallback scripts/build_report.py uses, so seals computed here match the
# seals that script stored.
DEFAULT_AGENT_VERSION = "harbor-recovery-agent@0.1.0"


@dataclass
class LoadedRun:
    """One run's parsed artifacts, cached against the file's identity."""

    run_id: str
    path: Path
    chain_ok: bool
    chain_error: str | None
    log: EvidenceLog | None
    data: ReportData | None
    pack_id: str | None
    agent_version: str
    stored_seal: str | None
    computed_seal: str | None
    title: str = ""
    conversation_id: str | None = None
    created_at: str | None = None
    clip_index: dict[str, Path] = field(default_factory=dict)

    @property
    def seal_state(self) -> str:
        """intact | broken | unsealed | unverifiable"""
        if self.stored_seal is None:
            return "unsealed"
        if self.computed_seal is None:
            return "unverifiable"
        return "intact" if self.stored_seal == self.computed_seal else "broken"


class RunService:
    """Loads runs once and serves them until the file on disk changes."""

    def __init__(self, runs_dir: Path = RUNS_DIR) -> None:
        self.runs_dir = runs_dir
        self._lock = threading.Lock()
        self._cache: dict[str, tuple[tuple[float, int], LoadedRun]] = {}
        self._packs: dict[str, PolicyPack | None] = {}

    # -- packs ------------------------------------------------------------

    def available_pack_ids(self) -> list[str]:
        if not POLICY_DIR.exists():
            return []
        return sorted(
            p.name
            for p in POLICY_DIR.iterdir()
            if (p / "manifest.json").exists() and (p / "sections.jsonl").exists()
        )

    def pack(self, pack_id: str) -> PolicyPack | None:
        with self._lock:
            if pack_id not in self._packs:
                try:
                    self._packs[pack_id] = load_policy_pack(pack_id)
                except PackError:
                    self._packs[pack_id] = None
            return self._packs[pack_id]

    def _resolve_pack(self, log: EvidenceLog) -> PolicyPack | None:
        """Match a run to the pack it adjudicated against.

        The log records the retriever's chunk_count in every retrieve.rule span,
        and chunk count is read from the pack manifests rather than assumed, so
        a 303-section corpus and a 15-section corpus resolve without any
        Regulation F constant appearing here.
        """
        chunk_count: int | None = None
        for span in log.of_type(SPAN_RETRIEVE_RULE):
            config = span.payload.get("retriever_config") or {}
            if config.get("chunk_count") is not None:
                chunk_count = int(config["chunk_count"])
                break

        candidates = [self.pack(pid) for pid in self.available_pack_ids()]
        packs = [p for p in candidates if p is not None]
        if chunk_count is not None:
            for pack in packs:
                if int(pack.manifest.get("record_count", -1)) == chunk_count:
                    return pack
        # A run with no retrieval spans (deterministic-only, or drill input)
        # cannot name its corpus. Fall back to the first available pack for
        # citation text only; section resolution still goes through the log.
        return packs[0] if packs else None

    # -- runs -------------------------------------------------------------

    def run_ids(self) -> list[str]:
        if not self.runs_dir.exists():
            return []
        out = []
        for path in sorted(self.runs_dir.iterdir()):
            if (path / "evidence.jsonl").exists():
                out.append(path.name)
        return out

    def load(self, run_id: str) -> LoadedRun | None:
        run_dir = self.runs_dir / run_id
        log_path = run_dir / "evidence.jsonl"
        if not log_path.exists():
            return None

        stat = log_path.stat()
        signature = (stat.st_mtime, stat.st_size)
        with self._lock:
            cached = self._cache.get(run_id)
            if cached is not None and cached[0] == signature:
                return cached[1]

        loaded = self._load_uncached(run_id, run_dir, log_path)
        with self._lock:
            self._cache[run_id] = (signature, loaded)
        return loaded

    def _load_uncached(self, run_id: str, run_dir: Path, log_path: Path) -> LoadedRun:
        stored_seal = None
        seal_path = run_dir / "report.seal"
        if seal_path.exists():
            stored_seal = seal_path.read_text(encoding="utf-8").strip()

        try:
            log = EvidenceLog.read(log_path)
        except (ChainError, KeyError, json.JSONDecodeError) as exc:
            return LoadedRun(
                run_id=run_id,
                path=run_dir,
                chain_ok=False,
                chain_error=str(exc),
                log=None,
                data=None,
                pack_id=None,
                agent_version=DEFAULT_AGENT_VERSION,
                stored_seal=stored_seal,
                computed_seal=None,
            )

        pack = self._resolve_pack(log)
        agent_version = DEFAULT_AGENT_VERSION
        for span in log.of_type("call.session"):
            if span.payload.get("agent_version"):
                agent_version = str(span.payload["agent_version"])
                break

        # A run's own title, written by whoever started it. Runs made before
        # titles existed have none, and the bench shows their identifier
        # instead rather than inventing a name for them.
        title = ""
        conversation_id = None
        created_at = None
        for span in log.of_type("run.meta"):
            title = str(span.payload.get("title") or "")
            conversation_id = span.payload.get("conversation_id")
            created_at = span.payload.get("created_at")
            break
        if not title:
            for span in log.of_type("conversation.start"):
                title = str(span.payload.get("title") or "")
                conversation_id = span.payload.get("conversation_id")
                break

        data = extract_report_data(
            log=log,
            agent_version=agent_version,
            policy_pack_version=pack.version if pack else "",
            policy_citation=pack.citation if pack else "unresolved corpus",
            clips_dir=run_dir / "clips",
        )

        return LoadedRun(
            run_id=run_id,
            path=run_dir,
            chain_ok=True,
            chain_error=None,
            log=log,
            data=data,
            pack_id=pack.pack_id if pack else None,
            agent_version=agent_version,
            stored_seal=stored_seal,
            computed_seal=data.seal() if pack else None,
            title=title,
            conversation_id=str(conversation_id) if conversation_id else None,
            created_at=str(created_at) if created_at else None,
        )

    # -- clips ------------------------------------------------------------

    def clip_path(self, run_id: str, digest: str) -> Path | None:
        """Map a content digest from the evidence log to a clip file on disk.

        Clips are content addressed: the digest in finding.emit is
        hash_text(bytes.hex()), computed by engine/audio.py when the clip was
        cut. Recomputing it here means a clip that was swapped on disk simply
        stops resolving instead of playing as if it were the evidence.
        """
        loaded = self.load(run_id)
        if loaded is None:
            return None
        if not loaded.clip_index:
            clips_dir = loaded.path / "clips"
            if not clips_dir.exists():
                return None
            index: dict[str, Path] = {}
            for wav in sorted(clips_dir.glob("*.wav")):
                index[hash_text(wav.read_bytes().hex())] = wav
            loaded.clip_index = index
        return loaded.clip_index.get(digest)

    # -- json artifacts ---------------------------------------------------

    def artifact(self, run_id: str, name: str) -> dict[str, Any] | list[Any] | None:
        """A JSON artifact stored beside the log: campaign, rerun, swap, scored."""
        allowed = {
            "campaign": "campaign.json",
            "rerun": "rerun.json",
            "swap": "swap.json",
            "scored": "scored.json",
        }
        filename = allowed.get(name)
        if filename is None:
            return None
        path = self.runs_dir / run_id / filename
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def report_path(self, run_id: str) -> Path | None:
        path = self.runs_dir / run_id / "deployment-readiness-report.html"
        return path if path.exists() else None


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


def finding_to_dict(finding: Finding, include_transcript: bool = True) -> dict[str, Any]:
    out: dict[str, Any] = {
        "claim_id": finding.claim_id,
        "turn_id": finding.turn_id,
        "verdict": finding.verdict,
        "is_abstention": finding.is_abstention,
        "severity": finding.severity,
        "section_id": finding.section_id,
        "rationale": finding.rationale,
        "claim_text": finding.claim_text,
        "rule_text": finding.rule_text,
        "char_start": finding.char_start,
        "char_end": finding.char_end,
        "candidates": finding.candidates,
        "offered_section_ids": finding.offered_section_ids,
        "selected_score": finding.selected_score,
        "model": finding.model,
        "prompt_hash": finding.prompt_hash,
        "entry_hash": finding.entry_hash,
        "audio_clip_ref": finding.audio_clip_ref,
        "has_clip": finding.clip_path is not None,
    }
    if include_transcript:
        out["transcript"] = finding.transcript
    return out


def run_summary(loaded: LoadedRun) -> dict[str, Any]:
    """The BENCH listing entry for one run."""
    base: dict[str, Any] = {
        "run_id": loaded.run_id,
        "title": loaded.title,
        "conversation_id": loaded.conversation_id,
        "created_at": loaded.created_at,
        "chain_ok": loaded.chain_ok,
        "chain_error": loaded.chain_error,
        "seal_state": loaded.seal_state,
        "pack_id": loaded.pack_id,
        "agent_version": loaded.agent_version,
        "artifacts": {
            "campaign": (loaded.path / "campaign.json").exists(),
            "rerun": (loaded.path / "rerun.json").exists(),
            "swap": (loaded.path / "swap.json").exists(),
            "scored": (loaded.path / "scored.json").exists(),
            "report": (loaded.path / "deployment-readiness-report.html").exists(),
        },
    }
    clips_dir = loaded.path / "clips"
    base["clip_count"] = (
        len(list(clips_dir.glob("*.wav"))) if clips_dir.exists() else 0
    )

    if loaded.data is None or loaded.log is None:
        base.update(
            {
                "span_count": 0,
                "turns": 0,
                "claims": 0,
                "violations": 0,
                "abstentions": 0,
                "supported": 0,
                "verdict_counts": {},
                "chain_head": None,
            }
        )
        return base

    data = loaded.data
    verdict_counts: dict[str, int] = {}
    for finding in data.findings:
        verdict_counts[finding.verdict] = verdict_counts.get(finding.verdict, 0) + 1

    deterministic = sum(
        1
        for span in loaded.log.of_type(SPAN_CHECK_DETERMINISTIC)
        if span.payload.get("decided")
    )

    base.update(
        {
            "span_count": len(loaded.log.spans),
            "chain_head": loaded.log.head,
            "turns": len(data.turns),
            "claims": len(data.findings),
            "violations": len(data.violations),
            "abstentions": len(data.abstentions),
            "supported": verdict_counts.get("supported", 0),
            "verdict_counts": verdict_counts,
            "deterministic_decisions": deterministic,
            "policy_gaps": len(data.policy_gaps),
        }
    )
    return base


def claim_detail(loaded: LoadedRun, claim_id: str) -> dict[str, Any] | None:
    """Everything recorded about one claim: the finding plus its raw spans.

    The trace view runs on this. Spans are returned with their hashes so the
    chain between them can be shown, and the retrieval span carries the full
    stored candidate list and thresholds rather than the report's trimmed six.
    """
    if loaded.log is None or loaded.data is None:
        return None

    finding = next(
        (f for f in loaded.data.findings if f.claim_id == claim_id), None
    )
    if finding is None:
        return None

    def span_dict(span: Any) -> dict[str, Any]:
        return {
            "span_type": span.span_type,
            "span_id": span.span_id,
            "payload": span.payload,
            "prev_hash": span.prev_hash,
            "entry_hash": span.entry_hash,
        }

    retrieval = None
    judge = None
    emit = None
    deterministic: list[dict[str, Any]] = []
    turn = None
    extract = None
    audio_spans: list[Any] = []

    for span in loaded.log.spans:
        payload = span.payload
        if span.span_type == SPAN_RETRIEVE_RULE and payload.get("claim_id") == claim_id:
            retrieval = span_dict(span)
        elif span.span_type == SPAN_JUDGE_RULE and payload.get("claim_id") == claim_id:
            judge = span_dict(span)
        elif span.span_type == SPAN_FINDING_EMIT and payload.get("claim_id") == claim_id:
            emit = span_dict(span)
        elif (
            span.span_type == SPAN_CHECK_DETERMINISTIC
            and payload.get("claim_id") == claim_id
        ):
            deterministic.append(span_dict(span))
        elif span.span_type == SPAN_EXTRACT_CLAIMS and any(
            c.get("claim_id") == claim_id for c in payload.get("claims", [])
        ):
            extract = span_dict(span)
        elif (
            span.span_type == SPAN_AGENT_TURN
            and str(payload.get("turn_id")) == finding.turn_id
        ):
            turn = span_dict(span)
        elif span.span_type == SPAN_AGENT_TURN_AUDIO:
            audio_spans.append(span)

    # The audio span carries no turn_id and may precede the agent.turn span in
    # the log, so it is matched afterwards by transcript hash, which is the
    # identity the claim offsets index into.
    turn_audio = None
    if turn is not None:
        transcript_hash = turn["payload"].get("transcript_hash")
        for span in audio_spans:
            if span.payload.get("transcript_hash") == transcript_hash:
                turn_audio = span_dict(span)
                break

    return {
        "run_id": loaded.run_id,
        "finding": finding_to_dict(finding),
        "turn": turn,
        "turn_audio": turn_audio,
        "extract": extract,
        "deterministic": deterministic,
        "retrieval": retrieval,
        "judge": judge,
        "emit": emit,
    }
