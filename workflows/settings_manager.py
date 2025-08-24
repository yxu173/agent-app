from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from db.session import get_db
from db.tables.workflow_settings import WorkflowSettings
from agno.utils.log import logger
import os
import json


class WorkflowSettingsManager:
    """Manager for workflow settings stored in the database."""
    
    # Fallback file for settings when database is not available
    FALLBACK_FILE = "tmp/workflow_settings.json"
    
    @staticmethod
    def _ensure_fallback_file():
        """Ensure the fallback file exists."""
        os.makedirs(os.path.dirname(WorkflowSettingsManager.FALLBACK_FILE), exist_ok=True)
        if not os.path.exists(WorkflowSettingsManager.FALLBACK_FILE):
            with open(WorkflowSettingsManager.FALLBACK_FILE, 'w') as f:
                json.dump({}, f)
    
    @staticmethod
    def _load_fallback_settings() -> Dict[str, Any]:
        """Load settings from fallback file."""
        WorkflowSettingsManager._ensure_fallback_file()
        try:
            with open(WorkflowSettingsManager.FALLBACK_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Error loading fallback settings: {e}")
            return {}
    
    @staticmethod
    def _save_fallback_settings(settings: Dict[str, Any]):
        """Save settings to fallback file."""
        WorkflowSettingsManager._ensure_fallback_file()
        try:
            with open(WorkflowSettingsManager.FALLBACK_FILE, 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving fallback settings: {e}")
    
    @staticmethod
    def get_setting(workflow_name: str, setting_key: str, default_value: Optional[str] = None) -> Optional[str]:
        """
        Get a setting value from the database or fallback file.
        
        Args:
            workflow_name: Name of the workflow
            setting_key: Key of the setting
            default_value: Default value if setting doesn't exist
            
        Returns:
            The setting value or default_value if not found
        """
        try:
            # Try database first
            db = next(get_db())
            setting = db.query(WorkflowSettings).filter(
                WorkflowSettings.workflow_name == workflow_name,
                WorkflowSettings.setting_key == setting_key,
                WorkflowSettings.is_active == True
            ).first()
            
            if setting:
                return setting.setting_value
                
        except Exception as e:
            logger.warning(f"Database access failed, using fallback: {e}")
        
        # Fallback to file-based storage
        try:
            settings = WorkflowSettingsManager._load_fallback_settings()
            workflow_settings = settings.get(workflow_name, {})
            return workflow_settings.get(setting_key, default_value)
        except Exception as e:
            logger.error(f"Error loading fallback settings: {e}")
            return default_value
        finally:
            if 'db' in locals():
                db.close()
    
    @staticmethod
    def save_setting(workflow_name: str, setting_key: str, setting_value: str, description: Optional[str] = None) -> bool:
        """
        Save a setting value to the database or fallback file.
        
        Args:
            workflow_name: Name of the workflow
            setting_key: Key of the setting
            setting_value: Value to save
            description: Optional description of the setting
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Try database first
            db = next(get_db())
            
            # Check if setting already exists
            existing_setting = db.query(WorkflowSettings).filter(
                WorkflowSettings.workflow_name == workflow_name,
                WorkflowSettings.setting_key == setting_key
            ).first()
            
            if existing_setting:
                # Update existing setting
                existing_setting.setting_value = setting_value
                if description:
                    existing_setting.description = description
                existing_setting.is_active = True
            else:
                # Create new setting
                new_setting = WorkflowSettings(
                    workflow_name=workflow_name,
                    setting_key=setting_key,
                    setting_value=setting_value,
                    description=description,
                    is_active=True
                )
                db.add(new_setting)
            
            db.commit()
            logger.info(f"Successfully saved setting {workflow_name}.{setting_key} to database")
            return True
            
        except Exception as e:
            logger.warning(f"Database save failed, using fallback: {e}")
            if 'db' in locals():
                db.rollback()
        
        # Fallback to file-based storage
        try:
            settings = WorkflowSettingsManager._load_fallback_settings()
            if workflow_name not in settings:
                settings[workflow_name] = {}
            settings[workflow_name][setting_key] = setting_value
            WorkflowSettingsManager._save_fallback_settings(settings)
            logger.info(f"Successfully saved setting {workflow_name}.{setting_key} to fallback file")
            return True
        except Exception as e:
            logger.error(f"Error saving fallback settings: {e}")
            return False
        finally:
            if 'db' in locals():
                db.close()
    
    @staticmethod
    def get_all_settings(workflow_name: str) -> Dict[str, str]:
        """
        Get all settings for a workflow.
        
        Args:
            workflow_name: Name of the workflow
            
        Returns:
            Dictionary of setting keys and values
        """
        try:
            # Try database first
            db = next(get_db())
            settings = db.query(WorkflowSettings).filter(
                WorkflowSettings.workflow_name == workflow_name,
                WorkflowSettings.is_active == True
            ).all()
            
            return {setting.setting_key: setting.setting_value for setting in settings}
                
        except Exception as e:
            logger.warning(f"Database access failed, using fallback: {e}")
        
        # Fallback to file-based storage
        try:
            settings = WorkflowSettingsManager._load_fallback_settings()
            return settings.get(workflow_name, {})
        except Exception as e:
            logger.error(f"Error loading fallback settings: {e}")
            return {}
        finally:
            if 'db' in locals():
                db.close()
    
    @staticmethod
    def delete_setting(workflow_name: str, setting_key: str) -> bool:
        """
        Soft delete a setting by setting is_active to False.
        
        Args:
            workflow_name: Name of the workflow
            setting_key: Key of the setting
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Try database first
            db = next(get_db())
            setting = db.query(WorkflowSettings).filter(
                WorkflowSettings.workflow_name == workflow_name,
                WorkflowSettings.setting_key == setting_key
            ).first()
            
            if setting:
                setting.is_active = False
                db.commit()
                logger.info(f"Successfully deleted setting {workflow_name}.{setting_key} from database")
                return True
            else:
                logger.warning(f"Setting {workflow_name}.{setting_key} not found in database")
                
        except Exception as e:
            logger.warning(f"Database delete failed, using fallback: {e}")
            if 'db' in locals():
                db.rollback()
        
        # Fallback to file-based storage
        try:
            settings = WorkflowSettingsManager._load_fallback_settings()
            if workflow_name in settings and setting_key in settings[workflow_name]:
                del settings[workflow_name][setting_key]
                WorkflowSettingsManager._save_fallback_settings(settings)
                logger.info(f"Successfully deleted setting {workflow_name}.{setting_key} from fallback file")
                return True
            else:
                logger.warning(f"Setting {workflow_name}.{setting_key} not found in fallback file")
                return False
        except Exception as e:
            logger.error(f"Error deleting fallback settings: {e}")
            return False
        finally:
            if 'db' in locals():
                db.close()
