
"""
Спільні залежності Study Plan Service.

Модуль забезпечує єдиний механізм отримання
ідентифікатора користувача та параметрів пагінації.
"""

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Query
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer
)

from exceptions import (
    UnauthorizedError,
    ServiceUnavailableError
)


# ==========================================================
# 1. АВТЕНТИФІКАЦІЯ КОРИСТУВАЧА
# ==========================================================

# Схема отримання Bearer-токена
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user_id(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme)
    ]
) -> UUID:
    """Отримання ідентифікатора автентифікованого користувача."""

    # Перевірка наявності Bearer-токена
    if credentials is None or not credentials.credentials:
        raise UnauthorizedError()

    # До інтеграції перевірки JWT доступ залишається закритим
    raise ServiceUnavailableError(
        "Authentication service unavailable"
    )


# ==========================================================
# 2. ПАРАМЕТРИ ПАГІНАЦІЇ
# ==========================================================

@dataclass(frozen=True)
class PaginationParams:
    """Параметри посторінкового отримання записів."""

    limit: int = 50
    offset: int = 0


def get_pagination(
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=100,
            description="Максимальна кількість записів"
        )
    ] = 50,

    offset: Annotated[
        int,
        Query(
            ge=0,
            description="Кількість пропущених записів"
        )
    ] = 0
) -> PaginationParams:
    """Отримання перевірених параметрів пагінації."""

    return PaginationParams(
        limit=limit,
        offset=offset
    )


# ==========================================================
# 3. СПІЛЬНІ ТИПИ ЗАЛЕЖНОСТЕЙ
# ==========================================================

CurrentUserId = Annotated[
    UUID,
    Depends(get_current_user_id)
]

Pagination = Annotated[
    PaginationParams,
    Depends(get_pagination)
]
