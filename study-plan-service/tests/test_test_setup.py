
"""
Перевірка спільної основи автоматизованого тестування
Study Plan Service.
"""

from uuid import UUID

from fastapi import FastAPI

from dependencies import (
    CurrentUserId,
    get_current_user_id
)


# ==========================================================
# 1. ПЕРЕВІРКА ТЕСТОВОЇ КОНФІГУРАЦІЇ
# ==========================================================

def test_configuration_fixture(test_settings):
    """Перевірка використання синтетичної конфігурації."""

    assert test_settings.db_host == "test-postgres"

    assert test_settings.db_name == "test_database"

    assert test_settings.db_user == "test_user"

    assert test_settings.app_timezone == "Europe/Kyiv"


# ==========================================================
# 2. ПЕРЕВІРКА ТЕСТОВИХ КОРИСТУВАЧІВ
# ==========================================================

def test_user_identifiers(
    test_user_id,
    other_user_id
):
    """Перевірка ідентифікаторів тестових користувачів."""

    assert isinstance(test_user_id, UUID)

    assert isinstance(other_user_id, UUID)

    assert test_user_id != other_user_id


# ==========================================================
# 3. ПЕРЕВІРКА ТЕСТОВОГО ЗАСТОСУНКУ
# ==========================================================

def test_application_fixture(test_app):
    """Перевірка створення FastAPI-застосунку."""

    assert isinstance(test_app, FastAPI)

    assert test_app.title == "Study Plan Service"

    assert test_app.dependency_overrides == {}


def test_api_client(api_client):
    """Перевірка службового HTTP-маршруту."""

    response = api_client.get("/")

    assert response.status_code == 200

    assert response.json() == {
        "message": "Study Plan Service is running"
    }


# ==========================================================
# 4. ПЕРЕВІРКА ТЕСТОВОЇ АВТЕНТИФІКАЦІЇ
# ==========================================================

def test_authenticated_client(
    test_app,
    authenticated_client,
    test_user_id
):
    """Перевірка автентифікації першого користувача."""

    @test_app.get("/test-user")
    def get_test_user(user_id: CurrentUserId):

        return {
            "user_id": str(user_id)
        }

    response = authenticated_client.get("/test-user")

    assert response.status_code == 200

    assert response.json() == {
        "user_id": str(test_user_id)
    }


def test_other_user_client(
    test_app,
    other_user_client,
    other_user_id
):
    """Перевірка автентифікації другого користувача."""

    @test_app.get("/test-user")
    def get_test_user(user_id: CurrentUserId):

        return {
            "user_id": str(user_id)
        }

    response = other_user_client.get("/test-user")

    assert response.status_code == 200

    assert response.json() == {
        "user_id": str(other_user_id)
    }


def test_unauthenticated_client(
    test_app,
    api_client
):
    """Перевірка відсутності обходу автентифікації."""

    assert (
        get_current_user_id
        not in test_app.dependency_overrides
    )

    @test_app.get("/test-user")
    def get_test_user(user_id: CurrentUserId):

        return {
            "user_id": str(user_id)
        }

    response = api_client.get("/test-user")

    assert response.status_code == 401

    assert response.headers["WWW-Authenticate"] == "Bearer"

    assert response.json() == {
        "detail": "Authentication required"
    }
