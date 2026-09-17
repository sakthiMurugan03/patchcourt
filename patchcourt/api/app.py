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


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}