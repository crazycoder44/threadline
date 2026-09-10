"""SQLAlchemy engine/session setup."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import DBConfig

engine = create_engine(DBConfig.url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def init_db() -> None:
    """Legacy compatibility hook; apply schema changes with Alembic instead."""
    return None
