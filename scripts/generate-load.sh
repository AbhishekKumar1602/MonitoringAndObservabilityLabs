#!/usr/bin/env bash
set -Eeuo pipefail

source "$(dirname -- "${BASH_SOURCE[0]}")/lib.sh"
load_lab_environment

DURATION_SECONDS="${1:-120}"
CONCURRENCY="${2:-4}"
APP_URL="${APP_URL:-http://${LAB_HTTP_HOST}:${APP_HOST_PORT:-8000}}"

is_positive_integer() {
  [[ "$1" =~ ^[1-9][0-9]*$ ]]
}

if ! is_positive_integer "${DURATION_SECONDS}" || ((DURATION_SECONDS > 900)); then
  echo "ERROR: duration must be an integer from 1 to 900 seconds" >&2
  exit 1
fi
if ! is_positive_integer "${CONCURRENCY}" || ((CONCURRENCY > 50)); then
  echo "ERROR: concurrency must be an integer from 1 to 50" >&2
  exit 1
fi
command -v curl >/dev/null 2>&1 || { echo "ERROR: curl is required" >&2; exit 1; }

request_once() {
  local sequence="$1"
  case $((sequence % 12)) in
    0)
      curl --silent --output /dev/null "${APP_URL}/api/v1/simulate/error?status_code=500"
      ;;
    1|2)
      curl --silent --output /dev/null "${APP_URL}/api/v1/simulate/latency?seconds=0.35"
      ;;
    3)
      curl --silent --output /dev/null "${APP_URL}/api/v1/simulate/trace"
      ;;
    4)
      curl --silent --output /dev/null "${APP_URL}/api/v1/simulate/cache?key=load-$((sequence % 10))"
      ;;
    *)
      curl --silent --output /dev/null "${APP_URL}/api/v1/orders?limit=20"
      ;;
  esac
}

echo "Generating load for ${DURATION_SECONDS}s with concurrency ${CONCURRENCY}."
deadline=$((SECONDS + DURATION_SECONDS))
sequence=0
while ((SECONDS < deadline)); do
  for ((worker = 0; worker < CONCURRENCY; worker += 1)); do
    request_once "${sequence}" &
    sequence=$((sequence + 1))
  done
  wait
done

echo "Load generation complete: ${sequence} requests attempted."
