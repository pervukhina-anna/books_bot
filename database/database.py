from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from config_data.config import DB_URL
from .models import Base


engine = create_async_engine(DB_URL, echo=True,)
async_sessionmaker = async_sessionmaker(engine, expire_on_commit=False)


async def connect_to_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return async_sessionmaker


async def close_database(session):
    await session.close()
