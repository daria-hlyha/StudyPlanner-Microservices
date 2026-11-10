import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

POSTGRES_USER = os.getenv("POSTGRES_USER", "studyplanner_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "445566")
POSTGRES_DB = os.getenv("POSTGRES_DB", "studyplanner")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")

# Додаємо +psycopg2, щоб SQLAlchemy чітко знала, який драйвер використовувати
DATABASE_URL = f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:5432/{POSTGRES_DB}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()