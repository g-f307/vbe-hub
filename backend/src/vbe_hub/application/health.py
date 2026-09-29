from dataclasses import asdict, dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class DependencyHealth:
    status: Literal["healthy", "unhealthy"]
    detail: str | None = None

    def as_dict(self) -> dict[str, str]:
        return {key: value for key, value in asdict(self).items() if value is not None}


class HealthService:
    async def check_postgres(self) -> DependencyHealth:
        raise NotImplementedError

    async def check_redis(self) -> DependencyHealth:
        raise NotImplementedError
