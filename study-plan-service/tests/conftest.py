
"""
Спільна основа автоматизованого тестування
Study Plan Service.

Модуль містить повторно використовувані fixtures
для конфігурації, FastAPI-застосунку,
HTTP-клієнтів та тестових користувачів.
"""

import os

from unittest.mock import patch
from uuid import UUID

import pytest

from fastapi.testclient import TestClient

from config import Settings, get_settings
from dependencies import get_current_user_id


# ==========================================================
# 1. ТЕСТОВА КОНФІГУРАЦІЯ
# ==========================================================

@pytest.fixture
def test_settings(monkeypatch):
    """Підготовка ізольованої конфігурації."""

    # Видалення наявних конфігураційних змінних
    field_names = {
        name.upper()
        for name in Settings.model_fields
    }

    for name in list(os.environ):

        if name.upper() in field_names:
            monkeypatch.delenv(name)

    # Встановлення синтетичних тестових параметрів
    values = {
        "DB_HOST": "test-postgres",
        "DB_PORT": "5432",
        "DB_NAME": "test_database",
        "DB_USER": "test_user",
        "DB_PASSWORD": "test_db_password",
        "RABBITMQ_USER": "test_user",
        "RABBITMQ_PASSWORD": "test_rabbitmq_password"
    }

    for name, value in values.items():
        monkeypatch.setenv(name, value)

    get_settings.cache_clear()

    try:

        yield get_settings()

    finally:

        get_settings.cache_clear()


# ==========================================================
# 2. ТЕСТОВІ КОРИСТУВАЧІ
# ==========================================================

@pytest.fixture
def test_user_id():
    """Ідентифікатор першого тестового користувача."""

    return UUID(
        "11111111-1111-4111-8111-111111111111"
    )


@pytest.fixture
def other_user_id():
    """Ідентифікатор другого тестового користувача."""

    return UUID(
        "22222222-2222-4222-8222-222222222222"
    )


# ==========================================================
# 3. ТЕСТОВИЙ FASTAPI-ЗАСТОСУНОК
# ==========================================================

@pytest.fixture
def test_app(test_settings):
    """Створення ізольованого FastAPI-застосунку."""

    # Запобігання зміні налаштувань журналювання pytest
    with patch("logging_config.dictConfig"):

        from main import create_app

    application = create_app()

    try:

        yield application

    finally:

        application.dependency_overrides.clear()


# ==========================================================
# 4. ТЕСТОВІ HTTP-КЛІЄНТИ
# ==========================================================

@pytest.fixture
def api_client(test_app):
    """HTTP-клієнт без підміни автентифікації."""

    with TestClient(test_app) as client:

        yield client


@pytest.fixture
def authenticated_client(
    test_app,
    test_user_id
):
    """HTTP-клієнт першого тестового користувача."""

    test_app.dependency_overrides[
        get_current_user_id
    ] = lambda: test_user_id

    try:

        with TestClient(test_app) as client:

            yield client

    finally:

        test_app.dependency_overrides.pop(
            get_current_user_id,
            None
        )


@pytest.fixture
def other_user_client(
    test_app,
    other_user_id
):
    """HTTP-клієнт другого тестового користувача."""

    test_app.dependency_overrides[
        get_current_user_id
    ] = lambda: other_user_id

    try:

        with TestClient(test_app) as client:

            yield client

    finally:

        test_app.dependency_overrides.pop(
            get_current_user_id,
            None
        )
