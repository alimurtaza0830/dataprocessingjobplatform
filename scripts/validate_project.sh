#!/usr/bin/env bash

set -euo pipefail

COMPOSE_ENV_FILE="${COMPOSE_ENV_FILE:-.env.example}"
COMPOSE=(docker compose --env-file "$COMPOSE_ENV_FILE")

echo "======================================"
echo "Starting application dependencies"
echo "======================================"

"${COMPOSE[@]}" up --build -d

echo
echo "======================================"
echo "Container status"
echo "======================================"

"${COMPOSE[@]}" ps

echo
echo "======================================"
echo "Running backend tests"
echo "======================================"

"${COMPOSE[@]}" --profile test run --rm backend-test \
  python -m pytest -v

echo
echo "======================================"
echo "Running frontend linting"
echo "======================================"

"${COMPOSE[@]}" exec -T frontend \
  npm run lint

echo
echo "======================================"
echo "Running frontend tests"
echo "======================================"

"${COMPOSE[@]}" exec -T frontend \
  npm test

echo
echo "======================================"
echo "Building production frontend"
echo "======================================"

"${COMPOSE[@]}" exec -T frontend \
  npm run build

echo
echo "======================================"
echo "Starting production frontend"
echo "======================================"

"${COMPOSE[@]}" \
  --profile production \
  up --build -d frontend-prod

echo
echo "======================================"
echo "Running production smoke test"
echo "======================================"

./scripts/production_smoke_test.sh

echo
echo "======================================"
echo "All project checks passed"
echo "======================================"
