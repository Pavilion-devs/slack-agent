"""
Slack Thread Manager for Bidirectional Responder System

Manages Slack thread creation, interactive components, and button handling
for the escalated support ticket system.
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
import logging
import json

from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError
from slack_bolt.async_app import AsyncApp

from ..core.session_manager import SessionManager, ConversationSession, SessionState

logger = logging.getLogger(__name__)


class SlackThreadManager:
    """Manages Slack threads and interactive components for escalated tickets."""
    
    def __init__(
        self, 
        slack_client: AsyncWebClient,
        session_manager: SessionManager,
        escalation_channel: str = "support-escalations"
    ):
        """Initialize Slack thread manager."""
        self.slack = slack_client
        self.session_manager = session_manager
        self.escalation_channel = escalation_channel
        self.message_handlers: Dict[str, Callable] = {}
        logger.info(f"SlackThreadManager initialized for channel #{escalation_channel}")
    
    async def create_escalation_thread(
        self, 
        session: ConversationSession,
        user_context: Dict[str, str]
    ) -> Optional[str]:
        """Create a new escalation thread in the support channel."""
        try:
            # Format conversation history for display
            history_summary = self._format_conversation_history(session.history[-5:])  # Last 5 messages
            
            # Create the escalation message blocks
            blocks = self._build_escalation_blocks(
                session=session,
                user_context=user_context,
                history_summary=history_summary
            )
            
            # Post message to escalation channel
            response = await self.slack.chat_postMessage(
                channel=f"#{self.escalation_channel}",
                text=f"🔔 New Support Request from {user_context.get('user_name', 'Unknown User')}",
                blocks=blocks,
                metadata={
                    "event_type": "escalation",
                    "session_id": session.session_id
                }
            )
            
            if response["ok"]:
                thread_ts = response["ts"]
                
                # Update session with thread timestamp
                await self.session_manager.update_session_thread(session.session_id, thread_ts)
                
                logger.info(f"Created escalation thread {thread_ts} for session {session.session_id}")
                return thread_ts
            else:
                logger.error(f"Failed to create escalation thread: {response.get('error')}")
                return None
                
        except SlackApiError as e:
            logger.error(f"Slack API error creating escalation thread: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating escalation thread: {e}")
            return None
    
    def _build_escalation_blocks(
        self,
        session: ConversationSession,
        user_context: Dict[str, str],
        history_summary: str
    ) -> List[Dict[str, Any]]:
        """Build Slack blocks for escalation message."""
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🔔 New Support Request"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*From:* {user_context.get('user_name', 'Unknown User')}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Email:* {user_context.get('user_email', 'N/A')}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Session ID:* `{session.session_id}`"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Escalated:* {session.escalated_at.strftime('%Y-%m-%d %H:%M UTC')}"
                    }
                ]
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Recent Conversation:*\n{history_summary}"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Accept Ticket"
                        },
                        "style": "primary",
                        "action_id": "accept_ticket",
                        "value": session.session_id
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View Full History"
                        },
                        "action_id": "view_history",
                        "value": session.session_id
                    }
                ]
            }
        ]
        
        return blocks
    
    def _format_conversation_history(self, messages: List[Dict[str, Any]]) -> str:
        """Format conversation history for display with clean formatting."""
        if not messages:
            return "_No recent messages_"
        
        formatted_messages = []
        
        # Show all messages from the conversation for full context
        for msg in messages:
            sender = msg.get('sender', 'User')
            content = msg.get('content', '')
            
            # Clean up sender names
            if sender == 'AI Agent':
                sender = 'AI Agent'
            elif sender in ['customer', 'Customer', 'User']:
                sender = 'Customer'  
            elif sender == 'human_agent':
                sender = 'Human Agent'
            else:
                # Handle any other sender formats
                sender = sender.replace('👤', '').replace('🤖', '').strip()
                if not sender:
                    sender = 'Customer'
            
            # Clean up content - remove conversation context artifacts
            if 'CONVERSATION CONTEXT:' in content:
                # Extract just the current user message
                if 'CURRENT USER MESSAGE:' in content:
                    content = content.split('CURRENT USER MESSAGE:')[-1].strip()
                else:
                    # If no current message marker, take the content after context
                    lines = content.split('\n')
                    # Find the last line that looks like actual user content
                    for line in reversed(lines):
                        line = line.strip()
                        if line and not line.startswith('User:') and not line.startswith('AI Assistant:'):
                            content = line
                            break
            
            # Truncate very long messages for readability
            if len(content) > 200:
                content = content[:200] + "..."
            
            # Format as clean message
            formatted_messages.append(f"**{sender}:** {content}")
        
        return "\n\n".join(formatted_messages)
    
    async def handle_accept_ticket(
        self, 
        ack: Callable,
        body: Dict[str, Any],
        client: AsyncWebClient
    ) -> None:
        """Handle Accept Ticket button click."""
        await ack()
        
        try:
            session_id = body["actions"][0]["value"]
            agent_user_id = body["user"]["id"]
            agent_name = body["user"]["name"]
            thread_ts = body["message"]["ts"]
            
            # Assign session to agent
            success = await self.session_manager.assign_session(
                session_id=session_id,
                agent_slack_id=agent_user_id,
                thread_ts=thread_ts
            )
            
            if success:
                # Update the message to show it's been accepted
                await self._update_escalation_message_accepted(
                    client=client,
                    channel=body["channel"]["id"],
                    ts=thread_ts,
                    agent_name=agent_name,
                    session_id=session_id
                )
                
                # Post confirmation in thread
                await client.chat_postMessage(
                    channel=body["channel"]["id"],
                    thread_ts=thread_ts,
                    text=f"✅ <@{agent_user_id}> has accepted this ticket. You can now reply in this thread to communicate with the user."
                )
                
                logger.info(f"Agent {agent_name} accepted session {session_id}")
            else:
                await client.chat_postMessage(
                    channel=body["channel"]["id"],
                    thread_ts=thread_ts,
                    text="❌ Failed to assign ticket. It may have already been taken."
                )
                
        except Exception as e:
            logger.error(f"Error handling accept ticket: {e}")
            await client.chat_postMessage(
                channel=body["channel"]["id"],
                thread_ts=body["message"]["ts"],
                text=f"❌ Error accepting ticket: {str(e)}"
            )
    
    async def handle_view_history(
        self,
        ack: Callable,
        body: Dict[str, Any],
        client: AsyncWebClient
    ) -> None:
        """Handle View Full History button click."""
        await ack()
        
        try:
            session_id = body["actions"][0]["value"]
            session = await self.session_manager.get_session(session_id)
            
            if not session:
                await client.chat_postMessage(
                    channel=body["channel"]["id"],
                    thread_ts=body["message"]["ts"],
                    text="❌ Session not found."
                )
                return
            
            # Format full conversation history
            history_text = self._format_full_history(session.history)
            
            # Post history in thread
            await client.chat_postMessage(
                channel=body["channel"]["id"],
                thread_ts=body["message"]["ts"],
                text=f"📖 *Full Conversation History for Session `{session_id}`*\n\n{history_text}"
            )
            
        except Exception as e:
            logger.error(f"Error handling view history: {e}")
            await client.chat_postMessage(
                channel=body["channel"]["id"],
                thread_ts=body["message"]["ts"],
                text=f"❌ Error retrieving history: {str(e)}"
            )
    
    def _format_full_history(self, messages: List[Dict[str, Any]]) -> str:
        """Format full conversation history with clean formatting."""
        if not messages:
            return "_No conversation history available_"
        
        formatted_messages = []
        for i, msg in enumerate(messages, 1):
            sender = msg.get('sender', 'User')
            content = msg.get('content', '')
            timestamp = msg.get('timestamp', '')
            
            # Clean up sender names
            if sender == 'AI Agent':
                sender = 'AI Agent'
            elif sender in ['customer', 'Customer', 'User']:
                sender = 'Customer'
            elif sender == 'human_agent':
                sender = 'Human Agent'
            else:
                sender = sender.replace('👤', '').replace('🤖', '').strip()
                if not sender:
                    sender = 'Customer'
            
            # Clean up content - remove conversation context artifacts
            if 'CONVERSATION CONTEXT:' in content:
                if 'CURRENT USER MESSAGE:' in content:
                    content = content.split('CURRENT USER MESSAGE:')[-1].strip()
                else:
                    lines = content.split('\n')
                    for line in reversed(lines):
                        line = line.strip()
                        if line and not line.startswith('User:') and not line.startswith('AI Assistant:'):
                            content = line
                            break
            
            # Format timestamp if available
            time_str = ""
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    time_str = f" ({dt.strftime('%H:%M')})"
                except:
                    pass
            
            formatted_messages.append(f"{i}. **{sender}**{time_str}: {content}")
        
        return "\n\n".join(formatted_messages)
    
    async def _update_escalation_message_accepted(
        self,
        client: AsyncWebClient,
        channel: str,
        ts: str,
        agent_name: str,
        session_id: str
    ) -> None:
        """Update escalation message to show it's been accepted."""
        try:
            # Get the original message
            result = await client.conversations_history(
                channel=channel,
                latest=ts,
                inclusive=True,
                limit=1
            )
            
            if not result["ok"] or not result["messages"]:
                return
            
            original_blocks = result["messages"][0].get("blocks", [])
            
            # Replace the actions block with accepted status
            updated_blocks = []
            for block in original_blocks:
                if block.get("type") == "actions":
                    # Replace actions with accepted status
                    updated_blocks.append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"✅ *Accepted by:* <@{agent_name}>\n_Reply in this thread to communicate with the user_"
                        }
                    })
                    updated_blocks.append({
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "Close Ticket"
                                },
                                "style": "danger",
                                "action_id": "close_ticket",
                                "value": session_id,
                                "confirm": {
                                    "title": {
                                        "type": "plain_text",
                                        "text": "Close Ticket"
                                    },
                                    "text": {
                                        "type": "mrkdwn",
                                        "text": "Are you sure you want to close this ticket? This will end the conversation with the user."
                                    },
                                    "confirm": {
                                        "type": "plain_text",
                                        "text": "Close"
                                    },
                                    "deny": {
                                        "type": "plain_text",
                                        "text": "Cancel"
                                    }
                                }
                            }
                        ]
                    })
                else:
                    updated_blocks.append(block)
            
            # Update the message
            await client.chat_update(
                channel=channel,
                ts=ts,
                blocks=updated_blocks,
                text="🔔 New Support Request - ACCEPTED"
            )
            
        except Exception as e:
            logger.error(f"Error updating escalation message: {e}")
    
    async def handle_close_ticket(
        self,
        ack: Callable,
        body: Dict[str, Any],
        client: AsyncWebClient
    ) -> None:
        """Handle Close Ticket button click."""
        await ack()
        
        try:
            session_id = body["actions"][0]["value"]
            agent_user_id = body["user"]["id"]
            
            # Close the session
            success = await self.session_manager.close_session(session_id)
            
            if success:
                # Update message to show closed status
                await self._update_escalation_message_closed(
                    client=client,
                    channel=body["channel"]["id"],
                    ts=body["message"]["ts"],
                    session_id=session_id
                )
                
                # Post closing message in thread
                await client.chat_postMessage(
                    channel=body["channel"]["id"],
                    thread_ts=body["message"]["ts"],
                    text=f"🔒 Ticket closed by <@{agent_user_id}>."
                )
                
                logger.info(f"Session {session_id} closed by agent {agent_user_id}")
            else:
                await client.chat_postMessage(
                    channel=body["channel"]["id"],
                    thread_ts=body["message"]["ts"],
                    text="❌ Failed to close ticket."
                )
                
        except Exception as e:
            logger.error(f"Error handling close ticket: {e}")
            await client.chat_postMessage(
                channel=body["channel"]["id"],
                thread_ts=body["message"]["ts"],
                text=f"❌ Error closing ticket: {str(e)}"
            )
    
    async def _update_escalation_message_closed(
        self,
        client: AsyncWebClient,
        channel: str,
        ts: str,
        session_id: str
    ) -> None:
        """Update escalation message to show it's been closed."""
        try:
            # Get the original message
            result = await client.conversations_history(
                channel=channel,
                latest=ts,
                inclusive=True,
                limit=1
            )
            
            if not result["ok"] or not result["messages"]:
                return
            
            original_blocks = result["messages"][0].get("blocks", [])
            
            # Remove actions and add closed status
            updated_blocks = []
            for block in original_blocks:
                if block.get("type") != "actions":
                    updated_blocks.append(block)
            
            # Add closed status
            updated_blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"🔒 *Status:* CLOSED\n_Session `{session_id}` has been archived_"
                }
            })
            
            # Update the message
            await client.chat_update(
                channel=channel,
                ts=ts,
                blocks=updated_blocks,
                text="🔔 Support Request - CLOSED"
            )
            
        except Exception as e:
            logger.error(f"Error updating closed escalation message: {e}")
    
    async def forward_agent_message_to_user(
        self,
        session_id: str,
        agent_message: str,
        agent_name: str,
        user_message_callback: Callable[[str, str], None]
    ) -> bool:
        """Forward agent reply to user through callback."""
        try:
            # Add message to session history
            await self.session_manager.add_message_to_session(
                session_id=session_id,
                message={
                    'sender': f'Agent ({agent_name})',
                    'content': agent_message,
                    'message_type': 'agent_reply'
                }
            )
            
            # Format message for user
            formatted_message = f"**Support Agent ({agent_name}):** {agent_message}"
            
            # Call the callback to send to user
            await user_message_callback(session_id, formatted_message)
            
            logger.info(f"Forwarded agent message from {agent_name} to user in session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error forwarding agent message: {e}")
            return False
    
    async def process_thread_reply(
        self,
        channel: str,
        thread_ts: str,
        message_text: str,
        user_id: str,
        user_name: str,
        user_message_callback: Callable[[str, str], None]
    ) -> None:
        """Process a reply in an escalation thread."""
        try:
            # Find session by thread timestamp
            # This would require adding a query method to session manager
            # For now, we'll extract session_id from the thread's original message
            
            # Get the original message metadata to find session_id
            result = await self.slack.conversations_history(
                channel=channel,
                latest=thread_ts,
                inclusive=True,
                limit=1
            )
            
            if not result["ok"] or not result["messages"]:
                logger.warning(f"Could not find original message for thread {thread_ts}")
                return
            
            # Extract session_id from message metadata or blocks
            session_id = None
            original_message = result["messages"][0]
            
            # Try to find session_id in metadata
            if "metadata" in original_message:
                session_id = original_message["metadata"].get("session_id")
            
            # If not in metadata, try to find in blocks
            if not session_id:
                blocks = original_message.get("blocks", [])
                for block in blocks:
                    if block.get("type") == "section" and "fields" in block:
                        for field in block["fields"]:
                            if "Session ID" in field.get("text", ""):
                                # Extract session_id from markdown text
                                text = field["text"]
                                if "`" in text:
                                    session_id = text.split("`")[1]
                                break
                    if session_id:
                        break
            
            if not session_id:
                logger.warning(f"Could not extract session_id from thread {thread_ts}")
                return
            
            # Verify session is assigned to this agent
            session = await self.session_manager.get_session(session_id)
            if not session or session.assigned_to != user_id:
                logger.warning(f"Agent {user_id} not assigned to session {session_id}")
                return
            
            # Forward message to user
            await self.forward_agent_message_to_user(
                session_id=session_id,
                agent_message=message_text,
                agent_name=user_name,
                user_message_callback=user_message_callback
            )
            
        except Exception as e:
            logger.error(f"Error processing thread reply: {e}")
    
    def register_message_callback(self, callback: Callable[[str, str], None]):
        """Register callback for sending messages to users."""
        self.user_message_callback = callback
    
    async def get_escalation_stats(self) -> Dict[str, int]:
        """Get escalation statistics."""
        try:
            stats = await self.session_manager.get_session_stats()
            return {
                'total_escalations': stats['total'],
                'active_tickets': stats['active'],
                'assigned_tickets': stats['assigned'],
                'closed_tickets': stats['closed']
            }
        except Exception as e:
            logger.error(f"Error getting escalation stats: {e}")
            return {'total_escalations': 0, 'active_tickets': 0, 'assigned_tickets': 0, 'closed_tickets': 0}