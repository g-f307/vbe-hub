import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from vbe_hub.infrastructure.settings import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(_env_file=None)


@pytest.fixture
async def db_session(settings: Settings):
    engine = create_async_engine(settings.sqlalchemy_database_url)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        session_factory = async_sessionmaker(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        async with session_factory() as session:
            yield session
        await transaction.rollback()
    await engine.dispose()
