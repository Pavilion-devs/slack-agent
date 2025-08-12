"""
Bidirectional Responder Agent

Core agent that handles escalated conversations with bidirectional communication
between Slack agents and users across different platforms (Chainlit, web, etc.)
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable, Union
import logging
from dataclasses import dataclass

from ..core.session_manager import SessionManager, ConversationSession, SessionState
from ..integrations.slack_thread_manager import SlackThreadManager
from ..models.schemas import SupportMessage, AgentResponse

logger = logging.getLogger(__name__)


@dataclass 
class ResponderConfig:
    """Configuration for responder agent."""
    auto_escalate_timeout: int = 300  # 5 minutes
    max_history_context: int = 10
    enable_smart_routing: bool = True
    escalation_channel: str = "support-escalations"  # Consolidated support channel
    sales_channel: str = "sales-activity"  # Demo bookings only


class ResponderAgent:
    """Bidirectional responder agent for human escalations."""
    
    def __init__(
        self,
        session_manager: SessionManager,
        thread_manager: SlackThreadManager,
        config: Optional[ResponderConfig] = None
    ):
        """Initialize responder agent."""
        self.session_manager = session_manager
        self.thread_manager = thread_manager
        self.config = config or ResponderConfig()
        
        # Message routing callbacks
        self.user_message_callbacks: Dict[str, Callable] = {}
        self.platform_handlers: Dict[str, Callable] = {}
        
        # Register thread manager callback
        self.thread_manager.register_message_callback(self._forward_to_user)
        
        logger.info("ResponderAgent initialized with bidirectional messaging")
    
    async def escalate_conversation(
        self,
        support_message: SupportMessage,
        escalation_reason: str,
        conversation_history: List[Dict[str, Any]],
        agent_context: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """Escalate a conversation to human agents."""
        try:
            # Check if user already has an active session
            existing_session = await self.session_manager.get_user_active_session(
                user_id=support_message.user_id
            )
            
            if existing_session:
                # Add to existing session
                await self.session_manager.add_message_to_session(
                    session_id=existing_session.session_id,
                    message={
                        'sender': 'User',
                        'content': support_message.content,
                        'message_type': 'user_message',
                        'platform': self._detect_platform(support_message.channel_id)
                    }
                )
                
                session = existing_session
                logger.info(f"Added message to existing session {session.session_id}")
            else:
                # Ensure original customer message is included in history
                enhanced_history = conversation_history.copy()
                
                # Add original customer message if not already present
                customer_message_found = any(
                    msg.get('content') == support_message.content and 
                    msg.get('sender') in ['Customer', 'customer', 'User'] 
                    for msg in enhanced_history
                )
                
                if not customer_message_found:
                    customer_msg = {
                        'sender': 'Customer',
                        'content': support_message.content,
                        'timestamp': support_message.timestamp.isoformat(),
                        'platform': self._detect_platform(support_message.channel_id),
                        'message_type': 'original_question'
                    }
                    # Insert at beginning to show the original question first
                    enhanced_history.insert(0, customer_msg)
                
                # Create new escalation session
                session = await self.session_manager.create_session(
                    user_id=support_message.user_id,
                    channel_id=support_message.channel_id,
                    escalation_reason=escalation_reason,
                    history=enhanced_history
                )
                logger.info(f"Created new escalation session {session.session_id} with {len(enhanced_history)} messages in history")
            
            # Prepare user context for Slack thread
            user_context = {
                'user_name': support_message.user_name,
                'user_email': support_message.user_email or 'N/A',
                'platform': self._detect_platform(support_message.channel_id),
                'original_message': support_message.content
            }
            
            # Create Slack escalation thread
            thread_ts = await self.thread_manager.create_escalation_thread(
                session=session,
                user_context=user_context
            )
            
            if thread_ts:
                # Prepare escalation response
                escalation_message = self._build_escalation_response(
                    session=session,
                    escalation_reason=escalation_reason,
                    platform=user_context['platform']
                )
                
                return AgentResponse(
                    agent_name="responder_agent",
                    response_text=escalation_message,
                    confidence_score=1.0,
                    should_escalate=True,
                    escalation_reason=escalation_reason,
                    requires_human_input=True,
                    session_id=session.session_id,
                    metadata={
                        'thread_ts': thread_ts,
                        'escalation_channel': self.config.escalation_channel,
                        'session_state': session.state.value
                    }
                )
            else:
                # Fallback if Slack thread creation failed
                return AgentResponse(
                    agent_name="responder_agent",
                    response_text="I'm escalating your request to our support team. You'll hear back from a human agent shortly.",
                    confidence_score=0.8,
                    should_escalate=True,
                    escalation_reason="Slack thread creation failed - manual escalation needed",
                    requires_human_input=True,
                    session_id=session.session_id
                )
                
        except Exception as e:
            logger.error(f"Error escalating conversation: {e}")
            return AgentResponse(
                agent_name="responder_agent",
                response_text="I'm having trouble escalating your request right now. Please try again in a moment.",
                confidence_score=0.1,
                should_escalate=False,
                escalation_reason=f"Escalation system error: {str(e)}",
                session_id=None  # Add session_id to match expected structure
            )
    
    def _detect_platform(self, channel_id: str) -> str:
        """Detect the platform based on channel ID."""
        if channel_id.startswith('chainlit'):
            return 'Chainlit'
        elif channel_id.startswith('web'):
            return 'Website'
        elif channel_id.startswith('C') or channel_id.startswith('D'):  # Slack channels/DMs
            return 'Slack'
        else:
            return 'Unknown'
    
    def _build_escalation_response(
        self,
        session: ConversationSession,
        escalation_reason: str,
        platform: str
    ) -> str:
        """Build the escalation response message for the user."""
        messages = [
            "I'm connecting you with one of our human support agents who can provide specialized help.",
            f"\n**Session ID:** `{session.session_id}`",
            f"**Escalation Reason:** {escalation_reason}",
            f"\nA support agent will respond shortly. Please stay connected on {platform}.",
            "\n*In the meantime, feel free to provide any additional context that might help resolve your issue faster.*"
        ]
        
        return "".join(messages)
    
    async def handle_user_followup(
        self,
        support_message: SupportMessage
    ) -> Optional[AgentResponse]:
        """Handle follow-up messages from users with active sessions."""
        try:
            # Check for active session
            session = await self.session_manager.get_user_active_session(
                user_id=support_message.user_id
            )
            
            if not session:
                return None
            
            # Add message to session history
            await self.session_manager.add_message_to_session(
                session_id=session.session_id,
                message={
                    'sender': 'User',
                    'content': support_message.content,
                    'message_type': 'followup_message',
                    'platform': self._detect_platform(support_message.channel_id)
                }
            )
            
            if session.state == SessionState.ACTIVE:
                # Still waiting for agent assignment
                return AgentResponse(
                    agent_name="responder_agent",
                    response_text="Thanks for the additional information. I've added it to your support request. An agent will be with you shortly.",
                    confidence_score=1.0,
                    should_escalate=False,
                    session_id=session.session_id,
                    metadata={'session_state': 'awaiting_agent'}
                )
            
            elif session.state == SessionState.ASSIGNED:
                # Forward to assigned agent via Slack thread
                if session.thread_ts:
                    await self._forward_user_message_to_slack(
                        session=session,
                        message=support_message.content,
                        user_name=support_message.user_name
                    )
                
                return AgentResponse(
                    agent_name="responder_agent", 
                    response_text="I've forwarded your message to the support agent handling your case. They'll respond shortly.",
                    confidence_score=1.0,
                    should_escalate=False,
                    session_id=session.session_id,
                    metadata={'session_state': 'forwarded_to_agent'}
                )
            
            else:
                # Closed session
                return None
                
        except Exception as e:
            logger.error(f"Error handling user followup: {e}")
            return AgentResponse(
                agent_name="responder_agent",
                response_text="I'm having trouble processing your message. Please try again.",
                confidence_score=0.1,
                should_escalate=False,
                escalation_reason=f"Followup handling error: {str(e)}"
            )
    
    async def _forward_user_message_to_slack(
        self,
        session: ConversationSession,
        message: str,
        user_name: str
    ) -> None:
        """Forward user message to Slack thread."""
        try:
            # Post message to Slack thread
            formatted_message = f"**{user_name}:** {message}"
            
            await self.thread_manager.slack.chat_postMessage(
                channel=f"#{self.config.escalation_channel}",
                thread_ts=session.thread_ts,
                text=formatted_message,
                metadata={
                    "event_type": "user_followup",
                    "session_id": session.session_id
                }
            )
            
            logger.info(f"Forwarded user message to Slack thread {session.thread_ts}")
            
        except Exception as e:
            logger.error(f"Error forwarding user message to Slack: {e}")
    
    async def _forward_to_user(self, session_id: str, agent_message: str) -> None:
        """Forward agent message to user (callback from thread manager)."""
        try:
            session = await self.session_manager.get_session(session_id)
            if not session:
                logger.warning(f"Session {session_id} not found for message forwarding")
                return
            
            # Determine platform and route message
            platform = self._detect_platform(session.channel_id)
            
            if platform in self.platform_handlers:
                await self.platform_handlers[platform](
                    user_id=session.user_id,
                    message=agent_message,
                    session_id=session_id
                )
            else:
                logger.warning(f"No handler registered for platform {platform}")
            
        except Exception as e:
            logger.error(f"Error forwarding message to user: {e}")
    
    def register_platform_handler(
        self,
        platform: str,
        handler: Callable[[str, str, str], None]
    ) -> None:
        """Register a message handler for a specific platform."""
        self.platform_handlers[platform] = handler
        logger.info(f"Registered handler for platform: {platform}")
    
    async def get_session_status(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get current session status for a user."""
        try:
            session = await self.session_manager.get_user_active_session(user_id)
            
            if not session:
                return None
            
            return {
                'session_id': session.session_id,
                'state': session.state.value,
                'escalated_at': session.escalated_at.isoformat(),
                'escalation_reason': session.escalation_reason,
                'assigned_to': session.assigned_to,
                'thread_ts': session.thread_ts,
                'message_count': len(session.history)
            }
            
        except Exception as e:
            logger.error(f"Error getting session status: {e}")
            return None
    
    async def close_user_session(self, user_id: str) -> bool:
        """Close user's active session (if they request it)."""
        try:
            session = await self.session_manager.get_user_active_session(user_id)
            
            if not session:
                return False
            
            success = await self.session_manager.close_session(session.session_id)
            
            if success and session.thread_ts:
                # Notify Slack thread
                await self.thread_manager.slack.chat_postMessage(
                    channel=f"#{self.config.escalation_channel}",
                    thread_ts=session.thread_ts,
                    text=f"📤 User has closed their session `{session.session_id}`"
                )
            
            return success
            
        except Exception as e:
            logger.error(f"Error closing user session: {e}")
            return False
    
    async def process_escalation_request(
        self,
        support_message: SupportMessage,
        escalation_reason: str,
        conversation_history: List[Dict[str, Any]]
    ) -> AgentResponse:
        """Main entry point for processing escalation requests."""
        # First check if this is a follow-up to existing session
        followup_response = await self.handle_user_followup(support_message)
        
        if followup_response:
            return followup_response
        
        # If no existing session, create new escalation
        return await self.escalate_conversation(
            support_message=support_message,
            escalation_reason=escalation_reason,
            conversation_history=conversation_history
        )
    
    async def get_responder_stats(self) -> Dict[str, Any]:
        """Get responder agent statistics."""
        try:
            session_stats = await self.session_manager.get_session_stats()
            escalation_stats = await self.thread_manager.get_escalation_stats()
            
            return {
                'active_escalations': session_stats['active'],
                'assigned_tickets': session_stats['assigned'],
                'closed_tickets': session_stats['closed'],
                'total_sessions': session_stats['total'],
                'platform_handlers': list(self.platform_handlers.keys()),
                'config': {
                    'escalation_channel': self.config.escalation_channel,
                    'auto_escalate_timeout': self.config.auto_escalate_timeout,
                    'max_history_context': self.config.max_history_context
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting responder stats: {e}")
            return {}
    
    async def health_check(self) -> Dict[str, bool]:
        """Perform health check on responder system."""
        try:
            health = {
                'session_manager': False,
                'thread_manager': False,
                'supabase_connection': False
            }
            
            # Test session manager
            try:
                stats = await self.session_manager.get_session_stats()
                health['session_manager'] = True
            except:
                pass
            
            # Test Slack connection
            try:
                await self.thread_manager.slack.auth_test()
                health['thread_manager'] = True
            except:
                pass
            
            # Test Supabase connection
            try:
                result = self.session_manager.supabase.table('conversation_sessions').select('session_id', count='exact').limit(1).execute()
                health['supabase_connection'] = True
            except:
                pass
            
            return health
            
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return {'session_manager': False, 'thread_manager': False, 'supabase_connection': False}