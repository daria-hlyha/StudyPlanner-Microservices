
"""
Централізована конфігурація Study Plan Service.

Модуль забезпечує отримання, валідацію та зберігання
конфігураційних параметрів мікросервісу.
"""

from functools import lru_cache
from typing import Self
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    Field,
    SecretStr,
    field_validator,
    model_validator
)

from pydantic_settings import BaseSettings, SettingsConfigDict


# ==========================================================
# 1. ЦЕНТРАЛІЗОВАНА КОНФІГУРАЦІЯ МІКРОСЕРВІСУ
# ==========================================================

class Settings(BaseSettings):

    """Конфігураційні параметри Study Plan Service."""

    # ------------------------------------------------------
    # 1.1. Налаштування конфігураційної моделі
    # ------------------------------------------------------

    model_config = SettingsConfigDict(
        env_file=None,
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
        frozen=True,
        validate_default=True,
        hide_input_in_errors=True,
        allow_inf_nan=False
    )

    # ------------------------------------------------------
    # 1.2. Загальні налаштування застосунку
    # ------------------------------------------------------

    app_name: str = "Study Plan Service"
    app_timezone: str = "Europe/Kyiv"

    # ------------------------------------------------------
    # 1.3. Налаштування PostgreSQL
    # ------------------------------------------------------

    db_host: str
    db_port: int = Field(ge=1, le=65535)
    db_name: str
    db_user: str
    db_password: SecretStr

    # ------------------------------------------------------
    # 1.4. Налаштування RabbitMQ
    # ------------------------------------------------------

    rabbitmq_host: str = "rabbitmq"
    rabbitmq_port: int = Field(default=5672, ge=1, le=65535)
    rabbitmq_user: str
    rabbitmq_password: SecretStr

    # ------------------------------------------------------
    # 1.5. Параметри підключення до RabbitMQ
    # ------------------------------------------------------

    rabbitmq_connection_attempts: int = Field(
        default=3,
        ge=1
    )

    rabbitmq_retry_delay: float = Field(
        default=2.0,
        ge=0
    )

    rabbitmq_socket_timeout: float = Field(
        default=5.0,
        gt=0
    )

    rabbitmq_stack_timeout: float = Field(
        default=10.0,
        gt=0
    )

    rabbitmq_blocked_connection_timeout: float = Field(
        default=10.0,
        gt=0
    )

    # ======================================================
    # 2. ВАЛІДАЦІЯ КОНФІГУРАЦІЙНИХ ПАРАМЕТРІВ
    # ======================================================

    # ------------------------------------------------------
    # 2.1. Перевірка текстових параметрів
    # ------------------------------------------------------

    @field_validator(
        "app_name",
        "app_timezone",
        "db_host",
        "db_name",
        "db_user",
        "rabbitmq_host",
        "rabbitmq_user"
    )
    @classmethod
    def validate_text(cls, value: str) -> str:

        """Перевірка непорожніх текстових параметрів."""

        value = value.strip()

        if not value:
            raise ValueError(
                "Текстовий параметр не може бути порожнім."
            )

        return value

    # ------------------------------------------------------
    # 2.2. Перевірка конфіденційних параметрів
    # ------------------------------------------------------

    @field_validator("db_password", "rabbitmq_password")
    @classmethod
    def validate_password(cls, value: SecretStr) -> SecretStr:

        """Перевірка паролів без зміни їхнього значення."""

        if not value.get_secret_value():
            raise ValueError(
                "Пароль не може бути порожнім."
            )

        return value

    # ------------------------------------------------------
    # 2.3. Перевірка часового поясу
    # ------------------------------------------------------

    @field_validator("app_timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:

        """Перевірка підтримки часового поясу."""

        try:
            ZoneInfo(value)

        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError(
                "Некоректний або непідтримуваний часовий пояс."
            ) from None

        return value

    # ------------------------------------------------------
    # 2.4. Перевірка узгодженості тайм-аутів RabbitMQ
    # ------------------------------------------------------

    @model_validator(mode="after")
    def validate_rabbitmq_timeouts(self) -> Self:

        """Перевірка співвідношення тайм-аутів RabbitMQ."""

        if self.rabbitmq_stack_timeout <= self.rabbitmq_socket_timeout:
            raise ValueError(
                "Stack timeout повинен перевищувати socket timeout."
            )

        return self


# ==========================================================
# 3. ОТРИМАННЯ КОНФІГУРАЦІЇ МІКРОСЕРВІСУ
# ==========================================================

@lru_cache(maxsize=1)
def get_settings() -> Settings:

    """Отримання та кешування конфігурації мікросервісу."""

    return Settings()
