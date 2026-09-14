SHELL := /usr/bin/env bash
.DEFAULT_GOAL := help

.PHONY: help setup config build up baseline down stop status logs verify smoke load test lint reset

help: ## Show available targets
	@awk 'BEGIN {FS = ":.*## "; printf "\nTargets:\n"} /^[a-zA-Z_-]+:.*## / {printf "  %-12s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup: ## Create .env and lab-notes directory without overwriting existing files
	@test -f .env || cp .env.example .env
	@mkdir -p lab-notes
	@echo "Setup complete. Review .env before starting Lab 1."

config: ## Render and validate the Compose model
	docker compose config --quiet

build: ## Build the FastAPI image
	docker compose build app

up: ## Start the full application and observability stack
	docker compose up -d --build

baseline: ## Start only the Lab 1 application baseline, with OTLP export disabled
	APP_OTEL_ENABLED=false docker compose up -d --build db redis app

down: ## Stop and remove containers while preserving named volumes
	docker compose down --remove-orphans

stop: ## Stop containers without removing them
	docker compose stop

status: ## Display container and health state
	docker compose ps

logs: ## Follow logs from all services
	docker compose logs --follow --tail=100

verify: ## Verify all service endpoints and telemetry paths
	./scripts/verify-stack.sh

smoke: ## Run CRUD and simulation smoke tests
	./scripts/smoke-test.sh

load: ## Generate a bounded mixed workload (DURATION and CONCURRENCY are optional)
	./scripts/generate-load.sh "$${DURATION:-120}" "$${CONCURRENCY:-4}"

test: ## Run application unit tests in a disposable container
	docker build --target test --tag observability-fastapi-labs-test ./app
	docker run --rm observability-fastapi-labs-test pytest -q tests

lint: ## Lint the application in a disposable container
	docker build --target test --tag observability-fastapi-labs-test ./app
	docker run --rm observability-fastapi-labs-test ruff check --select E,F,I,B,UP,ASYNC --line-length 100 app tests

reset: ## Interactively remove containers and all lab data volumes
	./scripts/reset-lab.sh --volumes
