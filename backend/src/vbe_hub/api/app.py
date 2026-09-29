import asyncio
from collections.abc import Callable

from fastapi import FastAPI, Response, status

from vbe_hub.application.health import HealthService
from vbe_hub.infrastructure.health import InfrastructureHealthService
from vbe_hub.infrastructure.settings import get_settings


def _default_health_service() -> HealthService:
    return InfrastructureHealthService(get_settings())


def create_app(health_service: HealthService | None = None) -> FastAPI:
    app = FastAPI(title="VBE Hub API", version="0.1.0")
    service_factory: Callable[[], HealthService] = (
        (lambda: health_service) if health_service is not None else _default_health_service
    )

    @app.get("/health/live", tags=["health"])
    async def liveness() -> dict[str, str]:
        return {"status": "alive"}

    @app.get("/health/ready", tags=["health"])
    async def readiness(response: Response) -> dict[str, object]:
        service = service_factory()
        postgres, redis = await asyncio.gather(
            service.check_postgres(),
            service.check_redis(),
        )
        ready = postgres.status == "healthy" and redis.status == "healthy"
        if not ready:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

        return {
            "status": "ready" if ready else "not_ready",
            "dependencies": {
                "postgres": postgres.as_dict(),
                "redis": redis.as_dict(),
            },
        }

    return app


app = create_app()
