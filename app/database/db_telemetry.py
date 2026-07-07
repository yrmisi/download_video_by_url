import logging
import time
from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import Connection
from sqlalchemy.engine.interfaces import DBAPICursor, ExecutionContext
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)

SLOW_QUERY_THRESHOLD = 1.0


# Функции-обработчики выносим на уровень модуля, чтобы их можно было передать в event.remove
def before_cursor_execute(
    conn: Connection,
    cursor: DBAPICursor,
    statement: str,
    parameters: Any,
    context: ExecutionContext,
    execmany: bool,
) -> None:
    setattr(context, "_query_start_time", time.perf_counter())


def after_cursor_execute(
    conn: Connection,
    cursor: DBAPICursor,
    statement: str,
    parameters: Any,
    context: ExecutionContext,
    execmany: bool,
) -> None:
    # Безопасно достаем время начала (на случай, если дочерний поток не отработал before)
    start_time = getattr(context, "_query_start_time", None)
    if start_time is None:
        return

    total_time = time.perf_counter() - start_time
    if total_time > SLOW_QUERY_THRESHOLD:
        logger.warning(
            f"⚠️ Slow query detected ({total_time:.4f}s)!\n"
            f"Statement: {statement}\n"
            f"Parameters: {parameters}"
        )


def setup_database_telemetry(engine: AsyncEngine) -> None:
    """
    Registers slow query monitoring hooks on the given Engine.
    """

    # Для AsyncEngine нужно слушать подлежащий синхронный движок: engine.sync_engine
    event.listen(engine.sync_engine, "before_cursor_execute", before_cursor_execute)
    event.listen(engine.sync_engine, "after_cursor_execute", after_cursor_execute)
    logger.info("Database slow query telemetry initialized.")


def close_database_telemetry(engine: AsyncEngine) -> None:
    """
    Removes tracking hooks, preventing memory leaks on shutdown.
    """

    try:
        event.remove(engine.sync_engine, "before_cursor_execute", before_cursor_execute)
        event.remove(engine.sync_engine, "after_cursor_execute", after_cursor_execute)
        logger.info("Database slow query telemetry cleaned up.")
    except Exception as e:
        logger.error(f"Failed to remove database telemetry: {e}")
