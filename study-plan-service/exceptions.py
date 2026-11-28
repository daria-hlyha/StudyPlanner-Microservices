
"""
Централізована обробка винятків Study Plan Service.

Модуль містить власні класи програмних винятків
та механізм їх перетворення на HTTP-відповіді.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


# ==========================================================
# 1. НАЛАШТУВАННЯ ЖУРНАЛЮВАННЯ
# ==========================================================

logger = logging.getLogger(__name__)


# ==========================================================
# 2. БАЗОВИЙ КЛАС ПРОГРАМНИХ ВИНЯТКІВ
# ==========================================================

class ApplicationError(Exception):
    """Базовий клас винятків мікросервісу."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "Internal server error"

    def __init__(self, detail: str | None = None):

        self.detail = (
            detail if detail is not None
            else self.default_detail
        )

        super().__init__(self.detail)


# ==========================================================
# 3. ПРЕДМЕТНІ ПРОГРАМНІ ВИНЯТКИ
# ==========================================================

class BadRequestError(ApplicationError):
    """Некоректна операція."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Bad request"


class UnauthorizedError(ApplicationError):
    """Помилка автентифікації користувача."""

    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "Authentication required"


class ForbiddenError(ApplicationError):
    """Недостатньо прав для виконання операції."""

    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "Access forbidden"


class NotFoundError(ApplicationError):
    """Запитуваний ресурс не знайдено."""

    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Resource not found"


class ConflictError(ApplicationError):
    """Конфлікт даних або порушення бізнес-правил."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "Resource conflict"


class ServiceUnavailableError(ApplicationError):
    """Залежний програмний компонент недоступний."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Service unavailable"


# ==========================================================
# 4. ЦЕНТРАЛІЗОВАНІ ОБРОБНИКИ ВИНЯТКІВ
# ==========================================================

async def application_error_handler(
    request: Request,
    exc: ApplicationError
) -> JSONResponse:
    """Перетворення програмного винятку на HTTP-відповідь."""

    headers = None

    # Обов'язковий заголовок для Bearer-автентифікації
    if exc.status_code == status.HTTP_401_UNAUTHORIZED:

        headers = {
            "WWW-Authenticate": "Bearer"
        }

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail
        },
        headers=headers
    )


async def unexpected_error_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """Обробка неочікуваних внутрішніх помилок."""

    # Запис типу помилки без її конфіденційного вмісту
    logger.error(
        "Unexpected application error: %s",
        type(exc).__name__
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error"
        }
    )


# ==========================================================
# 5. РЕЄСТРАЦІЯ ОБРОБНИКІВ У FASTAPI
# ==========================================================

def register_exception_handlers(application: FastAPI) -> None:
    """Реєстрація централізованих обробників винятків."""

    application.add_exception_handler(
        ApplicationError,
        application_error_handler
    )

    application.add_exception_handler(
        Exception,
        unexpected_error_handler
    )
