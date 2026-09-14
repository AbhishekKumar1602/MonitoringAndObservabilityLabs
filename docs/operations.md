# Operations Reference

## Runtime Modes

| Mode | Command | Services | Intended use |
|---|---|---|---|
| Baseline | `make baseline` | PostgreSQL, Redis, FastAPI | Lab 1; OTLP disabled |
| Selected | `docker compose up -d <services>` | Explicit subset plus dependencies | Progressive labs |
| Full | `make up` | Entire Compose model | Integrated labs and final verification |

## Telemetry Paths

| Signal | Producer | Transport | Collector/backend | Consumer |
|---|---|---|---|---|
| Native metrics | FastAPI Prometheus client | Prometheus scrape `/metrics` | Prometheus | Grafana, rules |
| OTel metrics | FastAPI OTel SDK | OTLP/gRPC 4317 | Collector → Prometheus exporter 8889 | Prometheus, Grafana |
| Traces | Automatic + custom instrumentation | OTLP/gRPC 4317 | Collector → Tempo 4317 | Grafana Explore |
| Logs | Python logging + OTel LoggingHandler | OTLP/gRPC 4317 | Collector → Loki native `/otlp` | Grafana Explore |
| Host metrics | Node Exporter | Prometheus scrape 9100 | Prometheus | Grafana, rules |
| Alerts | Prometheus rules | Alertmanager API | Alertmanager | UI and local webhook |

JSON stdout remains available through `docker compose logs app` even if the Collector or Loki is unavailable. That is an intentional independent diagnostic path.

## Health Semantics

- `/health/live` proves the Python process can answer HTTP. It does not probe dependencies.
- `/health/ready` probes PostgreSQL and Redis concurrently. Any failed dependency returns HTTP 503.
- Redis is a performance dependency: CRUD reads can fall back to PostgreSQL, but readiness still reports the degraded state so operators do not mistake it for normal operation.
- Compose dependency conditions affect startup ordering only. They do not continuously restart or gate a dependent service after startup.
- `scripts/verify-stack.sh` tests externally visible readiness and end-to-end signal paths; container health alone cannot prove those paths.

## Persistent Data

List the named volumes:

```bash
docker volume ls --filter name=obs-lab
```

`docker compose down` preserves them. `scripts/reset-lab.sh --volumes` requires explicit confirmation and permanently deletes them.

For a simple course checkpoint, stop writers and archive volumes using your organization's approved backup method. A filesystem copy of a live PostgreSQL data directory is not a valid logical database backup. Use `pg_dump`/`pg_restore` for database exercises and test every restore.

## Failure-Domain Order

When a request fails, investigate in this order and record evidence before changing state:

1. Client request, status, response body, request ID, and timestamp.
2. Application liveness and readiness.
3. `docker compose ps` and service-specific container logs.
4. PostgreSQL and Redis direct health.
5. Prometheus target health and relevant RED metrics.
6. Trace search around the failure time.
7. Loki logs filtered by service, trace ID, or request ID.
8. Collector exporter failures, queue pressure, refused spans, and dropped data.
9. Backend readiness and VM resource saturation.

Restart only after evidence identifies the failing layer. A broad restart destroys transient clues and may create a false recovery.

## Configuration Reloads

Prometheus starts with `--web.enable-lifecycle`. Validate rules and configuration before reloading:

```bash
docker compose exec prometheus promtool check config /etc/prometheus/prometheus.yml
docker compose exec prometheus promtool check rules /etc/prometheus/rules/*.yml
curl -fsS -X POST http://localhost:9090/-/reload
```

Alertmanager configuration can be validated inside its container:

```bash
docker compose exec alertmanager amtool check-config /etc/alertmanager/alertmanager.yml
```

Restart Collector, Loki, Tempo, or Grafana after changing their mounted configuration unless the relevant lab explicitly introduces a safe reload mechanism.

## Capacity Guardrails

- Prometheus retention is limited by both 15 days and 8 GB; whichever is reached first wins.
- Loki and Tempo retain seven days in their configurations, but a full disk can fail earlier.
- Docker's `json-file` logs rotate at three files of 10 MB per container.
- App simulation endpoints enforce strict duration/allocation bounds; the load script caps duration at 15 minutes and concurrency at 50.
- These are training defaults, not capacity promises. Monitor disk usage before and during heavy labs.

