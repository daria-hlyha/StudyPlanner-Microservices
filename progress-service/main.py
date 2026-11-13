from fastapi import FastAPI
from database import get_connection
from rabbitmq import get_rabbitmq_connection
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="Study Plan Service")


@app.get("/")
def home():
    return {"message": "Progress Service is running"}


# Перевірка підключення до PostgreSQL (схема progress)
@app.get("/db-check")
def check_database():
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT current_user, current_database()")
                result = cursor.fetchone()

        return {
            "status": "connected",
            "user": result[0],
            "database": result[1]
        }

    except Exception:
        return {"status": "error"}


# Перевірка підключення до RabbitMQ
@app.get("/rabbitmq-check")
def check_rabbitmq():
    try:
        connection = get_rabbitmq_connection()
        connection.close()
        return {"status": "connected"}

    except Exception:
        return {"status": "error"}


# Збирання метрик FastAPI для Prometheus
Instrumentator().instrument(app).expose(app)
