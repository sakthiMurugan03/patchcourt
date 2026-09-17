"""Ingest module — fetch PR data from GitHub."""
from patchcourt.ingest.github import fetch_pr, parse_pr_url

__all__ = ["fetch_pr", "parse_pr_url"]
