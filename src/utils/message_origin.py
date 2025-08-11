"""
Message Origin Detection Utilities
Distinguishes between human agent messages and customer messages in Slack integration.
"""

import logging
from typing import Dict, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class MessageOriginDetector:
    """Detects the origin of messages to determine routing logic."""
    
    def __init__(self):
        """Initialize message origin detector."""
        self._known_human_agents = {}  # Will be populated from session data
    
    async def detect_message_origin(
        self, 
        slack_event: Dict, 
        session_manager
    ) -> Tuple[str, Optional[Dict]]:
        """
        Detect if a message is from a human agent or customer.
        
        Args:
            slack_event: Slack event data containing message info
            session_manager: SessionManager instance for checking assignments
        
        Returns:
            Tuple of (origin_type, origin_info)
            origin_type: "human_agent", "customer", or "unknown"
            origin_info: Dict with additional info about the sender
        """
        try:
            user_id = slack_event.get('user')
            channel_id = slack_event.get('channel')
            thread_ts = slack_event.get('thread_ts')
            message_text = slack_event.get('text', '')
            
            if not user_id:
                return "unknown", None
            
            # IMPROVED: First check if this user is assigned to ANY session (more reliable)
            assigned_sessions = await session_manager.get_sessions_by_state("assigned")
            
            for session in assigned_sessions:
                if session.assigned_to == user_id and session.ai_disabled:
                    agent_info = {
                        'session_id': session.session_id,
                        'agent_id': user_id,
                        'agent_name': session.assigned_agent_name or 'Human Agent',
                        'customer_channel': session.channel_id,
                        'message_text': message_text,
                        'timestamp': datetime.now().isoformat()
                    }
                    logger.info(f"✅ Detected human agent message from {session.assigned_agent_name} (user {user_id}) for session {session.session_id}")
                    return "human_agent", agent_info
            
            # Fallback: Check by thread (original logic)
            session_info = await self._find_session_by_thread(
                thread_ts or slack_event.get('ts'), 
                channel_id, 
                session_manager
            )
            
            if session_info:
                session_id, session = session_info
                
                # Check if sender is the assigned human agent
                if session.assigned_to == user_id and session.ai_disabled:
                    agent_info = {
                        'session_id': session_id,
                        'agent_id': user_id,
                        'agent_name': session.assigned_agent_name or 'Human Agent',
                        'customer_channel': session.channel_id,
                        'message_text': message_text,
                        'timestamp': datetime.now().isoformat()
                    }
                    logger.info(f"✅ Detected human agent message from {session.assigned_agent_name} for session {session_id} (via thread)")
                    return "human_agent", agent_info
                
                # If session exists but sender is not the assigned agent, it might be the customer
                # (though customers shouldn't be in Slack - this is just a safety check)
                elif user_id != session.assigned_to:
                    logger.warning(f"Message from unrecognized user {user_id} in escalated session {session_id}")
                    return "unknown", {'user_id': user_id, 'session_id': session_id}
            
            # If no session found, this is likely a regular Slack message (not part of escalation)
            logger.debug(f"Message from {user_id} not associated with any escalated session")
            return "unknown", {'user_id': user_id, 'channel_id': channel_id}
            
        except Exception as e:
            logger.error(f"Error detecting message origin: {e}")
            return "unknown", None
    
    async def _find_session_by_thread(
        self, 
        thread_ts: str, 
        channel_id: str, 
        session_manager
    ) -> Optional[Tuple[str, 'ConversationSession']]:
        """Find session associated with a Slack thread."""
        try:
            if not thread_ts:
                return None
            
            # Get all assigned sessions (human-handled sessions)
            assigned_sessions = await session_manager.get_sessions_by_state("assigned")
            
            for session in assigned_sessions:
                # Check if thread_ts matches
                if session.thread_ts == thread_ts:
                    return session.session_id, session
                    
                # Also check if the thread_ts appears in session history
                for message in session.history:
                    if (message.get('thread_ts') == thread_ts or 
                        message.get('ts') == thread_ts):
                        return session.session_id, session
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding session by thread {thread_ts}: {e}")
            return None
    
    async def is_customer_message_in_chainlit(
        self, 
        message_content: str, 
        user_info: Dict, 
        session_manager
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if a Chainlit message is from a customer with an active human-assigned session.
        
        Returns:
            Tuple of (is_customer_with_human_agent, session_id)
        """
        try:
            # Look for session by user info
            user_id = f"chainlit_{user_info.get('email', 'unknown')}"
            
            # Get sessions for this user
            user_sessions = await session_manager.get_sessions_by_user(user_id)
            
            # Check for active assigned sessions
            for session in user_sessions:
                if session.state.value == "assigned" and session.ai_disabled:
                    logger.info(f"Customer message from {user_info.get('name')} in human-assigned session {session.session_id}")
                    return True, session.session_id
            
            return False, None
            
        except Exception as e:
            logger.error(f"Error checking customer message status: {e}")
            return False, None
    
    def should_route_to_human_channel(self, origin_type: str) -> bool:
        """Determine if message should be routed to human agent channel."""
        return origin_type == "customer_with_human"
    
    def should_route_to_customer_platform(self, origin_type: str) -> bool:
        """Determine if message should be routed to customer platform."""
        return origin_type == "human_agent"
    
    def should_disable_ai_processing(self, origin_type: str, session_info: Optional[Dict]) -> bool:
        """Determine if AI processing should be disabled."""
        if origin_type == "human_agent":
            return True
        
        if session_info and session_info.get('ai_disabled'):
            return True
            
        return False