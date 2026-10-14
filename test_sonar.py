import httpx, sys
sys.path.insert(0, '/app')
from patchcourt.config import settings

token = settings.sonar_token
server = settings.sonar_url
component = 'pr-sakthimurugan03-gi-ml-proj-2'
headers = {'Authorization': f'Bearer {token}'}

print(f"server: {server}")
print(f"token present: {bool(token)}")
print(f"component: {component}")

try:
    r = httpx.get(f'{server}/api/issues/search',
                  params={'componentKeys': component, 'resolved': 'false', 'ps': 5},
                  headers=headers, timeout=15)
    print(f"status: {r.status_code}")
    d = r.json()
    print(f"total: {d.get('paging',{}).get('total')}")
    print(f"issues: {len(d.get('issues',[]))}")
except Exception as e:
    print(f"ERROR: {e}")

# Also check if the project exists at all
try:
    r2 = httpx.get(f'{server}/api/projects/search',
                   params={'projects': component},
                   headers=headers, timeout=15)
    print(f"project search status: {r2.status_code}")
    d2 = r2.json()
    print(f"projects found: {len(d2.get('components', []))}")
    for p in d2.get('components', []):
        print(f"  - {p.get('key')}: {p.get('name')}")
except Exception as e:
    print(f"project search ERROR: {e}")
