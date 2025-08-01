"""Slack integration for the AI Support Agent."""

import asyncio
import logging
from typing import Dict, List, Optional
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
        self.client = AsyncWebClient(token=settings.slack_bot_token)
        self.app = AsyncApp(
            token=settings.slack_bot_token,
            signing_secret=settings.slack_signing_secret
        )
        self._setup_event_handlers()
    
    def _setup_event_handlers(self):
        """Set up Slack event handlers."""
        
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
    
    async def send_acknowledgment(self, message: SupportMessage) -> None:
        """Send immediate acknowledgment to user."""
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
        suggested_assignee: Optional[str] = None
    ) -> None:
        """Send escalation notification to support team."""
        try:
            escalation_text = (
                f"🚨 *Escalation Required*\n\n"
                f"*Original Message:* {message.content[:200]}...\n"
                f"*User:* <@{message.user_id}>\n"
                f"*Channel:* <#{message.channel_id}>\n"
                f"*Reason:* {escalation_reason}\n"
                f"*Message Link:* https://slack.com/archives/{message.channel_id}/p{message.message_id.replace('.', '')}"
            )
            
            if suggested_assignee:
                escalation_text += f"\n*Suggested Assignee:* <@{suggested_assignee}>"
            
            # Send to internal support channel (you'll need to configure this)
            support_channel = "#support-escalations"  # Configure in settings
            
            await self.client.chat_postMessage(
                channel=support_channel,
                text=escalation_text
            )
            
            logger.info(f"Sent escalation notification for message {message.message_id}")
            
        except SlackApiError as e:
            logger.error(f"Error sending escalation: {e}")
    
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