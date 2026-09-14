#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "${1:-}" != "--volumes" ]]; then
  echo "Usage: $0 --volumes" >&2
  echo "This intentionally removes the lab's containers and persistent named volumes." >&2
  exit 2
fi

echo "This will permanently delete PostgreSQL, Redis, Prometheus, Grafana, Loki, Tempo, and Alertmanager lab data."
read -r -p "Type DELETE-LAB-DATA to continue: " confirmation
if [[ "${confirmation}" != "DELETE-LAB-DATA" ]]; then
  echo "Reset cancelled."
  exit 1
fi

docker compose down --volumes --remove-orphans
echo "Lab containers and named volumes were removed. This cannot be recovered unless separately backed up."

