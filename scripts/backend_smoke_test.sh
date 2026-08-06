#!/usr/bin/env bash

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
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

echo "1. Checking backend readiness..."

curl --fail --silent \
  "$BASE_URL/health/ready" \
  > /dev/null

echo "Backend is ready."

echo "2. Uploading CSV..."

UPLOAD_RESPONSE="$(
  curl --fail --silent \
    -X POST \
    "$BASE_URL/jobs/upload" \
    -F "uploaded_file=@${TEMP_CSV};filename=customers.csv"
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
echo "3. Waiting for worker processing..."

FINAL_JOB=""

for attempt in $(seq 1 30); do
  JOB_RESPONSE="$(
    curl --fail --silent \
      "$BASE_URL/jobs/$JOB_ID"
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
    echo "Processing failed:"
    printf '%s' "$JOB_RESPONSE" | python3 -m json.tool
    exit 1
  fi

  sleep 1
done

if [[ -z "$FINAL_JOB" ]]; then
  echo "Job did not complete within 30 seconds."
  exit 1
fi

echo "4. Retrieving report..."

REPORT_RESPONSE="$(
  curl --fail --silent \
    "$BASE_URL/jobs/$JOB_ID/report"
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
echo "Backend smoke test passed successfully."
