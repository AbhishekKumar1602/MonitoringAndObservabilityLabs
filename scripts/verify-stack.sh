#!/usr/bin/env bash
set -Eeuo pipefail

source "$(dirname -- "${BASH_SOURCE[0]}")/lib.sh"
load_lab_environment

APP_URL="${APP_URL:-http://${LAB_HTTP_HOST}:${APP_HOST_PORT:-8000}}"
PROMETHEUS_URL="${PROMETHEUS_URL:-http://${LAB_HTTP_HOST}:${PROMETHEUS_HOST_PORT:-9090}}"
ALERTMANAGER_URL="${ALERTMANAGER_URL:-http://${LAB_HTTP_HOST}:${ALERTMANAGER_HOST_PORT:-9093}}"
GRAFANA_URL="${GRAFANA_URL:-http://${LAB_HTTP_HOST}:${GRAFANA_HOST_PORT:-3000}}"
LOKI_URL="${LOKI_URL:-http://127.0.0.1:${LOKI_HOST_PORT:-3100}}"
TEMPO_URL="${TEMPO_URL:-http://127.0.0.1:${TEMPO_HOST_PORT:-3200}}"
OTEL_INTERNAL_URL="${OTEL_INTERNAL_URL:-http://127.0.0.1:${OTEL_INTERNAL_METRICS_HOST_PORT:-8888}}"
OTEL_EXPORT_URL="${OTEL_EXPORT_URL:-http://127.0.0.1:${OTEL_EXPORTED_METRICS_HOST_PORT:-8889}}"
MAX_ATTEMPTS="${MAX_ATTEMPTS:-30}"

require_command() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: required command '$1' was not found" >&2
    exit 1
  }
}

wait_for_url() {
  local label="$1"
  local url="$2"
  local attempt
  for ((attempt = 1; attempt <= MAX_ATTEMPTS; attempt += 1)); do
    if curl --fail --silent --show-error --max-time 3 "${url}" >/dev/null 2>&1; then
      printf 'PASS  %s\n' "${label}"
      return 0
    fi
    sleep 2
  done
  printf 'FAIL  %s (%s)\n' "${label}" "${url}" >&2
  return 1
}

require_command curl
require_command jq

echo "Waiting for service endpoints..."
wait_for_url "FastAPI liveness" "${APP_URL}/health/live"
wait_for_url "FastAPI readiness" "${APP_URL}/health/ready"
wait_for_url "Prometheus readiness" "${PROMETHEUS_URL}/-/ready"
wait_for_url "Alertmanager readiness" "${ALERTMANAGER_URL}/-/ready"
wait_for_url "Grafana health" "${GRAFANA_URL}/api/health"
wait_for_url "Loki readiness" "${LOKI_URL}/ready"
wait_for_url "Tempo readiness" "${TEMPO_URL}/ready"
wait_for_url "Collector internal metrics" "${OTEL_INTERNAL_URL}/metrics"
wait_for_url "Collector application metrics exporter" "${OTEL_EXPORT_URL}/metrics"

echo "Running application smoke test..."
APP_URL="${APP_URL}" "$(dirname "$0")/smoke-test.sh"

echo "Waiting for Prometheus to scrape the required jobs..."
sleep 20
targets_json="$(curl --fail --silent --show-error "${PROMETHEUS_URL}/api/v1/targets?state=active")"
for job in orders-api otel-collector otel-application-metrics node-exporter; do
  if jq -e --arg job "${job}" '[.data.activeTargets[] | select(.labels.job == $job and .health == "up")] | length > 0' <<<"${targets_json}" >/dev/null; then
    printf 'PASS  Prometheus target %s\n' "${job}"
  else
    printf 'FAIL  Prometheus target %s is not up\n' "${job}" >&2
    exit 1
  fi
done

datasources_json="$(curl --fail --silent --show-error --user "${GRAFANA_ADMIN_USER:-admin}:${GRAFANA_ADMIN_PASSWORD:-admin_lab_password}" "${GRAFANA_URL}/api/datasources")"
for datasource in Prometheus Loki Tempo Alertmanager; do
  jq -e --arg name "${datasource}" 'any(.[]; .name == $name)' <<<"${datasources_json}" >/dev/null || {
    echo "FAIL  Grafana datasource ${datasource} is missing" >&2
    exit 1
  }
  printf 'PASS  Grafana datasource %s\n' "${datasource}"
done

echo "Waiting for OTLP batches to flush..."
sleep 12
curl --fail --silent --show-error --get \
  --data-urlencode 'query={service_name="orders-api"}' \
  --data-urlencode 'limit=1' \
  "${LOKI_URL}/loki/api/v1/query_range" | jq -e '.status == "success"' >/dev/null
echo "PASS  Loki query API"

curl --fail --silent --show-error "${TEMPO_URL}/api/search?limit=1" | jq -e 'has("traces")' >/dev/null
echo "PASS  Tempo search API"

echo "Full stack verification passed."
