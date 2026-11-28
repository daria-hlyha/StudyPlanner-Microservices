
"""
Автоматизовані тести централізованої обробки
винятків Study Plan Service.
"""

import logging

import pytest

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from exceptions import (
    ApplicationError,
    BadRequestError,
    UnauthorizedError,
    ForbiddenError,
    NotFoundError,
    ConflictError,
    ServiceUnavailableError,
    register_exception_handlers
)


# ==========================================================
# 1. ТЕСТОВІ ДАНІ
# ==========================================================

ERROR_CASES = [
    (BadRequestError, 400, "Bad request"),
    (UnauthorizedError, 401, "Authentication required"),
    (ForbiddenError, 403, "Access forbidden"),
    (NotFoundError, 404, "Resource not found"),
    (ConflictError, 409, "Resource conflict"),
    (ServiceUnavailableError, 503, "Service unavailable")
]


# ==========================================================
# 2. ПЕРЕВІРКА КЛАСІВ ВИНЯТКІВ
# ==========================================================

@pytest.mark.parametrize(
    "error_class,status_code,detail",
    ERROR_CASES
)
def test_application_errors(
    error_class,
    status_code,
    detail
):
    """Перевірка стандартних характеристик винятків."""

    error = error_class()

    assert isinstance(error, ApplicationError)
    assert isinstance(error, Exception)

    assert error.status_code == status_code
    assert error.detail == detail
    assert str(error) == detail


@pytest.mark.parametrize(
    "error_class,status_code,detail",
    ERROR_CASES
)
def test_custom_error_messages(
    error_class,
    status_code,
    detail
):
    """Перевірка власних повідомлень винятків."""

    error = error_class("Custom error message")

    assert error.status_code == status_code

    assert error.detail == "Custom error message"

    assert str(error) == "Custom error message"


# ==========================================================
# 3. ПЕРЕВІРКА HTTP-ВІДПОВІДЕЙ
# ==========================================================

@pytest.mark.parametrize(
    "error_class,status_code,detail",
    ERROR_CASES
)
def test_application_error_responses(
    error_class,
    status_code,
    detail
):
    """Перевірка централізованих HTTP-відповідей."""

    application = FastAPI()

    register_exception_handlers(application)

    @application.get("/test-error")
    def test_route():
        raise error_class()

    with TestClient(application) as client:

        response = client.get("/test-error")

    assert response.status_code == status_code

    assert response.json() == {
        "detail": detail
    }

    # Заголовок Bearer додається лише для HTTP 401
    if status_code == 401:

        assert response.headers["WWW-Authenticate"] == "Bearer"

    else:

        assert "WWW-Authenticate" not in response.headers


def test_custom_error_response():
    """Перевірка власного повідомлення HTTP-помилки."""

    application = FastAPI()

    register_exception_handlers(application)

    @application.get("/test-error")
    def test_route():
        raise NotFoundError("Study plan not found")

    with TestClient(application) as client:

        response = client.get("/test-error")

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Study plan not found"
    }


# ==========================================================
# 4. ПЕРЕВІРКА НЕОЧІКУВАНИХ ПОМИЛОК
# ==========================================================

def test_unexpected_error_response(caplog):
    """Перевірка HTTP 500 та приховування деталей."""

    application = FastAPI()

    register_exception_handlers(application)

    @application.get("/test-error")
    def test_route():
        raise RuntimeError("private_test_error")

    with caplog.at_level(
        logging.ERROR,
        logger="exceptions"
    ):

        with TestClient(
            application,
            raise_server_exceptions=False
        ) as client:

            response = client.get("/test-error")

    assert response.status_code == 500

    assert response.json() == {
        "detail": "Internal server error"
    }

    assert "private_test_error" not in response.text

    assert "RuntimeError" in caplog.text

    assert "private_test_error" not in caplog.text


# ==========================================================
# 5. СУМІСНІСТЬ ЗІ СТАНДАРТНИМИ ПОМИЛКАМИ FASTAPI
# ==========================================================

def test_request_validation_error():
    """Збереження стандартної структури HTTP 422."""

    application = FastAPI()

    register_exception_handlers(application)

    @application.get("/test-validation")
    def test_route(value: int):

        return {
            "value": value
        }

    with TestClient(application) as client:

        response = client.get(
            "/test-validation",
            params={
                "value": "invalid"
            }
        )

    assert response.status_code == 422

    assert isinstance(
        response.json()["detail"],
        list
    )

    assert any(
        error["loc"] == ["query", "value"]
        for error in response.json()["detail"]
    )


def test_standard_http_exception():
    """Збереження стандартних HTTPException FastAPI."""

    application = FastAPI()

    register_exception_handlers(application)

    @application.get("/test-error")
    def test_route():

        raise HTTPException(
            status_code=418,
            detail="Standard HTTP error"
        )

    with TestClient(application) as client:

        response = client.get("/test-error")

    assert response.status_code == 418

    assert response.json() == {
        "detail": "Standard HTTP error"
    }


def test_unknown_route():
    """Перевірка стандартної відповіді для відсутнього маршруту."""

    application = FastAPI()

    register_exception_handlers(application)

    with TestClient(application) as client:

        response = client.get("/unknown-route")

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Not Found"
    }


# ==========================================================
# 6. ПЕРЕВІРКА РЕЄСТРАЦІЇ ОБРОБНИКІВ
# ==========================================================

def test_exception_handler_registration():
    """Перевірка підключення централізованих обробників."""

    application = FastAPI()

    register_exception_handlers(application)

    assert ApplicationError in application.exception_handlers

    assert Exception in application.exception_handlers
