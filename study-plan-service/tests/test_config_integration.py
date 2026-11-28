
"""
Автоматизовані тести інтеграції централізованої
конфігурації Study Plan Service.

Перевіряється взаємодія config.py, database.py,
rabbitmq.py та main.py.

Тести не потребують реального підключення
до PostgreSQL або RabbitMQ.
"""

import os
import subprocess
import sys

from unittest.mock import patch

import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from config import Settings, get_settings
from database import get_connection
from rabbitmq import get_rabbitmq_connection


# ==========================================================
# 1. ПІДГОТОВКА ТЕСТОВОГО СЕРЕДОВИЩА
# ==========================================================

@pytest.fixture(autouse=True)
def isolated_configuration(monkeypatch):
    """Підготовка ізольованої тестової конфігурації."""

    field_names = set(Settings.model_fields)

    # Видалення наявних параметрів конфігурації
    for name in list(os.environ):
        if name.lower() in field_names:
            monkeypatch.delenv(name, raising=False)

    # Синтетичні параметри підключення
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

    yield

    get_settings.cache_clear()


@pytest.fixture
def application():
    """Створення окремого FastAPI-застосунку для тесту."""

    from main import create_app

    return create_app()


@pytest.fixture
def client(application):
    """Створення тестового HTTP-клієнта."""

    with TestClient(application) as test_client:
        yield test_client


def run_python(code):
    """Виконання перевірки в окремому Python-процесі."""

    return subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30
    )


# ==========================================================
# 2. ІНТЕГРАЦІЯ КОНФІГУРАЦІЇ З POSTGRESQL
# ==========================================================

def test_database_connection_parameters():
    """Перевірка параметрів підключення до PostgreSQL."""

    with patch("database.psycopg.connect") as mock:

        connection = get_connection()

        mock.assert_called_once_with(
            host="test-postgres",
            port=5432,
            dbname="test_database",
            user="test_user",
            password="test_db_password"
        )

        assert connection is mock.return_value


def test_database_rejects_invalid_configuration(monkeypatch):
    """Некоректна конфігурація не допускає підключення."""

    monkeypatch.delenv("DB_PASSWORD")

    with patch("database.psycopg.connect") as mock:

        with pytest.raises(ValidationError) as error:
            get_connection()

        assert any(
            item["loc"] == ("db_password",)
            and item["type"] == "missing"
            for item in error.value.errors(include_input=False)
        )

        mock.assert_not_called()


# ==========================================================
# 3. ІНТЕГРАЦІЯ КОНФІГУРАЦІЇ З RABBITMQ
# ==========================================================

@pytest.mark.parametrize("custom", [False, True])
def test_rabbitmq_connection_parameters(monkeypatch, custom):
    """Перевірка стандартної та перевизначеної конфігурації."""

    expected = {
        "host": "rabbitmq",
        "port": 5672,
        "connection_attempts": 3,
        "retry_delay": 2.0,
        "socket_timeout": 5.0,
        "stack_timeout": 10.0,
        "blocked_connection_timeout": 10.0
    }

    username = "test_user"
    password = "test_rabbitmq_password"

    if custom:

        expected.update({
            "host": "test-rabbitmq",
            "port": 5673,
            "connection_attempts": 4,
            "retry_delay": 1.5,
            "socket_timeout": 4.0,
            "stack_timeout": 8.0,
            "blocked_connection_timeout": 12.0
        })

        username = "custom_user"
        password = "custom_test_password"

        for name, value in expected.items():
            monkeypatch.setenv(
                f"RABBITMQ_{name.upper()}",
                str(value)
            )

        monkeypatch.setenv("RABBITMQ_USER", username)
        monkeypatch.setenv("RABBITMQ_PASSWORD", password)

    with patch("rabbitmq.pika.BlockingConnection") as mock:

        connection = get_rabbitmq_connection()

        mock.assert_called_once()

        parameters = mock.call_args.args[0]

        for name, value in expected.items():
            assert getattr(parameters, name) == value

        assert parameters.credentials.username == username
        assert parameters.credentials.password == password

        assert connection is mock.return_value


def test_rabbitmq_rejects_missing_configuration(monkeypatch):
    """Відсутній пароль RabbitMQ не допускає підключення."""

    monkeypatch.delenv("RABBITMQ_PASSWORD")

    with patch("rabbitmq.pika.BlockingConnection") as mock:

        with pytest.raises(ValidationError) as error:
            get_rabbitmq_connection()

        assert any(
            item["loc"] == ("rabbitmq_password",)
            and item["type"] == "missing"
            for item in error.value.errors(include_input=False)
        )

        mock.assert_not_called()


def test_rabbitmq_rejects_invalid_timeouts(monkeypatch):
    """Суперечливі тайм-аути не допускають підключення."""

    monkeypatch.setenv("RABBITMQ_SOCKET_TIMEOUT", "10")
    monkeypatch.setenv("RABBITMQ_STACK_TIMEOUT", "5")

    with patch("rabbitmq.pika.BlockingConnection") as mock:

        with pytest.raises(ValidationError) as error:
            get_rabbitmq_connection()

        assert any(
            item["loc"] == ()
            and item["type"] == "value_error"
            for item in error.value.errors(include_input=False)
        )

        mock.assert_not_called()


# ==========================================================
# 4. ПЕРЕВІРКА ІНІЦІАЛІЗАЦІЇ FASTAPI
# ==========================================================

def test_application_rejects_missing_configuration(monkeypatch):
    """FastAPI не створюється без обов'язкової конфігурації."""

    required_fields = {
        name
        for name, field in Settings.model_fields.items()
        if field.is_required()
    }

    for name in required_fields:
        monkeypatch.delenv(name.upper(), raising=False)

    code = """
import importlib
from pydantic import ValidationError

try:
    importlib.import_module("main")

except ValidationError as error:
    missing = {
        item["loc"][0]
        for item in error.errors(include_input=False)
        if item["type"] == "missing"
    }

    expected = {
        "db_host",
        "db_port",
        "db_name",
        "db_user",
        "db_password",
        "rabbitmq_user",
        "rabbitmq_password"
    }

    assert missing == expected
    print("Invalid application configuration rejected: PASS")

else:
    raise AssertionError("Invalid configuration accepted")
"""

    result = run_python(code)

    assert result.returncode == 0, result.stderr

    assert (
        "Invalid application configuration rejected: PASS"
        in result.stdout
    )


def test_application_import_without_connections():
    """Імпорт main.py не створює мережевих підключень."""

    code = """
from unittest.mock import patch

with patch("database.psycopg.connect") as database:
    with patch("rabbitmq.pika.BlockingConnection") as broker:

        import main

        database.assert_not_called()
        broker.assert_not_called()

        print("Application initialization: PASS")
"""

    result = run_python(code)

    assert result.returncode == 0, result.stderr

    assert "Application initialization: PASS" in result.stdout


# ==========================================================
# 5. ПЕРЕВІРКА КОНФІГУРАЦІЇ FASTAPI
# ==========================================================

def test_default_application_title(application):
    """Перевірка стандартної назви застосунку."""

    assert isinstance(application, FastAPI)

    assert application.title == "Study Plan Service"

    assert application.openapi()["info"]["title"] == (
        "Study Plan Service"
    )


def test_custom_application_title(monkeypatch):
    """Перевірка перевизначення назви застосунку."""

    monkeypatch.setenv("APP_NAME", "Custom Study Planner")

    from main import create_app

    application = create_app()

    assert application.title == "Custom Study Planner"

    assert application.openapi()["info"]["title"] == (
        "Custom Study Planner"
    )


# ==========================================================
# 6. ПЕРЕВІРКА ЗАРЕЄСТРОВАНИХ МАРШРУТІВ
# ==========================================================

def test_application_routes(application):
    """Перевірка наявності всіх службових маршрутів."""

    expected = {
        "/",
        "/db-check",
        "/rabbitmq-check",
        "/metrics",
        "/docs",
        "/openapi.json",
        "/docs/oauth2-redirect",
        "/redoc"
    }

    routes = {
        route.path
        for route in application.routes
    }

    assert expected.issubset(routes)


# ==========================================================
# 7. ПЕРЕВІРКА REST API ТА ДОКУМЕНТАЦІЇ
# ==========================================================

def test_root_endpoint(client):
    """Перевірка основного маршруту мікросервісу."""

    response = client.get("/")

    assert response.status_code == 200

    assert response.json() == {
        "message": "Study Plan Service is running"
    }


@pytest.mark.parametrize(
    "path",
    ["/docs", "/openapi.json", "/redoc"]
)
def test_api_documentation(client, path):
    """Перевірка доступності документації REST API."""

    response = client.get(path)

    assert response.status_code == 200


# ==========================================================
# 8. ПЕРЕВІРКА УСПІШНИХ СЛУЖБОВИХ МАРШРУТІВ
# ==========================================================

def test_database_health_endpoint(client):
    """Перевірка успішного підключення до PostgreSQL."""

    with patch("main.get_connection") as mock:

        connection = mock.return_value.__enter__.return_value

        cursor = (
            connection.cursor.return_value
            .__enter__.return_value
        )

        cursor.fetchone.return_value = (
            "study_plan_user",
            "studyplanner",
            "study_plan"
        )

        response = client.get("/db-check")

        assert response.status_code == 200

        assert response.json() == {
            "status": "connected",
            "user": "study_plan_user",
            "database": "studyplanner",
            "current_schema": "study_plan"
        }

        mock.assert_called_once_with()

        cursor.execute.assert_called_once_with(
            "SELECT current_user, current_database(), current_schema()"
        )

        cursor.fetchone.assert_called_once_with()

        mock.return_value.__exit__.assert_called_once()


def test_rabbitmq_health_endpoint(client):
    """Перевірка успішного підключення до RabbitMQ."""

    with patch("main.get_rabbitmq_connection") as mock:

        response = client.get("/rabbitmq-check")

        assert response.status_code == 200

        assert response.json() == {
            "status": "connected"
        }

        mock.assert_called_once_with()

        mock.return_value.close.assert_called_once_with()


# ==========================================================
# 9. ПЕРЕВІРКА ОБРОБКИ ПОМИЛОК ПІДКЛЮЧЕННЯ
# ==========================================================

@pytest.mark.parametrize(
    "path,target,detail",
    [
        (
            "/db-check",
            "main.get_connection",
            "Database connection error"
        ),
        (
            "/rabbitmq-check",
            "main.get_rabbitmq_connection",
            "RabbitMQ connection error"
        )
    ]
)
def test_connection_error_response(client, path, target, detail):
    """Перевірка HTTP 503 та приховування внутрішніх деталей."""

    internal_error = "private_test_error"

    with patch(
        target,
        side_effect=RuntimeError(internal_error)
    ) as mock:

        response = client.get(path)

        assert response.status_code == 503

        assert response.json() == {
            "detail": detail
        }

        assert internal_error not in response.text

        mock.assert_called_once_with()


# ==========================================================
# 10. ПЕРЕВІРКА МОНІТОРИНГУ PROMETHEUS
# ==========================================================

def test_prometheus_metrics(client):
    """Перевірка доступності HTTP-метрик."""

    response = client.get("/")

    assert response.status_code == 200

    metrics = client.get("/metrics")

    assert metrics.status_code == 200

    assert "http_requests_total" in metrics.text

    assert any(
        line.startswith("http_requests_total{")
        and 'handler="/"' in line
        and 'method="GET"' in line
        and 'status="2xx"' in line
        for line in metrics.text.splitlines()
    )


# ==========================================================
# 11. ПЕРЕВІРКА APPLICATION FACTORY
# ==========================================================

def test_application_factory():
    """Створення окремих екземплярів FastAPI."""

    from main import app, create_app

    first = create_app()
    second = create_app()

    assert isinstance(app, FastAPI)

    assert first is not second
    assert first is not app
    assert second is not app

    assert first.title == second.title

    first_routes = {
        route.path
        for route in first.routes
    }

    second_routes = {
        route.path
        for route in second.routes
    }

    assert first_routes == second_routes
