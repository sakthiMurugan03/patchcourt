from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")


class Settings(BaseModel):
    github_token: str = os.getenv("GITHUB_TOKEN", "")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_provider: str = os.getenv("LLM_PROVIDER", "mock")  # mock|openai|claude|gemini|ollama
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o")
    use_mock_llm: bool = os.getenv("USE_MOCK_LLM", "").lower() in ("1", "true", "yes")
    debate_max_rounds: int = 2
    block_threshold: float = 10.0
    needs_review_threshold: float = 4.0

    # Evidence engine
    enabled_tools: str = os.getenv("PATCHCOURT_TOOLS", "semgrep,bandit,gitleaks,radon")
    enable_synthetic_tools: bool = os.getenv("USE_SYNTHETIC_TOOLS", "false").lower() in ("1", "true", "yes")
    demo_mode: bool = os.getenv("PATCHCOURT_DEMO", "").lower() in ("1", "true", "yes")

    # Vector store (Qdrant)
    qdrant_url: str = os.getenv("QDRANT_URL", "")
    qdrant_collection: str = os.getenv("QDRANT_COLLECTION", "patchcourt_chunks")

    # Async queue + audit DB
    redis_url: str = os.getenv("REDIS_URL", "")
    database_url: str = os.getenv("DATABASE_URL", "")

    # SonarQube baseline
    sonar_url: str = os.getenv("SONAR_URL", "http://localhost:9000")
    sonar_token: str = os.getenv("SONAR_TOKEN", "")
    sonar_component: str = os.getenv("SONAR_COMPONENT", "patchcourt")

    # SonarQube Live
    sonar_project_key: str = os.getenv("SONAR_PROJECT_KEY", "patchcourt")
    sonar_host_url: str = os.getenv("SONAR_HOST_URL", "http://localhost:9000")

    # Sandbox
    sandbox_enabled: bool = os.getenv("SANDBOX_ENABLED", "false").lower() in ("1", "true", "yes")
    sandbox_image: str = os.getenv("SANDBOX_IMAGE", "patchcourt-sandbox:latest")
    sandbox_workspace: str = os.getenv("SANDBOX_WORKSPACE", "/workspace")
    # Base dir for per-run working copies. Must be a path the Docker *daemon* can
    # also see (bind-mounted into the container). Empty → local system tmp.
    sandbox_workdir: str = os.getenv("SANDBOX_WORKDIR", "")


settings = Settings()

TIER_WEIGHTS: dict[int, float] = {
    1: 1.0,
    2: 0.8,
    3: 0.5,
    4: 0.4,
    5: 0.1,
}
