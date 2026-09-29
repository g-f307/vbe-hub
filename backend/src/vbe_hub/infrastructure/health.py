import asyncio

import asyncpg
from redis.asyncio import Redis
from redis.exceptions import RedisError

from vbe_hub.application.health import DependencyHealth, HealthService
from vbe_hub.infrastructure.settings import Settings


class InfrastructureHealthService(HealthService):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def check_postgres(self) -> DependencyHealth:
        connection: asyncpg.Connection | None = None
        try:
            async with asyncio.timeout(self._settings.dependency_timeout_seconds):
                connection = await asyncpg.connect(
                    self._settings.database_url.get_secret_value(),
                    command_timeout=self._settings.dependency_timeout_seconds,
                )
                extension = await connection.fetchval(
                    "SELECT extname FROM pg_extension WHERE extname = 'vector'"
                )
                if extension != "vector":
                    return DependencyHealth(status="unhealthy", detail="vector extension missing")
        except TimeoutError:
            return DependencyHealth(status="unhealthy", detail="timeout")
        except (asyncpg.PostgresError, OSError):
            return DependencyHealth(status="unhealthy", detail="connection failed")
        finally:
            if connection is not None:
                await connection.close()

        return DependencyHealth(status="healthy")

    async def check_redis(self) -> DependencyHealth:
        client = Redis.from_url(
            self._settings.redis_url.get_secret_value(),
            socket_connect_timeout=self._settings.dependency_timeout_seconds,
            socket_timeout=self._settings.dependency_timeout_seconds,
        )
        try:
            async with asyncio.timeout(self._settings.dependency_timeout_seconds):
                if not await client.ping():
                    return DependencyHealth(status="unhealthy", detail="unexpected response")
        except TimeoutError:
            return DependencyHealth(status="unhealthy", detail="timeout")
        except (OSError, RedisError):
            return DependencyHealth(status="unhealthy", detail="connection failed")
        finally:
            await client.aclose()

        return DependencyHealth(status="healthy")
