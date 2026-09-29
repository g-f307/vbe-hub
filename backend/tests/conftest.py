import pytest

from vbe_hub.infrastructure.settings import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(_env_file=None)
