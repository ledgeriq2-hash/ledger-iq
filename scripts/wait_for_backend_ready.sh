#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
MAX_WAIT_SECONDS="${MAX_WAIT_SECONDS:-120}"
SLEEP_SECONDS="${SLEEP_SECONDS:-2}"
CHECK_DOCKER_HEALTH="${CHECK_DOCKER_HEALTH:-0}"
SERVICE_NAME="${SERVICE_NAME:-backend}"

log() {
  echo "[wait_for_backend_ready] $*"
}

start_epoch="$(date +%s)"

if [[ "${CHECK_DOCKER_HEALTH}" == "1" ]]; then
  log "Waiting for docker health status (${SERVICE_NAME})"
  while true; do
    container_id="$(docker compose ps -q "${SERVICE_NAME}" 2>/dev/null || true)"
    if [[ -n "${container_id}" ]]; then
      health_status="$(docker inspect -f '{{.State.Health.Status}}' "${container_id}" 2>/dev/null || echo "")"
      if [[ "${health_status}" == "healthy" ]]; then
        log "Container health: healthy"
        break
      fi
      if [[ "${health_status}" == "unhealthy" ]]; then
        log "Container health: unhealthy (waiting)"
      else
        log "Container health: ${health_status:-unknown} (waiting)"
      fi
    else
      log "Container not found (waiting)"
    fi

    elapsed="$(( $(date +%s) - start_epoch ))"
    if [[ "${elapsed}" -ge "${MAX_WAIT_SECONDS}" ]]; then
      log "Timed out waiting for docker health after ${elapsed}s"
      exit 1
    fi
    sleep "${SLEEP_SECONDS}"
  done
fi

log "Waiting for ${BASE_URL}/healthz and ${BASE_URL}/readyz"
while true; do
  health_code="$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/healthz" || true)"
  ready_code="$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/readyz" || true)"

  if [[ "${health_code}" == "200" && "${ready_code}" == "200" ]]; then
    log "Backend ready (healthz=${health_code}, readyz=${ready_code})"
    exit 0
  fi

  elapsed="$(( $(date +%s) - start_epoch ))"
  if [[ "${elapsed}" -ge "${MAX_WAIT_SECONDS}" ]]; then
    log "Timed out after ${elapsed}s (healthz=${health_code}, readyz=${ready_code})"
    exit 1
  fi

  log "Not ready yet (healthz=${health_code}, readyz=${ready_code}); retrying in ${SLEEP_SECONDS}s"
  sleep "${SLEEP_SECONDS}"
done
