from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import Settings

engine = None
async_session = None


class Base(DeclarativeBase):
    pass


async def init_db(settings: Settings):
    global engine, async_session
    engine = create_async_engine(
        settings.database_url, connect_args={"check_same_thread": False}
    )
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Add selector_item column if upgrading from pre-v2 schema
        try:
            await conn.run_sync(
                lambda c: c.exec_driver_sql(
                    "ALTER TABLE sources ADD COLUMN selector_item VARCHAR(500)"
                )
            )
        except Exception:
            pass  # Column already exists

        # Add modification/deletion tracking columns
        try:
            await conn.run_sync(
                lambda c: c.exec_driver_sql(
                    "ALTER TABLE articles ADD COLUMN is_modified BOOLEAN DEFAULT 0"
                )
            )
        except Exception:
            pass
        try:
            await conn.run_sync(
                lambda c: c.exec_driver_sql(
                    "ALTER TABLE articles ADD COLUMN previous_title VARCHAR(500)"
                )
            )
        except Exception:
            pass
        try:
            await conn.run_sync(
                lambda c: c.exec_driver_sql(
                    "ALTER TABLE articles ADD COLUMN modified_at DATETIME"
                )
            )
        except Exception:
            pass
        try:
            await conn.run_sync(
                lambda c: c.exec_driver_sql(
                    "ALTER TABLE articles ADD COLUMN is_deleted BOOLEAN DEFAULT 0"
                )
            )
        except Exception:
            pass
        try:
            await conn.run_sync(
                lambda c: c.exec_driver_sql(
                    "ALTER TABLE articles ADD COLUMN deleted_at DATETIME"
                )
            )
        except Exception:
            pass


async def get_db():
    async with async_session() as session:
        yield session
