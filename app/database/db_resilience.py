import logging

from asyncpg.exceptions import ConnectionDoesNotExistError
from sqlalchemy.exc import DBAPIError
from sqlalchemy.exc import OperationalError as SQLAOperationalError
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

# Декоратор для безопасных транзакций с БД
retry_db_transaction = retry(
    # Повторяем только при временных сетевых ошибках или проблемах с пулом соединений
    retry=retry_if_exception_type((SQLAOperationalError, DBAPIError, ConnectionDoesNotExistError)),
    stop=stop_after_attempt(3),  # Делаем максимум 3 попытки
    wait=wait_exponential(multiplier=1, min=2, max=10),  # Ждем 2с, затем 4с...
    before_sleep=before_sleep_log(
        logger, logging.WARNING
    ),  # Логируем каждую неудачу перед повтором
    reraise=True,  # Если все попытки провалены, прокидываем ошибку наверх
)
