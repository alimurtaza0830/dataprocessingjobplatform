from collections.abc import Generator

from sqlalchemy.orm import Session

from app.database import SessionLocal


def get_database_session() -> Generator[Session, None, None]:
    """
    Create one database session for an API request.

    The session is automatically closed after the request finishes,
    even if an error occurs.
    """
    database_session = SessionLocal()

    try:
        yield database_session
    finally:
        database_session.close()
