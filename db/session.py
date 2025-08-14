from typing import Generator
import os

from sqlalchemy.engine import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from db.settings import db_settings

# Create SQLAlchemy Engine using a database URL
db_url: str = db_settings.get_db_url()

# SQLite-specific configuration
if db_url.startswith("sqlite"):
    # Ensure the directory exists
    db_file = db_url.replace("sqlite:///", "")
    db_dir = os.path.dirname(db_file)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    
    # SQLite engine with proper configuration
    db_engine: Engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},  # Allow multiple threads
        pool_pre_ping=True,
        echo=False,  # Set to True for SQL debugging
    )
else:
    # For other databases (fallback)
    db_engine: Engine = create_engine(db_url, pool_pre_ping=True)

# Create a SessionLocal class
SessionLocal: sessionmaker[Session] = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency to get a database session.

    Yields:
        Session: An SQLAlchemy database session.
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
