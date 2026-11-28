
"""
Автоматизовані тести спільних схем даних
Study Plan Service.
"""

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from pydantic import TypeAdapter, ValidationError

from schemas.common import (
    BaseSchema,
    ResponseSchema,
    TimestampSchema,
    PaginatedResponse,
    ErrorResponse,
    NonEmptyString,
    TitleString,
    PositiveSmallInt,
    AwareDateTime
)


# ==========================================================
# 1. ПЕРЕВІРКА ТЕКСТОВИХ ТИПІВ
# ==========================================================

@pytest.mark.parametrize(
    "value,expected",
    [
        ("Test", "Test"),
        ("  Test  ", "Test"),
        ("Навчальний план", "Навчальний план")
    ]
)
def test_non_empty_string(value, expected):
    """Перевірка допустимих текстових рядків."""

    adapter = TypeAdapter(NonEmptyString)

    assert adapter.validate_python(value) == expected


@pytest.mark.parametrize(
    "value",
    ["", "   ", "\t\n"]
)
def test_invalid_non_empty_string(value):
    """Перевірка відхилення порожнього тексту."""

    adapter = TypeAdapter(NonEmptyString)

    with pytest.raises(ValidationError):
        adapter.validate_python(value)


@pytest.mark.parametrize(
    "value",
    ["A", "A" * 255]
)
def test_valid_title(value):
    """Перевірка допустимої довжини назви."""

    adapter = TypeAdapter(TitleString)

    assert adapter.validate_python(value) == value


@pytest.mark.parametrize(
    "value",
    ["", "   ", "A" * 256]
)
def test_invalid_title(value):
    """Перевірка некоректної довжини назви."""

    adapter = TypeAdapter(TitleString)

    with pytest.raises(ValidationError):
        adapter.validate_python(value)


# ==========================================================
# 2. ПЕРЕВІРКА ЧИСЛОВИХ ТИПІВ
# ==========================================================

@pytest.mark.parametrize(
    "value",
    [1, 100, 32767]
)
def test_valid_positive_smallint(value):
    """Перевірка допустимих числових значень."""

    adapter = TypeAdapter(PositiveSmallInt)

    assert adapter.validate_python(value) == value


@pytest.mark.parametrize(
    "value",
    [0, -1, 32768, 1.5, "5", True]
)
def test_invalid_positive_smallint(value):
    """Перевірка некоректних числових значень."""

    adapter = TypeAdapter(PositiveSmallInt)

    with pytest.raises(ValidationError):
        adapter.validate_python(value)


# ==========================================================
# 3. ПЕРЕВІРКА БАЗОВИХ СХЕМ
# ==========================================================

def test_base_schema():
    """Перевірка базової схеми вхідних даних."""

    class ExampleSchema(BaseSchema):
        name: TitleString

    result = ExampleSchema(name="  Test  ")

    assert result.name == "Test"


def test_unknown_fields_rejected():
    """Перевірка відхилення невідомих полів."""

    class ExampleSchema(BaseSchema):
        name: TitleString

    with pytest.raises(ValidationError):

        ExampleSchema(
            name="Test",
            unknown_field="invalid"
        )


def test_default_value_validation():
    """Перевірка валідації значень за замовчуванням."""

    class ExampleSchema(BaseSchema):
        name: TitleString = ""

    with pytest.raises(ValidationError):
        ExampleSchema()


def test_response_from_attributes():
    """Створення вихідної схеми з атрибутів об'єкта."""

    class ExampleResponse(ResponseSchema):
        name: str

    source = SimpleNamespace(
        name="Test"
    )

    result = ExampleResponse.model_validate(source)

    assert result.name == "Test"


# ==========================================================
# 4. ПЕРЕВІРКА ДАТИ ТА ЧАСУ
# ==========================================================

@pytest.mark.parametrize(
    "value",
    [
        "2026-11-28T10:00:00Z",
        "2026-11-28T12:00:00+02:00",
        datetime(
            2026, 11, 28, 10, 0,
            tzinfo=timezone.utc
        )
    ]
)
def test_aware_datetime(value):
    """Перевірка дати та часу з часовим поясом."""

    adapter = TypeAdapter(AwareDateTime)

    result = adapter.validate_python(value)

    assert result.tzinfo is not None
    assert result.utcoffset() is not None


@pytest.mark.parametrize(
    "value",
    [
        "2026-11-28T10:00:00",
        datetime(2026, 11, 28, 10, 0),
        "invalid"
    ]
)
def test_invalid_datetime(value):
    """Відхилення некоректної дати або часу без часового поясу."""

    adapter = TypeAdapter(AwareDateTime)

    with pytest.raises(ValidationError):
        adapter.validate_python(value)


def test_timestamp_schema():
    """Перевірка спільних часових полів."""

    value = datetime(
        2026, 11, 28, 10, 0,
        tzinfo=timezone.utc
    )

    result = TimestampSchema(
        created_at=value,
        updated_at=value
    )

    assert result.created_at == value
    assert result.updated_at == value


# ==========================================================
# 5. ПЕРЕВІРКА ПАГІНАЦІЇ
# ==========================================================

def test_empty_paginated_response():
    """Перевірка порожнього списку записів."""

    result = PaginatedResponse[str](
        items=[],
        total=0
    )

    assert result.model_dump() == {
        "items": [],
        "total": 0,
        "limit": 50,
        "offset": 0
    }


def test_paginated_response():
    """Перевірка відповіді з предметними записами."""

    class ExampleResponse(ResponseSchema):
        name: str

    result = PaginatedResponse[ExampleResponse](
        items=[
            {"name": "Subject 1"},
            {"name": "Subject 2"}
        ],
        total=10,
        limit=2,
        offset=4
    )

    assert isinstance(
        result.items[0],
        ExampleResponse
    )

    assert result.model_dump() == {
        "items": [
            {"name": "Subject 1"},
            {"name": "Subject 2"}
        ],
        "total": 10,
        "limit": 2,
        "offset": 4
    }


@pytest.mark.parametrize(
    "changes",
    [
        {"total": -1},
        {"limit": 0},
        {"limit": 101},
        {"offset": -1}
    ]
)
def test_invalid_paginated_response(changes):
    """Перевірка некоректних параметрів пагінації."""

    data = {
        "items": [],
        "total": 0,
        "limit": 50,
        "offset": 0
    }

    data.update(changes)

    with pytest.raises(ValidationError):
        PaginatedResponse[str](**data)


def test_invalid_paginated_item():
    """Перевірка валідації вкладених записів."""

    class ExampleResponse(ResponseSchema):
        name: str

    with pytest.raises(ValidationError):

        PaginatedResponse[ExampleResponse](
            items=[{}],
            total=1
        )


# ==========================================================
# 6. ПЕРЕВІРКА СХЕМИ ПОМИЛКИ
# ==========================================================

def test_error_response():
    """Перевірка стандартної структури помилки."""

    result = ErrorResponse(
        detail="Resource not found"
    )

    assert result.model_dump() == {
        "detail": "Resource not found"
    }
