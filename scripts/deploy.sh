#!/usr/bin/env bash
set -euo pipefail

# -----------------------------------------------------------------------------
# Script: scripts/deploy.sh
# Purpose:
#   - Start the full DPP stack interactively.
#   - Detect port conflicts with other projects.
#   - Automatically adjust .env when needed.
#   - Validate basic endpoints when deployment finishes.
# -----------------------------------------------------------------------------

# Directory of this script and repository root.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$ROOT_DIR/.env"
DEFAULT_KEYCLOAK_VERSION="25.0.6"

# External port variables that this script can check/fix.
EXTERNAL_PORT_KEYS=(
  "MONGO_EXTERNAL_PORT"
  "ORION_EXTERNAL_PORT"
  "KEYCLOAK_EXTERNAL_PORT"
  "WEB_EXTERNAL_PORT"
)

# Containers belonging to this stack, used to avoid conflicts with other projects.
OWN_CONTAINER_NAMES=(
  "mongo-db"
  "orion-ld"
  "keycloak-dpp"
  "web"
)

log() {
  printf '[DPP] %s\n' "$*"
}

warn() {
  printf '[DPP][WARN] %s\n' "$*" >&2
}

die() {
  printf '[DPP][ERROR] %s\n' "$*" >&2
  exit 1
}

ensure_requirements() {
  # Minimum dependencies required to operate Docker and check ports/endpoints.
  command -v docker >/dev/null 2>&1 || die "Docker is not installed or is not available in PATH."
  docker compose version >/dev/null 2>&1 || die "Docker Compose plugin is not available. Use 'docker compose'."
  command -v ss >/dev/null 2>&1 || die "'ss' was not found and is required to check ports."
  command -v curl >/dev/null 2>&1 || die "'curl' was not found."
  [[ -f "$ENV_FILE" ]] || die "$ENV_FILE does not exist."
}

escape_sed_replacement() {
  local value="$1"
  value="${value//\\/\\\\}"
  value="${value//&/\\&}"
  value="${value//|/\\|}"
  printf '%s' "$value"
}

get_env() {
  local key="$1"
  grep -E "^${key}=" "$ENV_FILE" | head -n1 | cut -d'=' -f2-
}

set_env() {
  # Update an existing key in .env, or add it if it does not exist.
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

is_valid_port() {
  local port="$1"
  [[ "$port" =~ ^[0-9]+$ ]] || return 1
  (( port >= 1 && port <= 65535 ))
}

port_is_listening() {
  local port="$1"
  ss -ltn | awk -v p=":$port" '$4 ~ p"$" {found=1} END {exit !found}'
}

port_owners() {
  local port="$1"
  docker ps --format '{{.Names}}\t{{.Ports}}' | awk -v p="$port" '$0 ~ ("0.0.0.0:" p "->") || $0 ~ ("\\[::\\]:" p "->") {print $1}'
}

is_own_container() {
  local name="$1"
  local own

  for own in "${OWN_CONTAINER_NAMES[@]}"; do
    [[ "$name" == "$own" ]] && return 0
  done

  return 1
}

port_conflict_with_other_projects() {
  local port="$1"
  local owners owner

  owners="$(port_owners "$port" || true)"
  if [[ -n "$owners" ]]; then
    while IFS= read -r owner; do
      [[ -z "$owner" ]] && continue
      if ! is_own_container "$owner"; then
        return 0
      fi
    done <<< "$owners"

    return 1
  fi

  if port_is_listening "$port"; then
    return 0
  fi

  return 1
}

port_in_use_anywhere() {
  local port="$1"
  local owners

  owners="$(port_owners "$port" || true)"
  [[ -n "$owners" ]] && return 0

  if port_is_listening "$port"; then
    return 0
  fi

  return 1
}

find_free_port() {
  local start="$1"
  local candidate="$start"

  while port_in_use_anywhere "$candidate"; do
    ((candidate++))
  done

  printf '%s' "$candidate"
}

configure_optional_values() {
  if ! prompt_yes_no "Do you want to review the configuration before starting?" "n"; then
    return
  fi

  local key current candidate

  for key in "${EXTERNAL_PORT_KEYS[@]}"; do
    current="$(get_env "$key")"

    while true; do
      candidate="$(prompt_value "Host port for ${key}" "$current")"

      if ! is_valid_port "$candidate"; then
        warn "${candidate} is not a valid port."
        continue
      fi

      if [[ "$candidate" != "$current" ]] && port_in_use_anywhere "$candidate"; then
        warn "Port ${candidate} is already in use."
        continue
      fi

      set_env "$key" "$candidate"
      break
    done
  done

  local kc_admin kc_version kc_password

  kc_admin="$(get_env KEYCLOAK_ADMIN)"
  kc_admin="$(prompt_value "Keycloak admin user (KEYCLOAK_ADMIN)" "$kc_admin")"
  set_env "KEYCLOAK_ADMIN" "$kc_admin"

  read -r -s -p "Keycloak admin password (empty to keep current value): " kc_password || true
  printf '\n'
  if [[ -n "${kc_password:-}" ]]; then
    set_env "KEYCLOAK_ADMIN_PASSWORD" "$kc_password"
  fi

  kc_version="$(get_env KEYCLOAK_VERSION)"
  kc_version="$(prompt_value "Keycloak version" "$kc_version")"
  set_env "KEYCLOAK_VERSION" "$kc_version"
}

auto_resolve_port_conflicts() {
  # If a port is used by another project/process, suggest a free one.
  local key current suggested owners custom

  for key in "${EXTERNAL_PORT_KEYS[@]}"; do
    current="$(get_env "$key")"

    if ! is_valid_port "$current"; then
      warn "${key}=${current} is not valid."

      while true; do
        custom="$(prompt_value "New value for ${key}" "1027")"

        if is_valid_port "$custom" && ! port_in_use_anywhere "$custom"; then
          set_env "$key" "$custom"
          current="$custom"
          break
        fi

        warn "Invalid value or port already in use."
      done
    fi

    if port_conflict_with_other_projects "$current"; then
      owners="$(port_owners "$current" || true)"

      if [[ -n "$owners" ]]; then
        warn "${key} uses ${current}, which is occupied by other containers: ${owners//$'\n'/, }"
      else
        warn "${key} uses ${current}, which is occupied by another local process."
      fi

      suggested="$(find_free_port "$((current + 1))")"

      if prompt_yes_no "Do you want to change ${key} to ${suggested}?" "y"; then
        set_env "$key" "$suggested"
        log "${key} updated to ${suggested}."
      else
        while true; do
          custom="$(prompt_value "Enter a free port for ${key}" "$suggested")"

          if ! is_valid_port "$custom"; then
            warn "${custom} is not valid."
            continue
          fi

          if port_in_use_anywhere "$custom"; then
            warn "${custom} is still occupied."
            continue
          fi

          set_env "$key" "$custom"
          log "${key} updated to ${custom}."
          break
        done
      fi
    fi
  done
}

ensure_keycloak_version_works() {
  # Check whether the configured Keycloak version starts on this machine.
  # If it fails, offer a fallback to a known compatible version.
  local version fallback

  version="$(get_env KEYCLOAK_VERSION)"

  log "Checking local compatibility for Keycloak ${version}..."
  if docker run --rm "quay.io/keycloak/keycloak:${version}" --version >/dev/null 2>&1; then
    log "Keycloak ${version} is compatible with this host."
    return
  fi

  warn "Keycloak ${version} does not start correctly on this host."
  fallback="$DEFAULT_KEYCLOAK_VERSION"

  if prompt_yes_no "Change KEYCLOAK_VERSION to ${fallback}?" "y"; then
    set_env "KEYCLOAK_VERSION" "$fallback"
    log "KEYCLOAK_VERSION updated to ${fallback}."
  else
    warn "Keeping the current version. If startup fails, change KEYCLOAK_VERSION manually."
  fi
}

wait_for_http() {
  # Wait for HTTP/HTTPS availability to provide clear feedback to the user.
  local name="$1"
  local url="$2"
  local insecure="$3"
  local attempts="${4:-30}"
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

  warn "${name} did not respond correctly at ${url}."
  return 1
}

keycloak_needs_local_access() {
  local keycloak_port body

  keycloak_port="$(get_env KEYCLOAK_EXTERNAL_PORT)"
  body="$(curl -k -s --max-time 10 "https://localhost:${keycloak_port}/" || true)"
  grep -qi "Local access required" <<< "$body"
}

reset_keycloak_data_for_bootstrap() {
  # Fix the "Local access required" case by clearing only the Keycloak volume.
  local volume_name

  volume_name="$(docker inspect keycloak-dpp --format '{{range .Mounts}}{{if eq .Destination "/opt/keycloak/data"}}{{.Name}}{{end}}{{end}}' 2>/dev/null || true)"

  if [[ -z "$volume_name" ]]; then
    die "Could not locate the Keycloak volume to reset it automatically."
  fi

  warn "The following Keycloak data volume will be deleted: ${volume_name}"

  docker compose stop keycloak >/dev/null 2>&1 || true
  docker rm -f keycloak-dpp >/dev/null 2>&1 || true
  docker volume rm "$volume_name" >/dev/null 2>&1 || die "Could not delete ${volume_name}."

  docker compose up -d keycloak
  wait_for_http "Keycloak" "https://localhost:$(get_env KEYCLOAK_EXTERNAL_PORT)/" true 45 2 || true
}

show_summary() {
  # Final summary with operational URLs.
  local web_port orion_port keycloak_port

  web_port="$(get_env WEB_EXTERNAL_PORT)"
  orion_port="$(get_env ORION_EXTERNAL_PORT)"
  keycloak_port="$(get_env KEYCLOAK_EXTERNAL_PORT)"

  echo
  log "Services are running."
  log "Web:      https://localhost:${web_port}"
  log "Orion-LD: http://localhost:${orion_port}/version"
  log "Keycloak: https://localhost:${keycloak_port}"
  echo

  docker compose ps
}

main() {
  # Main interactive deployment flow.
  cd "$ROOT_DIR"
  ensure_requirements

  configure_optional_values
  auto_resolve_port_conflicts
  ensure_keycloak_version_works

  log "Starting stack with docker compose..."
  docker compose up -d --build

  wait_for_http "Web" "https://localhost:$(get_env WEB_EXTERNAL_PORT)/" true 40 2 || true
  wait_for_http "Orion-LD" "http://localhost:$(get_env ORION_EXTERNAL_PORT)/version" false 40 2 || true
  wait_for_http "Keycloak" "https://localhost:$(get_env KEYCLOAK_EXTERNAL_PORT)/" true 45 2 || true

  if keycloak_needs_local_access; then
    warn "Keycloak shows 'Local access required'."

    if prompt_yes_no "Do you want to reset ONLY Keycloak data to create the admin user automatically?" "y"; then
      reset_keycloak_data_for_bootstrap

      if keycloak_needs_local_access; then
        warn "The 'Local access required' message is still shown. Check KEYCLOAK_ADMIN and KEYCLOAK_ADMIN_PASSWORD in .env."
      else
        log "Keycloak no longer shows 'Local access required'."
      fi
    fi
  fi

  show_summary
}

main "$@"