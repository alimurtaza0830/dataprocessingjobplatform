#!/usr/bin/env bash
#
# Deploy the production profile with Docker Compose and roll back
# automatically if the new release does not become healthy.
#
# Steps:
#   1. Tag the currently deployed images as :previous
#   2. Build new images (running containers are not touched)
#   3. Start the new release and wait for health checks (one retry)
#   4. Run the production smoke test
#   5. On failure: restore :previous images, redeploy, re-run smoke test,
#      and exit non-zero so the deployment is reported as failed

set -euo pipefail

COMPOSE_ENV_FILE="${COMPOSE_ENV_FILE:-.env.example}"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-dataprocessingjobplatform}"
WAIT_TIMEOUT_SECONDS="${WAIT_TIMEOUT_SECONDS:-180}"
DEPLOY_ATTEMPTS="${DEPLOY_ATTEMPTS:-2}"
BASE_URL="${BASE_URL:-http://localhost:8080}"
DEPLOY_SHA="${DEPLOY_SHA:-$(git rev-parse HEAD)}"
STEP_SUMMARY="${GITHUB_STEP_SUMMARY:-/dev/null}"

export COMPOSE_PROJECT_NAME BASE_URL

COMPOSE=(
  docker compose
  --env-file "$COMPOSE_ENV_FILE"
  --profile production
)

# Services whose images are built from this repository.
BUILT_SERVICES=(
  backend-migrate
  backend
  worker
  frontend-prod
)

# Services that make up the production deployment.
DEPLOY_SERVICES=(
  database
  redis
  storage-init
  backend-migrate
  backend
  worker
  frontend-prod
)

ROLLBACK_AVAILABLE=false

log() {
  echo
  echo "======================================"
  echo "$*"
  echo "======================================"
}

summary() {
  echo "$*" >> "$STEP_SUMMARY"
}

image_name() {
  echo "${COMPOSE_PROJECT_NAME}-$1"
}

snapshot_current_images() {
  log "Saving currently deployed images as :previous"

  local service
  local missing=0

  for service in "${BUILT_SERVICES[@]}"; do
    local image
    local container_id
    local image_id=""

    image="$(image_name "$service")"

    # Use the image the deployed container runs, not whatever :latest
    # points to (an earlier failed build may have moved :latest).
    container_id="$(
      "${COMPOSE[@]}" ps --all --quiet "$service" 2> /dev/null | head -n 1
    )"

    if [[ -n "$container_id" ]]; then
      image_id="$(docker inspect --format '{{.Image}}' "$container_id")"
    fi

    if [[ -n "$image_id" ]]; then
      docker image tag "$image_id" "${image}:previous"
      echo "Saved ${image}:previous (${image_id:7:12})"
    else
      echo "No deployed container for ${service}; rollback unavailable"
      missing=1
    fi
  done

  if [[ "$missing" -eq 0 ]]; then
    ROLLBACK_AVAILABLE=true
  fi
}

restore_previous_images() {
  local service

  for service in "${BUILT_SERVICES[@]}"; do
    local image
    image="$(image_name "$service")"
    docker image tag "${image}:previous" "${image}:latest"
    echo "Restored ${image}:latest from :previous"
  done
}

start_release() {
  "${COMPOSE[@]}" up \
    --detach \
    --no-build \
    --wait \
    --wait-timeout "$WAIT_TIMEOUT_SECONDS" \
    "${DEPLOY_SERVICES[@]}"
}

start_release_with_retry() {
  local attempt

  for attempt in $(seq 1 "$DEPLOY_ATTEMPTS"); do
    echo "Deployment attempt ${attempt}/${DEPLOY_ATTEMPTS}"

    if start_release; then
      return 0
    fi

    echo "Deployment attempt ${attempt} failed"
    "${COMPOSE[@]}" ps || true
  done

  return 1
}

verify_release() {
  ./scripts/production_smoke_test.sh
}

rollback() {
  log "Deployment failed; rolling back"

  if [[ "$ROLLBACK_AVAILABLE" != true ]]; then
    echo "No previous images available; cannot roll back"
    summary "| Rollback | ❌ not possible (no previous images) |"
    return 1
  fi

  restore_previous_images

  if start_release_with_retry && verify_release; then
    echo "Rollback succeeded; previous release is serving traffic"
    summary "| Rollback | ✅ previous release restored and smoke-tested |"
    summary ""
    summary "> Database migrations are not rolled back automatically."
    return 0
  fi

  echo "Rollback failed"
  summary "| Rollback | ❌ failed — manual intervention required |"
  return 1
}

main() {
  log "Deploying ${DEPLOY_SHA}"
  docker version --format 'Docker Engine {{.Server.Version}}'
  docker compose version

  summary "## Deployment: \`${DEPLOY_SHA:0:7}\`"
  summary ""
  summary "| Step | Result |"
  summary "|---|---|"
  summary "| Docker | $(docker version --format '{{.Server.Version}}'), Compose $(docker compose version --short) |"

  snapshot_current_images

  log "Building images"
  if ! "${COMPOSE[@]}" build "${BUILT_SERVICES[@]}"; then
    summary "| Build | ❌ failed — running release untouched |"
    exit 1
  fi
  summary "| Build | ✅ |"

  log "Starting new release"
  if ! start_release_with_retry; then
    summary "| Start (healthy within ${WAIT_TIMEOUT_SECONDS}s) | ❌ |"
    rollback || true
    exit 1
  fi
  summary "| Start (healthy within ${WAIT_TIMEOUT_SECONDS}s) | ✅ |"

  log "Running production smoke test"
  if ! verify_release; then
    summary "| Smoke test | ❌ |"
    rollback || true
    exit 1
  fi
  summary "| Smoke test | ✅ |"

  log "Deployment of ${DEPLOY_SHA} succeeded"
}

main "$@"
