# 50 Progressive Hands-On Labs

This roadmap is the curriculum contract for the repository. Each lab adds one operational idea, preserves evidence in `lab-notes/`, and builds on prior behavior. `Lab-1.md` is fully included; later lab guides can follow the same structure without changing the platform architecture.

## Phase 1 — Know the Workload Before Monitoring It

| Lab | Title | Primary outcome |
|---:|---|---|
| 1 | Application Baseline, Persistence, and Dependency Health | Operate FastAPI, PostgreSQL, and Redis; distinguish liveness, readiness, cache degradation, and persistent state. |
| 2 | Telemetry and Metrics Before Prometheus | Read raw OpenMetrics exposition and identify families, samples, labels, counters, gauges, and histograms. |
| 3 | Designing Prometheus Instrumentation | Implement useful RED and business metrics while avoiding unsafe labels. |
| 4 | Prometheus Discovery and the Scrape Lifecycle | Start Prometheus, inspect targets, understand scrape intervals, staleness, and target health. |
| 5 | PromQL Selectors, Matchers, and Aggregation | Query series safely and control dimensionality. |
| 6 | Counter Math: `rate`, `irate`, and `increase` | Interpret counters across resets and select correct time windows. |
| 7 | Histograms, Quantiles, and Exemplars | Calculate p50/p95/p99 correctly and jump from latency observations to representative traces. |
| 8 | Recording Rules and Query Cost | Precompute stable service-level queries and validate rule output. |
| 9 | VM Monitoring with Node Exporter | Diagnose CPU, memory, disk, filesystem, and saturation signals on the host. |
| 10 | Grafana Dashboard Fundamentals | Build a truthful dashboard from requirements, not from available metrics alone. |

## Phase 2 — Visualization, Alerting, and Reliability

| Lab | Title | Primary outcome |
|---:|---|---|
| 11 | Dashboard Variables and Reuse | Create low-risk variables for route, status, instance, and environment. |
| 12 | Dashboard UX and Operational Review | Apply units, thresholds, legends, drilldowns, and evidence-oriented panel design. |
| 13 | Prometheus Alert Rule Lifecycle | Understand inactive, pending, and firing states and test `for` durations. |
| 14 | Alertmanager Routing and Grouping | Route by severity/team and observe `group_wait`, `group_interval`, and repeats. |
| 15 | Inhibition, Silences, and Maintenance | Suppress symptom noise without hiding root-cause alerts. |
| 16 | Define SLIs and SLOs | Turn user-facing behavior into availability and latency objectives. |
| 17 | Multi-Window Burn-Rate Alerting | Detect fast and slow error-budget consumption without brittle thresholds. |
| 18 | Labels and Cardinality Economics | Measure series growth and identify cardinality multipliers. |
| 19 | Metric and Target Relabeling | Normalize targets and drop unsafe telemetry before ingestion. |
| 20 | Prometheus Retention and Capacity | Estimate disk, memory, ingestion, and query costs on the VM. |

## Phase 3 — Logs and Loki

| Lab | Title | Primary outcome |
|---:|---|---|
| 21 | Structured Application Logging | Design machine-parseable JSON events with stable fields and appropriate severity. |
| 22 | Loki Architecture and OTLP Ingestion | Follow logs from the SDK through the Collector into Loki's TSDB store. |
| 23 | LogQL Selectors and Filters | Query indexed labels, line filters, and time windows efficiently. |
| 24 | JSON Parsing and Structured Metadata | Extract fields, format output, and understand indexed labels versus metadata. |
| 25 | Metrics from Logs | Convert selected log events into rates and aggregations without replacing real metrics. |
| 26 | Log-Based Alerts | Alert on high-value events while controlling noise and query cost. |
| 27 | Loki Retention and Label Design | Test retention behavior and diagnose label/cardinality mistakes. |

## Phase 4 — OpenTelemetry and Distributed Tracing

| Lab | Title | Primary outcome |
|---:|---|---|
| 28 | OpenTelemetry Signals and Resources | Explain API, SDK, semantic conventions, resources, instrumentation scopes, and OTLP. |
| 29 | Collector Receivers, Processors, and Exporters | Trace all three signal pipelines and inspect Collector self-telemetry. |
| 30 | Automatic Application Instrumentation | Compare framework, SQLAlchemy, Redis, and HTTP client spans. |
| 31 | Context Propagation | Follow W3C Trace Context across boundaries and diagnose broken parentage. |
| 32 | Custom Spans, Events, Attributes, and Status | Add business context without leaking secrets or creating cardinality hazards. |
| 33 | Tempo Search and TraceQL | Find slow, failed, and attribute-matched traces with TraceQL. |
| 34 | Trace-to-Logs Correlation | Pivot from a failing span to precisely scoped Loki logs. |
| 35 | Trace-to-Metrics and Exemplars | Pivot between RED metrics, span metrics, and representative traces. |
| 36 | Service Graphs and Virtual Nodes | Explain relationships among API, PostgreSQL, Redis, and external dependencies. |
| 37 | Head Sampling Tradeoffs | Quantify cost and diagnostic loss at multiple trace sample ratios. |
| 38 | Tail Sampling in the Collector | Preserve errors and high latency using policies while sampling ordinary traffic. |
| 39 | Collector Queues, Retries, Memory, and Backpressure | Observe exporter failure, dropped data risk, recovery, and sizing signals. |
| 40 | Correlated Incident Investigation | Use metrics, logs, and traces together without jumping randomly between tools. |

## Phase 5 — Failure Engineering and Professional Operations

| Lab | Title | Primary outcome |
|---:|---|---|
| 41 | Redis Failure and Graceful Degradation | Prove cache fallback, readiness semantics, latency impact, and recovery. |
| 42 | PostgreSQL Failure and Data-Path Impact | Separate process health from failed writes, inspect pools, and validate durable recovery. |
| 43 | Observability Backend Failure | Understand application behavior when Collector, Loki, Tempo, or Prometheus is unavailable. |
| 44 | Load, Saturation, and Bottleneck Analysis | Drive bounded traffic and distinguish utilization, saturation, latency, and errors. |
| 45 | SLO Operations Dashboard | Combine objective, budget, burn, traffic, dependencies, and deploy context. |
| 46 | Security and Exposure Review | Harden ports, credentials, telemetry content, container privileges, and administrative APIs. |
| 47 | Configuration Validation and CI Gates | Automate Python, YAML, Prometheus rules, Alertmanager, Collector, Loki, Tempo, and dashboard checks. |
| 48 | Backup, Restore, Upgrade, and Rollback | Back up named-volume data, practice restore, and use pinned-version upgrade checkpoints. |
| 49 | Translate the Workload to Minikube | Map Compose services, health checks, config, secrets, storage, and discovery to Kubernetes. |
| 50 | Capstone Game Day and Evidence-Based Postmortem | Diagnose multiple injected failures, restore service safely, and produce a professional postmortem. |

## Standard Lab Structure

Every full lab guide should contain:

1. Purpose, scope, and explicit exclusions.
2. Prerequisites and inherited system state.
3. Measurable learning objectives.
4. Current architecture and signal flow.
5. A clean starting-state check.
6. Concepts immediately paired with commands and observations.
7. Prediction checkpoints before changes or failures.
8. A controlled experiment with bounded blast radius.
9. Evidence capture from more than one layer.
10. Recovery and proof of recovery.
11. Troubleshooting paths for expected mistakes.
12. Production implications and tradeoffs.
13. Knowledge checks.
14. A lab notebook template.
15. Observable completion criteria.
16. A transition that explains why the next lab exists.

## Professional Coverage Boundary

The 50 labs provide hands-on depth for the repository's actual platform: service behavior, metrics, dashboards, alert routing, logs, traces, OpenTelemetry pipelines, cross-signal investigation, SLOs, cardinality, capacity, security review, configuration validation, recovery, upgrades, and a Compose-to-Kubernetes translation.

Some professional topics from the accompanying handbooks cannot be proven faithfully on one VM with this tool set. Continuous profiling and eBPF require an additional profiling backend; browser real-user monitoring requires a browser application; meaningful synthetic monitoring requires an independent probe location; and production high availability, multi-tenancy, regional disaster recovery, object storage, SSO, TLS, and enterprise secret management require multiple failure domains or external systems. The labs identify those boundaries rather than presenting a single-node simulation as production proof.

Use this curriculum as a practical core, then add environment-specific labs for those areas before declaring production readiness for a real organization.
