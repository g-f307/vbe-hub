from fastapi.testclient import TestClient

from vbe_hub.api.app import create_app
from vbe_hub.application.health import DependencyHealth, HealthService


class StubHealthService(HealthService):
    def __init__(self, postgres: DependencyHealth, redis: DependencyHealth) -> None:
        self._postgres = postgres
        self._redis = redis

    async def check_postgres(self) -> DependencyHealth:
        return self._postgres

    async def check_redis(self) -> DependencyHealth:
        return self._redis


def test_liveness_reports_the_process_as_alive() -> None:
    client = TestClient(create_app())

    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_readiness_reports_all_dependencies_as_healthy() -> None:
    health_service = StubHealthService(
        postgres=DependencyHealth(status="healthy"),
        redis=DependencyHealth(status="healthy"),
    )
    client = TestClient(create_app(health_service=health_service))

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "dependencies": {
            "postgres": {"status": "healthy"},
            "redis": {"status": "healthy"},
        },
    }


def test_readiness_is_unavailable_when_postgres_is_down() -> None:
    health_service = StubHealthService(
        postgres=DependencyHealth(status="unhealthy", detail="connection failed"),
        redis=DependencyHealth(status="healthy"),
    )
    client = TestClient(create_app(health_service=health_service))

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.json()["dependencies"]["postgres"] == {
        "status": "unhealthy",
        "detail": "connection failed",
    }


def test_readiness_exposes_redis_failure_without_hiding_postgres_state() -> None:
    health_service = StubHealthService(
        postgres=DependencyHealth(status="healthy"),
        redis=DependencyHealth(status="unhealthy", detail="timeout"),
    )
    client = TestClient(create_app(health_service=health_service))

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["dependencies"] == {
        "postgres": {"status": "healthy"},
        "redis": {"status": "unhealthy", "detail": "timeout"},
    }
