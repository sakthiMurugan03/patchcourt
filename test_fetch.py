import httpx, asyncio, sys, traceback
sys.path.insert(0, '/app')
from patchcourt.ingest.github import fetch_pr

async def test():
    try:
        pr = await fetch_pr('https://github.com/sakthiMurugan03/gi-ml-proj/pull/2')
        print('OK files:', list(pr.file_contents.keys())[:5])
    except Exception as e:
        traceback.print_exc()

asyncio.run(test())
