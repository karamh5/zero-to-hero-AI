"""The UI's HTTP surface. Read-only over stored artifacts, plus the job API.

Mounted onto the existing capture proxy app by `attach_ui`, which is the only
change adapter/proxy.py carries for the UI. A failure to attach must never
break the proxy, for the same reason a capture failure never becomes a request
failure.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from core.config import PROJECT_ROOT
from core.packs import PackError, load_criteria
from engine.report import gate_decision

from api import conversations as conversations_mod
from api import measurements as measurements_mod
from api.jobs import JobManager
from api.runsvc import RunService, claim_detail, finding_to_dict, run_summary

UI_DIST = PROJECT_ROOT / "ui" / "dist"

# Shared across app instances so parsed runs are cached once per process.
service = RunService()
jobs = JobManager(
    ceiling_provider=lambda: measurements_mod.operating_ceiling(service)
)


def _err(status: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": message})


router = APIRouter(prefix="/api")


# -- runs -------------------------------------------------------------------


@router.get("/runs")
def list_runs() -> dict[str, Any]:
    out = []
    for run_id in service.run_ids():
        loaded = service.load(run_id)
        if loaded is not None:
            out.append(run_summary(loaded))
    return {"runs": out}


@router.get("/runs/{run_id}")
def run_detail(run_id: str) -> Any:
    loaded = service.load(run_id)
    if loaded is None:
        return _err(404, f"no run named {run_id} on disk")
    summary = run_summary(loaded)

    gate = None
    if loaded.data is not None:
        try:
            label, css, reason = gate_decision(loaded.data, load_criteria("criteria"))
            gate = {"label": label, "kind": css, "reason": reason}
        except PackError:
            gate = None

    detail: dict[str, Any] = {
        **summary,
        "gate": gate,
        "retriever_config": loaded.data.retriever_config if loaded.data else {},
        "thresholds": loaded.data.thresholds if loaded.data else {},
        "policy_gap_claims": [
            finding_to_dict(f, include_transcript=False)
            for f in (loaded.data.policy_gaps if loaded.data else [])
        ],
        "campaign": service.artifact(run_id, "campaign"),
        "rerun": service.artifact(run_id, "rerun"),
        "swap": service.artifact(run_id, "swap"),
    }
    return detail


@router.get("/runs/{run_id}/findings")
def run_findings(run_id: str) -> Any:
    loaded = service.load(run_id)
    if loaded is None:
        return _err(404, f"no run named {run_id} on disk")
    if loaded.data is None:
        return _err(409, f"evidence chain for {run_id} does not verify: {loaded.chain_error}")
    return {
        "run_id": run_id,
        "findings": [finding_to_dict(f) for f in loaded.data.findings],
    }


@router.get("/runs/{run_id}/spans")
def run_spans(run_id: str) -> Any:
    loaded = service.load(run_id)
    if loaded is None:
        return _err(404, f"no run named {run_id} on disk")
    if loaded.log is None:
        return _err(409, f"evidence chain for {run_id} does not verify: {loaded.chain_error}")
    return {
        "run_id": run_id,
        "head": loaded.log.head,
        "spans": [s.to_dict() for s in loaded.log.spans],
    }


@router.get("/runs/{run_id}/claims/{claim_id}")
def run_claim(run_id: str, claim_id: str) -> Any:
    loaded = service.load(run_id)
    if loaded is None:
        return _err(404, f"no run named {run_id} on disk")
    if loaded.data is None:
        return _err(409, f"evidence chain for {run_id} does not verify: {loaded.chain_error}")
    detail = claim_detail(loaded, claim_id)
    if detail is None:
        return _err(404, f"no claim {claim_id} in run {run_id}")
    return detail


@router.get("/runs/{run_id}/campaign")
def run_campaign(run_id: str) -> Any:
    artifact = service.artifact(run_id, "campaign")
    if artifact is None:
        return _err(404, f"run {run_id} has no campaign.json")
    return artifact


@router.get("/runs/{run_id}/rerun")
def run_rerun(run_id: str) -> Any:
    artifact = service.artifact(run_id, "rerun")
    if artifact is None:
        return _err(404, f"run {run_id} has no rerun.json")
    return artifact


@router.get("/runs/{run_id}/swap")
def run_swap(run_id: str) -> Any:
    artifact = service.artifact(run_id, "swap")
    if artifact is None:
        return _err(404, f"run {run_id} has no swap.json")
    return artifact


@router.get("/runs/{run_id}/clips/{digest}")
def run_clip(run_id: str, digest: str) -> Any:
    path = service.clip_path(run_id, digest)
    if path is None:
        return _err(404, "no clip with that digest in this run")
    return FileResponse(path, media_type="audio/wav")


@router.get("/runs/{run_id}/report")
def run_report(run_id: str) -> Any:
    path = service.report_path(run_id)
    if path is None:
        return _err(
            404,
            f"run {run_id} has no rendered report. "
            f"Build one with: python scripts/build_report.py --run-id {run_id}",
        )
    return FileResponse(path, media_type="text/html")


# -- corpus, criteria, measurements ----------------------------------------


@router.get("/corpus")
def corpus_list() -> dict[str, Any]:
    packs = []
    for pack_id in service.available_pack_ids():
        pack = service.pack(pack_id)
        if pack is not None:
            packs.append(
                {
                    "pack_id": pack.pack_id,
                    "label": pack.manifest.get("label", pack.pack_id),
                    "citation": pack.citation,
                    "record_count": len(pack.sections),
                    "version": pack.version,
                }
            )
    return {"packs": packs}


@router.get("/corpus/{pack_id}")
def corpus_detail(pack_id: str, run: str | None = None) -> Any:
    pack = service.pack(pack_id)
    if pack is None:
        return _err(404, f"policy pack {pack_id} is not built")

    coverage: dict[str, dict[str, int]] = {}
    if run:
        loaded = service.load(run)
        if loaded is not None and loaded.log is not None:
            for span in loaded.log.of_type("retrieve.rule"):
                for candidate in span.payload.get("candidates", []):
                    sid = str(candidate.get("section_id"))
                    coverage.setdefault(sid, {"retrieved": 0, "cited": 0})
                    coverage[sid]["retrieved"] += 1
            for span in loaded.log.of_type("judge.rule"):
                sid = span.payload.get("judge_selected_section_id") or span.payload.get(
                    "section_id"
                )
                if sid:
                    coverage.setdefault(str(sid), {"retrieved": 0, "cited": 0})
                    coverage[str(sid)]["cited"] += 1

    return {
        "pack_id": pack.pack_id,
        "manifest": pack.manifest,
        "hierarchy_separators": list(pack.hierarchy_separators),
        "sections": [s.to_dict() for s in pack.sections],
        "coverage": coverage,
        "coverage_run": run,
    }


@router.get("/criteria")
def criteria() -> Any:
    try:
        return load_criteria("criteria")
    except PackError as exc:
        return _err(404, str(exc))


@router.get("/measurements")
def measurement_panel() -> Any:
    return measurements_mod.assemble(service)


# -- live adjudication ------------------------------------------------------


@router.get("/adjudicate/availability")
def adjudicate_availability() -> Any:
    return jobs.availability()


@router.get("/conversations")
def conversation_packs() -> Any:
    """The prepared library, one entry per conversation pack."""
    packs = []
    for pack_id in conversations_mod.available_packs():
        policy = service.pack(pack_id)
        described = conversations_mod.describe(pack_id)
        described["policy_label"] = (
            policy.manifest.get("label", pack_id) if policy else pack_id
        )
        described["policy_citation"] = policy.citation if policy else None
        described["provisions"] = len(policy.sections) if policy else None
        packs.append(described)
    return {"packs": packs}


@router.get("/conversations/{pack_id}")
def conversation_pack(pack_id: str) -> Any:
    if pack_id not in conversations_mod.available_packs():
        return _err(404, f"no conversation pack {pack_id}")
    return conversations_mod.describe(pack_id)


@router.post("/adjudicate")
async def adjudicate(request: Request) -> Any:
    """Run one prepared conversation.

    Free text is deliberately not accepted. A conversation without speaker
    labels cannot be adjudicated safely, because the guarantee that only
    agent turns are scored depends on knowing who said what.
    """
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return _err(400, "body must be JSON")

    pack_id = str(body.get("pack_id") or "")
    conversation_id = str(body.get("conversation_id") or "")
    title = str(body.get("title") or "")

    if body.get("transcript") and not conversation_id:
        return _err(
            400,
            "free text is not accepted. Submit a prepared conversation by "
            "pack_id and conversation_id: unlabelled text cannot guarantee "
            "that only agent turns are adjudicated.",
        )
    if not pack_id or not conversation_id:
        return _err(400, "pack_id and conversation_id are required")

    conversation = conversations_mod.get(pack_id, conversation_id)
    if conversation is None:
        return _err(404, f"no conversation {conversation_id} in pack {pack_id}")

    call_date = None
    if body.get("call_date"):
        try:
            call_date = date.fromisoformat(str(body["call_date"]))
        except ValueError:
            return _err(400, "call_date must be ISO format")

    try:
        job = jobs.submit_conversation(
            pack_id=pack_id,
            conversation=conversation,
            title=title,
            call_date=call_date,
        )
    except ValueError as exc:
        return _err(400, str(exc))
    except PermissionError as exc:
        return _err(503, str(exc))
    return job.to_dict()


@router.get("/adjudicate/{job_id}")
def adjudicate_status(job_id: str) -> Any:
    job = jobs.get(job_id)
    if job is None:
        return _err(404, f"no job {job_id}")
    return job.to_dict()


@router.get("/adjudicate/{job_id}/events")
def adjudicate_events(job_id: str) -> Any:
    job = jobs.get(job_id)
    if job is None:
        return _err(404, f"no job {job_id}")
    return StreamingResponse(
        jobs.stream(job),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# -- static UI --------------------------------------------------------------


def attach_ui(app: FastAPI) -> None:
    """Mount the API router and, when built, the compiled UI."""
    app.include_router(router)

    dist = UI_DIST
    index = dist / "index.html"

    if (dist / "assets").exists():
        from fastapi.staticfiles import StaticFiles

        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="ui-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str) -> Any:
        """Serve the single page app for any non-API path.

        Registered last, so every real route wins. Deep links like /runs/x
        land here and get index.html, which is what client side routing needs.
        """
        if full_path.startswith(("api/", "v1/")):
            return _err(404, "no such route")
        if index.exists():
            candidate = (dist / full_path).resolve()
            if (
                full_path
                and candidate.is_file()
                and str(candidate).startswith(str(dist.resolve()))
            ):
                return FileResponse(candidate)
            return FileResponse(index, media_type="text/html")
        return JSONResponse(
            status_code=503,
            content={
                "error": "UI is not built",
                "hint": "cd EchoProof/ui && npm install && npm run build, "
                "or run the Vite dev server with npm run dev",
            },
        )
