from sqlalchemy import Column, String, Text, DateTime, Boolean
from sqlalchemy.sql import func
from db.tables.base import Base


class WorkflowSettings(Base):
    """Database table for storing workflow-specific settings."""
    
    __tablename__ = "workflow_settings"
    
    # Primary key - workflow name
    workflow_name = Column(String(100), primary_key=True, nullable=False)
    
    # Setting key - specific setting within the workflow
    setting_key = Column(String(100), primary_key=True, nullable=False)
    
    # Setting value - the actual setting content
    setting_value = Column(Text, nullable=False)
    
    # Description of the setting
    description = Column(Text, nullable=True)
    
    # Whether this setting is active
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<WorkflowSettings(workflow_name='{self.workflow_name}', setting_key='{self.setting_key}')>"
