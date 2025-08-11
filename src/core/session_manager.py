"""
Session State Manager for Bidirectional Slack Responder System

Manages conversation sessions with UUID tracking, agent assignment, and state management
using Supabase as the backend database.
"""

import uuid
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import json
import logging

from supabase import create_client, Client
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class SessionState(str, Enum):
    """Session state enumeration."""
    ACTIVE = "active"
    ASSIGNED = "assigned"
    CLOSED = "closed"


@dataclass
class ConversationSession:
    """Conversation session data structure."""
    session_id: str
    user_id: str
    channel_id: str
    thread_ts: Optional[str]
    state: SessionState
    assigned_to: Optional[str]
    escalated_at: datetime
    escalation_reason: str
    history: List[Dict[str, Any]]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'channel_id': self.channel_id,
            'thread_ts': self.thread_ts,
            'state': self.state.value,
            'assigned_to': self.assigned_to,
            'escalated_at': self.escalated_at.isoformat(),
            'escalation_reason': self.escalation_reason,
            'history': json.dumps(self.history),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationSession':
        """Create from database dictionary."""
        return cls(
            session_id=data['session_id'],
            user_id=data['user_id'],
            channel_id=data['channel_id'],
            thread_ts=data.get('thread_ts'),
            state=SessionState(data['state']),
            assigned_to=data.get('assigned_to'),
            escalated_at=datetime.fromisoformat(data['escalated_at'].replace('Z', '+00:00')),
            escalation_reason=data['escalation_reason'],
            history=json.loads(data['history']) if data['history'] else [],
            created_at=datetime.fromisoformat(data['created_at'].replace('Z', '+00:00')) if data.get('created_at') else None,
            updated_at=datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00')) if data.get('updated_at') else None
        )


class SessionManager:
    """Session state manager using Supabase backend."""
    
    def __init__(self, supabase_url: str, supabase_key: str):
        """Initialize session manager with Supabase credentials."""
        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.table_name = 'conversation_sessions'
        logger.info("SessionManager initialized with Supabase")
    
    async def create_session(
        self, 
        user_id: str, 
        channel_id: str, 
        escalation_reason: str,
        history: Optional[List[Dict[str, Any]]] = None
    ) -> ConversationSession:
        """Create a new conversation session."""
        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        session = ConversationSession(
            session_id=session_id,
            user_id=user_id,
            channel_id=channel_id,
            thread_ts=None,
            state=SessionState.ACTIVE,
            assigned_to=None,
            escalated_at=now,
            escalation_reason=escalation_reason,
            history=history or [],
            created_at=now,
            updated_at=now
        )
        
        try:
            result = self.supabase.table(self.table_name).insert(session.to_dict()).execute()
            logger.info(f"Created session {session_id} for user {user_id}")
            return session
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise
    
    async def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """Retrieve a session by ID."""
        try:
            result = self.supabase.table(self.table_name).select("*").eq('session_id', session_id).execute()
            
            if result.data:
                return ConversationSession.from_dict(result.data[0])
            return None
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            raise
    
    async def get_user_active_session(self, user_id: str) -> Optional[ConversationSession]:
        """Get user's active or assigned session."""
        try:
            result = self.supabase.table(self.table_name).select("*").eq('user_id', user_id).in_('state', ['active', 'assigned']).order('escalated_at', desc=True).limit(1).execute()
            
            if result.data:
                return ConversationSession.from_dict(result.data[0])
            return None
        except Exception as e:
            logger.error(f"Failed to get user active session for {user_id}: {e}")
            raise
    
    async def assign_session(self, session_id: str, agent_slack_id: str, thread_ts: str) -> bool:
        """Assign a session to an agent."""
        try:
            now = datetime.now(timezone.utc)
            update_data = {
                'state': SessionState.ASSIGNED.value,
                'assigned_to': agent_slack_id,
                'thread_ts': thread_ts,
                'updated_at': now.isoformat()
            }
            
            result = self.supabase.table(self.table_name).update(update_data).eq('session_id', session_id).execute()
            
            if result.data:
                logger.info(f"Assigned session {session_id} to agent {agent_slack_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to assign session {session_id}: {e}")
            raise
    
    async def close_session(self, session_id: str) -> bool:
        """Close a conversation session."""
        try:
            now = datetime.now(timezone.utc)
            update_data = {
                'state': SessionState.CLOSED.value,
                'updated_at': now.isoformat()
            }
            
            result = self.supabase.table(self.table_name).update(update_data).eq('session_id', session_id).execute()
            
            if result.data:
                logger.info(f"Closed session {session_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to close session {session_id}: {e}")
            raise
    
    async def add_message_to_session(
        self, 
        session_id: str, 
        message: Dict[str, Any]
    ) -> bool:
        """Add a message to session history."""
        try:
            session = await self.get_session(session_id)
            if not session:
                logger.warning(f"Session {session_id} not found")
                return False
            
            # Add timestamp to message
            message['timestamp'] = datetime.now(timezone.utc).isoformat()
            session.history.append(message)
            
            now = datetime.now(timezone.utc)
            update_data = {
                'history': json.dumps(session.history),
                'updated_at': now.isoformat()
            }
            
            result = self.supabase.table(self.table_name).update(update_data).eq('session_id', session_id).execute()
            
            if result.data:
                logger.debug(f"Added message to session {session_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to add message to session {session_id}: {e}")
            raise
    
    async def get_assigned_sessions(self, agent_slack_id: str) -> List[ConversationSession]:
        """Get all sessions assigned to an agent."""
        try:
            result = self.supabase.table(self.table_name).select("*").eq('assigned_to', agent_slack_id).eq('state', SessionState.ASSIGNED.value).execute()
            
            return [ConversationSession.from_dict(data) for data in result.data]
        except Exception as e:
            logger.error(f"Failed to get assigned sessions for {agent_slack_id}: {e}")
            raise
    
    async def get_active_sessions(self) -> List[ConversationSession]:
        """Get all active (unassigned) sessions."""
        try:
            result = self.supabase.table(self.table_name).select("*").eq('state', SessionState.ACTIVE.value).order('escalated_at', desc=True).execute()
            
            return [ConversationSession.from_dict(data) for data in result.data]
        except Exception as e:
            logger.error(f"Failed to get active sessions: {e}")
            raise
    
    async def update_session_thread(self, session_id: str, thread_ts: str) -> bool:
        """Update session with Slack thread timestamp."""
        try:
            now = datetime.now(timezone.utc)
            update_data = {
                'thread_ts': thread_ts,
                'updated_at': now.isoformat()
            }
            
            result = self.supabase.table(self.table_name).update(update_data).eq('session_id', session_id).execute()
            
            if result.data:
                logger.debug(f"Updated session {session_id} with thread {thread_ts}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to update session thread {session_id}: {e}")
            raise
    
    async def cleanup_old_sessions(self, days_old: int = 30) -> int:
        """Clean up old closed sessions."""
        try:
            cutoff_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            cutoff_date = cutoff_date.replace(day=cutoff_date.day - days_old)
            
            result = self.supabase.table(self.table_name).delete().eq('state', SessionState.CLOSED.value).lt('updated_at', cutoff_date.isoformat()).execute()
            
            count = len(result.data) if result.data else 0
            logger.info(f"Cleaned up {count} old sessions")
            return count
        except Exception as e:
            logger.error(f"Failed to cleanup old sessions: {e}")
            raise
    
    async def get_session_stats(self) -> Dict[str, int]:
        """Get session statistics."""
        try:
            # Get counts for each state
            active_result = self.supabase.table(self.table_name).select("session_id", count="exact").eq('state', SessionState.ACTIVE.value).execute()
            assigned_result = self.supabase.table(self.table_name).select("session_id", count="exact").eq('state', SessionState.ASSIGNED.value).execute()
            closed_result = self.supabase.table(self.table_name).select("session_id", count="exact").eq('state', SessionState.CLOSED.value).execute()
            
            return {
                'active': active_result.count or 0,
                'assigned': assigned_result.count or 0,
                'closed': closed_result.count or 0,
                'total': (active_result.count or 0) + (assigned_result.count or 0) + (closed_result.count or 0)
            }
        except Exception as e:
            logger.error(f"Failed to get session stats: {e}")
            return {'active': 0, 'assigned': 0, 'closed': 0, 'total': 0}