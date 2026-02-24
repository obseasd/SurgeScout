"""SurgeScout API server — FastAPI backend powering the agent and dashboard."""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import config
from .moltbook import MoltbookClient, scout_moltbook, extract_projects_from_posts
from .analyzer import analyze_project, analyze_batch, generate_launch_report
from .launcher import SurgeLauncher, launch_pipeline

log = logging.getLogger("surgescout.server")

app = FastAPI(
    title="SurgeScout",
    description="AI Deal Flow Agent for Internet Capital Markets on SURGE",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# State
_state = {
    "scouted_projects": [],
    "analyses": [],
    "launches": [],
    "moltbook_posts": [],
    "last_scout": None,
    "last_analysis": None,
}

DATA_FILE = os.path.join(config.DATA_DIR, "state.json")


def _save_state():
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(_state, f, indent=2, default=str)
    except Exception as e:
        log.warning(f"Failed to save state: {e}")


def _load_state():
    global _state
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE) as f:
                _state = json.load(f)
        except Exception:
            pass


_load_state()


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class ScoutRequest(BaseModel):
    submolts: list[str] | None = None
    keywords: list[str] | None = None


class AnalyzeRequest(BaseModel):
    project: dict | None = None
    project_id: str | None = None
    min_score: int = 0


class LaunchRequest(BaseModel):
    analysis_index: int | None = None
    project_name: str | None = None
    chain: str = "base"


class MoltbookPostRequest(BaseModel):
    title: str
    body: str
    submolt: str = ""


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
async def index():
    """Serve the dashboard."""
    html_path = Path(__file__).parent.parent / "web" / "index.html"
    if html_path.exists():
        return FileResponse(html_path, media_type="text/html")
    return HTMLResponse("<h1>SurgeScout</h1><p>Dashboard not found. Check web/index.html</p>")


@app.get("/api/health")
async def health():
    has_key = bool(config.ANTHROPIC_API_KEY or config.OPENAI_API_KEY)
    return {
        "status": "ok",
        "provider": config.AI_PROVIDER,
        "api_key_configured": has_key,
        "projects_scouted": len(_state["scouted_projects"]),
        "analyses_done": len(_state["analyses"]),
        "launches": len(_state["launches"]),
    }


@app.get("/api/state")
async def get_state():
    """Return full agent state."""
    return _state


# ------ Scout ------

@app.post("/api/scout")
async def scout(req: ScoutRequest):
    """Scout Moltbook for promising projects."""
    projects = scout_moltbook(
        submolts=req.submolts,
        keywords=req.keywords,
    )
    _state["scouted_projects"] = projects
    _state["last_scout"] = datetime.now(timezone.utc).isoformat()
    _save_state()
    return {
        "count": len(projects),
        "projects": projects,
    }


# ------ Analyze ------

@app.post("/api/analyze")
async def analyze(req: AnalyzeRequest):
    """Analyze a project or all scouted projects."""
    if req.project:
        result = analyze_project(req.project)
        _state["analyses"].append(result)
        _save_state()
        return result

    if req.project_id:
        proj = next(
            (p for p in _state["scouted_projects"] if str(p.get("id")) == req.project_id),
            None,
        )
        if not proj:
            raise HTTPException(404, f"Project {req.project_id} not found in scouted list")
        result = analyze_project(proj)
        _state["analyses"].append(result)
        _save_state()
        return result

    # Analyze all scouted projects
    if not _state["scouted_projects"]:
        raise HTTPException(400, "No scouted projects. Run /api/scout first.")

    results = analyze_batch(_state["scouted_projects"], min_score=req.min_score)
    _state["analyses"] = results
    _state["last_analysis"] = datetime.now(timezone.utc).isoformat()
    _save_state()
    return {
        "count": len(results),
        "analyses": results,
    }


@app.get("/api/analyses")
async def list_analyses():
    """List all completed analyses."""
    return _state["analyses"]


@app.get("/api/report/{index}")
async def get_report(index: int):
    """Get a human-readable report for an analysis."""
    if index < 0 or index >= len(_state["analyses"]):
        raise HTTPException(404, "Analysis not found")
    report = generate_launch_report(_state["analyses"][index])
    return {"report": report, "analysis": _state["analyses"][index]}


# ------ Launch ------

@app.post("/api/launch")
async def launch(req: LaunchRequest):
    """Launch a token based on analysis results."""
    analysis = None

    if req.analysis_index is not None:
        if req.analysis_index < 0 or req.analysis_index >= len(_state["analyses"]):
            raise HTTPException(404, "Analysis not found at that index")
        analysis = _state["analyses"][req.analysis_index]
    elif req.project_name:
        analysis = next(
            (a for a in _state["analyses"] if a.get("project_name") == req.project_name),
            None,
        )
    else:
        # Use the best analysis
        if _state["analyses"]:
            analysis = max(_state["analyses"], key=lambda a: a.get("overall_score", 0))

    if not analysis:
        raise HTTPException(400, "No analysis found. Run /api/analyze first.")

    result = launch_pipeline(analysis, chain=req.chain)
    _state["launches"].append({
        "project": analysis.get("project_name"),
        "result": result,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    _save_state()
    return result


@app.get("/api/launches")
async def list_launches():
    """List all token launches."""
    return _state["launches"]


# ------ Moltbook ------

@app.post("/api/moltbook/post")
async def moltbook_post(req: MoltbookPostRequest):
    """Post an update to Moltbook."""
    client = MoltbookClient()
    result = client.post_update(req.title, req.body, req.submolt)
    _state["moltbook_posts"].append({
        "title": req.title,
        "body": req.body[:200],
        "result": result,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    _save_state()
    return result


@app.post("/api/moltbook/report")
async def moltbook_report(req: AnalyzeRequest):
    """Generate and post a report to Moltbook for the best analysis."""
    if not _state["analyses"]:
        raise HTTPException(400, "No analyses available. Run /api/analyze first.")

    idx = 0
    if req.project_id:
        for i, a in enumerate(_state["analyses"]):
            if a.get("project_name") == req.project_id:
                idx = i
                break

    analysis = _state["analyses"][idx]
    report = generate_launch_report(analysis)

    client = MoltbookClient()
    title = f"[SurgeScout] Analysis: {analysis.get('project_name', '?')} — {analysis.get('verdict', '?')}"
    result = client.post_update(title, report)

    _state["moltbook_posts"].append({
        "title": title,
        "body": report[:200],
        "result": result,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    _save_state()
    return {"post_result": result, "report": report}


# ------ Pipeline (full cycle) ------

@app.post("/api/pipeline")
async def full_pipeline(req: ScoutRequest):
    """Run the full SurgeScout pipeline: Scout -> Analyze -> Report.

    This is the main autonomous pipeline the OpenClaw agent triggers.
    """
    # 1. Scout
    projects = scout_moltbook(submolts=req.submolts, keywords=req.keywords)
    _state["scouted_projects"] = projects
    _state["last_scout"] = datetime.now(timezone.utc).isoformat()

    if not projects:
        _save_state()
        return {"status": "no_projects_found", "step": "scout"}

    # 2. Analyze top candidates (max 5 to save API calls)
    top_projects = projects[:5]
    analyses = analyze_batch(top_projects, min_score=30)
    _state["analyses"] = analyses
    _state["last_analysis"] = datetime.now(timezone.utc).isoformat()

    if not analyses:
        _save_state()
        return {"status": "no_viable_projects", "step": "analyze", "scouted": len(projects)}

    # 3. Generate reports for top results
    reports = []
    for analysis in analyses[:3]:
        report = generate_launch_report(analysis)
        reports.append({
            "project": analysis.get("project_name"),
            "score": analysis.get("overall_score"),
            "verdict": analysis.get("verdict"),
            "report": report,
        })

    _save_state()

    return {
        "status": "complete",
        "scouted": len(projects),
        "analyzed": len(analyses),
        "reports": reports,
        "best_project": analyses[0].get("project_name") if analyses else None,
        "best_score": analyses[0].get("overall_score") if analyses else 0,
    }
