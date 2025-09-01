from sqlalchemy import Column, String, Text, DateTime, Integer, Boolean
from sqlalchemy.sql import func
from db.tables.base import Base


class ExcelWorkflowSessions(Base):
    """Database table for storing Excel workflow session data."""
    
    __tablename__ = "excel_workflow_sessions"
    
    # Primary key - session ID (UUID)
    session_id = Column(String(36), primary_key=True, nullable=False)
    
    # Session name (user-friendly name)
    session_name = Column(String(255), nullable=False, unique=True)
    
    # File path of the uploaded Excel file
    file_path = Column(Text, nullable=False)
    
    # Original file name
    original_filename = Column(String(255), nullable=False)
    
    # Niche/topic for keyword analysis
    niche = Column(String(255), nullable=False)
    
    # Chunk size used for processing
    chunk_size = Column(Integer, nullable=False)
    
    # Results file path (where processed results are saved)
    results_file_path = Column(Text, nullable=True)
    
    # Total keywords processed
    total_keywords = Column(Integer, default=0, nullable=False)
    
    # Processing status
    status = Column(String(50), default="pending", nullable=False)  # pending, processing, completed, failed
    
    # User ID (if available)
    user_id = Column(String(100), nullable=True)
    
    # Model ID used for processing
    model_id = Column(String(100), nullable=True)
    
    # Whether the session is active
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<ExcelWorkflowSessions(session_id='{self.session_id}', session_name='{self.session_name}')>"
