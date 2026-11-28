
"""
Підключення до бази даних Study Plan Service.

Модуль забезпечує створення підключень до PostgreSQL
на основі централізованої конфігурації мікросервісу.
"""

import psycopg
from psycopg import Connection

from config import get_settings


# ==========================================================
# 1. СТВОРЕННЯ ПІДКЛЮЧЕННЯ ДО POSTGRESQL
# ==========================================================

def get_connection() -> Connection:

    """Створення підключення до бази даних PostgreSQL."""

    # Отримання централізованої конфігурації
    settings = get_settings()

    # Створення підключення до бази даних
    connection = psycopg.connect(
        host=settings.db_host,
        port=settings.db_port,
        dbname=settings.db_name,
        user=settings.db_user,
        password=settings.db_password.get_secret_value()
    )

    return connection
