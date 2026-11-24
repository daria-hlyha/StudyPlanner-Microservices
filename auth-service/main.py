
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="Auth Service")

Instrumentator().instrument(app).expose(app)


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
