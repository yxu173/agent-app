import os
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import and_

from db.session import get_db
from db.tables.excel_workflow_sessions import ExcelWorkflowSessions
from agno.utils.log import logger


class ExcelSessionManager:
    """Manager for Excel workflow sessions with database persistence."""
    
    def __init__(self):
        # Initialize database tables first
        self._init_database()
        self.db_session = next(get_db())
    
    def _init_database(self):
        """Initialize database tables if they don't exist."""
        try:
            from db.init_db import init_database
            init_database()
        except Exception as e:
            logger.warning(f"Database initialization failed: {e}")
            # Continue without failing the session manager initialization
    
    def __del__(self):
        """Close database session when manager is destroyed."""
        if hasattr(self, 'db_session') and self.db_session:
            try:
                self.db_session.close()
            except Exception:
                pass  # Ignore errors during cleanup
    
    def create_session(
        self,
        session_name: str,
        file_path: str,
        original_filename: str,
        niche: str,
        chunk_size: int,
        user_id: Optional[str] = None,
        model_id: Optional[str] = None
    ) -> str:
        """
        Create a new Excel workflow session.
        
        Args:
            session_name: User-friendly name for the session
            file_path: Path to the uploaded Excel file
            original_filename: Original name of the uploaded file
            niche: Niche/topic for keyword analysis
            chunk_size: Chunk size for processing
            user_id: Optional user ID
            model_id: Optional model ID used for processing
            
        Returns:
            str: Session ID (UUID)
        """
        try:
            # Generate a unique session ID
            session_id = str(uuid.uuid4())
            
            # Create session record
            session_record = ExcelWorkflowSessions(
                session_id=session_id,
                session_name=session_name,
                file_path=file_path,
                original_filename=original_filename,
                niche=niche,
                chunk_size=chunk_size,
                user_id=user_id,
                model_id=model_id,
                status="pending",
                is_active=True
            )
            
            self.db_session.add(session_record)
            self.db_session.commit()
            
            logger.info(f"Created Excel session: {session_id} with name: {session_name}")
            return session_id
            
        except Exception as e:
            try:
                self.db_session.rollback()
            except Exception:
                pass  # Ignore rollback errors
            logger.error(f"Error creating Excel session: {e}")
            raise
    
    def get_session_by_name(self, session_name: str) -> Optional[Dict[str, Any]]:
        """
        Get session data by session name.
        
        Args:
            session_name: The session name to look up
            
        Returns:
            Dict with session data or None if not found
        """
        try:
            session_record = self.db_session.query(ExcelWorkflowSessions).filter(
                and_(
                    ExcelWorkflowSessions.session_name == session_name,
                    ExcelWorkflowSessions.is_active == True
                )
            ).first()
            
            if session_record:
                return self._session_record_to_dict(session_record)
            return None
            
        except Exception as e:
            logger.error(f"Error getting session by name '{session_name}': {e}")
            return None
    
    def get_session_by_id(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session data by session ID.
        
        Args:
            session_id: The session ID to look up
            
        Returns:
            Dict with session data or None if not found
        """
        try:
            session_record = self.db_session.query(ExcelWorkflowSessions).filter(
                and_(
                    ExcelWorkflowSessions.session_id == session_id,
                    ExcelWorkflowSessions.is_active == True
                )
            ).first()
            
            if session_record:
                return self._session_record_to_dict(session_record)
            return None
            
        except Exception as e:
            logger.error(f"Error getting session by ID '{session_id}': {e}")
            return None
    
    def update_session_status(
        self,
        session_id: str,
        status: str,
        results_file_path: Optional[str] = None,
        total_keywords: Optional[int] = None,
        enhanced_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update session status and related data.
        
        Args:
            session_id: The session ID to update
            status: New status (pending, processing, completed, failed)
            results_file_path: Optional path to results file
            total_keywords: Optional total number of keywords processed
            enhanced_data: Optional enhanced session data
            
        Returns:
            bool: True if update was successful
        """
        try:
            session_record = self.db_session.query(ExcelWorkflowSessions).filter(
                ExcelWorkflowSessions.session_id == session_id
            ).first()
            
            if not session_record:
                logger.warning(f"Session not found for update: {session_id}")
                return False
            
            session_record.status = status
            session_record.updated_at = datetime.utcnow()
            
            if results_file_path:
                session_record.results_file_path = results_file_path
            
            if total_keywords is not None:
                session_record.total_keywords = total_keywords
            
            if status == "completed":
                session_record.completed_at = datetime.utcnow()
            
            # Store enhanced data if provided
            if enhanced_data is not None:
                # For now, we'll store it as a JSON string in a comment field
                # In a future version, we could add a dedicated column for this
                import json
                try:
                    enhanced_json = json.dumps(enhanced_data)
                    # Store in a way that doesn't break existing functionality
                    # For now, we'll log it and could extend the database schema later
                    logger.info(f"Enhanced data for session {session_id}: {enhanced_json[:200]}...")
                except Exception as e:
                    logger.warning(f"Could not serialize enhanced data: {e}")
            
            self.db_session.commit()
            logger.info(f"Updated session {session_id} status to {status}")
            return True
            
        except Exception as e:
            try:
                self.db_session.rollback()
            except Exception:
                pass  # Ignore rollback errors
            logger.error(f"Error updating session {session_id}: {e}")
            return False

    def store_workflow_response(self, session_id: str, response_content: str, response_type: str = "assistant") -> bool:
        """
        Store workflow response in session for conversation history.
        
        Args:
            session_id: The session ID to store response for
            response_content: The content of the response
            response_type: Type of response (user, assistant, system)
            
        Returns:
            bool: True if storage was successful
        """
        try:
            # Store in session cache for now (could be extended to database later)
            if not hasattr(self, '_workflow_responses'):
                self._workflow_responses = {}
            
            if session_id not in self._workflow_responses:
                self._workflow_responses[session_id] = []
            
            self._workflow_responses[session_id].append({
                'type': response_type,
                'content': response_content,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            logger.info(f"Stored workflow response for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing workflow response for session {session_id}: {e}")
            return False

    def get_workflow_responses(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get workflow responses for a session.
        
        Args:
            session_id: The session ID to get responses for
            
        Returns:
            List of response dictionaries
        """
        try:
            if hasattr(self, '_workflow_responses') and session_id in self._workflow_responses:
                return self._workflow_responses[session_id]
            return []
            
        except Exception as e:
            logger.error(f"Error getting workflow responses for session {session_id}: {e}")
            return []

    def clear_workflow_responses(self, session_id: str) -> bool:
        """
        Clear workflow responses for a session.
        
        Args:
            session_id: The session ID to clear responses for
            
        Returns:
            bool: True if clearing was successful
        """
        try:
            if hasattr(self, '_workflow_responses') and session_id in self._workflow_responses:
                del self._workflow_responses[session_id]
                logger.info(f"Cleared workflow responses for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing workflow responses for session {session_id}: {e}")
            return False
    
    def list_user_sessions(
        self,
        user_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        List sessions for a user.
        
        Args:
            user_id: Optional user ID to filter by
            limit: Maximum number of sessions to return
            
        Returns:
            List of session dictionaries
        """
        try:
            query = self.db_session.query(ExcelWorkflowSessions).filter(
                ExcelWorkflowSessions.is_active == True
            )
            
            if user_id:
                query = query.filter(ExcelWorkflowSessions.user_id == user_id)
            
            sessions = query.order_by(
                ExcelWorkflowSessions.created_at.desc()
            ).limit(limit).all()
            
            return [self._session_record_to_dict(session) for session in sessions]
            
        except Exception as e:
            logger.error(f"Error listing sessions for user {user_id}: {e}")
            return []
    
    def delete_session(self, session_id: str) -> bool:
        """
        Soft delete a session (mark as inactive).
        
        Args:
            session_id: The session ID to delete
            
        Returns:
            bool: True if deletion was successful
        """
        try:
            session_record = self.db_session.query(ExcelWorkflowSessions).filter(
                ExcelWorkflowSessions.session_id == session_id
            ).first()
            
            if not session_record:
                logger.warning(f"Session not found for deletion: {session_id}")
                return False
            
            session_record.is_active = False
            session_record.updated_at = datetime.utcnow()
            
            self.db_session.commit()
            logger.info(f"Deleted session: {session_id}")
            return True
            
        except Exception as e:
            try:
                self.db_session.rollback()
            except Exception:
                pass  # Ignore rollback errors
            logger.error(f"Error deleting session {session_id}: {e}")
            return False
    
    def _session_record_to_dict(self, session_record: ExcelWorkflowSessions) -> Dict[str, Any]:
        """Convert session record to dictionary."""
        return {
            'session_id': session_record.session_id,
            'session_name': session_record.session_name,
            'file_path': session_record.file_path,
            'original_filename': session_record.original_filename,
            'niche': session_record.niche,
            'chunk_size': session_record.chunk_size,
            'results_file_path': session_record.results_file_path,
            'total_keywords': session_record.total_keywords,
            'status': session_record.status,
            'user_id': session_record.user_id,
            'model_id': session_record.model_id,
            'is_active': session_record.is_active,
            'created_at': session_record.created_at,
            'updated_at': session_record.updated_at,
            'completed_at': session_record.completed_at
        }
    
    def generate_session_name(self, original_filename: str, niche: str) -> str:
        """
        Generate a user-friendly session name.
        
        Args:
            original_filename: Original filename
            niche: Niche/topic
            
        Returns:
            str: Generated session name
        """
        # Remove file extension
        base_name = os.path.splitext(original_filename)[0]
        
        # Create timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # Generate session name
        session_name = f"{base_name} - {niche} - {timestamp}"
        
        # Ensure uniqueness
        counter = 1
        original_name = session_name
        while self.get_session_by_name(session_name) is not None:
            session_name = f"{original_name} ({counter})"
            counter += 1
        
        return session_name
