import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.engine import URL

DB_HOST = os.getenv("DB_HOST") or os.getenv("POSTGRES_HOST", "postgres")
DB_PORT = os.getenv("DB_PORT") or os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("DB_NAME") or os.getenv("POSTGRES_DB", "studyplanner")
DB_USER = os.getenv("DB_USER") or os.getenv("POSTGRES_USER", "auth_user")
DB_PASSWORD = (
    os.getenv("DB_PASSWORD")
    or os.getenv("AUTH_DB_PASSWORD")
    or os.getenv("POSTGRES_PASSWORD")
    or "auth_pass_123"
)

DATABASE_URL = URL.create(
    drivername="postgresql+psycopg2",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=int(DB_PORT),
    database=DB_NAME
)

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()