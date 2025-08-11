"""Slack integration for the AI Support Agent."""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

from src.core.config import settings
from src.models.schemas import SupportMessage, MessageCategory, UrgencyLevel


logger = logging.getLogger(__name__)


class SlackClient:
    """Async Slack client for handling messages and responses."""
    
    def __init__(self):
        # Check if Slack credentials are available
        self.enabled = bool(settings.slack_bot_token and settings.slack_signing_secret)
        
        # Initialize shared dependencies once to avoid repeated instantiation
        self._session_manager = None
        self._thread_manager = None
        
        if self.enabled:
            self.client = AsyncWebClient(token=settings.slack_bot_token)
            self.app = AsyncApp(
                token=settings.slack_bot_token,
                signing_secret=settings.slack_signing_secret
            )
            self._setup_event_handlers()
        else:
            logger.warning("Slack credentials not provided. Slack integration disabled.")
            self.client = None
            self.app = None
    
    def _get_session_manager(self):
        """Get or create SessionManager instance."""
        if self._session_manager is None:
            from src.core.session_manager import SessionManager
            from src.core.config import settings
            self._session_manager = SessionManager(
                supabase_url=settings.supabase_url,
                supabase_key=settings.supabase_key
            )
        return self._session_manager
    
    def _get_thread_manager(self, slack_client):
        """Get or create SlackThreadManager instance."""
        if self._thread_manager is None:
            from src.integrations.slack_thread_manager import SlackThreadManager
            self._thread_manager = SlackThreadManager(
                slack_client=slack_client,
                session_manager=self._get_session_manager()
            )
        return self._thread_manager
    
    def _setup_event_handlers(self):
        """Set up Slack event handlers."""
        if not self.enabled:
            return
            
        @self.app.event("message")
        async def handle_message_events(body, logger, say):
            """Handle incoming message events."""
            try:
                event = body["event"]
                
                # Skip bot messages and thread replies (for now)
                if event.get("bot_id") or event.get("subtype"):
                    return
                
                # Create support message object
                support_message = SupportMessage(
                    message_id=event["ts"],
                    channel_id=event["channel"],
                    user_id=event["user"],
                    timestamp=datetime.fromtimestamp(float(event["ts"])),
                    content=event["text"],
                    thread_ts=event.get("thread_ts")
                )
                
                # Send immediate acknowledgment
                await self.send_acknowledgment(support_message)
                
                # Process message (this will be handled by the agent workflow)
                # For now, just log it
                logger.info(f"Received message: {support_message.content[:100]}...")
                
            except Exception as e:
                logger.error(f"Error handling message event: {e}")
        
        # Add button action handlers
        @self.app.action("accept_ticket")
        async def handle_accept_ticket(ack, body, client):
            """Handle Accept Ticket button click."""
            try:
                thread_manager = self._get_thread_manager(client)
                await thread_manager.handle_accept_ticket(ack, body, client)
                
            except Exception as e:
                await ack()
                logger.error(f"Error handling accept ticket: {e}")
                await client.chat_postMessage(
                    channel=body["channel"]["id"],
                    thread_ts=body["message"]["ts"],
                    text=f"❌ Error accepting ticket: {str(e)}"
                )
        
        @self.app.action("view_history")
        async def handle_view_history(ack, body, client):
            """Handle View Full History button click."""
            try:
                thread_manager = self._get_thread_manager(client)
                await thread_manager.handle_view_history(ack, body, client)
                
            except Exception as e:
                await ack()
                logger.error(f"Error handling view history: {e}")
                await client.chat_postMessage(
                    channel=body["channel"]["id"],
                    thread_ts=body["message"]["ts"],
                    text=f"❌ Error retrieving history: {str(e)}"
                )
        
        @self.app.action("close_ticket")
        async def handle_close_ticket(ack, body, client):
            """Handle Close Ticket button click."""
            try:
                thread_manager = self._get_thread_manager(client)
                await thread_manager.handle_close_ticket(ack, body, client)
                
            except Exception as e:
                await ack()
                logger.error(f"Error handling close ticket: {e}")
                await client.chat_postMessage(
                    channel=body["channel"]["id"],
                    thread_ts=body["message"]["ts"],
                    text=f"❌ Error closing ticket: {str(e)}"
                )
        
        # Legacy button handlers - redirect to proper thread manager workflow
        @self.app.action("take_ownership")
        async def handle_take_ownership(ack, body, client):
            """Handle legacy Take Ownership button - redirect to Accept Ticket."""
            await ack()
            try:
                await client.chat_postMessage(
                    channel=body["channel"]["id"],
                    thread_ts=body["message"]["ts"],
                    text="⚠️ This is a legacy escalation message. Please use the 'Accept Ticket' button on newer escalation messages."
                )
            except Exception as e:
                logger.error(f"Error handling take ownership: {e}")
        
        @self.app.action("view_context")
        async def handle_view_context(ack, body, client):
            """Handle legacy View Context button - redirect to View History."""
            await ack()
            try:
                await client.chat_postMessage(
                    channel=body["channel"]["id"],
                    thread_ts=body["message"]["ts"],
                    text="⚠️ This is a legacy escalation message. Please use the 'View Full History' button on newer escalation messages."
                )
            except Exception as e:
                logger.error(f"Error handling view context: {e}")
        
        @self.app.action("schedule_meeting")
        async def handle_schedule_meeting(ack, body, client):
            """Handle legacy Schedule Meeting button."""
            await ack()
            try:
                await client.chat_postMessage(
                    channel=body["channel"]["id"],
                    thread_ts=body["message"]["ts"],
                    text="⚠️ This is a legacy escalation message. For meeting scheduling, please use the regular agent interface."
                )
            except Exception as e:
                logger.error(f"Error handling schedule meeting: {e}")
    
    async def send_acknowledgment(self, message: SupportMessage) -> None:
        """Send immediate acknowledgment to user."""
        if not self.enabled or message.channel_id in ["DASHBOARD_TEST", "TERMINAL_CHAT"]:
            logger.info(f"[TEST MODE] Would send acknowledgment for message {message.message_id}")
            return
            
        acknowledgment_templates = [
            "👋 Got it! Looking into this now - should have an answer in 2-3 minutes.",
            "🔍 Thanks for reaching out! Searching our knowledge base for the best solution.",
            "⚡ On it! This looks like a technical question - checking our docs.",
            "📋 Received your message! Let me find the most relevant information for you."
        ]
        
        try:
            # Simple template selection (can be made more intelligent later)
            template = acknowledgment_templates[0]
            
            await self.client.chat_postMessage(
                channel=message.channel_id,
                text=template,
                thread_ts=message.thread_ts
            )
            
            logger.info(f"Sent acknowledgment for message {message.message_id}")
            
        except SlackApiError as e:
            logger.error(f"Error sending acknowledgment: {e}")
    
    async def send_response(
        self, 
        message: SupportMessage, 
        response_text: str,
        sources: Optional[List[str]] = None
    ) -> None:
        """Send AI-generated response to user."""
        if not self.enabled or message.channel_id in ["DASHBOARD_TEST", "TERMINAL_CHAT"]:
            logger.info(f"[TEST MODE] Would send response for message {message.message_id}: {response_text[:100]}...")
            return
            
        try:
            # Format response with sources if provided
            formatted_response = response_text
            if sources:
                formatted_response += f"\n\n📚 *Sources:*\n" + "\n".join([f"• {source}" for source in sources])
            
            await self.client.chat_postMessage(
                channel=message.channel_id,
                text=formatted_response,
                thread_ts=message.thread_ts or message.message_id
            )
            
            logger.info(f"Sent response for message {message.message_id}")
            
        except SlackApiError as e:
            logger.error(f"Error sending response: {e}")
    
    async def send_escalation_notification(
        self, 
        message: SupportMessage, 
        escalation_reason: str,
        suggested_assignee: Optional[str] = None,
        escalation_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log escalation notification (actual Slack posting handled by ResponderAgent to avoid duplicates)."""
        logger.info(f"Escalation logged for message {message.message_id}: {escalation_reason}")
        
        # NOTE: Actual Slack escalation posting is now handled by ResponderAgent's 
        # SlackThreadManager to avoid duplicate messages with different button schemas.
        # This method now only logs the escalation for audit purposes.
        
        if not self.enabled:
            logger.info(f"[TEST MODE] Would escalate message {message.message_id}: {escalation_reason}")
        else:
            logger.info(f"Escalation routing: {escalation_reason} -> ResponderAgent will handle Slack posting")
    
    def _determine_escalation_channel(self, escalation_reason: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Determine the appropriate Slack channel for escalation (for logging purposes only)."""
        reason_lower = escalation_reason.lower()
        
        # NOTE: This method is now only used for logging. Actual channel routing 
        # is handled by ResponderAgent's SlackThreadManager.
        
        if any(keyword in reason_lower for keyword in ['demo', 'schedule', 'meeting', 'book']):
            if any(keyword in reason_lower for keyword in ['book', 'schedule', 'meeting']):
                return "#sales-activity"  # For logging only
        
        return "#support-escalations"  # For logging only
    
    
    async def send_meeting_notification(
        self, 
        meeting_details: Dict[str, Any],
        notification_type: str = "booked"  # "booked", "cancelled", "rescheduled"
    ) -> None:
        """Send meeting booking notification to appropriate Slack channel."""
        if not self.enabled:
            logger.info(f"[TEST MODE] Would send meeting notification: {notification_type}")
            return
            
        try:
            # Determine notification channel based on meeting type
            meeting_type = meeting_details.get('meeting_type', 'demo')
            channel = self._get_meeting_notification_channel(meeting_type)
            
            # Create notification blocks
            blocks = self._create_meeting_notification_blocks(meeting_details, notification_type)
            
            # Send notification
            await self.client.chat_postMessage(
                channel=channel,
                text=f"📅 Meeting {notification_type}: {meeting_details.get('title', 'Untitled')}",
                blocks=blocks
            )
            
            logger.info(f"Sent meeting {notification_type} notification to {channel}")
            
        except SlackApiError as e:
            logger.error(f"Error sending meeting notification: {e}")
    
    def _get_meeting_notification_channel(self, meeting_type: str) -> str:
        """Get the appropriate channel for meeting notifications."""
        # Consolidated approach: All meeting bookings go to sales-activity
        # Support-related meetings handled through escalations
        channel_mapping = {
            'demo': '#sales-activity',
            'sales_discussion': '#sales-activity', 
            'technical_support': '#sales-activity',  # All meetings go to sales
            'compliance_consultation': '#sales-activity',  # All meetings go to sales
            'onboarding_session': '#sales-activity'  # All meetings go to sales
        }
        return channel_mapping.get(meeting_type, '#sales-activity')
    
    def _create_meeting_notification_blocks(
        self, 
        meeting_details: Dict[str, Any], 
        notification_type: str
    ) -> List[Dict[str, Any]]:
        """Create rich blocks for meeting notifications."""
        blocks = []
        
        # Header with appropriate emoji
        emoji_map = {
            "booked": "📅",
            "cancelled": "❌", 
            "rescheduled": "🔄"
        }
        emoji = emoji_map.get(notification_type, "📅")
        
        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{emoji} Meeting {notification_type.title()}"
            }
        })
        
        # Meeting details
        fields = []
        
        if meeting_details.get('title'):
            fields.append({
                "type": "mrkdwn",
                "text": f"*Meeting:*\n{meeting_details['title']}"
            })
        
        if meeting_details.get('start_time'):
            fields.append({
                "type": "mrkdwn",
                "text": f"*When:*\n{meeting_details['start_time']}"
            })
        
        if meeting_details.get('duration_minutes'):
            fields.append({
                "type": "mrkdwn", 
                "text": f"*Duration:*\n{meeting_details['duration_minutes']} minutes"
            })
        
        if meeting_details.get('meeting_type'):
            meeting_type_display = meeting_details['meeting_type'].replace('_', ' ').title()
            fields.append({
                "type": "mrkdwn",
                "text": f"*Type:*\n{meeting_type_display}"
            })
        
        blocks.append({
            "type": "section",
            "fields": fields
        })
        
        # Customer information
        customer_info = []
        if meeting_details.get('customer_name'):
            customer_info.append(f"*Name:* {meeting_details['customer_name']}")
        if meeting_details.get('customer_email'):
            customer_info.append(f"*Email:* {meeting_details['customer_email']}")
        
        if customer_info:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Customer:*\n{' • '.join(customer_info)}"
                }
            })
        
        # Calendar link if available
        if meeting_details.get('calendar_link'):
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Calendar Event:* <{meeting_details['calendar_link']}|View in Calendar>"
                }
            })
        
        # Action buttons for booked meetings
        if notification_type == "booked":
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Prep Notes"
                        },
                        "action_id": "prep_notes",
                        "value": meeting_details.get('event_id', '')
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Customer Context"
                        },
                        "action_id": "customer_context",
                        "value": meeting_details.get('customer_email', '')
                    }
                ]
            })
        
        return blocks
    
    async def update_message_with_typing(self, channel_id: str) -> None:
        """Show typing indicator while processing."""
        try:
            # Note: Slack doesn't have a direct typing indicator API
            # This is a placeholder for future implementation
            pass
        except Exception as e:
            logger.error(f"Error showing typing indicator: {e}")
    
    async def get_user_info(self, user_id: str) -> Dict:
        """Get user information from Slack."""
        try:
            result = await self.client.users_info(user=user_id)
            return result["user"]
        except SlackApiError as e:
            logger.error(f"Error getting user info: {e}")
            return {}
    
    async def get_channel_info(self, channel_id: str) -> Dict:
        """Get channel information from Slack."""
        try:
            result = await self.client.conversations_info(channel=channel_id)
            return result["channel"]
        except SlackApiError as e:
            logger.error(f"Error getting channel info: {e}")
            return {}
    
    def categorize_message(self, content: str) -> MessageCategory:
        """Simple message categorization based on keywords."""
        content_lower = content.lower()
        
        # Compliance keywords
        compliance_keywords = ["soc2", "iso27001", "gdpr", "hipaa", "audit", "compliance", "security", "privacy"]
        if any(keyword in content_lower for keyword in compliance_keywords):
            return MessageCategory.COMPLIANCE
        
        # Demo keywords
        demo_keywords = ["demo", "demonstration", "meeting", "schedule", "show me", "walkthrough"]
        if any(keyword in content_lower for keyword in demo_keywords):
            return MessageCategory.DEMO
        
        # Billing keywords
        billing_keywords = ["billing", "invoice", "payment", "cost", "price", "subscription"]
        if any(keyword in content_lower for keyword in billing_keywords):
            return MessageCategory.BILLING
        
        # Technical keywords
        technical_keywords = ["api", "integration", "error", "bug", "configuration", "setup", "install"]
        if any(keyword in content_lower for keyword in technical_keywords):
            return MessageCategory.TECHNICAL
        
        return MessageCategory.GENERAL
    
    def assess_urgency(self, content: str) -> UrgencyLevel:
        """Simple urgency assessment based on keywords."""
        content_lower = content.lower()
        
        # Critical keywords
        critical_keywords = ["urgent", "critical", "emergency", "down", "broken", "not working", "production"]
        if any(keyword in content_lower for keyword in critical_keywords):
            return UrgencyLevel.CRITICAL
        
        # High priority keywords
        high_keywords = ["asap", "quickly", "important", "priority", "issue"]
        if any(keyword in content_lower for keyword in high_keywords):
            return UrgencyLevel.HIGH
        
        # Question marks and help requests suggest medium priority
        if "?" in content or any(word in content_lower for word in ["help", "how", "what", "why"]):
            return UrgencyLevel.MEDIUM
        
        return UrgencyLevel.LOW


# Global Slack client instance
slack_client = SlackClient()