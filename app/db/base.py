"""SQLAlchemy engine/session setup."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import DBConfig

engine = create_engine(DBConfig.url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def init_db() -> None:
    """Create all tables. Replace with Alembic migrations once the schema stabilizes."""
    from app.db import models  # noqa: F401 (registers models on Base)
    Base.metadata.create_all(bind=engine)
