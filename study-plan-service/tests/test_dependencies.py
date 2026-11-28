
"""
Автоматизовані тести спільних залежностей
Study Plan Service.
"""

from uuid import UUID

import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from dependencies import (
    CurrentUserId,
    Pagination,
    get_current_user_id
)

from exceptions import register_exception_handlers


# ==========================================================
# 1. ПІДГОТОВКА ТЕСТОВОГО ЗАСТОСУНКУ
# ==========================================================

@pytest.fixture
def application():
    """Створення ізольованого тестового застосунку."""

    app = FastAPI()

    register_exception_handlers(app)

    @app.get("/test-pagination")
    def test_pagination(pagination: Pagination):

        return {
            "limit": pagination.limit,
            "offset": pagination.offset
        }

    @app.get("/test-user")
    def test_user(user_id: CurrentUserId):

        return {
            "user_id": str(user_id)
        }

    return app


@pytest.fixture
def client(application):
    """Створення тестового HTTP-клієнта."""

    with TestClient(application) as test_client:
        yield test_client


# ==========================================================
# 2. ПЕРЕВІРКА ПАГІНАЦІЇ
# ==========================================================

def test_default_pagination(client):
    """Перевірка стандартних параметрів."""

    response = client.get("/test-pagination")

    assert response.status_code == 200

    assert response.json() == {
        "limit": 50,
        "offset": 0
    }


@pytest.mark.parametrize(
    "limit,offset",
    [
        (1, 0),
        (20, 40),
        (50, 100),
        (100, 0)
    ]
)
def test_valid_pagination(client, limit, offset):
    """Перевірка допустимих параметрів."""

    response = client.get(
        "/test-pagination",
        params={
            "limit": limit,
            "offset": offset
        }
    )

    assert response.status_code == 200

    assert response.json() == {
        "limit": limit,
        "offset": offset
    }


@pytest.mark.parametrize(
    "params",
    [
        {"limit": 0},
        {"limit": -1},
        {"limit": 101},
        {"limit": "invalid"},
        {"offset": -1},
        {"offset": "invalid"}
    ]
)
def test_invalid_pagination(client, params):
    """Перевірка відхилення некоректних параметрів."""

    response = client.get(
        "/test-pagination",
        params=params
    )

    assert response.status_code == 422

    assert isinstance(
        response.json()["detail"],
        list
    )


# ==========================================================
# 3. ПЕРЕВІРКА АВТЕНТИФІКАЦІЇ
# ==========================================================

@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Basic test"},
        {"Authorization": "Bearer"}
    ]
)
def test_missing_bearer_token(client, headers):
    """Перевірка відсутнього або некоректного Bearer-токена."""

    response = client.get(
        "/test-user",
        headers=headers
    )

    assert response.status_code == 401

    assert response.json() == {
        "detail": "Authentication required"
    }

    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_unverified_token_rejected(client):
    """Неперевірений токен не надає доступу."""

    response = client.get(
        "/test-user",
        headers={
            "Authorization": "Bearer unverified-test-token"
        }
    )

    assert response.status_code == 503

    assert response.json() == {
        "detail": "Authentication service unavailable"
    }


# ==========================================================
# 4. ПЕРЕВІРКА ВПРОВАДЖЕННЯ ЗАЛЕЖНОСТЕЙ
# ==========================================================

def test_current_user_dependency(application):
    """Перевірка отримання UUID через тестову залежність."""

    user_id = UUID(
        "11111111-1111-4111-8111-111111111111"
    )

    # Підміна автентифікації лише в тестовому застосунку
    application.dependency_overrides[
        get_current_user_id
    ] = lambda: user_id

    try:

        with TestClient(application) as client:

            response = client.get("/test-user")

        assert response.status_code == 200

        assert response.json() == {
            "user_id": str(user_id)
        }

    finally:

        application.dependency_overrides.clear()
