import asyncio, sys, traceback
sys.path.insert(0, '/app')

async def test():
    from patchcourt.ingest.github import fetch_pr
    from patchcourt.config import settings
    print(f"github_token: {bool(settings.github_token)}")
    
    try:
        print("Fetching PR...")
        pr = await fetch_pr('https://github.com/sakthiMurugan03/gi-ml-proj/pull/2')
        print(f"PR fetched OK: {len(pr.file_contents)} files")
        print(f"files: {list(pr.file_contents.keys())}")
    except Exception as e:
        print(f"fetch_pr FAILED: {type(e).__name__}: {e}")
        traceback.print_exc()
        return

    from patchcourt.baseline.sonarqube_baseline import project_key_for_pr, build_report
    owner, repo, num = 'sakthiMurugan03', 'gi-ml-proj', 2
    project_key = project_key_for_pr(owner, repo, num)
    print(f"project_key: {project_key}")
    
    try:
        print("Building report (no scan, just fetch issues)...")
        baseline = build_report('https://github.com/sakthiMurugan03/gi-ml-proj/pull/2', component=project_key)
        print(f"baseline OK: {baseline.get('total_open_issues')} issues, {baseline.get('issues_touching_pr')} in PR")
    except Exception as e:
        print(f"build_report FAILED: {type(e).__name__}: {e}")
        traceback.print_exc()

asyncio.run(test())
