from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings

async_engine = create_async_engine(
    url=settings.db.url_sqla_async,
    echo=settings.db.sqla.echo,
    pool_pre_ping=settings.db.sqla.pool_pre_ping,
    pool_size=settings.db.sqla.pool_size,
    max_overflow=settings.db.sqla.max_overflow,
    pool_timeout=settings.db.sqla.pool_timeout,
    pool_recycle=settings.db.sqla.pool_recycle,
)

session_pool = async_sessionmaker(
    async_engine,
    autoflush=settings.db.poll.autoflush,
    expire_on_commit=settings.db.poll.expire_on_commit,
)
