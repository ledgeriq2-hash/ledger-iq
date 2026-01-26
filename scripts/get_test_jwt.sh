#!/usr/bin/env bash
set -euo pipefail

print_export=0
base_url=""
email=""
password=""
tenant=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --print-export)
      print_export=1
      shift
      ;;
    --base-url)
      base_url="$2"
      shift 2
      ;;
    --email)
      email="$2"
      shift 2
      ;;
    --password)
      password="$2"
      shift 2
      ;;
    --tenant)
      tenant="$2"
      shift 2
      ;;
    --help)
      echo "Usage: source scripts/get_test_jwt.sh [--base-url URL] [--email EMAIL] [--password PASSWORD] [--tenant TENANT] [--print-export]"
      exit 0
      ;;
    *)
      echo "Unknown arg: $1" >&2
      exit 1
      ;;
  esac
 done

base_url="${base_url:-${AI_BASE_URL:-${BASE_URL:-${AI_TEST_BASE_URL:-http://127.0.0.1:8000}}}}"
base_url="${base_url%/}"

email="${email:-${LOGIN_EMAIL:-${LEDGERIQ_ADMIN_EMAIL:-}}}"
password="${password:-${LOGIN_PASSWORD:-${LEDGERIQ_ADMIN_PASSWORD:-}}}"
tenant="${tenant:-${LOGIN_TENANT:-${TENANT_ID:-${TENANT_SLUG:-}}}}"

if [[ -z "$email" || -z "$password" || -z "$tenant" ]]; then
  echo "Missing login input. Provide --email/--password/--tenant or set LOGIN_EMAIL/LOGIN_PASSWORD/LOGIN_TENANT (or LEDGERIQ_ADMIN_EMAIL/LEDGERIQ_ADMIN_PASSWORD)." >&2
  exit 1
fi

header_args=("-H" "Content-Type: application/json")
if [[ "$tenant" =~ ^[0-9a-fA-F-]{36}$ ]]; then
  header_args+=("-H" "X-Tenant-ID: $tenant")
else
  header_args+=("-H" "X-Tenant-Slug: $tenant")
fi

body=$(python - <<'PY'
import json
import sys
email = sys.argv[1]
password = sys.argv[2]
tenant = sys.argv[3]
print(json.dumps({"email": email, "password": password, "tenant": tenant}))
PY
"$email" "$password" "$tenant")

response=$(curl -sS -w "\n%{http_code}" -X POST "$base_url/api/v1/auth/login" "${header_args[@]}" -d "$body")
status="${response##*$'\n'}"
body="${response%$'\n'*}"

if [[ "$status" != "200" ]]; then
  if echo "$body" | grep -q "csrf_failed"; then
    if [[ ! "$tenant" =~ ^[0-9a-fA-F-]{36}$ ]]; then
      echo "csrf_failed detected. Provide a tenant UUID via --tenant or TENANT_ID." >&2
      exit 1
    fi
    issue_output=$(cd backend && python -m app.management.issue_test_jwt --tenant-id "$tenant" --email "$email" --print-full 2>&1) || {
      echo "issue_test_jwt failed:" >&2
      echo "$issue_output" >&2
      exit 1
    }
    token=$(echo "$issue_output" | sed -n 's/^export AI_TEST_JWT="\\(.*\\)"/\\1/p' | head -n 1)
    tenant_id=$(echo "$issue_output" | sed -n 's/^export AI_TEST_TENANT_ID="\\(.*\\)"/\\1/p' | head -n 1)
    if [[ -z "$token" ]]; then
      echo "Failed to parse AI_TEST_JWT from issue_test_jwt output." >&2
      exit 1
    fi
    export AI_TEST_JWT="$token"
    if [[ -n "$tenant_id" ]]; then
      export AI_TEST_TENANT_ID="$tenant_id"
    fi
    masked="***"
    if [[ ${#token} -gt 14 ]]; then
      masked="${token:0:8}...${token: -6}"
    fi
    echo "AI_TEST_JWT set in current shell (token=$masked)"
    if [[ -n "$tenant_id" ]]; then
      echo "AI_TEST_TENANT_ID set in current shell ($tenant_id)"
    fi
    echo "Next: run python verify_sprint16_ai_ingest.py"
    exit 0
  fi
  echo "Login failed ($status): $body" >&2
  exit 1
fi

token=$(python - <<'PY'
import json
import sys
payload = json.loads(sys.stdin.read() or "{}")
if isinstance(payload, dict):
    tokens = payload.get("tokens") or {}
    for key in ("access_token", "token", "jwt"):
        if key in payload and payload[key]:
            print(payload[key]); sys.exit(0)
    if isinstance(tokens, dict) and tokens.get("access_token"):
        print(tokens.get("access_token")); sys.exit(0)
sys.exit(1)
PY
<<<"$body")

if [[ -z "$token" ]]; then
  echo "Login succeeded but no token field found in response." >&2
  exit 1
fi

tenant_id=$(python - <<'PY'
import json
import sys
payload = json.loads(sys.stdin.read() or "{}")
if isinstance(payload, dict):
    tenant = payload.get("tenant") or {}
    if isinstance(tenant, dict) and tenant.get("id"):
        print(tenant.get("id")); sys.exit(0)
sys.exit(1)
PY
<<<"$body" || true)

masked="***"
if [[ ${#token} -gt 14 ]]; then
  masked="${token:0:8}...${token: -6}"
fi

export AI_TEST_JWT="$token"
if [[ -n "$tenant_id" ]]; then
  export AI_TEST_TENANT_ID="$tenant_id"
fi

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  echo "AI_TEST_JWT set in subprocess (token=$masked)"
  echo "Tip: source this script to persist: source scripts/get_test_jwt.sh"
  if [[ $print_export -eq 1 ]]; then
    echo "export AI_TEST_JWT='$token'"
    if [[ -n "$tenant_id" ]]; then
      echo "export AI_TEST_TENANT_ID='$tenant_id'"
    fi
  fi
else
  echo "AI_TEST_JWT set in current shell (token=$masked)"
fi

if [[ -n "$tenant_id" ]]; then
  echo "AI_TEST_TENANT_ID set in current shell ($tenant_id)"
else
  echo "AI_TEST_TENANT_ID not found in login response. Use /api/v1/dev/tenants or DB query to locate it."
fi

echo "Next: run python verify_sprint16_ai_ingest.py"
