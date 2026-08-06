#!/usr/bin/env bash

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080}"
TEMP_CSV="$(mktemp --suffix=.csv)"

cleanup() {
  rm -f "$TEMP_CSV"
}

trap cleanup EXIT

cat > "$TEMP_CSV" <<'CSV'
id,name,email,age
1,Adam,adam@example.com,35
2,Sarah,sarah@example.com,29
3,John,,42
2,Sarah,sarah@example.com,29
CSV

echo "1. Waiting for the production application..."

for attempt in $(seq 1 45); do
  frontend_ready=false
  backend_ready=false

  if curl --fail --silent \
    "$BASE_URL/health" \
    > /dev/null 2>&1; then
    frontend_ready=true
  fi

  if curl --fail --silent \
    "$BASE_URL/api/health/ready" \
    > /dev/null 2>&1; then
    backend_ready=true
  fi

  if [[ "$frontend_ready" == true &&
        "$backend_ready" == true ]]; then
    echo "Production application is ready."
    break
  fi

  if [[ "$attempt" -eq 45 ]]; then
    echo "Production application did not become ready."
    exit 1
  fi

  sleep 1
done

echo "2. Verifying the React application..."

FRONTEND_HTML="$(
  curl --fail --silent "$BASE_URL/"
)"

if ! printf '%s' "$FRONTEND_HTML" |
  grep --quiet --ignore-case "<html"; then
  echo "The frontend did not return an HTML document."
  exit 1
fi

echo "React frontend is available."

echo "3. Uploading a CSV through Nginx..."

UPLOAD_RESPONSE="$(
  curl --fail --silent \
    --request POST \
    "$BASE_URL/api/jobs/upload" \
    --form \
    "uploaded_file=@${TEMP_CSV};filename=customers.csv"
)"

JOB_ID="$(
  printf '%s' "$UPLOAD_RESPONSE" |
    python3 -c '
import json
import sys

response = json.load(sys.stdin)
print(response["id"])
'
)"

echo "Created job: $JOB_ID"

echo "4. Waiting for background processing..."

FINAL_JOB=""

for attempt in $(seq 1 30); do
  JOB_RESPONSE="$(
    curl --fail --silent \
      "$BASE_URL/api/jobs/$JOB_ID"
  )"

  JOB_STATUS="$(
    printf '%s' "$JOB_RESPONSE" |
      python3 -c '
import json
import sys

response = json.load(sys.stdin)
print(response["status"])
'
  )"

  echo "Attempt $attempt: $JOB_STATUS"

  if [[ "$JOB_STATUS" == "completed" ]]; then
    FINAL_JOB="$JOB_RESPONSE"
    break
  fi

  if [[ "$JOB_STATUS" == "failed" ]]; then
    echo "The processing job failed:"
    printf '%s' "$JOB_RESPONSE" |
      python3 -m json.tool
    exit 1
  fi

  sleep 1
done

if [[ -z "$FINAL_JOB" ]]; then
  echo "The job did not complete within 30 seconds."
  exit 1
fi

echo "5. Retrieving and validating the report..."

REPORT_RESPONSE="$(
  curl --fail --silent \
    "$BASE_URL/api/jobs/$JOB_ID/report"
)"

printf '%s' "$REPORT_RESPONSE" |
  python3 -c '
import json
import sys

response = json.load(sys.stdin)
report = response["report"]

assert response["status"] == "completed"
assert report["row_count"] == 4
assert report["column_count"] == 4
assert report["total_missing_values"] == 1
assert report["duplicate_rows"] == 1

print(json.dumps(response, indent=2))
'

echo
echo "Production smoke test passed successfully."
