#!/usr/bin/env bash
set -euo pipefail

# -----------------------------------------------------------------------------
# Script: scripts/init-keycloak.sh
# Purpose:
#   - Initialize Keycloak for this project without manual UI configuration.
#   - Create the target realm if it does not already exist (default: unimaas).
#   - Create or update the OIDC client used by the web application.
#   - Store the resulting realm, client_id, and client_secret in .env.
#   - Optionally create a demo user.
#
# Behavior:
#   - Idempotent: if a resource already exists, it is reused or updated.
#   - Uses the Keycloak Administration API.
#   - Designed for local development environments with self-signed TLS.
# -----------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$ROOT_DIR/.env"
TARGET_REALM_DEFAULT="unimaas"
ADMIN_REALM="master"

KEYCLOAK_BASE_URL=""
TARGET_REALM=""
CLIENT_ID=""
WEB_EXTERNAL_PORT=""
WEB_PROTOCOL=""
HOSTS_CSV=""
CLIENT_PAYLOAD=""
CLIENT_UUID=""
CLIENT_SECRET=""
ADMIN_TOKEN=""

KC_STATUS=""
KC_BODY=""

log() {
  printf '[Keycloak Init] %s\n' "$*"
}

warn() {
  printf '[Keycloak Init][WARN] %s\n' "$*" >&2
}

die() {
  printf '[Keycloak Init][ERROR] %s\n' "$*" >&2
  exit 1
}

# Minimum requirements to run the script.
ensure_requirements() {
  command -v docker >/dev/null 2>&1 || die "Docker is not installed or is not available in PATH."
  docker compose version >/dev/null 2>&1 || die "Docker Compose plugin is not available."
  command -v curl >/dev/null 2>&1 || die "'curl' was not found."
  command -v python3 >/dev/null 2>&1 || die "'python3' was not found."
  [[ -f "$ENV_FILE" ]] || die "$ENV_FILE does not exist."
}

escape_sed_replacement() {
  local value="$1"
  value="${value//\\/\\\\}"
  value="${value//&/\\&}"
  value="${value//|/\\|}"
  printf '%s' "$value"
}

# Read a variable from .env.
get_env() {
  local key="$1"
  grep -E "^${key}=" "$ENV_FILE" | head -n1 | cut -d'=' -f2-
}

# Write or update a variable in .env.
set_env() {
  local key="$1"
  local value="$2"
  local escaped
  escaped="$(escape_sed_replacement "$value")"

  if grep -qE "^${key}=" "$ENV_FILE"; then
    sed -i "s|^${key}=.*|${key}=${escaped}|" "$ENV_FILE"
  else
    printf '\n%s=%s\n' "$key" "$value" >> "$ENV_FILE"
  fi
}

prompt_yes_no() {
  local question="$1"
  local default="$2"
  local prompt answer

  if [[ "$default" == "y" ]]; then
    prompt=" [Y/n] "
  else
    prompt=" [y/N] "
  fi

  while true; do
    read -r -p "${question}${prompt}" answer || true
    answer="${answer:-}"

    case "${answer,,}" in
      "")
        [[ "$default" == "y" ]] && return 0 || return 1
        ;;
      y|yes)
        return 0
        ;;
      n|no)
        return 1
        ;;
      *)
        warn "Invalid response. Use y/n."
        ;;
    esac
  done
}

prompt_value() {
  local question="$1"
  local default="$2"
  local answer

  read -r -p "${question} [${default}]: " answer || true
  if [[ -z "${answer:-}" ]]; then
    printf '%s' "$default"
  else
    printf '%s' "$answer"
  fi
}

prompt_non_empty_secret() {
  local question="$1"
  local value

  while true; do
    read -r -s -p "$question" value || true
    printf '\n'
    if [[ -n "${value:-}" ]]; then
      printf '%s' "$value"
      return
    fi
    warn "Value cannot be empty."
  done
}

url_encode() {
  python3 - "$1" <<'PY'
import sys
import urllib.parse

print(urllib.parse.quote(sys.argv[1], safe=''))
PY
}

status_is_one_of() {
  local current="$1"
  shift
  local expected

  for expected in "$@"; do
    if [[ "$current" == "$expected" ]]; then
      return 0
    fi
  done

  return 1
}

expect_status() {
  local context="$1"
  shift

  if status_is_one_of "$KC_STATUS" "$@"; then
    return 0
  fi

  local compact_body
  compact_body="$(printf '%s' "$KC_BODY" | tr '\n' ' ' | head -c 500)"
  die "${context} -> HTTP ${KC_STATUS}. Response: ${compact_body}"
}

# Authenticated call to the Keycloak Administration API.
kc_call() {
  local method="$1"
  local path="$2"
  local data="${3:-}"
  local url response

  url="${KEYCLOAK_BASE_URL}${path}"

  if [[ -n "$data" ]]; then
    response="$(curl -k -sS --max-time 40 -X "$method" "$url" \
      -H "Authorization: Bearer ${ADMIN_TOKEN}" \
      -H "Content-Type: application/json" \
      --data "$data" \
      -w $'\n%{http_code}')"
  else
    response="$(curl -k -sS --max-time 40 -X "$method" "$url" \
      -H "Authorization: Bearer ${ADMIN_TOKEN}" \
      -w $'\n%{http_code}')"
  fi

  KC_STATUS="${response##*$'\n'}"
  KC_BODY="${response%$'\n'*}"
}

wait_for_http() {
  local name="$1"
  local url="$2"
  local insecure="$3"
  local attempts="${4:-45}"
  local delay="${5:-2}"
  local code i

  for ((i=1; i<=attempts; i++)); do
    if [[ "$insecure" == "true" ]]; then
      code="$(curl -k -s --max-time 8 -o /dev/null -w '%{http_code}' "$url" || true)"
    else
      code="$(curl -s --max-time 8 -o /dev/null -w '%{http_code}' "$url" || true)"
    fi

    case "$code" in
      200|201|204|301|302|303)
        log "${name} is available (${code})"
        return 0
        ;;
    esac

    sleep "$delay"
  done

  die "${name} did not respond correctly at ${url}."
}

# Start Keycloak if it is not already running.
ensure_keycloak_running() {
  cd "$ROOT_DIR"

  if ! docker ps --format '{{.Names}}' | grep -qx 'keycloak-dpp'; then
    log "Keycloak is not running. Starting keycloak service..."
    docker compose up -d keycloak
  fi

  local keycloak_port
  keycloak_port="$(get_env KEYCLOAK_EXTERNAL_PORT)"
  [[ -n "$keycloak_port" ]] || die "KEYCLOAK_EXTERNAL_PORT was not found in .env"

  KEYCLOAK_BASE_URL="https://localhost:${keycloak_port}"
  wait_for_http "Keycloak" "$KEYCLOAK_BASE_URL/" true 60 2
}

# Obtain admin token using KEYCLOAK_ADMIN / KEYCLOAK_ADMIN_PASSWORD from .env.
obtain_admin_token() {
  local admin_user admin_pass token_response

  admin_user="$(get_env KEYCLOAK_ADMIN)"
  admin_pass="$(get_env KEYCLOAK_ADMIN_PASSWORD)"

  [[ -n "$admin_user" ]] || die "KEYCLOAK_ADMIN is empty in .env"
  [[ -n "$admin_pass" ]] || die "KEYCLOAK_ADMIN_PASSWORD is empty in .env"

  token_response="$(curl -k -sS --max-time 25 \
    --request POST "${KEYCLOAK_BASE_URL}/realms/${ADMIN_REALM}/protocol/openid-connect/token" \
    --header 'Content-Type: application/x-www-form-urlencoded' \
    --data-urlencode 'grant_type=password' \
    --data-urlencode 'client_id=admin-cli' \
    --data-urlencode "username=${admin_user}" \
    --data-urlencode "password=${admin_pass}")"

  ADMIN_TOKEN="$(python3 - <<'PY' "$token_response"
import json
import sys

raw = sys.argv[1]

try:
    data = json.loads(raw)
except Exception:
    print("")
    raise SystemExit(0)

print(data.get("access_token", ""))
PY
)"

  if [[ -z "$ADMIN_TOKEN" ]]; then
    local err
    err="$(python3 - <<'PY' "$token_response"
import json
import sys

raw = sys.argv[1]

try:
    data = json.loads(raw)
except Exception:
    print(raw)
    raise SystemExit(0)

print(data.get("error_description") or data.get("error") or raw)
PY
)"
    die "Failed to obtain Keycloak admin token. Details: ${err}"
  fi

  log "Administration token obtained successfully."
}

collect_inputs() {
  local env_realm env_client_id current_web_port env_web_protocol env_web_host extra_hosts

  env_realm="$(get_env KEYCLOAK_REALM)"
  env_client_id="$(get_env KEYCLOAK_CLIENT_ID)"
  current_web_port="$(get_env WEB_EXTERNAL_PORT)"
  env_web_protocol="$(get_env WEB_PROTOCOL)"
  env_web_host="$(get_env WEB_INTERNAL_HOSTNAME)"

  if [[ -n "$env_realm" && "$env_realm" != "$TARGET_REALM_DEFAULT" ]]; then
    log "Current realm in .env: ${env_realm}. Recommended value: '${TARGET_REALM_DEFAULT}'."
  fi

  TARGET_REALM="$(prompt_value "Target realm to initialize" "$TARGET_REALM_DEFAULT")"
  CLIENT_ID="$(prompt_value "OIDC Client ID for the web application" "${env_client_id:-unimaas}")"
  WEB_EXTERNAL_PORT="${current_web_port:-8080}"
  WEB_PROTOCOL="${env_web_protocol:-http://}"

  extra_hosts="$(prompt_value "Extra hosts for redirect URIs (comma-separated, without protocol or port)" "")"

  # Local base hosts plus extra hosts provided by the user.
  HOSTS_CSV="$(python3 - <<'PY' "$env_web_host" "$extra_hosts"
import sys

env_web_host = sys.argv[1].strip()
raw = sys.argv[2]
hosts = ["localhost", "127.0.0.1"]
seen = set(hosts)

if env_web_host and env_web_host not in seen:
    hosts.append(env_web_host)
    seen.add(env_web_host)

for item in raw.split(","):
    host = item.strip()
    if host and host not in seen:
        hosts.append(host)
        seen.add(host)

print(",".join(hosts))
PY
)"

  CLIENT_PAYLOAD="$(python3 - <<'PY' "$CLIENT_ID" "$WEB_EXTERNAL_PORT" "$HOSTS_CSV" "$WEB_PROTOCOL"
import json
import sys

client_id = sys.argv[1]
web_port = sys.argv[2]
hosts = [h for h in sys.argv[3].split(",") if h]
web_protocol = sys.argv[4].strip() or "http://"

if not web_protocol.endswith("://"):
    web_protocol = f"{web_protocol}://"

redirect_uris = [f"{web_protocol}{host}:{web_port}/*" for host in hosts]
web_origins = [f"{web_protocol}{host}:{web_port}" for host in hosts]
post_logout = "##".join(redirect_uris)

payload = {
    "clientId": client_id,
    "name": "UniMaaS DPP Client",
    "description": "Client for DPP web app (auto-managed by scripts/init-keycloak.sh)",
    "enabled": True,
    "protocol": "openid-connect",
    "publicClient": False,
    "standardFlowEnabled": True,
    "directAccessGrantsEnabled": True,
    "serviceAccountsEnabled": False,
    "redirectUris": redirect_uris,
    "webOrigins": web_origins,
    "attributes": {
        "post.logout.redirect.uris": post_logout
    }
}

print(json.dumps(payload, separators=(",", ":")))
PY
)"
}

ensure_realm() {
  kc_call GET "/admin/realms/${TARGET_REALM}"

  if [[ "$KC_STATUS" == "404" ]]; then
    log "Realm '${TARGET_REALM}' does not exist. Creating it..."

    local realm_payload
    realm_payload="$(python3 - <<'PY' "$TARGET_REALM"
import json
import sys

realm_name = sys.argv[1]
payload = {
    "realm": realm_name,
    "enabled": True,
    "registrationAllowed": True,
    "loginWithEmailAllowed": True,
    "duplicateEmailsAllowed": False,
    "resetPasswordAllowed": True,
    "rememberMe": True
}

print(json.dumps(payload, separators=(",", ":")))
PY
)"

    kc_call POST "/admin/realms" "$realm_payload"
    expect_status "Creating realm ${TARGET_REALM}" 201
    log "Realm '${TARGET_REALM}' created."
    return
  fi

  expect_status "Checking realm ${TARGET_REALM}" 200
  log "Realm '${TARGET_REALM}' already exists. Applying recommended settings..."

  local updated_payload
  updated_payload="$(python3 - <<'PY' "$KC_BODY"
import json
import sys

realm = json.loads(sys.argv[1])
realm["enabled"] = True
realm["registrationAllowed"] = True
realm["loginWithEmailAllowed"] = True
realm["duplicateEmailsAllowed"] = False
realm["resetPasswordAllowed"] = True
realm["rememberMe"] = True

print(json.dumps(realm, separators=(",", ":")))
PY
)"

  kc_call PUT "/admin/realms/${TARGET_REALM}" "$updated_payload"
  expect_status "Updating realm configuration ${TARGET_REALM}" 204
}

get_client_uuid() {
  local encoded_client_id
  encoded_client_id="$(url_encode "$CLIENT_ID")"

  kc_call GET "/admin/realms/${TARGET_REALM}/clients?clientId=${encoded_client_id}"
  expect_status "Searching client ${CLIENT_ID}" 200

  CLIENT_UUID="$(python3 - <<'PY' "$KC_BODY"
import json
import sys

clients = json.loads(sys.argv[1])

if not clients:
    print("")
else:
    print(clients[0].get("id", ""))
PY
)"
}

ensure_client() {
  get_client_uuid

  if [[ -z "$CLIENT_UUID" ]]; then
    log "Client '${CLIENT_ID}' does not exist in realm '${TARGET_REALM}'. Creating it..."
    kc_call POST "/admin/realms/${TARGET_REALM}/clients" "$CLIENT_PAYLOAD"
    expect_status "Creating client ${CLIENT_ID}" 201

    get_client_uuid
    [[ -n "$CLIENT_UUID" ]] || die "Could not retrieve the ID of the newly created client."
  else
    log "Client '${CLIENT_ID}' already exists. Updating configuration..."
    kc_call PUT "/admin/realms/${TARGET_REALM}/clients/${CLIENT_UUID}" "$CLIENT_PAYLOAD"
    expect_status "Updating client ${CLIENT_ID}" 204
  fi

  kc_call GET "/admin/realms/${TARGET_REALM}/clients/${CLIENT_UUID}/client-secret"
  expect_status "Retrieving client secret for ${CLIENT_ID}" 200

  CLIENT_SECRET="$(python3 - <<'PY' "$KC_BODY"
import json
import sys

data = json.loads(sys.argv[1])
print(data.get("value", ""))
PY
)"

  if [[ -z "$CLIENT_SECRET" ]]; then
    warn "Could not read the current client secret. Regenerating it..."
    kc_call POST "/admin/realms/${TARGET_REALM}/clients/${CLIENT_UUID}/client-secret"
    expect_status "Regenerating client secret for ${CLIENT_ID}" 200

    CLIENT_SECRET="$(python3 - <<'PY' "$KC_BODY"
import json
import sys

data = json.loads(sys.argv[1])
print(data.get("value", ""))
PY
)"
  fi

  [[ -n "$CLIENT_SECRET" ]] || die "Could not obtain a valid client secret."
}

maybe_create_demo_user() {
  if ! prompt_yes_no "Do you want to create/update a demo user in realm '${TARGET_REALM}'?" "n"; then
    return
  fi

  local username email password encoded_username user_id user_payload pass_payload

  username="$(prompt_value "Demo username" "demo-unimaas")"
  email="$(prompt_value "Demo user email" "${username}@localhost")"
  password="$(prompt_non_empty_secret "Demo user password: ")"

  encoded_username="$(url_encode "$username")"
  kc_call GET "/admin/realms/${TARGET_REALM}/users?username=${encoded_username}"
  expect_status "Searching user ${username}" 200

  user_id="$(python3 - <<'PY' "$KC_BODY" "$username"
import json
import sys

users = json.loads(sys.argv[1])
target = sys.argv[2].lower()

for user in users:
    if user.get("username", "").lower() == target:
        print(user.get("id", ""))
        raise SystemExit(0)

print("")
PY
)"

  if [[ -z "$user_id" ]]; then
    user_payload="$(python3 - <<'PY' "$username" "$email"
import json
import sys

username = sys.argv[1]
email = sys.argv[2]

payload = {
    "username": username,
    "email": email,
    "enabled": True,
    "emailVerified": True
}

print(json.dumps(payload, separators=(",", ":")))
PY
)"

    kc_call POST "/admin/realms/${TARGET_REALM}/users" "$user_payload"
    expect_status "Creating user ${username}" 201

    kc_call GET "/admin/realms/${TARGET_REALM}/users?username=${encoded_username}"
    expect_status "Reading user ${username} again" 200

    user_id="$(python3 - <<'PY' "$KC_BODY" "$username"
import json
import sys

users = json.loads(sys.argv[1])
target = sys.argv[2].lower()

for user in users:
    if user.get("username", "").lower() == target:
        print(user.get("id", ""))
        raise SystemExit(0)

print("")
PY
)"

    [[ -n "$user_id" ]] || die "Could not retrieve the ID of the created user (${username})."
    log "User '${username}' created."
  else
    log "User '${username}' already exists. Its password will be updated."
  fi

  pass_payload="$(python3 - <<'PY' "$password"
import json
import sys

payload = {
    "type": "password",
    "value": sys.argv[1],
    "temporary": False
}

print(json.dumps(payload, separators=(",", ":")))
PY
)"

  kc_call PUT "/admin/realms/${TARGET_REALM}/users/${user_id}/reset-password" "$pass_payload"
  expect_status "Updating password for ${username}" 204

  log "Password for '${username}' updated."
}

persist_project_config() {
  # Store final configuration in .env so the web application can use this realm/client.
  set_env "KEYCLOAK_REALM" "$TARGET_REALM"
  set_env "KEYCLOAK_CLIENT_ID" "$CLIENT_ID"
  set_env "KEYCLOAK_CLIENT_SECRET" "$CLIENT_SECRET"

  log "Configuration persisted in .env:"
  log "- KEYCLOAK_REALM=${TARGET_REALM}"
  log "- KEYCLOAK_CLIENT_ID=${CLIENT_ID}"
  log "- KEYCLOAK_CLIENT_SECRET=<hidden>"
}

maybe_restart_web_service() {
  # The web application reads environment variables at startup. If .env changes, it should be recreated.
  if prompt_yes_no "Do you want to recreate the web service to apply the new realm/client secret?" "y"; then
    local web_protocol
    web_protocol="$(get_env WEB_PROTOCOL)"
    [[ -n "$web_protocol" ]] || web_protocol="http://"

    cd "$ROOT_DIR"
    docker compose up -d web
    wait_for_http "Web" "${web_protocol}localhost:$(get_env WEB_EXTERNAL_PORT)/" true 40 2
  fi
}

show_summary() {
  local keycloak_port
  keycloak_port="$(get_env KEYCLOAK_EXTERNAL_PORT)"

  local redirects
  redirects="$(python3 - <<'PY' "$HOSTS_CSV" "$WEB_EXTERNAL_PORT" "$WEB_PROTOCOL"
import sys

hosts = [h for h in sys.argv[1].split(",") if h]
port = sys.argv[2]
protocol = sys.argv[3].strip() or "http://"

if not protocol.endswith("://"):
    protocol = f"{protocol}://"

for host in hosts:
    print(f"  - {protocol}{host}:{port}/*")
PY
)"

  echo
  log "Keycloak initialization completed."
  log "Realm: ${TARGET_REALM}"
  log "Client ID: ${CLIENT_ID}"
  log "Keycloak URL: https://localhost:${keycloak_port}"
  echo "Configured redirect URIs:"
  printf '%s\n' "$redirects"
}

main() {
  cd "$ROOT_DIR"
  ensure_requirements
  ensure_keycloak_running
  collect_inputs
  obtain_admin_token
  ensure_realm
  ensure_client
  maybe_create_demo_user
  persist_project_config
  maybe_restart_web_service
  show_summary
}

main "$@"
