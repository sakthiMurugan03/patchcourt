#!/usr/bin/env bash
# PatchCourt SonarQube baseline demo.
#
# Stands up a self-contained SonarQube (embedded DB), waits until it is UP,
# provisions an admin access token, runs the community scanner over this repo,
# then prints the baseline summary. Requires Docker (docker compose v2+).
#
# Env overrides: SONAR_URL, SONAR_TOKEN, SONAR_COMPONENT, PR_URL
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${REPO_DIR}/.venv/bin/python"
[[ -x "${PYTHON}" ]] || PYTHON="${REPO_DIR}/.venv/Scripts/python.exe"
SERVER="${SONAR_URL:-http://localhost:9000}"
COMPONENT="${SONAR_COMPONENT:-patchcourt}"
PR_URL="${PR_URL:-https://github.com/octocat/Hello-World/pull/1}"
TOKEN_FILE="${REPO_DIR}/.sonar-token"

# The scanner runs inside a container, so 'localhost' must point at the host.
SCAN_HOST="${SONAR_SCANNER_HOST:-host.docker.internal}"
SCAN_SERVER="${SERVER}"
if [[ "${SCAN_SERVER}" == *localhost* || "${SCAN_SERVER}" == *127.0.0.1* ]]; then
  SCAN_SERVER="${SCAN_SERVER//localhost/${SCAN_HOST}}"
  SCAN_SERVER="${SCAN_SERVER//127.0.0.1/${SCAN_HOST}}"
fi

echo "==> PatchCourt SonarQube baseline demo"
echo "    server    : ${SERVER}"
echo "    component : ${COMPONENT}"
echo "    pr        : ${PR_URL}"

echo
echo "==> Starting standalone SonarQube (embedded database)…"
docker compose -f "${REPO_DIR}/docker-compose.sonar.yml" up -d --wait --wait-timeout 300 \
  || docker compose -f "${REPO_DIR}/docker-compose.sonar.yml" up -d

echo "==> Waiting for SonarQube to be UP at ${SERVER} …"
for _ in $(seq 1 60); do
  if curl -fsS "${SERVER}/api/system/status" 2>/dev/null | grep -q '"status":"UP"'; then
    break
  fi
  sleep 5
done
curl -fsS "${SERVER}/api/system/status"
echo

if [[ -z "${SONAR_TOKEN:-}" && -f "${TOKEN_FILE}" && -s "${TOKEN_FILE}" ]]; then
  SONAR_TOKEN="$(cat "${TOKEN_FILE}")"
fi
if [[ -z "${SONAR_TOKEN:-}" ]]; then
  echo "==> Creating admin access token (default admin/admin on fresh installs)…"
  # USER_TOKEN, not GLOBAL_ANALYSIS_TOKEN: the latter can push a scan but (as
  # of SonarQube's current versioning) can no longer browse issues/measures/
  # quality-gate, which the dashboard's Live tab and the baseline command need
  # from this same token.
  SONAR_TOKEN="$(curl -fsS -u admin:admin -X POST "${SERVER}/api/user_tokens/generate" \
      -d 'name=patchcourt-baseline' -d 'type=USER_TOKEN' \
      | "${PYTHON}" -c 'import sys, json; print(json.load(sys.stdin)["token"])')"
  echo "${SONAR_TOKEN}" > "${TOKEN_FILE}"
  chmod 600 "${TOKEN_FILE}"
fi

echo "==> Running community scanner over the repo (python analysis)…"
# MSYS_NO_PATHCONV scoped to just this call: git-bash's automatic POSIX->Windows
# path rewriting mangles the "-v src:dst" bind-mount spec (colliding with the
# drive-letter colon), which silently mounts an empty/wrong directory instead
# of erroring — but the same rewriting is needed elsewhere (e.g. `docker compose
# -f <path>`), so it must not be set for the whole script.
MSYS_NO_PATHCONV=1 docker run --rm \
  -v "${REPO_DIR}:/usr/src" \
  -e SONAR_HOST_URL="${SCAN_SERVER}" \
  -e SONAR_TOKEN="${SONAR_TOKEN}" \
  -e SONAR_SCANNER_OPTS="-Dsonar.projectKey=${COMPONENT} -Dsonar.projectName=${COMPONENT} -Dsonar.sources=. -Dsonar.python.version=3.12 -Dsonar.exclusions=dashboard/**,.venv/**,.sandbox/**,.scannerwork/**,reports/**,docs/**" \
  sonarsource/sonar-scanner-cli:11

echo
echo "==> Waiting for SonarQube to finish processing the analysis report…"
# The scanner upload returns as soon as the report is queued — SonarQube then
# processes it asynchronously (Compute Engine). Querying issues before that
# finishes silently returns 0, even on a real scan of real files.
for _ in $(seq 1 60); do
  ce_status="$(curl -fsS -u "${SONAR_TOKEN}:" "${SERVER}/api/ce/component?component=${COMPONENT}" 2>/dev/null \
    | "${PYTHON}" -c 'import sys, json; d=json.load(sys.stdin); c=d.get("current"); q=d.get("queue",[]); print("PENDING" if q else (c.get("status") if c else "NONE"))' 2>/dev/null || echo "NONE")"
  [[ "${ce_status}" == "SUCCESS" || "${ce_status}" == "FAILED" || "${ce_status}" == "CANCELED" ]] && break
  sleep 5
done
echo "    analysis processing status: ${ce_status:-unknown}"

echo
echo "==> Generating baseline report (compares SonarQube issues against PR files)…"
cd "${REPO_DIR}"
SONAR_URL="${SERVER}" SONAR_TOKEN="${SONAR_TOKEN}" SONAR_COMPONENT="${COMPONENT}" \
  "${PYTHON}" -m patchcourt baseline "${PR_URL}"

echo
echo "==> Done. Report files under ${REPO_DIR}/reports/ (token cached at ${TOKEN_FILE})."