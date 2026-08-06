import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://data_quality_user:local_password@database:5432/data_quality",
)


engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)


SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


def check_database_connection() -> bool:
    """
    Run a simple query to verify that PostgreSQL is reachable.
    """
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    return True
