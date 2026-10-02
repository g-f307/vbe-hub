import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import async_engine_from_config

from vbe_hub.adapters.persistence.embedding_models import EmbeddingModel  # noqa: F401
from vbe_hub.adapters.persistence.models import Base
from vbe_hub.adapters.persistence.relation_models import RelationAssessmentModel  # noqa: F401
from vbe_hub.adapters.persistence.signal_models import (  # noqa: F401
    ConsolidatedSignalModel,
    SignalGroupingConflictModel,
    SignalMemberModel,
    SignalRelationLinkModel,
)
from vbe_hub.infrastructure.settings import get_settings

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_settings().sqlalchemy_database_url)
target_metadata = Base.metadata


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        pool_pre_ping=True,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    raise RuntimeError("offline migrations are not supported")

asyncio.run(run_async_migrations())
