"""FastAPI backend for PatchCourt."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from patchcourt.api.webhook import router as webhook_router
from patchcourt.demo import demo_pr
from patchcourt.graph import run_review
from patchcourt.ingest import parse_pr_url

logger = logging.getLogger("patchcourt.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        from patchcourt.db.session import init_db

        init_db()  # creates tables when a DATABASE_URL is configured
    except Exception:
        logger.debug("audit DB not configured", exc_info=True)
    yield


app = FastAPI(title="PatchCourt", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(webhook_router)

_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
app.mount(
    "/static",
    StaticFiles(directory=os.path.join(_TEMPLATES_DIR, "static")),
    name="static",
)


class ReviewRequest(BaseModel):
    pr_url: str = Field(..., description="GitHub PR URL, e.g. https://github.com/owner/repo/pull/123")


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    path = os.path.join(_TEMPLATES_DIR, "index.html")
    with open(path) as f:
        return HTMLResponse(f.read())


@app.post("/api/review")
async def review(req: ReviewRequest) -> dict:
    try:
        parse_pr_url(req.pr_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    try:
        report = await run_review(req.pr_url)
    except Exception as e:  # network / API failures surface to the client
        raise HTTPException(status_code=502, detail=f"Review failed: {e}")
    return report.model_dump()


@app.post("/api/review/demo")
async def review_demo() -> dict:
    from patchcourt.config import settings
    from patchcourt.llm import reset_llm

    pr_url = "https://github.com/patchcourt/demo/pull/1337"
    was_demo = settings.demo_mode
    was_mock = settings.use_mock_llm
    reset_llm()
    settings.demo_mode = True  # synthetic scanner + mock LLM, fully offline
    settings.use_mock_llm = True
    try:
        report = await run_review(pr_url, pr=demo_pr())
    finally:
        settings.demo_mode = was_demo
        settings.use_mock_llm = was_mock
    return report.model_dump()


@app.get("/api/baseline/latest")
async def baseline_latest() -> dict:
    """Most recently saved SonarQube baseline report (instant — no live calls)."""
    from patchcourt.baseline import latest_report

    report = latest_report()
    if report is None:
        raise HTTPException(status_code=404, detail="No baseline report saved yet — run a baseline first")
    return report


@app.post("/api/baseline")
async def baseline_compare(req: ReviewRequest) -> dict:
    """Fresh comparison: SonarQube issues vs the files touched by a PR, plus a
    PatchCourt reconciliation run. Requires SonarQube + token (explicit action)."""
    from patchcourt.baseline import build_report, compare_with_review, write_report

    try:
        parse_pr_url(req.pr_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    try:
        baseline = build_report(req.pr_url)
        review = await run_review(req.pr_url)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Baseline comparison failed: {e}")

    comparison = compare_with_review(
        baseline, [c.model_dump() for c in review.claims], review.verdict, review.overall_score
    )
    baseline["patchcourt"] = {
        "verdict": review.verdict,
        "overall_score": review.overall_score,
        "comparison": comparison,
    }
    write_report(req.pr_url, baseline)
    return baseline


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/api/sonar/health")
async def sonar_health() -> dict:
    """Check if SonarQube is reachable."""
    from patchcourt.sonar_live import check_sonar_available
    return await check_sonar_available()


@app.get("/api/sonar/quality-gate")
async def sonar_quality_gate() -> dict:
    """Quality gate status for the configured project."""
    from patchcourt.sonar_live import get_quality_gate, SonarQubeUnavailable
    try:
        return await get_quality_gate()
    except SonarQubeUnavailable as e:
        return {"available": False, "error": str(e)}


@app.get("/api/sonar/measures")
async def sonar_measures() -> dict:
    """Component measures (metrics) for the configured project."""
    from patchcourt.sonar_live import get_measures, SonarQubeUnavailable
    try:
        return await get_measures()
    except SonarQubeUnavailable as e:
        return {"available": False, "error": str(e)}


@app.get("/api/sonar/issues")
async def sonar_issues(
    page: int = 1,
    page_size: int = 20,
    severities: str | None = None,
    types: str | None = None,
) -> dict:
    """Paginated issue search for the configured project."""
    from patchcourt.sonar_live import get_issues, SonarQubeUnavailable
    try:
        return await get_issues(page=page, page_size=page_size, severities=severities, types=types)
    except SonarQubeUnavailable as e:
        return {"available": False, "error": str(e)}