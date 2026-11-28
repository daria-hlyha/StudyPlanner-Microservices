
"""
Основний FastAPI-застосунок Study Plan Service.

Модуль забезпечує створення та налаштування застосунку,
управління життєвим циклом, реєстрацію REST API,
обробку винятків та моніторинг.
"""

import logging

from contextlib import asynccontextmanager

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from config import get_settings
from database import get_connection
from rabbitmq import get_rabbitmq_connection

from exceptions import (
    ServiceUnavailableError,
    register_exception_handlers
)

from logging_config import configure_logging
from schemas.common import ErrorResponse


logger = logging.getLogger(__name__)


# ==========================================================
# 1. ЖИТТЄВИЙ ЦИКЛ ЗАСТОСУНКУ
# ==========================================================

@asynccontextmanager
async def lifespan(application: FastAPI):
    """Управління запуском та завершенням роботи застосунку."""

    logger.info(
        "%s started",
        application.title
    )

    try:

        yield

    finally:

        logger.info(
            "%s stopped",
            application.title
        )


# ==========================================================
# 2. СЛУЖБОВІ МАРШРУТИ REST API
# ==========================================================

def home():
    """Перевірка доступності Study Plan Service."""

    return {
        "message": "Study Plan Service is running"
    }


def check_database():
    """Перевірка підключення до PostgreSQL."""

    try:

        with get_connection() as connection:

            with connection.cursor() as cursor:

                cursor.execute(
                    "SELECT current_user, "
                    "current_database(), current_schema()"
                )

                result = cursor.fetchone()

        return {
            "status": "connected",
            "user": result[0],
            "database": result[1],
            "current_schema": result[2]
        }

    except Exception as exc:

        logger.warning(
            "Database connection check failed: %s",
            type(exc).__name__
        )

        raise ServiceUnavailableError(
            "Database connection error"
        ) from None


def check_rabbitmq():
    """Перевірка підключення до RabbitMQ."""

    try:

        connection = get_rabbitmq_connection()

        connection.close()

        return {
            "status": "connected"
        }

    except Exception as exc:

        logger.warning(
            "RabbitMQ connection check failed: %s",
            type(exc).__name__
        )

        raise ServiceUnavailableError(
            "RabbitMQ connection error"
        ) from None


# ==========================================================
# 3. СТВОРЕННЯ FASTAPI-ЗАСТОСУНКУ
# ==========================================================

def create_app() -> FastAPI:
    """Створення та налаштування FastAPI-застосунку."""

    # Отримання та перевірка централізованої конфігурації
    settings = get_settings()

    # Створення FastAPI-застосунку
    application = FastAPI(
        title=settings.app_name,
        lifespan=lifespan
    )

    # Реєстрація централізованих обробників винятків
    register_exception_handlers(application)

    # Документування службових помилок HTTP 503
    unavailable_response = {
        503: {
            "model": ErrorResponse,
            "description": "Service unavailable"
        }
    }

    # Реєстрація службових маршрутів
    application.get(
        "/",
        tags=["Infrastructure"]
    )(home)

    application.get(
        "/db-check",
        tags=["Infrastructure"],
        responses=unavailable_response
    )(check_database)

    application.get(
        "/rabbitmq-check",
        tags=["Infrastructure"],
        responses=unavailable_response
    )(check_rabbitmq)

    # Тут підключатимуться предметні маршрутизатори

    # Підключення моніторингу Prometheus
    Instrumentator().instrument(application).expose(application)

    return application


# ==========================================================
# 4. ІНІЦІАЛІЗАЦІЯ ЗАСТОСУНКУ
# ==========================================================

configure_logging()

app = create_app()
