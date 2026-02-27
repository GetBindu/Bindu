import os
import pytest
from unittest.mock import AsyncMock, patch

from bindu.server.storage.factory import create_storage
from bindu.settings import app_settings


@pytest.mark.asyncio
async def test_auto_switch_to_postgres(monkeypatch):
    """Should auto-switch to postgres if DATABASE_URL is set and STORAGE_TYPE not defined."""

    monkeypatch.delenv("STORAGE_TYPE", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")

    app_settings.storage.backend = "memory"
    app_settings.storage.postgres_url = os.getenv("DATABASE_URL")

    with patch("bindu.server.storage.factory.PostgresStorage") as MockPostgres:
        instance = MockPostgres.return_value
        instance.connect = AsyncMock()

        storage = await create_storage()

        assert MockPostgres.called
        assert storage == instance