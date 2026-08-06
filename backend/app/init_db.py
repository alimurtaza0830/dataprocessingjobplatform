from app.database import Base, engine
from app.models import ProcessingJob


def create_database_tables() -> None:
    """
    Create all database tables defined by SQLAlchemy models.

    Importing ProcessingJob registers the processing_jobs table
    with Base.metadata before create_all() runs.
    """
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    create_database_tables()
    print("Database tables created successfully")
