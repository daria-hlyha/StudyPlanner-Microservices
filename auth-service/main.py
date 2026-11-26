
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db
from rabbitmq import get_rabbitmq_connection
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="Auth Service")


@app.get("/")
def home():
    return {"message": "Auth Service is running"}


# Перевірка підключення до PostgreSQL
@app.get("/db-check")
def db_check(db: Session = Depends(get_db)):
    try:
        result = db.execute(
            text("SELECT current_user, current_database(), current_schema()")
        ).fetchone()

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


# Збирання метрик FastAPI для Prometheus
Instrumentator().instrument(app).expose(app)
