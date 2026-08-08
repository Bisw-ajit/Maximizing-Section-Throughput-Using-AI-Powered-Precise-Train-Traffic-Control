from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from .config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    from ..models.models import (  # noqa: F401 - ensure models are registered
        Train, Node, Section, SectionOccupancy, Conflict,
        Recommendation, Scenario, SimulationRun, UserPreference
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
