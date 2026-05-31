import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

import pytest
from httpx import ASGITransport, AsyncClient

from app.database import db_manager, get_db
from app.models.base import Base
from app.models.brigade_transaction import BrigadeTransaction
import pandas as pd

from app.main import create_app

# ---------------------------------------------------------------------------
# SQLite dialect shims
# ---------------------------------------------------------------------------
# The production models use PostgreSQL-specific JSONB and UUID column types.
# SQLite (used for in-memory test databases) does not know these types.
# We patch the SQLite type compiler here — before any table-creation call —
# so that JSONB maps to JSON and PG UUID maps to VARCHAR(36).
# This does NOT touch any production model or schema code.
# ---------------------------------------------------------------------------
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler  # noqa: E402
from sqlalchemy.dialects.postgresql import UUID as PG_UUID_TYPE  # noqa: E402


def _sqlite_visit_JSONB(self, type_, **kw):
    """Render PostgreSQL JSONB as standard JSON on SQLite."""
    return "JSON"


def _sqlite_visit_UUID(self, type_, **kw):
    """Render PostgreSQL UUID as VARCHAR(36) on SQLite."""
    return "VARCHAR(36)"


# Register shims only if not already registered (idempotent)
if not hasattr(SQLiteTypeCompiler, "visit_JSONB"):
    SQLiteTypeCompiler.visit_JSONB = _sqlite_visit_JSONB

if not hasattr(SQLiteTypeCompiler, "visit_UUID"):
    SQLiteTypeCompiler.visit_UUID = _sqlite_visit_UUID
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Generates a session-scoped async event loop for running tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def client(test_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Configures an asynchronous test client wrapping the ASGI application factory."""
    app = create_app()
    app.dependency_overrides[get_db] = lambda: test_db
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

@pytest.fixture(scope="session")
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Fixture to create a temporary in-memory async SQLite database for a test session.
    """
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Load test data from CSV into the in-memory database
    csv_path = "Brigade_Bangalore_10_April_26 (1)bc6219c (1).csv"
    df = pd.read_csv(csv_path)
    df.columns = [
        'order_id', 'coupon_code', 'offer_name', 'discount_code',
        'invoice_number', 'invoice_type', 'order_date', 'order_time',
        'return_id', 'store_id', 'store_name', 'city', 'customer_name',
        'customer_number', 'sku', 'product_id', 'ean', 'product_name',
        'brand_name', 'dep_name', 'sub_category', 'brand_type', 'tax',
        'hsn_code', 'salesperson_id', 'employee_code', 'salesperson_name',
        'qty', 'gmv', 'nmv', 'coupon_amount', 'item_promotion',
        'amt_without_gwp', 'total_amount', 'pb_eb_sale', 'week_assigned',
        'tax_m', 'taxable_amt', 'tax_amt'
    ]
    import uuid
    from datetime import datetime
    df['order_date'] = pd.to_datetime(df['order_date']).dt.date
    df['order_time'] = pd.to_datetime(df['order_time']).dt.time
    df['id'] = [str(uuid.uuid4()) for _ in range(len(df))]
    df['created_at'] = datetime.now()
    df['updated_at'] = datetime.now()

    async with engine.connect() as conn:
        def insert_data(sync_conn):
            df.to_sql(name=BrigadeTransaction.__tablename__, con=sync_conn, if_exists="append", index=False)
        await conn.run_sync(insert_data)


    SessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)
    async with SessionLocal() as db:
        yield db
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
