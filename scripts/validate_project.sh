#!/usr/bin/env bash

set -euo pipefail

echo "======================================"
echo "Starting application dependencies"
echo "======================================"

docker compose up --build -d

echo
echo "======================================"
echo "Container status"
echo "======================================"

docker compose ps

echo
echo "======================================"
echo "Running backend tests"
echo "======================================"

docker compose run --rm backend \
  python -m pytest -v

echo
echo "======================================"
echo "Running frontend linting"
echo "======================================"

docker compose exec -T frontend \
  npm run lint

echo
echo "======================================"
echo "Running frontend tests"
echo "======================================"

docker compose exec -T frontend \
  npm test

echo
echo "======================================"
echo "Building production frontend"
echo "======================================"

docker compose exec -T frontend \
  npm run build

echo
echo "======================================"
echo "Starting production frontend"
echo "======================================"

docker compose \
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
