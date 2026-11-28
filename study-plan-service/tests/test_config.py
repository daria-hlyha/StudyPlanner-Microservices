
"""
Автоматизовані тести централізованої конфігурації
Study Plan Service.

Тести використовують синтетичні конфігураційні параметри
та не потребують підключення до PostgreSQL або RabbitMQ.
"""

import os

import pytest
from pydantic import ValidationError

from config import Settings, get_settings


# ==========================================================
# 1. ПІДГОТОВКА ТЕСТОВОГО СЕРЕДОВИЩА
# ==========================================================

@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch):
    """Ізоляція конфігурації перед кожним тестом."""

    field_names = set(Settings.model_fields)

    for name in list(os.environ):
        if name.lower() in field_names:
            monkeypatch.delenv(name, raising=False)

    get_settings.cache_clear()

    yield

    get_settings.cache_clear()


@pytest.fixture
def valid_settings():
    """Коректні синтетичні параметри конфігурації."""

    return {
        "db_host": "test-postgres",
        "db_port": 5432,
        "db_name": "test_database",
        "db_user": "test_user",
        "db_password": "test_db_password",
        "rabbitmq_user": "test_user",
        "rabbitmq_password": "test_rabbitmq_password"
    }


# ==========================================================
# 2. ПЕРЕВІРКА СТРУКТУРИ ТА СТАНДАРТНИХ ЗНАЧЕНЬ
# ==========================================================

def test_configuration_structure(valid_settings):
    """Перевірка структури конфігураційної моделі."""

    required_fields = {
        name
        for name, field in Settings.model_fields.items()
        if field.is_required()
    }

    assert len(Settings.model_fields) == 16
    assert required_fields == set(valid_settings)
    assert len(required_fields) == 7


def test_default_values(valid_settings):
    """Перевірка стандартних значень конфігурації."""

    settings = Settings(**valid_settings)

    assert settings.app_name == "Study Plan Service"
    assert settings.app_timezone == "Europe/Kyiv"

    assert settings.rabbitmq_host == "rabbitmq"
    assert settings.rabbitmq_port == 5672

    assert settings.rabbitmq_connection_attempts == 3
    assert settings.rabbitmq_retry_delay == 2.0
    assert settings.rabbitmq_socket_timeout == 5.0
    assert settings.rabbitmq_stack_timeout == 10.0
    assert settings.rabbitmq_blocked_connection_timeout == 10.0


# ==========================================================
# 3. ОТРИМАННЯ ЗМІННИХ СЕРЕДОВИЩА
# ==========================================================

def test_environment_variables(monkeypatch, valid_settings):
    """Перевірка отримання всіх параметрів із середовища."""

    values = {
        **valid_settings,
        "app_name": "Test Study Planner",
        "app_timezone": "UTC",
        "rabbitmq_host": "test-rabbitmq",
        "rabbitmq_port": 5673,
        "rabbitmq_connection_attempts": 4,
        "rabbitmq_retry_delay": 1.5,
        "rabbitmq_socket_timeout": 4.0,
        "rabbitmq_stack_timeout": 8.0,
        "rabbitmq_blocked_connection_timeout": 12.0
    }

    for name, value in values.items():
        monkeypatch.setenv(name.upper(), str(value))

    settings = Settings()

    for name, expected in values.items():

        actual = getattr(settings, name)

        if name in ("db_password", "rabbitmq_password"):
            actual = actual.get_secret_value()

        assert actual == expected

    assert isinstance(settings.db_port, int)
    assert isinstance(settings.rabbitmq_port, int)
    assert isinstance(settings.rabbitmq_connection_attempts, int)
    assert isinstance(settings.rabbitmq_retry_delay, float)


def test_explicit_values_priority(monkeypatch, valid_settings):
    """Перевірка пріоритету явно переданих параметрів."""

    monkeypatch.setenv("DB_PORT", "1234")

    settings = Settings(**valid_settings)

    assert settings.db_port == 5432


def test_unknown_environment_variable(monkeypatch, valid_settings):
    """Невідома змінна не повинна змінювати конфігурацію."""

    monkeypatch.setenv("UNRELATED_TEST_SETTING", "test")

    settings = Settings(**valid_settings)

    assert "UNRELATED_TEST_SETTING" not in settings.model_dump()
    assert len(settings.model_dump()) == 16


# ==========================================================
# 4. ПЕРЕВІРКА ОБОВ'ЯЗКОВИХ ПАРАМЕТРІВ
# ==========================================================

@pytest.mark.parametrize(
    "field",
    [
        "db_host",
        "db_port",
        "db_name",
        "db_user",
        "db_password",
        "rabbitmq_user",
        "rabbitmq_password"
    ]
)
def test_missing_required_field(valid_settings, field):
    """Відсутність обов'язкового параметра."""

    valid_settings.pop(field)

    with pytest.raises(ValidationError) as error:
        Settings(**valid_settings)

    assert any(
        item["loc"] == (field,) and item["type"] == "missing"
        for item in error.value.errors(include_input=False)
    )


# ==========================================================
# 5. ПЕРЕВІРКА ТЕКСТОВИХ ПАРАМЕТРІВ
# ==========================================================

@pytest.mark.parametrize(
    "field",
    [
        "app_name",
        "app_timezone",
        "db_host",
        "db_name",
        "db_user",
        "rabbitmq_host",
        "rabbitmq_user"
    ]
)
@pytest.mark.parametrize("value", ["", "   "])
def test_empty_text_fields(valid_settings, field, value):
    """Відхилення порожніх текстових параметрів."""

    valid_settings[field] = value

    with pytest.raises(ValidationError) as error:
        Settings(**valid_settings)

    assert any(
        item["loc"] == (field,)
        for item in error.value.errors(include_input=False)
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("app_name", " Test Application "),
        ("app_timezone", " UTC "),
        ("db_host", " postgres "),
        ("db_name", " studyplanner "),
        ("db_user", " test_user "),
        ("rabbitmq_host", " rabbitmq "),
        ("rabbitmq_user", " test_user ")
    ]
)
def test_text_normalization(valid_settings, field, value):
    """Видалення крайніх пробілів у текстових параметрах."""

    valid_settings[field] = value

    settings = Settings(**valid_settings)

    assert getattr(settings, field) == value.strip()


# ==========================================================
# 6. ПЕРЕВІРКА ПОРТІВ
# ==========================================================

@pytest.mark.parametrize("field", ["db_port", "rabbitmq_port"])
@pytest.mark.parametrize("value", [1, 65535])
def test_valid_ports(valid_settings, field, value):
    """Перевірка допустимих меж портів."""

    valid_settings[field] = value

    settings = Settings(**valid_settings)

    assert getattr(settings, field) == value


@pytest.mark.parametrize("field", ["db_port", "rabbitmq_port"])
@pytest.mark.parametrize(
    "value",
    [0, -1, 65536, "invalid", 1.5]
)
def test_invalid_ports(valid_settings, field, value):
    """Відхилення некоректних портів."""

    valid_settings[field] = value

    with pytest.raises(ValidationError) as error:
        Settings(**valid_settings)

    assert any(
        item["loc"] == (field,)
        for item in error.value.errors(include_input=False)
    )


# ==========================================================
# 7. ПЕРЕВІРКА КОНФІДЕНЦІЙНИХ ПАРАМЕТРІВ
# ==========================================================

def test_password_masking(valid_settings):
    """Паролі не відображаються відкритим текстом."""

    settings = Settings(**valid_settings)

    assert str(settings.db_password) == "**********"
    assert str(settings.rabbitmq_password) == "**********"

    for field in ("db_password", "rabbitmq_password"):

        assert valid_settings[field] not in str(settings)
        assert valid_settings[field] not in repr(settings)
        assert valid_settings[field] not in settings.model_dump_json()


@pytest.mark.parametrize(
    "field",
    ["db_password", "rabbitmq_password"]
)
def test_empty_password(valid_settings, field):
    """Відхилення порожнього пароля."""

    valid_settings[field] = ""

    with pytest.raises(ValidationError) as error:
        Settings(**valid_settings)

    assert any(
        item["loc"] == (field,)
        for item in error.value.errors(include_input=False)
    )


@pytest.mark.parametrize(
    "field",
    ["db_password", "rabbitmq_password"]
)
def test_password_preservation(valid_settings, field):
    """Збереження оригінального значення пароля."""

    password = " test password "

    valid_settings[field] = password

    settings = Settings(**valid_settings)

    assert getattr(settings, field).get_secret_value() == password


# ==========================================================
# 8. ПЕРЕВІРКА ЧАСОВИХ ПОЯСІВ
# ==========================================================

@pytest.mark.parametrize(
    "timezone",
    ["Europe/Kyiv", "Europe/Vilnius", "UTC"]
)
def test_valid_timezone(valid_settings, timezone):
    """Перевірка підтримуваних часових поясів."""

    valid_settings["app_timezone"] = timezone

    settings = Settings(**valid_settings)

    assert settings.app_timezone == timezone


@pytest.mark.parametrize(
    "timezone",
    ["Invalid/Timezone", "../UTC", "/UTC"]
)
def test_invalid_timezone(valid_settings, timezone):
    """Відхилення некоректних часових поясів."""

    valid_settings["app_timezone"] = timezone

    with pytest.raises(ValidationError) as error:
        Settings(**valid_settings)

    assert any(
        item["loc"] == ("app_timezone",)
        for item in error.value.errors(include_input=False)
    )


# ==========================================================
# 9. ПЕРЕВІРКА ПАРАМЕТРІВ RABBITMQ
# ==========================================================

def test_valid_connection_parameters(valid_settings):
    """Перевірка допустимих параметрів підключення."""

    valid_settings.update({
        "rabbitmq_connection_attempts": 1,
        "rabbitmq_retry_delay": 0.0,
        "rabbitmq_socket_timeout": 1.0,
        "rabbitmq_stack_timeout": 2.0,
        "rabbitmq_blocked_connection_timeout": 0.5
    })

    settings = Settings(**valid_settings)

    assert settings.rabbitmq_connection_attempts == 1
    assert settings.rabbitmq_retry_delay == 0.0
    assert settings.rabbitmq_socket_timeout == 1.0
    assert settings.rabbitmq_stack_timeout == 2.0
    assert settings.rabbitmq_blocked_connection_timeout == 0.5


@pytest.mark.parametrize(
    "field,value",
    [
        ("rabbitmq_connection_attempts", 0),
        ("rabbitmq_connection_attempts", -1),
        ("rabbitmq_connection_attempts", 1.5),
        ("rabbitmq_retry_delay", -1),
        ("rabbitmq_socket_timeout", 0),
        ("rabbitmq_socket_timeout", -1),
        ("rabbitmq_stack_timeout", 0),
        ("rabbitmq_stack_timeout", -1),
        ("rabbitmq_blocked_connection_timeout", 0),
        ("rabbitmq_blocked_connection_timeout", -1)
    ]
)
def test_invalid_connection_parameters(valid_settings, field, value):
    """Відхилення некоректних параметрів підключення."""

    valid_settings[field] = value

    with pytest.raises(ValidationError) as error:
        Settings(**valid_settings)

    assert any(
        item["loc"] == (field,)
        for item in error.value.errors(include_input=False)
    )


@pytest.mark.parametrize(
    "field",
    [
        "rabbitmq_retry_delay",
        "rabbitmq_socket_timeout",
        "rabbitmq_stack_timeout",
        "rabbitmq_blocked_connection_timeout"
    ]
)
@pytest.mark.parametrize(
    "value",
    [float("inf"), float("-inf"), float("nan")]
)
def test_non_finite_values(valid_settings, field, value):
    """Відхилення нескінченних значень та NaN."""

    valid_settings[field] = value

    with pytest.raises(ValidationError) as error:
        Settings(**valid_settings)

    assert any(
        item["loc"] == (field,)
        for item in error.value.errors(include_input=False)
    )


# ==========================================================
# 10. ПЕРЕВІРКА УЗГОДЖЕНОСТІ ТАЙМ-АУТІВ
# ==========================================================

@pytest.mark.parametrize(
    "socket_timeout,stack_timeout",
    [(5.0, 5.0), (10.0, 5.0)]
)
def test_invalid_timeout_relationship(
    valid_settings,
    socket_timeout,
    stack_timeout
):
    """Stack timeout повинен перевищувати socket timeout."""

    valid_settings["rabbitmq_socket_timeout"] = socket_timeout
    valid_settings["rabbitmq_stack_timeout"] = stack_timeout

    with pytest.raises(ValidationError) as error:
        Settings(**valid_settings)

    assert any(
        item["loc"] == ()
        and item["type"] == "value_error"
        for item in error.value.errors(include_input=False)
    )


# ==========================================================
# 11. ПЕРЕВІРКА НЕЗМІННОСТІ КОНФІГУРАЦІЇ
# ==========================================================

def test_frozen_settings(valid_settings):
    """Заборона зміни створеного об'єкта конфігурації."""

    settings = Settings(**valid_settings)

    with pytest.raises(ValidationError) as error:
        settings.db_port = 1234

    assert error.value.errors(include_input=False)[0]["type"] == (
        "frozen_instance"
    )

    assert settings.db_port == 5432


# ==========================================================
# 12. ПЕРЕВІРКА КЕШУВАННЯ
# ==========================================================

def test_settings_cache(monkeypatch, valid_settings):
    """Повторне використання об'єкта конфігурації."""

    for name, value in valid_settings.items():
        monkeypatch.setenv(name.upper(), str(value))

    first = get_settings()
    second = get_settings()

    assert first is second
    assert get_settings.cache_info().currsize == 1

    monkeypatch.setenv("DB_PORT", "5433")

    assert get_settings().db_port == 5432

    get_settings.cache_clear()

    third = get_settings()

    assert third is not first
    assert third.db_port == 5433


def test_failed_settings_not_cached(monkeypatch, valid_settings):
    """Невдала ініціалізація не зберігається в кеші."""

    with pytest.raises(ValidationError):
        get_settings()

    assert get_settings.cache_info().currsize == 0

    for name, value in valid_settings.items():
        monkeypatch.setenv(name.upper(), str(value))

    settings = get_settings()

    assert settings.db_port == 5432
    assert get_settings.cache_info().currsize == 1


# ==========================================================
# 13. ПЕРЕВІРКА БЕЗПЕКИ ПОВІДОМЛЕНЬ ПРО ПОМИЛКИ
# ==========================================================

def test_validation_error_masks_inputs(valid_settings):
    """Приховування вхідних даних у тексті помилки."""

    invalid_value = "private_test_input"

    valid_settings["db_port"] = invalid_value

    with pytest.raises(ValidationError) as error:
        Settings(**valid_settings)

    assert invalid_value not in str(error.value)
    assert valid_settings["db_password"] not in str(error.value)
    assert valid_settings["rabbitmq_password"] not in str(error.value)


def test_model_validation_masks_passwords(valid_settings):
    """Паролі не розкриваються при міжпольовій валідації."""

    valid_settings["rabbitmq_stack_timeout"] = 1.0

    with pytest.raises(ValidationError) as error:
        Settings(**valid_settings)

    message = str(error.value)

    assert valid_settings["db_password"] not in message
    assert valid_settings["rabbitmq_password"] not in message


# ==========================================================
# 14. ПЕРЕВІРКА НЕЗАЛЕЖНОСТІ ВІД ФАЙЛУ .env
# ==========================================================

def test_dotenv_is_not_loaded(monkeypatch, tmp_path, valid_settings):
    """Конфігурація не читає локальний .env автоматично."""

    monkeypatch.chdir(tmp_path)

    env_file = tmp_path / ".env"

    env_file.write_text(
        "APP_NAME=Unexpected application\n"
        "RABBITMQ_PORT=9999\n",
        encoding="utf-8"
    )

    settings = Settings(**valid_settings)

    assert settings.app_name == "Study Plan Service"
    assert settings.rabbitmq_port == 5672
