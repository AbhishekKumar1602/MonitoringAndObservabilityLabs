import httpx
import pytest
from app.main import app


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/", "/health", "/health/live"])
async def test_public_baseline_endpoints(path: str) -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(path)

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_metrics_endpoint_exposes_openmetrics() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/metrics")

    assert response.status_code == 200
    assert "application/openmetrics-text" in response.headers["content-type"]
    assert "obslab_http_requests_total" in response.text


@pytest.mark.asyncio
async def test_zero_latency_simulation_is_safe_and_observable() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/simulate/latency", params={"seconds": 0})

    assert response.status_code == 200
    assert response.json() == {"simulation": "latency", "slept_seconds": 0.0}
