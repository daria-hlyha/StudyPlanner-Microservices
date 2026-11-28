
"""
Спільні схеми даних Study Plan Service.

Модуль містить базові Pydantic-схеми,
універсальні типи даних та структури відповідей REST API.
"""

from typing import Annotated, Generic, TypeVar

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints
)


# ==========================================================
# 1. СПІЛЬНІ ТИПИ ДАНИХ
# ==========================================================

# Непорожній текстовий рядок
NonEmptyString = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1
    )
]


# Назва об'єкта відповідно до VARCHAR(255)
TitleString = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=255
    )
]


# Додатне ціле число відповідно до PostgreSQL SMALLINT
PositiveSmallInt = Annotated[
    int,
    Field(
        strict=True,
        ge=1,
        le=32767
    )
]


# Дата та час з обов'язковим часовим поясом
AwareDateTime = AwareDatetime


# ==========================================================
# 2. БАЗОВІ СХЕМИ ДАНИХ
# ==========================================================

class BaseSchema(BaseModel):
    """Базова схема вхідних даних."""

    model_config = ConfigDict(
        extra="forbid",
        validate_default=True
    )


class ResponseSchema(BaseModel):
    """Базова схема вихідних даних."""

    model_config = ConfigDict(
        from_attributes=True
    )


# ==========================================================
# 3. СПІЛЬНІ ЧАСОВІ ПОЛЯ
# ==========================================================

class TimestampSchema(ResponseSchema):
    """Схема часових характеристик запису."""

    created_at: AwareDateTime

    updated_at: AwareDateTime


# ==========================================================
# 4. УНІВЕРСАЛЬНА СХЕМА ПАГІНАЦІЇ
# ==========================================================

T = TypeVar("T")


class PaginatedResponse(ResponseSchema, Generic[T]):
    """Посторінкова відповідь зі списком записів."""

    items: list[T]

    total: int = Field(
        ge=0
    )

    limit: int = Field(
        default=50,
        ge=1,
        le=100
    )

    offset: int = Field(
        default=0,
        ge=0
    )


# ==========================================================
# 5. СХЕМА ПОВІДОМЛЕННЯ ПРО ПОМИЛКУ
# ==========================================================

class ErrorResponse(ResponseSchema):
    """Стандартна відповідь при програмній помилці."""

    detail: str
