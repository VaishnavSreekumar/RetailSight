import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.database import db_manager
from app.main import create_app


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Generates a session-scoped async event loop for running tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Configures an asynchronous test client wrapping the ASGI application factory."""
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        yield ac


@pytest.fixture(autouse=True)
def mock_database_connectivity(monkeypatch) -> None:
    """Automatically mocks database connection checks to run tests without db service dependencies."""
    monkeypatch.setattr(
        db_manager, "check_connection", AsyncMock(return_value=True)
    )
