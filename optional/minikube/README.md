# Optional Minikube Workload Translation

These manifests support Lab 49. They are intentionally not prerequisites for Labs 1–48 or 50, and Docker Compose remains the canonical course environment.

The optional base deploys only FastAPI, PostgreSQL, and Redis. Observability backends remain in Compose until the Kubernetes lab explicitly asks you to translate or install them. OTLP export is disabled in this base so the application does not continuously retry a nonexistent Collector.

## Prerequisites

- A working Minikube installation.
- `kubectl`.
- At least 4 CPUs and 6 GB assigned to Minikube.

## Build the Local Application Image

From the repository root:

```bash
minikube start --cpus=4 --memory=6144
minikube image build -t observability-labs/orders-api:1.0.0 ./app
```

## Apply the Base

```bash
kubectl apply -k optional/minikube/base
kubectl -n observability-labs rollout status statefulset/postgres --timeout=180s
kubectl -n observability-labs rollout status statefulset/redis --timeout=180s
kubectl -n observability-labs rollout status deployment/orders-api --timeout=180s
```

Access the API:

```bash
kubectl -n observability-labs port-forward service/orders-api 8000:8000
```

In another terminal:

```bash
curl -fsS http://localhost:8000/health/ready | jq
```

## Remove the Optional Environment

This deletes the namespace and its PVC-backed lab data:

```bash
kubectl delete namespace observability-labs
```

Minikube itself and unrelated namespaces are not removed.

