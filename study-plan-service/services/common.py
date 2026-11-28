
"""
Спільні допоміжні функції бізнес-логіки Study Plan Service.

Модуль забезпечує перевірку ресурсів, прав власності,
часових інтервалів, параметрів оновлення та управління
транзакціями запису.
"""

import hashlib

from contextlib import contextmanager
from datetime import date, datetime, timezone
from typing import Any, Iterator, TypeVar
from uuid import UUID

from psycopg import Connection
from pydantic import BaseModel

from database import get_connection

from exceptions import (
    BadRequestError,
    NotFoundError
)


T = TypeVar("T")


# ==========================================================
# 1. ПЕРЕВІРКА РЕСУРСІВ ТА ПРАВ ВЛАСНОСТІ
# ==========================================================

def require_resource(
    resource: T | None,
    detail: str = "Resource not found"
) -> T:
    """Перевірка існування запитуваного ресурсу."""

    if resource is None:
        raise NotFoundError(detail)

    return resource


def require_ownership(
    resource_user_id: UUID,
    current_user_id: UUID,
    detail: str = "Resource not found"
) -> None:
    """Перевірка належності ресурсу користувачу."""

    if resource_user_id != current_user_id:
        raise NotFoundError(detail)


# ==========================================================
# 2. ОБРОБКА ЧАСТКОВОГО ОНОВЛЕННЯ
# ==========================================================

def get_update_data(
    data: BaseModel
) -> dict[str, Any]:
    """Отримання явно переданих полів PATCH-запиту."""

    update_data = data.model_dump(
        exclude_unset=True
    )

    if not update_data:
        raise BadRequestError(
            "No fields provided for update"
        )

    return update_data


# ==========================================================
# 3. РОБОТА З ДАТАМИ ТА ЧАСОМ
# ==========================================================

def validate_date_range(
    start_date: date | None,
    end_date: date | None
) -> None:
    """Перевірка коректності діапазону календарних дат."""

    if (
        start_date is not None
        and end_date is not None
        and end_date < start_date
    ):
        raise BadRequestError(
            "End date must not be earlier than start date"
        )


def to_utc(value: datetime) -> datetime:
    """Перетворення дати та часу в UTC."""

    if (
        value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise BadRequestError(
            "Datetime must contain timezone information"
        )

    return value.astimezone(timezone.utc)


def validate_datetime_range(
    start_at: datetime,
    end_at: datetime
) -> None:
    """Перевірка коректності часового інтервалу."""

    start_utc = to_utc(start_at)

    end_utc = to_utc(end_at)

    if end_utc <= start_utc:
        raise BadRequestError(
            "End time must be later than start time"
        )


# ==========================================================
# 4. СИНХРОНІЗАЦІЯ ОПЕРАЦІЙ КОРИСТУВАЧА
# ==========================================================

def get_user_lock_key(user_id: UUID) -> int:
    """Формування стабільного ключа блокування користувача."""

    source = (
        b"study_plan:user:"
        + user_id.bytes
    )

    digest = hashlib.sha256(source).digest()

    return int.from_bytes(
        digest[:8],
        byteorder="big",
        signed=True
    )


def lock_user_transaction(
    connection: Connection,
    user_id: UUID
) -> None:
    """Блокування операцій запису одного користувача."""

    if connection.autocommit:
        raise RuntimeError(
            "User lock requires an active transaction"
        )

    lock_key = get_user_lock_key(user_id)

    with connection.cursor() as cursor:

        cursor.execute(
            "SELECT pg_advisory_xact_lock(%s)",
            (lock_key,)
        )


# ==========================================================
# 5. УПРАВЛІННЯ ТРАНЗАКЦІЯМИ ЗАПИСУ
# ==========================================================

@contextmanager
def write_transaction(
    user_id: UUID
) -> Iterator[Connection]:
    """Створення транзакції запису з блокуванням користувача."""

    with get_connection() as connection:

        # Блокування отримується до виконання бізнес-операцій
        lock_user_transaction(
            connection,
            user_id
        )

        # Передавання підключення предметному сервісу
        yield connection

        # При успішному завершенні виконується COMMIT.
        # При виникненні винятку виконується ROLLBACK.
        # Підключення закривається контекстним менеджером.
