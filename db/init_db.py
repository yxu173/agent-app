#!/usr/bin/env python3
"""
Database initialization script.
Creates required tables if they don't exist.
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, MetaData, inspect
from sqlalchemy.exc import OperationalError
from db.settings import db_settings
from db.tables.excel_workflow_sessions import ExcelWorkflowSessions
from db.tables.workflow_settings import WorkflowSettings
from agno.utils.log import logger


def init_database():
    """Initialize the database with required tables."""
    try:
        # Get the database URL
        db_url = db_settings.get_db_url()
        logger.info(f"Initializing database: {db_url}")
        
        # Create engine
        engine = create_engine(db_url)
        
        # Create inspector to check existing tables
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        logger.info(f"Existing tables: {existing_tables}")
        
        # Create tables if they don't exist
        tables_to_create = []
        
        if 'excel_workflow_sessions' not in existing_tables:
            tables_to_create.append('excel_workflow_sessions')
            logger.info("Creating excel_workflow_sessions table...")
            ExcelWorkflowSessions.__table__.create(engine, checkfirst=True)
        
        if 'workflow_settings' not in existing_tables:
            tables_to_create.append('workflow_settings')
            logger.info("Creating workflow_settings table...")
            WorkflowSettings.__table__.create(engine, checkfirst=True)
        
        if tables_to_create:
            logger.info(f"Created tables: {tables_to_create}")
        else:
            logger.info("All required tables already exist")
        
        # Verify tables exist
        inspector = inspect(engine)
        final_tables = inspector.get_table_names()
        logger.info(f"Final tables: {final_tables}")
        
        # Check if required tables exist
        required_tables = ['excel_workflow_sessions', 'workflow_settings']
        missing_tables = [table for table in required_tables if table not in final_tables]
        
        if missing_tables:
            logger.error(f"Missing required tables: {missing_tables}")
            return False
        else:
            logger.info("✅ Database initialization completed successfully")
            return True
            
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return False


if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
