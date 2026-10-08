import asyncio
from collections.abc import Callable

from fastapi import FastAPI, Response, status
from fastapi.responses import JSONResponse

from vbe_hub.api.signals import router as signals_router
from vbe_hub.api.workflow import (
    get_review_actor_id,
    get_workflow_service,
)
from vbe_hub.api.workflow import (
    router as workflow_router,
)
from vbe_hub.application.health import HealthService
from vbe_hub.application.workflow import (
    ConcurrencyConflict,
    InvalidTransition,
    WorkflowError,
    WorkflowNotFound,
    WorkflowService,
    WorkflowValidationError,
)
from vbe_hub.infrastructure.health import InfrastructureHealthService
from vbe_hub.infrastructure.settings import get_settings


def _default_health_service() -> HealthService:
    return InfrastructureHealthService(get_settings())


def create_app(
    health_service: HealthService | None = None,
    workflow_service: WorkflowService | None = None,
    review_actor_id: str | None = None,
) -> FastAPI:
    app = FastAPI(title="VBE Hub API", version="0.1.0")
    app.include_router(signals_router)
    app.include_router(workflow_router)
    if workflow_service is not None:
        app.dependency_overrides[get_workflow_service] = lambda: workflow_service
    if review_actor_id is not None:
        app.dependency_overrides[get_review_actor_id] = lambda: review_actor_id
    service_factory: Callable[[], HealthService] = (
        (lambda: health_service) if health_service is not None else _default_health_service
    )

    @app.exception_handler(WorkflowError)
    async def workflow_error_handler(_request, error: WorkflowError) -> JSONResponse:
        detail: dict[str, object] = {"code": error.code}
        response_status = status.HTTP_422_UNPROCESSABLE_ENTITY
        if isinstance(error, WorkflowNotFound):
            response_status = status.HTTP_404_NOT_FOUND
        elif isinstance(error, ConcurrencyConflict):
            response_status = status.HTTP_409_CONFLICT
            detail.update(
                expected_version=error.expected_version,
                current_version=error.current_version,
            )
        elif isinstance(error, InvalidTransition):
            response_status = status.HTTP_409_CONFLICT
            detail.update(current_state=error.current.value, requested_state=error.requested.value)
        elif not isinstance(error, WorkflowValidationError):
            response_status = status.HTTP_500_INTERNAL_SERVER_ERROR
            detail = {"code": "workflow_internal_error"}
        return JSONResponse(status_code=response_status, content={"detail": detail})

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
