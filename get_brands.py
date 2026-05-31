import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def main():
    engine = create_async_engine(
        "postgresql+asyncpg://postgres:postgres@localhost:5432/retail_intelligence",
        echo=False,
    )

    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT DISTINCT brand_name FROM brigade_transactions WHERE brand_name IS NOT NULL;"))
        brands = [r[0] for r in res.all()]
        print("Brands:", sorted(brands))
            
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
