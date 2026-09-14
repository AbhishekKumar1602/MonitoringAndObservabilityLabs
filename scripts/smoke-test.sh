#!/usr/bin/env bash
set -Eeuo pipefail

source "$(dirname -- "${BASH_SOURCE[0]}")/lib.sh"
load_lab_environment

APP_URL="${APP_URL:-http://${LAB_HTTP_HOST}:${APP_HOST_PORT:-8000}}"

require_command() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: required command '$1' was not found" >&2
    exit 1
  }
}

require_command curl
require_command jq

echo "Checking liveness and readiness..."
curl --fail --silent --show-error "${APP_URL}/health/live" | jq -e '.status == "alive"' >/dev/null
curl --fail --silent --show-error "${APP_URL}/health/ready" | jq -e '.status == "ready"' >/dev/null

echo "Creating an order..."
created="$({
  curl --fail --silent --show-error \
    --request POST \
    --header 'content-type: application/json' \
    --data '{"customer_name":"Smoke Test","product":"Observability Workbook","quantity":2,"unit_price":"24.50"}' \
    "${APP_URL}/api/v1/orders"
})"
order_id="$(jq -er '.id' <<<"${created}")"

echo "Reading order ${order_id} twice to exercise cache miss and hit..."
curl --fail --silent --show-error "${APP_URL}/api/v1/orders/${order_id}" | jq -e ".id == ${order_id}" >/dev/null
curl --fail --silent --show-error "${APP_URL}/api/v1/orders/${order_id}" | jq -e ".id == ${order_id}" >/dev/null

echo "Updating order ${order_id}..."
curl --fail --silent --show-error \
  --request PUT \
  --header 'content-type: application/json' \
  --data '{"status":"paid"}' \
  "${APP_URL}/api/v1/orders/${order_id}" | jq -e '.status == "paid"' >/dev/null

echo "Creating a controlled latency span..."
curl --fail --silent --show-error "${APP_URL}/api/v1/simulate/latency?seconds=0.1" | jq -e '.simulation == "latency"' >/dev/null

echo "Creating a nested checkout trace..."
curl --fail --silent --show-error "${APP_URL}/api/v1/simulate/trace" | jq -e '.status == "checkout_complete"' >/dev/null

echo "Verifying Prometheus exposition..."
curl --fail --silent --show-error "${APP_URL}/metrics" | grep -q '^obslab_http_requests_total'

echo "Deleting order ${order_id}..."
delete_status="$(curl --silent --output /dev/null --write-out '%{http_code}' --request DELETE "${APP_URL}/api/v1/orders/${order_id}")"
test "${delete_status}" = "204"

echo "Smoke test passed."
