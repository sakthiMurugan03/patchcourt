"""FastAPI backend for PatchCourt."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from patchcourt.api.webhook import router as webhook_router
from patchcourt.demo import demo_pr
from patchcourt.graph import run_review
from patchcourt.ingest import parse_pr_url
from patchcourt.runtime_llm_config import get_runtime_config, update_runtime_config, get_effective_llm_settings
from patchcourt.llm import reset_llm, LLMInvalidKey, LLMQuotaExhausted, LLMServiceBusy, LLMUnreachable

logger = logging.getLogger("patchcourt.api")


# ------------------------------------------------------------------
# User-friendly error mapping
# ------------------------------------------------------------------
def friendly_error(e: Exception) -> tuple[str, str]:
    """Convert a raw exception into (category, user_message).
    
    Returns a clean category and human-readable message.
    Raw error is logged server-side only.
    """
    # Typed LLM failures first — precise, not string-sniffed.
    if isinstance(e, LLMQuotaExhausted):
        return (
            "llm_quota_exhausted",
            "Gemini API quota exhausted — the free-tier daily/rate limit was reached. "
            "Switch to Offline (Mock) mode in Settings, or add a new API key.",
        )
    if isinstance(e, LLMInvalidKey):
        return (
            "llm_invalid_key",
            "Invalid API key — check it in Settings.",
        )
    if isinstance(e, LLMServiceBusy):
        return (
            "llm_service_busy",
            "Gemini is temporarily overloaded — please retry in a moment.",
        )
    if isinstance(e, LLMUnreachable):
        return (
            "llm_unreachable",
            "Couldn't reach the LLM provider — check your connection or switch to Offline mode.",
        )

    error_str = str(e).lower()
    
    # 429 / quota
    if any(k in error_str for k in ["429", "resource_exhausted", "quota"]):
        return (
            "llm_quota_exhausted",
            "Gemini API quota exhausted — the free-tier daily/rate limit was reached. "
            "Switch to Offline (Mock) mode in Settings, or add a new API key."
        )
    
    # 503 / busy
    if any(k in error_str for k in ["503", "unavailable", "overloaded", "busy"]):
        return (
            "service_busy",
            "Gemini is busy, please retry in a moment"
        )
    
    # 404 / not found
    if any(k in error_str for k in ["404", "not found", "does not exist", "not a valid github", "invalid github pr url"]):
        if "model" in error_str:
            return (
                "model_not_found",
                "LLM model not found — check the model name in Settings"
            )
        if "pr" in error_str or "pull" in error_str or "repository" in error_str or "github" in error_str:
            return (
                "pr_not_found",
                "GitHub PR not found — check the URL"
            )
        return (
            "not_found",
            "Resource not found"
        )
    
    # 401 / auth
    if any(k in error_str for k in ["401", "unauthorized", "authentication", "invalid api key", "invalid key"]):
        return (
            "auth_failed",
            "Invalid API key — check your key in Settings"
        )
    
    # 403 / forbidden
    if any(k in error_str for k in ["403", "forbidden", "permission denied"]):
        return (
            "forbidden",
            "Access denied — check API key permissions"
        )
    
    # Timeout
    if any(k in error_str for k in ["timeout", "timed out", "deadline exceeded"]):
        return (
            "timeout",
            "Request timed out — please retry"
        )
    
    # Connection
    if any(k in error_str for k in ["connection", "connect", "dns", "resolve", "refused"]):
        if "sonar" in error_str:
            return (
                "sonar_offline",
                "SonarQube offline — check SonarQube is running and URL is correct"
            )
        if "github" in error_str:
            return (
                "github_unreachable",
                "Cannot reach GitHub — check network"
            )
        return (
            "connection_failed",
            "Connection failed — check service is running"
        )
    
    # Rate limit (generic)
    if "rate limit" in error_str:
        return (
            "rate_limited",
            "Rate limited — please wait and retry"
        )
    
    # LLM specific
    if "model" in error_str and ("not found" in error_str or "unknown" in error_str):
        return (
            "model_not_found",
            "LLM model not found — check the model name in Settings"
        )
    
    # Check specific patterns
    specific = _match_error(error_str)
    if specific:
        return specific

    # Default
    logger.exception("Unhandled error in API")
    return (
        "unknown",
        "Something went wrong — please try again"
    )


# Specific error patterns for common cases
def _match_error(error_str: str) -> tuple[str, str] | None:
    """Additional specific error pattern matching."""
    if "no baseline report" in error_str or "baseline report saved" in error_str:
        return ("not_found", "No baseline report saved yet — run a baseline first")
    return None


# Custom HTTPException with category
class FriendlyHTTPException(HTTPException):
    def __init__(self, status_code: int, category: str, detail: str):
        super().__init__(status_code=status_code, detail={"category": category, "message": detail})


class LLMSettingsResponse(BaseModel):
    provider: str
    model: str
    base_url: str
    use_mock_llm: bool
    has_api_key: bool
    available_providers: list[str]


class LLMSettingsUpdate(BaseModel):
    provider: str | None = None
    model: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    use_mock_llm: bool | None = None


class LLMTestRequest(BaseModel):
    pass  # uses current runtime config


class LLMTestResponse(BaseModel):
    ok: bool
    detail: str


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
        cat, msg = friendly_error(e)
        raise FriendlyHTTPException(status_code=400, category=cat, detail=msg)
    try:
        report = await run_review(req.pr_url)
    except Exception as e:
        logger.exception("Review failed")
        cat, msg = friendly_error(e)
        raise FriendlyHTTPException(status_code=502, category=cat, detail=msg)
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
    except Exception as e:
        logger.exception("Demo review failed")
        cat, msg = friendly_error(e)
        raise FriendlyHTTPException(status_code=502, category=cat, detail=msg)
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
        cat, msg = friendly_error(ValueError("No baseline report"))
        raise FriendlyHTTPException(status_code=404, category=cat, detail=msg)
    return report


@app.post("/api/baseline")
async def baseline_compare(req: ReviewRequest) -> dict:
    """Fresh comparison: SonarQube issues vs the files touched by a PR, plus a
    PatchCourt reconciliation run. Requires SonarQube + token (explicit action)."""
    from patchcourt.baseline import build_report, compare_with_review, write_report

    try:
        parse_pr_url(req.pr_url)
    except ValueError as e:
        cat, msg = friendly_error(e)
        raise FriendlyHTTPException(status_code=400, category=cat, detail=msg)
    try:
        baseline = build_report(req.pr_url)
        review = await run_review(req.pr_url)
    except Exception as e:
        logger.exception("Baseline comparison failed")
        cat, msg = friendly_error(e)
        raise FriendlyHTTPException(status_code=502, category=cat, detail=msg)

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
    try:
        return await check_sonar_available()
    except Exception as e:
        logger.exception("Sonar health check failed")
        cat, msg = friendly_error(e)
        return {"available": False, "category": cat, "message": msg}


@app.get("/api/sonar/quality-gate")
async def sonar_quality_gate() -> dict:
    """Quality gate status for the configured project."""
    from patchcourt.sonar_live import get_quality_gate, SonarQubeUnavailable
    try:
        return await get_quality_gate()
    except SonarQubeUnavailable as e:
        cat, msg = friendly_error(e)
        return {"available": False, "category": cat, "message": msg}
    except Exception as e:
        logger.exception("Sonar quality gate failed")
        cat, msg = friendly_error(e)
        return {"available": False, "category": cat, "message": msg}


@app.get("/api/sonar/measures")
async def sonar_measures() -> dict:
    """Component measures (metrics) for the configured project."""
    from patchcourt.sonar_live import get_measures, SonarQubeUnavailable
    try:
        return await get_measures()
    except SonarQubeUnavailable as e:
        cat, msg = friendly_error(e)
        return {"available": False, "category": cat, "message": msg}
    except Exception as e:
        logger.exception("Sonar measures failed")
        cat, msg = friendly_error(e)
        return {"available": False, "category": cat, "message": msg}


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
        cat, msg = friendly_error(e)
        return {"available": False, "category": cat, "message": msg}
    except Exception as e:
        logger.exception("Sonar issues failed")
        cat, msg = friendly_error(e)
        return {"available": False, "category": cat, "message": msg}


# ------------------------------------------------------------------
# LLM Settings (runtime, no container restart needed)
# ------------------------------------------------------------------
@app.get("/api/settings/llm", response_model=LLMSettingsResponse)
async def get_llm_settings() -> LLMSettingsResponse:
    """Get current effective LLM settings (runtime overrides env)."""
    return get_effective_llm_settings()


@app.post("/api/settings/llm", response_model=LLMSettingsResponse)
async def update_llm_settings(req: LLMSettingsUpdate) -> LLMSettingsResponse:
    """Update LLM settings at runtime. Re-initializes the LLM client."""
    cfg = update_runtime_config(
        provider=req.provider,
        model=req.model,
        api_key=req.api_key,
        base_url=req.base_url,
        use_mock_llm=req.use_mock_llm,
    )
    return cfg.to_dict()


@app.post("/api/settings/llm/test", response_model=LLMTestResponse)
async def test_llm_connection() -> LLMTestResponse:
    """Test the current LLM provider connection.
    
    For Gemini: calls the generativelanguage models endpoint.
    For others: attempts a minimal generate call.
    Returns { ok: bool, detail: str } for UI feedback.
    """
    from patchcourt.llm import get_llm, LLMClient
    
    cfg = get_runtime_config()
    
    # Mock provider always "works" offline
    if cfg.use_mock_llm or cfg.provider == "mock":
        return LLMTestResponse(ok=True, detail="Mock provider — no API call needed")
    
    if not cfg.has_key():
        return LLMTestResponse(ok=False, detail="No API key configured for this provider")
    
    try:
        client = get_llm()
        if not isinstance(client, LLMClient) or client._use_mock:
            return LLMTestResponse(ok=False, detail="LLM client not properly initialized")
        
        # For Gemini, test with the models endpoint (lightweight)
        if cfg.provider == "gemini":
            # Try a minimal call to verify auth
            await client.generate(
                "You are a test assistant.",
                "Reply with exactly: {\"test\": \"ok\"}"
            )
            return LLMTestResponse(ok=True, detail="Gemini connection OK")
        elif cfg.provider == "openai":
            await client.generate(
                "You are a test assistant.",
                "Reply with exactly: {\"test\": \"ok\"}"
            )
            return LLMTestResponse(ok=True, detail="OpenAI connection OK")
        elif cfg.provider == "ollama":
            await client.generate(
                "You are a test assistant.",
                "Reply with exactly: {\"test\": \"ok\"}"
            )
            return LLMTestResponse(ok=True, detail="Ollama connection OK")
        else:
            return LLMTestResponse(ok=False, detail=f"Unknown provider: {cfg.provider}")
            
    except Exception as e:
        error_str = str(e).lower()
        logger.warning("LLM connection test failed: %s", e)
        if any(k in error_str for k in ["401", "unauthorized", "auth", "invalid key"]):
            return LLMTestResponse(ok=False, detail="Invalid API key — check it in Settings")
        if any(k in error_str for k in ["429", "resource_exhausted", "quota"]):
            return LLMTestResponse(
                ok=False,
                detail="Gemini API quota exhausted — the free-tier daily/rate limit was reached. "
                "Switch to Offline (Mock) mode in Settings, or add a new API key.",
            )
        if any(k in error_str for k in ["503", "overloaded", "unavailable", "busy"]):
            return LLMTestResponse(ok=False, detail="Gemini is temporarily overloaded — please retry in a moment")
        if any(k in error_str for k in ["timeout", "connection", "connect", "dns", "resolve", "refused"]):
            return LLMTestResponse(
                ok=False,
                detail="Couldn't reach the LLM provider — check your connection or switch to Offline mode",
            )
        # Unknown error: never surface raw provider output to the UI.
        return LLMTestResponse(ok=False, detail="Something went wrong while testing the connection")