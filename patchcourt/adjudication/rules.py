"""Repository-aware rule adjudication (Enhancement 2).

Provides a static-analysis rule catalog (so a finding can be tied to the
semantics of the rule that produced it) and a repository-policy loader (so
findings can be adjudicated against the project's own coding standards,
API-boundary rules, and security policy rather than the tool's default
recommendation).
"""
from __future__ import annotations

import dataclasses
import re
from pathlib import Path

from patchcourt.agents.schemas import PolicyRef
from patchcourt.tools.base import Finding

POLICY_FILE_PREFIX = ".patchcourt/policies/"


@dataclasses.dataclass(frozen=True)
class RuleInfo:
    id: str
    title: str
    category: str
    rationale: str
    dangerous_patterns: tuple[str, ...] = ()
    safe_patterns: tuple[str, ...] = ()
    recommendation: str = ""


RULE_CATALOG: dict[str, RuleInfo] = {
    "SHELL_TRUE": RuleInfo(
        id="SHELL_TRUE",
        title="Command execution with shell=True",
        category="security",
        rationale="A shell interprets metacharacters, so untrusted input can inject commands.",
        dangerous_patterns=(r"subprocess\.(call|Popen|run)\([^)]*shell\s*=\s*True",),
        recommendation="avoid shell=True or pass a fixed argument list",
    ),
    "OS_SYSTEM": RuleInfo(
        id="OS_SYSTEM",
        title="os.system shell invocation",
        category="security",
        rationale="os.system executes through a shell and is injection-prone.",
        dangerous_patterns=(r"os\.system\(",),
        recommendation="use subprocess with an argument list",
    ),
    "DYN_EXEC": RuleInfo(
        id="DYN_EXEC",
        title="Dynamic code execution",
        category="security",
        rationale="exec/eval on non-constant input allows arbitrary code execution.",
        dangerous_patterns=(r"\b(exec|eval)\(",),
        recommendation="avoid exec/eval on dynamic input",
    ),
    "SQL_CONCAT": RuleInfo(
        id="SQL_CONCAT",
        title="SQL built by string concatenation",
        category="security",
        rationale="Concatenating values into SQL lets input alter the query structure.",
        dangerous_patterns=(
            r"['\"]\s*SELECT[^'\"]*['\"]?\s*\+",
            r"[fF]?['\"]\s*SELECT",
            r"(?i)select\b[^;]*(\+|\{|%|\.format)",
        ),
        safe_patterns=(r"(?i)(execute|query|cursor)\w*\(\s*[^,)]+,\s*[\(\[]",),
        recommendation="use parameterized queries",
    ),
    "HARDCODED_SECRET": RuleInfo(
        id="HARDCODED_SECRET",
        title="Hardcoded credential",
        category="security",
        rationale="Secrets committed to source leak through history and forks.",
        dangerous_patterns=(
            r"(?i)\b\w*(password|passwd|secret|token|api[_-]?key)\w*\s*=\s*['\"][^'\"]{6,}['\"]",
        ),
        safe_patterns=(
            r"(?i)['\"](changeme|change_me|placeholder|example|dummy|xxxx+|your[_-]?\w*|<[^>]+>|todo|fake)['\"]",
            r"(?i)\b\w*(password|secret|token|api[_-]?key)\w*\s*=\s*(os\.environ|getenv|settings)",
        ),
        recommendation="load the secret from the environment or a secret manager",
    ),
    "HTTP_PLAINTEXT": RuleInfo(
        id="HTTP_PLAINTEXT",
        title="Plaintext HTTP request",
        category="security",
        rationale="Plaintext HTTP exposes traffic to interception.",
        dangerous_patterns=(r"requests\.(get|post|put|delete)\(['\"]http://",),
        safe_patterns=(r"https://",),
        recommendation="use HTTPS",
    ),
    "UNSAFE_DESERIAL": RuleInfo(
        id="UNSAFE_DESERIAL",
        title="Unsafe deserialization",
        category="security",
        rationale="Untrusted serialized data can trigger code execution during load.",
        dangerous_patterns=(r"pickle\.loads?\(", r"yaml\.load\([^)]*FullLoader"),
        recommendation="use a safe loader or data-only format",
    ),
    "VISIBILITY": RuleInfo(
        id="VISIBILITY",
        title="Member visibility recommendation",
        category="maintainability",
        rationale="Broadening visibility expands a class's externally accessible surface.",
        dangerous_patterns=(),
        safe_patterns=(),
        recommendation="widen visibility",
    ),
    "COMPLEXITY": RuleInfo(
        id="COMPLEXITY",
        title="High cyclomatic complexity",
        category="maintainability",
        rationale="Complex functions are harder to test and reason about.",
        recommendation="refactor into smaller units",
    ),
    "UNUSED_CODE": RuleInfo(
        id="UNUSED_CODE",
        title="Unused declaration",
        category="maintainability",
        rationale="Dead declarations add noise and can hide mistakes.",
        recommendation="remove the unused declaration",
    ),
}

_ALIASES: dict[str, str] = {
    "b602": "SHELL_TRUE",
    "b604": "SHELL_TRUE",
    "b605": "OS_SYSTEM",
    "b607": "OS_SYSTEM",
    "b608": "SQL_CONCAT",
    "b105": "HARDCODED_SECRET",
    "b106": "HARDCODED_SECRET",
    "b107": "HARDCODED_SECRET",
    "b301": "UNSAFE_DESERIAL",
    "b310": "HTTP_PLAINTEXT",
    "b506": "UNSAFE_DESERIAL",
    "shell_true": "SHELL_TRUE",
    "os_system": "OS_SYSTEM",
    "dyn_exec": "DYN_EXEC",
    "sql_concat": "SQL_CONCAT",
    "sql_injection": "SQL_CONCAT",
    "hardcoded_secret": "HARDCODED_SECRET",
    "http_plaintext": "HTTP_PLAINTEXT",
    "unsafe_deserial": "UNSAFE_DESERIAL",
}

_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("shell=true", "SHELL_TRUE"),
    ("os.system", "OS_SYSTEM"),
    ("command injection", "SHELL_TRUE"),
    ("sql injection", "SQL_CONCAT"),
    ("sql", "SQL_CONCAT"),
    ("eval", "DYN_EXEC"),
    ("exec", "DYN_EXEC"),
    ("hardcoded", "HARDCODED_SECRET"),
    ("secret", "HARDCODED_SECRET"),
    ("password", "HARDCODED_SECRET"),
    ("api key", "HARDCODED_SECRET"),
    ("http://", "HTTP_PLAINTEXT"),
    ("plaintext", "HTTP_PLAINTEXT"),
    ("pickle", "UNSAFE_DESERIAL"),
    ("deserial", "UNSAFE_DESERIAL"),
    ("visibility", "VISIBILITY"),
    ("public", "VISIBILITY"),
    ("private", "VISIBILITY"),
    ("complex", "COMPLEXITY"),
    ("unused", "UNUSED_CODE"),
)


def rule_for(finding: Finding) -> RuleInfo | None:
    """Resolve the rule that produced a finding, by id, alias, or message keyword."""
    raw = (finding.rule or "").strip()
    if raw:
        canonical = raw.split(":")[-1]
        for key in (raw.upper(), raw.lower(), canonical.upper(), canonical.lower()):
            if key in RULE_CATALOG:
                return RULE_CATALOG[key]
            if key in _ALIASES:
                return RULE_CATALOG[_ALIASES[key]]
    haystack = f"{finding.rule} {finding.message} {finding.recommendation}".lower()
    for needle, rule_id in _KEYWORDS:
        if needle in haystack:
            return RULE_CATALOG[rule_id]
    return None


def category_for(finding: Finding, rule: RuleInfo | None = None) -> str:
    if finding.category:
        return finding.category
    if rule is not None:
        return rule.category
    return "unknown"


@dataclasses.dataclass(frozen=True)
class Policy:
    id: str
    title: str
    body: str
    source: str = "bundled"

    @property
    def keywords(self) -> set[str]:
        return {t for t in re.findall(r"[a-z][a-z_-]{3,}", self.body.lower())}


def _policy_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.strip().startswith("#"):
            return line.lstrip("# ").strip() or fallback
    return fallback


def _bundled_policies_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "policies"


def load_repository_policies(
    extra_files: dict[str, str] | None = None,
    policies_dir: Path | None = None,
) -> list[Policy]:
    """Load bundled policies plus any ``.patchcourt/policies/*.md`` shipped in the PR."""
    policies: dict[str, Policy] = {}
    base = policies_dir or _bundled_policies_dir()
    if base.is_dir():
        for path in sorted(base.glob("*.md")):
            text = path.read_text(encoding="utf-8", errors="replace")
            policies[path.stem] = Policy(
                id=path.stem,
                title=_policy_title(text, path.stem),
                body=text,
                source="bundled",
            )
    for fname, text in (extra_files or {}).items():
        norm = fname.replace("\\", "/").lstrip("/")
        if not norm.startswith(POLICY_FILE_PREFIX) or not norm.endswith(".md"):
            continue
        stem = norm[len(POLICY_FILE_PREFIX):-3].strip("/").replace("/", "-") or "policy"
        policies[f"repo:{stem}"] = Policy(
            id=f"repo:{stem}",
            title=_policy_title(text, stem),
            body=text,
            source="repository",
        )
    return list(policies.values())


def match_policies(text: str, policies: list[Policy], limit: int = 3) -> list[PolicyRef]:
    """Return the repository policies most relevant to a finding's text."""
    tokens = {t for t in re.findall(r"[a-z][a-z_-]{3,}", (text or "").lower())}
    scored: list[tuple[int, Policy]] = []
    for policy in policies:
        score = len(tokens & policy.keywords)
        if score:
            scored.append((score, policy))
    scored.sort(key=lambda item: (-item[0], item[1].id))
    refs: list[PolicyRef] = []
    for _, policy in scored[:limit]:
        excerpt = " ".join(policy.body.split())[:240]
        refs.append(
            PolicyRef(id=policy.id, title=policy.title, excerpt=excerpt, source=policy.source)
        )
    return refs
