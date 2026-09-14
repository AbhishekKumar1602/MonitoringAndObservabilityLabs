from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="APP_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    name: str = "Observable Orders API"
    version: str = "1.0.0"
    environment: str = "lab"
    log_level: str = "INFO"
    build_sha: str = "development"

    database_url: str = "postgresql+asyncpg://orders_app:orders_app_lab_password@db:5432/orders"
    database_pool_size: int = Field(default=5, ge=1, le=50)
    database_max_overflow: int = Field(default=10, ge=0, le=100)
    database_connect_timeout_seconds: float = Field(default=2.0, ge=0.5, le=30.0)
    database_command_timeout_seconds: float = Field(default=5.0, ge=1.0, le=60.0)

    redis_url: str = "redis://redis:6379/0"
    cache_ttl_seconds: int = Field(default=300, ge=1, le=3600)

    otel_enabled: bool = True
    otel_service_name: str = "orders-api"
    otel_exporter_otlp_endpoint: str = "http://otel-collector:4317"
    otel_exporter_otlp_insecure: bool = True
    otel_trace_sample_ratio: float = Field(default=1.0, ge=0.0, le=1.0)
    otel_metric_export_interval_ms: int = Field(default=10_000, ge=1_000, le=300_000)

    simulation_max_latency_seconds: float = Field(default=15.0, ge=0.1, le=60.0)
    simulation_max_cpu_seconds: float = Field(default=10.0, ge=0.1, le=30.0)
    simulation_max_memory_mb: int = Field(default=128, ge=1, le=512)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
