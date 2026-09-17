"""CLI for PatchCourt."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys

from patchcourt.config import settings


async def _review(pr_url: str | None, demo: bool, quiet: bool) -> None:
    from patchcourt.graph import run_review

    if demo:
        settings.demo_mode = True
        settings.enable_synthetic_tools = True
        settings.use_mock_llm = True
        from patchcourt.demo import demo_pr
        from patchcourt.config import TIER_WEIGHTS  # noqa: F401

        report = await run_review("https://github.com/patchcourt/demo/pull/1337", pr=demo_pr())
    else:
        report = await run_review(pr_url)

    print(f"\nPATCHCOURT REVIEW  —  {report.pr_url}")
    print(f"\tOverall score : {report.overall_score}")
    print(f"\tVerdict       : {report.verdict}")
    if report.debate_transcripts:
        print(f"\tDebates       : {len(report.debate_transcripts)} dispute(s)")
    for f in report.files:
        print(f"\n  {f.file}  (score {f.score})")
        for c in f.claims:
            tiers = ",".join(f"T{e.tier}" for e in c.evidence)
            corr = " corroborated" if c.corroborated else ""
            print(f"\t[{c.agent}] sev{c.severity} T{c.tier}{corr} conf{c.confidence} "
                  f"{c.file}:{c.line} — {c.issue}")
            print(f"\t\tevidence tags: {tiers}")
    if not quiet:
        print("\n--- full report ---")
        print(json.dumps(report.model_dump(), indent=2))


def _baseline(pr_url: str, demo: bool = False, quiet: bool = False) -> None:
    from patchcourt.baseline import build_report, write_report

    report = build_report(pr_url)
    md_path, json_path = write_report(pr_url, report)
    s = report["summary"]
    print(f"\nSONARQUBE BASELINE  —  {report['component']} @ {report['server_url']}")
    print(f"\tPR             : {report['pr_url']}")
    print(f"\tOpen issues    : {report['total_open_issues']}")
    print(f"\tTouching PR    : {report['issues_touching_pr']}")
    print(f"\tBy type        : {s['vulnerabilities']} vuln / {s['bugs']} bug / {s['code_smells']} smell")
    for row in report["issues"]:
        if row["in_pr"]:
            mark = "  IN-PR"
        else:
            mark = "       "
        print(f"\t{mark} [{row['severity']:>7}] {row['file']}:{row['line'] or '-'} {row['rule']}")
    print(f"\n\tReport         : {md_path}")
    print(f"\tJSON           : {json_path}")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="patchcourt", description="Evidence-tiered AI PR review")
    sub = p.add_subparsers(dest="command", required=True)

    review = sub.add_parser("review", help="Review a GitHub PR (offline demo with --demo)")
    review.add_argument("pr_url", nargs="?", help="https://github.com/owner/repo/pull/NUMBER")
    review.add_argument("--demo", action="store_true", help="use the bundled insecure demo PR (no GitHub needed)")
    review.add_argument("--quiet", action="store_true", help="omit the full JSON report")
    review.set_defaults(fn=_review)

    baseline = sub.add_parser(
        "baseline", help="Compare SonarQube issues against the files changed by a PR"
    )
    baseline.add_argument(
        "pr_url", help="https://github.com/owner/repo/pull/NUMBER (files compared against SonarQube issues)"
    )
    baseline.set_defaults(fn=_baseline, quiet=False)

    args = p.parse_args(argv)
    if args.command == "review" and not args.demo and not args.pr_url:
        p.error("review requires either a <pr_url> or --demo")
    demo = getattr(args, "demo", False)
    quiet = getattr(args, "quiet", False)
    fn = args.fn
    if asyncio.iscoroutinefunction(fn):
        asyncio.run(fn(args.pr_url, demo, quiet))
    else:
        fn(args.pr_url, demo, quiet)


if __name__ == "__main__":
    sys.exit(main())