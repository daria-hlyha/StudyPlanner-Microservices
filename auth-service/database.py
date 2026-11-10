import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Отримуємо параметри підключення зі змінних оточення (.env)
POSTGRES_USER = os.getenv("POSTGRES_USER", "studyplanner_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "445566")
POSTGRES_DB = os.getenv("POSTGRES_DB", "studyplanner")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")

# Формуємо URL підключення до PostgreSQL
DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:5432/{POSTGRES_DB}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
