
"""
Автоматизовані тести спільних допоміжних функцій
бізнес-логіки Study Plan Service.
"""

from datetime import (
    date,
    datetime,
    timedelta,
    timezone
)

from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from schemas.common import BaseSchema

from exceptions import (
    BadRequestError,
    NotFoundError
)

from services.common import (
    require_resource,
    require_ownership,
    get_update_data,
    validate_date_range,
    validate_datetime_range,
    to_utc,
    get_user_lock_key,
    lock_user_transaction,
    write_transaction
)


# ==========================================================
# 1. ТЕСТОВІ ДАНІ
# ==========================================================

USER_ID = UUID(
    "11111111-1111-4111-8111-111111111111"
)

OTHER_USER_ID = UUID(
    "22222222-2222-4222-8222-222222222222"
)


class ExampleUpdate(BaseSchema):
    """Тестова схема часткового оновлення."""

    title: str | None = None

    description: str | None = None


# ==========================================================
# 2. ПЕРЕВІРКА РЕСУРСІВ
# ==========================================================

def test_existing_resource():
    resource = {
        "id": USER_ID,
        "title": "Test"
    }

    assert require_resource(resource) is resource


def test_missing_resource():
    with pytest.raises(NotFoundError):
        require_resource(None)


def test_custom_resource_error():
    with pytest.raises(
        NotFoundError,
        match="Study plan not found"
    ):
        require_resource(
            None,
            "Study plan not found"
        )


def test_resource_owner():
    assert require_ownership(
        USER_ID,
        USER_ID
    ) is None


def test_foreign_resource():
    with pytest.raises(NotFoundError):
        require_ownership(
            OTHER_USER_ID,
            USER_ID
        )


# ==========================================================
# 3. ПЕРЕВІРКА PATCH-ЗАПИТІВ
# ==========================================================

def test_update_data():
    data = ExampleUpdate(
        title="New title"
    )

    assert get_update_data(data) == {
        "title": "New title"
    }


def test_explicit_null_update():
    data = ExampleUpdate(
        description=None
    )

    assert get_update_data(data) == {
        "description": None
    }


def test_multiple_update_fields():
    data = ExampleUpdate(
        title="New title",
        description=None
    )

    assert get_update_data(data) == {
        "title": "New title",
        "description": None
    }


def test_empty_update():
    with pytest.raises(BadRequestError):
        get_update_data(
            ExampleUpdate()
        )


# ==========================================================
# 4. ПЕРЕВІРКА КАЛЕНДАРНИХ ДАТ
# ==========================================================

@pytest.mark.parametrize(
    "start_date,end_date",
    [
        (None, None),
        (date(2026, 12, 1), None),
        (None, date(2026, 12, 10)),
        (date(2026, 12, 1), date(2026, 12, 1)),
        (date(2026, 12, 1), date(2026, 12, 10))
    ]
)
def test_valid_date_range(
    start_date,
    end_date
):
    assert validate_date_range(
        start_date,
        end_date
    ) is None


def test_invalid_date_range():
    with pytest.raises(BadRequestError):
        validate_date_range(
            date(2026, 12, 10),
            date(2026, 12, 1)
        )


# ==========================================================
# 5. ПЕРЕВІРКА ДАТИ ТА ЧАСУ
# ==========================================================

def test_utc_conversion():
    source = datetime(
        2026, 12, 1, 12, 0,
        tzinfo=timezone(
            timedelta(hours=2)
        )
    )

    expected = datetime(
        2026, 12, 1, 10, 0,
        tzinfo=timezone.utc
    )

    assert to_utc(source) == expected

    assert to_utc(source).tzinfo == timezone.utc


def test_naive_datetime():
    with pytest.raises(BadRequestError):
        to_utc(
            datetime(2026, 12, 1, 10, 0)
        )


def test_valid_datetime_range():
    start = datetime(
        2026, 12, 1, 10, 0,
        tzinfo=timezone.utc
    )

    end = start + timedelta(hours=1)

    assert validate_datetime_range(
        start,
        end
    ) is None


@pytest.mark.parametrize(
    "minutes",
    [0, -1, -60]
)
def test_invalid_datetime_range(minutes):
    start = datetime(
        2026, 12, 1, 10, 0,
        tzinfo=timezone.utc
    )

    end = start + timedelta(
        minutes=minutes
    )

    with pytest.raises(BadRequestError):
        validate_datetime_range(
            start,
            end
        )


def test_datetime_range_different_timezones():
    start = datetime(
        2026, 12, 1, 12, 0,
        tzinfo=timezone(
            timedelta(hours=2)
        )
    )

    end = datetime(
        2026, 12, 1, 11, 0,
        tzinfo=timezone.utc
    )

    assert validate_datetime_range(
        start,
        end
    ) is None


def test_equal_instants_different_timezones():
    start = datetime(
        2026, 12, 1, 12, 0,
        tzinfo=timezone(
            timedelta(hours=2)
        )
    )

    end = datetime(
        2026, 12, 1, 10, 0,
        tzinfo=timezone.utc
    )

    with pytest.raises(BadRequestError):
        validate_datetime_range(
            start,
            end
        )


# ==========================================================
# 6. ПЕРЕВІРКА КЛЮЧІВ БЛОКУВАННЯ
# ==========================================================

def test_user_lock_key_is_integer():
    assert isinstance(
        get_user_lock_key(USER_ID),
        int
    )


def test_user_lock_key_is_stable():
    assert (
        get_user_lock_key(USER_ID)
        == get_user_lock_key(USER_ID)
    )


def test_different_user_lock_keys():
    assert (
        get_user_lock_key(USER_ID)
        != get_user_lock_key(OTHER_USER_ID)
    )


def test_user_lock_key_range():
    key = get_user_lock_key(USER_ID)

    assert -(2 ** 63) <= key <= 2 ** 63 - 1


def test_transaction_lock():
    connection = MagicMock()

    connection.autocommit = False

    cursor = (
        connection.cursor.return_value
        .__enter__.return_value
    )

    lock_user_transaction(
        connection,
        USER_ID
    )

    cursor.execute.assert_called_once_with(
        "SELECT pg_advisory_xact_lock(%s)",
        (get_user_lock_key(USER_ID),)
    )


def test_transaction_lock_rejects_autocommit():
    connection = MagicMock()

    connection.autocommit = True

    with pytest.raises(RuntimeError):
        lock_user_transaction(
            connection,
            USER_ID
        )

    connection.cursor.assert_not_called()


# ==========================================================
# 7. ПЕРЕВІРКА ТРАНЗАКЦІЙ ЗАПИСУ
# ==========================================================

def test_write_transaction():
    connection = MagicMock()

    connection.__enter__.return_value = connection

    with (
        patch(
            "services.common.get_connection",
            return_value=connection
        ) as connect,

        patch(
            "services.common.lock_user_transaction"
        ) as lock
    ):

        with write_transaction(USER_ID) as result:

            assert result is connection

            lock.assert_called_once_with(
                connection,
                USER_ID
            )

        connect.assert_called_once_with()

        connection.__exit__.assert_called_once_with(
            None,
            None,
            None
        )


def test_write_transaction_error():
    connection = MagicMock()

    connection.__enter__.return_value = connection

    connection.__exit__.return_value = False

    with (
        patch(
            "services.common.get_connection",
            return_value=connection
        ),

        patch(
            "services.common.lock_user_transaction"
        )
    ):

        with pytest.raises(
            RuntimeError,
            match="Test transaction error"
        ):

            with write_transaction(USER_ID):

                raise RuntimeError(
                    "Test transaction error"
                )

    connection.__exit__.assert_called_once()

    error_type, error, traceback = (
        connection.__exit__.call_args.args
    )

    assert error_type is RuntimeError

    assert str(error) == "Test transaction error"

    assert traceback is not None
