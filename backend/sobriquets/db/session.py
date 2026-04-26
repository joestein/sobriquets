from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from sobriquets.config import Settings

_engine = None
_session_factory = None


def init_engine(settings: Settings) -> None:
    global _engine, _session_factory
    _engine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_size=5,
        max_overflow=10,
    )
    _session_factory = async_sessionmaker(
        _engine, class_=AsyncSession, expire_on_commit=False
    )


def get_engine():
    if _engine is None:
        raise RuntimeError("Database engine not initialized. Call init_engine first.")
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    if _session_factory is None:
        raise RuntimeError("Database engine not initialized. Call init_engine first.")
    return _session_factory


async def get_session() -> AsyncSession:
    factory = get_session_factory()
    async with factory() as session:
        yield session
