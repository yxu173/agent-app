#!/usr/bin/env python3
"""
Standalone script to ensure database tables exist.
This script can be run in any environment (local, Docker, etc.) to create required tables.
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def ensure_db_tables():
    """Ensure required database tables exist."""
    try:
        # Import after path setup
        from db.init_db import init_database
        
        print("🔧 Ensuring database tables exist...")
        success = init_database()
        
        if success:
            print("✅ Database tables are ready!")
            return True
        else:
            print("❌ Failed to create database tables")
            return False
            
    except Exception as e:
        print(f"❌ Error ensuring database tables: {e}")
        return False

if __name__ == "__main__":
    success = ensure_db_tables()
    sys.exit(0 if success else 1)
