#!/usr/bin/env bash

# Shared, side-effect-free helpers for lab scripts. The caller enables strict
# shell options before sourcing this file.

load_lab_environment() {
  local script_directory repository_root
  script_directory="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
  repository_root="$(cd -- "${script_directory}/.." && pwd)"

  if [[ -f "${repository_root}/.env" ]]; then
    set -a
    # shellcheck disable=SC1091 -- the learner-owned file has a resolved path
    source "${repository_root}/.env"
    set +a
  fi

  LAB_HTTP_HOST="${LAB_HTTP_HOST:-${BIND_ADDRESS:-127.0.0.1}}"
  if [[ "${LAB_HTTP_HOST}" == "0.0.0.0" || "${LAB_HTTP_HOST}" == "::" ]]; then
    LAB_HTTP_HOST=127.0.0.1
  fi
}
