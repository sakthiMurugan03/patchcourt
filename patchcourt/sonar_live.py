"""SonarQube Web API client for Live dashboard."""
from __future__ import annotations

import httpx
import logging
from typing import Any

from patchcourt.config import settings

logger = logging.getLogger("patchcourt.sonar_live")

SONAR_TIMEOUT = httpx.Timeout(10.0, connect=5.0)
# Shorter timeout for measures endpoint which can hang
SONAR_MEASURES_TIMEOUT = httpx.Timeout(5.0, connect=3.0)


class SonarQubeUnavailable(Exception):
    """Raised when SonarQube is not reachable."""
    pass


async def _sonar_get(path: str, params: dict | None = None, timeout: httpx.Timeout | None = None) -> dict[str, Any]:
    """Make a GET request to SonarQube API."""
    url = f"{settings.sonar_url.rstrip('/')}/api{path}"
    headers = {}
    if settings.sonar_token:
        headers["Authorization"] = f"Bearer {settings.sonar_token}"
    try:
        async with httpx.AsyncClient(timeout=timeout or SONAR_TIMEOUT) as client:
            resp = await client.get(url, params=params, headers=headers)
            if resp.status_code == 404:
                raise SonarQubeUnavailable("SonarQube returned 404")
            resp.raise_for_status()
            return resp.json()
    except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as e:
        logger.warning("SonarQube request failed: %s", e)
        raise SonarQubeUnavailable(f"SonarQube unavailable: {e}") from e


async def _sonar_get_measures(path: str, params: dict | None = None) -> dict[str, Any]:
    """Make a GET request to SonarQube measures API with shorter timeout."""
    url = f"{settings.sonar_url.rstrip('/')}/api{path}"
    headers = {}
    if settings.sonar_token:
        headers["Authorization"] = f"Bearer {settings.sonar_token}"
    try:
        async with httpx.AsyncClient(timeout=SONAR_MEASURES_TIMEOUT) as client:
            resp = await client.get(url, params=params, headers=headers)
            if resp.status_code == 404:
                raise SonarQubeUnavailable("SonarQube returned 404")
            resp.raise_for_status()
            return resp.json()
    except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as e:
        logger.warning("SonarQube measures request failed: %s", e)
        raise SonarQubeUnavailable(f"SonarQube unavailable: {e}") from e


async def get_quality_gate(project_key: str | None = None) -> dict[str, Any]:
    """Get quality gate status for a project."""
    params = {"projectKey": project_key or settings.sonar_project_key}
    data = await _sonar_get("/qualitygates/project_status", params=params)
    return {
        "available": True,
        "project_key": project_key or settings.sonar_project_key,
        "status": data.get("projectStatus", {}).get("status", "UNKNOWN"),
        "conditions": data.get("projectStatus", {}).get("conditions", []),
        "period_index": data.get("projectStatus", {}).get("periodIndex", 1),
    }


async def get_measures(project_key: str | None = None) -> dict[str, Any]:
    """Get component measures (metrics) with short timeout."""
    metric_keys = [
        "bugs",
        "vulnerabilities",
        "code_smells",
        "security_hotspots",
        "coverage",
        "duplicated_lines_density",
        "reliability_rating",
        "security_rating",
        "sqale_rating",
    ]
    params = {
        "component": project_key or settings.sonar_project_key,
        "metricKeys": ",".join(metric_keys),
    }
    try:
        data = await _sonar_get_measures("/measures/component", params=params)
        measures = data.get("component", {}).get("measures", [])
        result = {"available": True, "project_key": project_key or settings.sonar_project_key}
        for m in measures:
            result[m["metric"]] = m.get("value")
        return result
    except SonarQubeUnavailable:
        # Return unavailable but with default structure so frontend shows "—"
        return {
            "available": False,
            "project_key": project_key or settings.sonar_project_key,
            "bugs": None,
            "vulnerabilities": None,
            "code_smells": None,
            "security_hotspots": None,
            "coverage": None,
            "duplicated_lines_density": None,
            "reliability_rating": None,
            "security_rating": None,
            "sqale_rating": None,
        }


async def get_issues(
    project_key: str | None = None,
    page: int = 1,
    page_size: int = 20,
    severities: str | None = None,
    types: str | None = None,
) -> dict[str, Any]:
    """Search for issues with pagination."""
    params = {
        "componentKeys": project_key or settings.sonar_project_key,
        "p": page,
        "ps": page_size,
    }
    if severities:
        params["severities"] = severities
    if types:
        params["types"] = types
    data = await _sonar_get("/issues/search", params=params)
    issues = data.get("issues", [])
    return {
        "available": True,
        "project_key": project_key or settings.sonar_project_key,
        "total": data.get("total", 0),
        "page": data.get("p", page),
        "page_size": data.get("ps", page_size),
        "issues": [
            {
                "key": i.get("key"),
                "rule": i.get("rule"),
                "severity": i.get("severity"),
                "type": i.get("type"),
                "component": i.get("component"),
                "file": i.get("component", "").split(":")[-1] if i.get("component") else "",
                "line": i.get("textRange", {}).get("startLine") if i.get("textRange") else None,
                "message": i.get("message"),
                "status": i.get("status"),
                "tags": i.get("tags", []),
            }
            for i in issues
        ],
    }


async def check_sonar_available() -> dict[str, Any]:
    """Check if SonarQube is reachable."""
    try:
        await _sonar_get("/system/status")
        return {"available": True}
    except SonarQubeUnavailable as e:
        return {"available": False, "error": str(e)}