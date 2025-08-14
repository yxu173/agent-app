from os import path

from pydantic_settings import BaseSettings


class DbSettings(BaseSettings):
    """Database settings that can be set using environment variables.

    Reference: https://docs.pydantic.dev/latest/usage/pydantic_settings/
    """

    # SQLite database configuration
    db_file: str = "tmp/agent_app.db"
    db_driver: str = "sqlite"
    # Create/Upgrade database on startup using alembic
    migrate_db: bool = False

    def get_db_url(self) -> str:
        # Ensure tmp directory exists
        db_dir = path.dirname(self.db_file)
        if db_dir and not path.exists(db_dir):
            import os
            os.makedirs(db_dir, exist_ok=True)
        
        # Return SQLite URL
        db_url = f"sqlite:///{self.db_file}"
        
        # Validate database connection
        if not db_url:
            raise ValueError("Could not build database connection")
        return db_url


# Create DbSettings object
db_settings = DbSettings()
