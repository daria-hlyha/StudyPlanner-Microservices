
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from database import get_connection
from rabbitmq import get_rabbitmq_connection
from prometheus_fastapi_instrumentator import Instrumentator

from db_init import init_db
from progress_api import router as progress_router


logging.basicConfig(level=logging.INFO)


# Створення предметних таблиць у схемі progress під час запуску
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Progress Service",
    description=(
        "Сервіс відстеження прогресу (d): відстеження завдань і модулів, "
        "статуси завдань, розрахунок прогресу планів і досягнення цілей."
    ),
    lifespan=lifespan,
)


@app.get("/")
def home():
    return {"message": "Progress Service is running"}


# Перевірка підключення до PostgreSQL
@app.get("/db-check")
def check_database():
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT current_user, current_database(), current_schema()"
                )
                result = cursor.fetchone()

        return {
            "status": "connected",
            "user": result[0],
            "database": result[1],
            "current_schema": result[2]
        }

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Database connection error"
        )


# Перевірка підключення до RabbitMQ
@app.get("/rabbitmq-check")
def check_rabbitmq():
    try:
        connection = get_rabbitmq_connection()
        connection.close()

        return {"status": "connected"}

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="RabbitMQ connection error"
        )


# Предметна функціональність сервісу відстеження прогресу
app.include_router(progress_router)


# Збирання метрик FastAPI для Prometheus
Instrumentator().instrument(app).expose(app)
