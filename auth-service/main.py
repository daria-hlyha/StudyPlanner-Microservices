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


@app.get("/db-check")
def db_check(db: Session = Depends(get_db)):
    try:
        result = db.execute(text("SELECT current_schema();")).fetchone()
        return {
            "status": "connected",
            "database": "studyplanner",
            "current_schema": result[0]
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database connection error: {str(e)}"
        )
