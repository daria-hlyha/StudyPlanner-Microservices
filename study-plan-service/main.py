from fastapi import FastAPI
from database import get_connection
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="Study Plan Service")


@app.get("/")
def home():
    return {"message": "Study Plan Service is running"}


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


# Збирання метрик FastAPI
Instrumentator().instrument(app).expose(app)
