# Security Boundary

This repository is deliberately vulnerable to operational disruption: it exposes endpoints that create latency, errors, exceptions, CPU load, memory allocation, cache activity, and failed SQL. Run it only on an isolated training VM or private development workstation.

Before allowing network access:

- change all default passwords;
- bind services to a private interface;
- restrict ports with a host firewall or cloud security group;
- never publish PostgreSQL, Redis, Loki, Tempo, Collector, or Node Exporter to the public internet;
- place authenticated TLS termination in front of browser-facing services;
- review logs, span attributes, and metric labels for confidential data;
- disable or protect `/api/v1/simulate/*` and `/api/v1/lab/alerts` outside training;
- replace local filesystem backends with supported production storage and backup controls.

Do not report the intentionally documented simulation endpoints as vulnerabilities. Report accidental security issues privately to the repository owner and include affected version, reproduction, impact, and a proposed mitigation when possible.