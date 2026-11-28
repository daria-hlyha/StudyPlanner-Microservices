
"""
Автоматизовані тести журналювання та налаштування
FastAPI-застосунку Study Plan Service.
"""

import logging
import time

from unittest.mock import patch

import pytest

from fastapi.testclient import TestClient

from config import Settings, get_settings

from logging_config import (
    UTCFormatter,
    configure_logging
)


# ==========================================================
# 1. ПІДГОТОВКА ТЕСТОВОГО СЕРЕДОВИЩА
# ==========================================================

@pytest.fixture
def application(monkeypatch):
    """Створення застосунку з тестовою конфігурацією."""

    # Видалення наявних конфігураційних змінних
    import os

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

        # Не змінюємо конфігурацію логерів pytest під час імпорту
        with patch("logging_config.dictConfig"):

            from main import create_app

        yield create_app()

    finally:

        get_settings.cache_clear()


# ==========================================================
# 2. ПЕРЕВІРКА ЖУРНАЛЮВАННЯ
# ==========================================================

def test_utc_formatter():
    """Перевірка використання часу UTC."""

    formatter = UTCFormatter(
        fmt="%(asctime)sZ",
        datefmt="%Y-%m-%dT%H:%M:%S"
    )

    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None
    )

    record.created = 0

    assert formatter.converter == time.gmtime

    assert formatter.format(record) == (
        "1970-01-01T00:00:00Z"
    )


def test_logging_configuration():
    """Перевірка структури налаштувань журналювання."""

    with patch("logging_config.dictConfig") as configure:

        configure_logging()

    configure.assert_called_once()

    config = configure.call_args.args[0]

    assert config["version"] == 1

    assert config["disable_existing_loggers"] is False

    assert config["root"]["level"] == "INFO"

    assert config["root"]["handlers"] == ["console"]

    assert config["handlers"]["console"]["stream"] == (
        "ext://sys.stdout"
    )

    assert config["formatters"]["standard"]["()"] is UTCFormatter

    assert config["loggers"]["pika"]["level"] == "WARNING"


# ==========================================================
# 3. ПЕРЕВІРКА ЖИТТЄВОГО ЦИКЛУ
# ==========================================================

def test_application_lifespan(application, caplog):
    """Перевірка журналювання запуску та завершення."""

    with caplog.at_level(
        logging.INFO,
        logger="main"
    ):

        with TestClient(application) as client:

            response = client.get("/")

            assert response.status_code == 200

            assert "Study Plan Service started" in caplog.text

    assert "Study Plan Service stopped" in caplog.text


def test_lifespan_without_external_connections(application):
    """Запуск не потребує підключень до зовнішніх компонентів."""

    with (
        patch("main.get_connection") as database,

        patch("main.get_rabbitmq_connection") as rabbitmq
    ):

        with TestClient(application) as client:

            response = client.get("/")

            assert response.status_code == 200

        database.assert_not_called()

        rabbitmq.assert_not_called()


# ==========================================================
# 4. ПЕРЕВІРКА ЖУРНАЛЮВАННЯ ПОМИЛОК
# ==========================================================

@pytest.mark.parametrize(
    "path,target,log_message,response_message",
    [
        (
            "/db-check",
            "main.get_connection",
            "Database connection check failed",
            "Database connection error"
        ),

        (
            "/rabbitmq-check",
            "main.get_rabbitmq_connection",
            "RabbitMQ connection check failed",
            "RabbitMQ connection error"
        )
    ]
)
def test_connection_error_logging(
    application,
    caplog,
    path,
    target,
    log_message,
    response_message
):
    """Перевірка журналювання без розкриття деталей помилки."""

    with (
        caplog.at_level(
            logging.WARNING,
            logger="main"
        ),

        patch(
            target,
            side_effect=RuntimeError("private_test_error")
        )
    ):

        with TestClient(application) as client:

            response = client.get(path)

    assert response.status_code == 503

    assert response.json() == {
        "detail": response_message
    }

    assert log_message in caplog.text

    assert "RuntimeError" in caplog.text

    assert "private_test_error" not in caplog.text

    assert "private_test_error" not in response.text


# ==========================================================
# 5. ПЕРЕВІРКА OPENAPI
# ==========================================================

def test_infrastructure_route_tags(application):
    """Перевірка групування службових маршрутів."""

    schema = application.openapi()

    for path in ["/", "/db-check", "/rabbitmq-check"]:

        operation = schema["paths"][path]["get"]

        assert operation["tags"] == ["Infrastructure"]


@pytest.mark.parametrize(
    "path",
    ["/db-check", "/rabbitmq-check"]
)
def test_service_unavailable_documentation(
    application,
    path
):
    """Перевірка документування HTTP 503."""

    schema = application.openapi()

    response = (
        schema["paths"][path]["get"]["responses"]["503"]
    )

    assert response["description"] == "Service unavailable"

    assert (
        response["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/ErrorResponse"
    )

    error_schema = (
        schema["components"]["schemas"]["ErrorResponse"]
    )

    assert error_schema["properties"]["detail"]["type"] == "string"
