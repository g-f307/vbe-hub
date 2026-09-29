import asyncpg
import pytest
from redis.asyncio import Redis

from vbe_hub.infrastructure.settings import Settings


@pytest.mark.integration
async def test_postgres_has_vector_extension(settings: Settings) -> None:
    connection = await asyncpg.connect(settings.database_url.get_secret_value())
    try:
        extension = await connection.fetchval(
            "SELECT extname FROM pg_extension WHERE extname = 'vector'"
        )
    finally:
        await connection.close()

    assert extension == "vector"


@pytest.mark.integration
async def test_redis_accepts_connections(settings: Settings) -> None:
    client = Redis.from_url(settings.redis_url.get_secret_value())
    try:
        response = await client.ping()
    finally:
        await client.aclose()

    assert response is True
