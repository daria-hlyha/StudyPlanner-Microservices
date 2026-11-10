from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db

app = FastAPI(title="Auth Service")

# Старий маршрут залишаємо, щоб знати, що сервіс працює
@app.get("/")
def home():
    return {"message": "Auth Service is running"}

# Новий маршрут для перевірки підключення до PostgreSQL
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
        raise HTTPException(status_code=500, detail=f"Database connection error: {str(e)}")