"""Live adjudication as a job: submit, stream real progress, render when done.

A single turn takes up to 140 seconds (demo/latency.json), so the UI never
waits on a request. It submits a job, gets an id back immediately, and follows
the pipeline's own on_progress callbacks over SSE.

Honesty rules enforced at this layer:

  * Every streamed event with a pipeline stage name came from
    engine.pipeline.adjudicate_turn's on_progress callback. Nothing here
    invents, retimes or interpolates a stage.
  * Job lifecycle events are namespaced job.* so a client can never mistake
    them for pipeline work.
  * There is no percentage anywhere. retrieve.query carries number/of, which
    is the only honest basis for progress, and it is passed through untouched.

Each job writes a NEW run directory through the engine's public pipeline, the
same way scripts/run_proxy.py does, so a live adjudication lands on the bench
beside the recorded runs with a verifiable chain of its own.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from queue import Queue
from typing import Any, Callable, Iterator

from core.config import RUNS_DIR, load_settings

# Job states. `disabled` never appears on a job; it is the manager's own state
# when no model credential is present.
QUEUED = "queued"
LOADING_STACK = "loading_stack"
RUNNING = "running"
DONE = "done"
FAILED = "failed"

MAX_TRANSCRIPT_CHARS = 4000


@dataclass
class Job:
    job_id: str
    run_id: str
    transcript: str
    expectations: dict[str, Any]
    call_date: date
    # A prepared conversation, when the job runs one. The rig only ever
    # submits these: free text carries no speaker labels, and without labels
    # there is no way to guarantee that a consumer utterance is not scored.
    conversation_id: str | None = None
    pack_id: str | None = None
    title: str = ""
    turns: list[dict[str, Any]] = field(default_factory=list)
    status: str = QUEUED
    error: str | None = None
    result: dict[str, Any] | None = None
    events: list[dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    cond: threading.Condition = field(default_factory=threading.Condition)

    def emit(self, stage: str, detail: dict[str, Any]) -> None:
        with self.cond:
            self.events.append(
                {
                    "seq": len(self.events),
                    "at": round(time.time() - self.created_at, 3),
                    "stage": stage,
                    "detail": detail,
                }
            )
            self.cond.notify_all()

    def finish(self, status: str, error: str | None = None) -> None:
        with self.cond:
            self.status = status
            self.error = error
            self.cond.notify_all()

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "run_id": self.run_id,
            "title": self.title,
            "conversation_id": self.conversation_id,
            "pack_id": self.pack_id,
            "status": self.status,
            "error": self.error,
            "result": self.result,
            "event_count": len(self.events),
        }


class AdjudicationStack:
    """The engine stack, loaded once and shared by every job.

    Loading pulls the embedding and reranker weights (roughly 20 seconds warm,
    a 1.5 GB download cold), which is why it happens lazily on the first job
    rather than at server start: the UI must be fully explorable against
    stored runs without ever paying this cost.
    """

    def __init__(self) -> None:
        self.state = "cold"  # cold | loading | ready | failed
        self.error: str | None = None
        self._lock = threading.Lock()
        self.client: Any = None
        self.retriever: Any = None
        self.config: Any = None
        self.criteria: dict[str, Any] | None = None
        self.obligations: dict[str, str] | None = None
        self.pack_id: str | None = None
        self.corpus_size: int | None = None

    def ensure(self, operating_ceiling: float | None) -> None:
        with self._lock:
            if self.state == "ready":
                return
            if self.state == "failed":
                raise RuntimeError(self.error or "stack failed to load")
            self.state = "loading"
        try:
            self._load(operating_ceiling)
            self.state = "ready"
        except Exception as exc:
            self.state = "failed"
            self.error = str(exc)
            raise

    def _load(self, operating_ceiling: float | None) -> None:
        # Imported here, not at module top: these pull torch and the model
        # weights, and a UI process serving stored runs must never need them.
        from core.packs import load_criteria, load_policy_pack, policy_index_dir
        from engine.retrieval.base import RetrievalConfig
        from engine.retrieval.chunking import build_chunks
        from engine.retrieval.local_faiss_bm25 import LocalHybridRetriever
        from engine.retrieval.rerank import CrossEncoderReranker
        from models.client import ModelClient

        settings = load_settings()
        thresholds_file = load_criteria("thresholds")
        pack_id = str(thresholds_file.get("pack_id", "reg_f"))
        pack = load_policy_pack(pack_id)
        thresholds = thresholds_file["thresholds"]

        # The ceiling is the operating point recorded in the scored campaign
        # run, when one exists on disk, so the rig adjudicates at the same
        # point the published numbers were measured at. The calibrated value
        # in the thresholds file exceeds every score observed in a fixture
        # run and would abstain on everything (LIMITATIONS.md).
        ceiling = (
            operating_ceiling
            if operating_ceiling is not None
            else float(thresholds["ceiling"])
        )

        self.config = RetrievalConfig(
            floor=float(thresholds["floor"]),
            ceiling=ceiling,
            conflict_margin=float(thresholds["conflict_margin"]),
            top_k=int(thresholds.get("top_k", 50)),
            first_stage_k=int(thresholds.get("first_stage_k", 50)),
            rerank_k=int(thresholds.get("rerank_k", 50)),
            judge_candidates=int(thresholds.get("judge_candidates", 10)),
        )
        retriever = LocalHybridRetriever(
            cache_dir=policy_index_dir(pack_id), reranker=CrossEncoderReranker()
        )
        retriever.index(build_chunks(pack.sections))
        self.retriever = retriever
        self.criteria = load_criteria("criteria")
        self.obligations = {
            s.section_id: s.obligation_type.value for s in pack.sections
        }
        self.client = ModelClient(settings)
        self.pack_id = pack_id
        self.corpus_size = len(pack.sections)


class JobManager:
    """One worker thread, one stack, jobs processed in order."""

    def __init__(
        self, ceiling_provider: Callable[[], float | None] | None = None
    ) -> None:
        self.stack = AdjudicationStack()
        # Resolved on first use, because the provider reads the campaign run's
        # recorded thresholds and a UI process must not parse runs at import.
        self.ceiling_provider = ceiling_provider
        self.operating_ceiling: float | None = None
        self.jobs: dict[str, Job] = {}
        self._queue: Queue[Job] = Queue()
        self._worker: threading.Thread | None = None
        self._lock = threading.Lock()

    # -- availability -----------------------------------------------------

    def availability(self) -> dict[str, Any]:
        settings = load_settings(require_model=False)
        available = bool(settings.mistral_api_key)
        return {
            "available": available,
            "reason": None
            if available
            else "MISTRAL_API_KEY is not set. Live adjudication is disabled; "
            "stored runs remain fully explorable.",
            "stack_state": self.stack.state,
            "stack_error": self.stack.error,
            "model_key_present": bool(settings.mistral_api_key),
            "deepgram_key_present": bool(settings.deepgram_api_key),
            "queued": self._queue.qsize(),
        }

    # -- submission -------------------------------------------------------

    def next_run_number(self) -> int:
        """Sequential assessment numbers, so a run has an identity a person
        can say out loud. Derived from what is already on disk rather than
        from a counter that resets when the process does."""
        highest = 0
        if RUNS_DIR.exists():
            for path in RUNS_DIR.iterdir():
                name = path.name
                if name.startswith("assessment-"):
                    head = name.split("-")[1] if "-" in name else ""
                    if head.isdigit():
                        highest = max(highest, int(head))
        return highest + 1

    def submit_conversation(
        self,
        pack_id: str,
        conversation: dict[str, Any],
        title: str,
        call_date: date | None = None,
    ) -> Job:
        """Queue a prepared, role-labelled conversation.

        This is the only way the rig starts a run. Free text is refused
        because it has no speaker labels, and the agent-only guarantee cannot
        be enforced on text where nobody knows who was speaking.
        """
        availability = self.availability()
        if not availability["available"]:
            raise PermissionError(availability["reason"])

        turns = conversation.get("turns") or []
        if not turns:
            raise ValueError("conversation has no turns")

        job_id = uuid.uuid4().hex[:12]
        number = self.next_run_number()
        clean_title = (title or conversation.get("title") or "Untitled assessment").strip()
        job = Job(
            job_id=job_id,
            run_id=f"assessment-{number:04d}",
            transcript="",
            expectations=dict(conversation.get("deterministic") or {}),
            call_date=call_date or date.today(),
            conversation_id=str(conversation.get("conversation_id")),
            pack_id=pack_id,
            title=clean_title,
            turns=list(turns),
        )
        with self._lock:
            self.jobs[job_id] = job
            if self._worker is None:
                self._worker = threading.Thread(
                    target=self._run, name="echoproof-rig", daemon=True
                )
                self._worker.start()
        self._queue.put(job)
        return job

    def get(self, job_id: str) -> Job | None:
        return self.jobs.get(job_id)

    # -- worker -----------------------------------------------------------

    def _run(self) -> None:
        while True:
            job = self._queue.get()
            try:
                self._process(job)
            except Exception as exc:  # noqa: BLE001 - a failed job must not kill the worker
                job.emit("job.failed", {"error": str(exc)})
                job.finish(FAILED, error=str(exc))
            finally:
                self._queue.task_done()

    def _process(self, job: Job) -> None:
        from engine.conversation import adjudicate_conversation, parse_turns
        from engine.evidence import EvidenceLog

        if self.operating_ceiling is None and self.ceiling_provider is not None:
            self.operating_ceiling = self.ceiling_provider()

        if self.stack.state != "ready":
            job.status = LOADING_STACK
            job.emit(
                "job.stack",
                {
                    "state": "loading",
                    "note": "loading embedding and reranker weights; "
                    "roughly 20 seconds warm, a 1.5 GB download cold",
                },
            )
            self.stack.ensure(self.operating_ceiling)
            job.emit("job.stack", {"state": "ready"})

        turns = parse_turns(job.turns)
        agent_turns = sum(1 for turn in turns if turn.is_agent)

        job.status = RUNNING
        job.emit(
            "job.config",
            {
                "run_id": job.run_id,
                "title": job.title,
                "conversation_id": job.conversation_id,
                "pack_id": self.stack.pack_id,
                "corpus_size": self.stack.corpus_size,
                "thresholds": self.stack.config.to_dict(),
                "expectations": job.expectations,
                "call_date": job.call_date.isoformat(),
                "agent_turns": agent_turns,
                "customer_turns": len(turns) - agent_turns,
                "scope": "agent turns only; consumer turns are context and are "
                "never extracted from or given a verdict",
            },
        )

        log = EvidenceLog(run_id=job.run_id)
        # The run's own identity, written into the chain so the bench can show
        # a title the operator chose instead of a generated name.
        log.append(
            "run.meta",
            {
                "run_id": job.run_id,
                "title": job.title,
                "conversation_id": job.conversation_id,
                "conversation_pack": job.pack_id,
                "policy_pack": self.stack.pack_id,
                "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            },
        )

        result = adjudicate_conversation(
            client=self.stack.client,
            retriever=self.stack.retriever,
            config=self.stack.config,
            turns=turns,
            conversation_id=job.conversation_id or job.run_id,
            title=job.title,
            call_date=job.call_date,
            log=log,
            criteria=self.stack.criteria,
            section_obligations=self.stack.obligations,
            expectations=job.expectations,
            on_progress=job.emit,
        )
        out_path = RUNS_DIR / job.run_id / "evidence.jsonl"
        log.write(out_path)

        job.result = {
            "run_id": job.run_id,
            "title": job.title,
            "claims": result.claim_count,
            "findings": len(result.findings),
            "abstentions": len(result.abstentions),
            "supported": len(result.supported),
            "agent_turns": result.agent_turn_count,
            "customer_turns_skipped": result.customer_turn_count,
            "verdicts": [
                {
                    "claim_id": j.adjudication.claim_id,
                    "verdict": j.adjudication.verdict.value,
                    "section_id": j.adjudication.section_id,
                    "decided_by": j.adjudication.decided_by,
                }
                for turn_result in result.turn_results
                for j in turn_result.judgements
            ],
            "cost_usd": round(result.cost_usd, 6),
            "evidence_path": str(out_path),
        }
        job.emit("job.done", job.result)
        job.finish(DONE)

    # -- streaming --------------------------------------------------------

    def stream(self, job: Job, heartbeat_seconds: float = 15.0) -> Iterator[str]:
        """SSE frames: replay stored events, then follow until the job ends."""
        import json as _json

        cursor = 0
        while True:
            with job.cond:
                while cursor >= len(job.events) and job.status in (
                    QUEUED,
                    LOADING_STACK,
                    RUNNING,
                ):
                    if not job.cond.wait(timeout=heartbeat_seconds):
                        break  # heartbeat
                fresh = job.events[cursor:]
                status = job.status
            if not fresh and status in (QUEUED, LOADING_STACK, RUNNING):
                yield ": keepalive\n\n"
                continue
            for event in fresh:
                cursor += 1
                payload = _json.dumps(event, ensure_ascii=False)
                yield f"id: {event['seq']}\nevent: {event['stage']}\ndata: {payload}\n\n"
            if status in (DONE, FAILED) and cursor >= len(job.events):
                yield f"event: end\ndata: {_json.dumps(job.to_dict())}\n\n"
                return
