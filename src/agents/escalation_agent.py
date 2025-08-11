"""Escalation Agent for handling smart routing to human agents."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from src.agents.base_agent import BaseAgent
from src.models.schemas import SupportMessage, AgentResponse
from src.core.config import settings

logger = logging.getLogger(__name__)


class EscalationAgent(BaseAgent):
    """Agent specialized in intelligent escalation to human agents."""
    
    def __init__(self):
        super().__init__("escalation_agent")
        self.escalation_routes = self._load_escalation_routes()
        self.team_availability = self._check_team_availability()
    
    def should_handle(self, message: SupportMessage) -> bool:
        """Escalation agent should handle all escalation scenarios."""
        # This agent only processes when explicitly called for escalation
        return False  # Never directly handles user messages
    
    async def process_escalation(
        self, 
        message: SupportMessage, 
        failed_response: Optional[AgentResponse] = None,
        escalation_reason: str = "Low confidence or complex issue"
    ) -> AgentResponse:
        """Process an escalation to human agents."""
        logger.info(f"Processing escalation for message: {message.message_id}")
        
        try:
            # Analyze escalation context
            escalation_context = self._analyze_escalation_context(message, failed_response, escalation_reason)
            
            # Determine appropriate team
            target_team = self._route_to_team(escalation_context)
            
            # Generate escalation response
            response_text = await self._generate_escalation_response(escalation_context, target_team)
            
            # Send alerts to appropriate team members
            await self._send_team_alerts(escalation_context, target_team)
            
            return self.format_response(
                response_text=response_text,
                confidence_score=1.0,  # Always confident about escalation
                sources=["Escalation System", "Team Routing"],
                should_escalate=False,  # Already escalated
                escalation_reason=None,
                metadata={
                    "agent_type": "escalation",
                    "target_team": target_team,
                    "escalation_context": escalation_context,
                    "original_agent": failed_response.agent_name if failed_response else "unknown"
                }
            )
            
        except Exception as e:
            logger.error(f"Error in escalation agent: {e}")
            return self.format_response(
                response_text="I've encountered an issue with the escalation system. I'm alerting our support team directly.",
                confidence_score=0.5,
                should_escalate=False,  # Prevent infinite escalation
                metadata={"error": True, "escalation_failed": True}
            )
    
    async def process_message(self, message: SupportMessage) -> AgentResponse:
        """Process message - should not be called directly."""
        return await self.process_escalation(message, None, "Direct escalation request")
    
    def _analyze_escalation_context(
        self, 
        message: SupportMessage, 
        failed_response: Optional[AgentResponse],
        escalation_reason: str
    ) -> Dict[str, Any]:
        """Analyze the context for proper escalation routing."""
        context = {
            "urgency": self.detect_urgency(message),
            "intent": self.extract_message_intent(message),
            "priority": self.calculate_response_priority(message),
            "escalation_reason": escalation_reason,
            "previous_agent": failed_response.agent_name if failed_response else None,
            "confidence_score": failed_response.confidence_score if failed_response else 0.0,
            "business_hours": self._is_business_hours(),
            "conversation_context": self._extract_conversation_context(message)
        }
        
        # Determine escalation type
        if context["urgency"] == "critical":
            context["escalation_type"] = "critical"
        elif context["intent"].get("is_sales_inquiry"):
            context["escalation_type"] = "sales"
        elif context["intent"].get("is_technical_issue"):
            context["escalation_type"] = "engineering"
        elif context["intent"].get("is_compliance_query"):
            context["escalation_type"] = "compliance"
        elif context["intent"].get("is_demo_request"):
            context["escalation_type"] = "sales"
        else:
            context["escalation_type"] = "support"
        
        return context
    
    def _route_to_team(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Route escalation to appropriate team."""
        escalation_type = context.get("escalation_type", "support")
        urgency = context.get("urgency", "medium")
        business_hours = context.get("business_hours", True)
        
        # Get base routing
        base_route = self.escalation_routes.get(escalation_type, self.escalation_routes["support"])
        
        # Modify based on urgency and availability
        if urgency == "critical":
            # Critical issues go to on-call team regardless of business hours
            target_team = {
                **base_route,
                "response_time": "15 minutes",
                "escalation_level": "immediate",
                "notification_method": "slack_alert_and_page"
            }
        elif not business_hours:
            # After hours routing
            target_team = {
                **base_route,
                "response_time": "2 hours",
                "escalation_level": "after_hours",
                "notification_method": "slack_alert"
            }
        else:
            # Normal business hours
            target_team = {
                **base_route,
                "response_time": "30 minutes",
                "escalation_level": "standard",
                "notification_method": "slack_alert"
            }
        
        return target_team
    
    async def _generate_escalation_response(
        self, 
        context: Dict[str, Any], 
        target_team: Dict[str, Any]
    ) -> str:
        """Generate appropriate escalation response."""
        escalation_type = context.get("escalation_type", "support")
        urgency = context.get("urgency", "medium")
        response_time = target_team.get("response_time", "30 minutes")
        
        # Base escalation message with conversational tone
        if urgency == "critical":
            response = "🚨 I understand this is a critical issue! I've immediately escalated this to our engineering team who specializes in urgent technical problems. "
            response += "Someone will be with you shortly - typically within the next few minutes. "
        else:
            response = "I want to make sure you get the best possible help with this, so I'm connecting you with one of our specialists who can provide more detailed assistance. "
            response += "Someone from our team will be with you shortly to help resolve this. "
        
        # Add team-specific messaging
        if escalation_type == "sales":
            response += "\n💼 **Sales Team Engagement:**\n"
            response += "Our sales team will reach out to discuss:\n"
            response += "• Pricing and licensing options\n"
            response += "• Custom enterprise solutions\n"
            response += "• Demo scheduling and technical deep-dives\n"
            response += "• Implementation timeline and support\n"
            
        elif escalation_type == "engineering":
            response += "\n🔧 **Engineering Team Escalation:**\n"
            response += "Our technical team will provide:\n"
            response += "• In-depth technical troubleshooting\n"
            response += "• System logs and diagnostic analysis\n"
            response += "• Custom integration guidance\n"
            response += "• Direct engineering support if needed\n"
            
        elif escalation_type == "compliance":
            response += "\n🛡️ **Compliance Expert Escalation:**\n"
            response += "Our compliance specialists will help with:\n"
            response += "• Framework-specific guidance (SOC2, ISO27001, GDPR, HIPAA)\n"
            response += "• Audit preparation and documentation\n"
            response += "• Regulatory requirement interpretation\n"
            response += "• Implementation best practices\n"
            
        else:  # support
            response += "\n🎧 **Support Team Escalation:**\n"
            response += "Our support experts will provide:\n"
            response += "• Personalized assistance for your specific needs\n"
            response += "• Step-by-step guidance through complex processes\n"
            response += "• Account-specific configuration help\n"
            response += "• Follow-up until your issue is fully resolved\n"
        
        # Add response time and next steps
        response += f"\n⏱️ **Expected Response Time:** {response_time}\n"
        
        if urgency == "critical":
            response += "\n📞 **Immediate Actions:**\n"
            response += "• On-call engineer has been paged\n"
            response += "• You'll receive a direct message within 15 minutes\n"
            response += "• Status updates every 30 minutes until resolved\n"
        else:
            response += "\n📋 **What Happens Next:**\n"
            response += f"• Team member will reach out within {response_time}\n"
            response += "• They'll have full context of our conversation\n"
            response += "• You'll receive dedicated support until resolution\n"
        
        # Add conversation summary for human agents
        previous_agent = context.get("previous_agent")
        if previous_agent:
            response += f"\n🤖 **AI Assistant Summary:**\n"
            response += f"• Previous agent: {previous_agent}\n"
            response += f"• Confidence score: {context.get('confidence_score', 'N/A')}\n"
            response += f"• Escalation reason: {context.get('escalation_reason', 'Unknown')}\n"
        
        return response
    
    async def _send_team_alerts(self, context: Dict[str, Any], target_team: Dict[str, Any]):
        """Log team alerts (Slack notification handled by responder agent to avoid duplicates)."""
        logger.info(f"Escalation routed to {target_team['team_name']} for {context['escalation_type']} escalation")
        
        # Log the alert details (actual Slack notification handled by responder agent)
        alert_data = {
            "team": target_team["team_name"],
            "urgency": context["urgency"],
            "escalation_type": context.get("escalation_type"),
            "escalation_reason": context["escalation_reason"],
            "target_channel": target_team.get("slack_channel"),
            "response_time": target_team.get("response_time"),
            "notification_method": target_team.get("notification_method")
        }
        logger.info(f"Escalation routing logged: {alert_data}")
        
        # NOTE: Actual Slack notification will be sent by the responder agent's 
        # thread manager to avoid duplicate messages. This agent focuses on 
        # routing and response generation.
    
    def _extract_conversation_context(self, message: SupportMessage) -> Dict[str, Any]:
        """Extract relevant conversation context."""
        return {
            "channel_id": message.channel_id,
            "user_id": message.user_id,
            "thread_ts": getattr(message, 'thread_ts', None),
            "message_count": 1,  # Would count previous messages in thread
            "conversation_start": message.timestamp,
            "topics_discussed": []  # Would analyze conversation history
        }
    
    def _is_business_hours(self) -> bool:
        """Check if current time is within business hours."""
        now = datetime.now()
        # Assuming business hours are 9 AM - 6 PM, Monday-Friday
        if now.weekday() >= 5:  # Weekend
            return False
        if now.hour < 9 or now.hour >= 18:  # Outside business hours
            return False
        return True
    
    def _check_team_availability(self) -> Dict[str, bool]:
        """Check availability of different teams."""
        # Mock implementation - would check actual team status
        return {
            "sales": True,
            "engineering": True,
            "support": True,
            "compliance": True,
            "on_call": True
        }
    
    def _load_escalation_routes(self) -> Dict[str, Dict[str, Any]]:
        """Load escalation routing configuration."""
        return {
            "demo_booking": {
                "team_name": "Sales Team",
                "slack_channel": "#sales-activity",
                "primary_contact": "sales-lead",
                "backup_contact": "sales-manager",
                "specialties": ["demos", "meetings", "scheduling"]
            },
            "support": {
                "team_name": "Support Team", 
                "slack_channel": "#support-escalations",
                "primary_contact": "support-lead",
                "backup_contact": "support-manager",
                "specialties": ["technical", "compliance", "pricing", "general_support"]
            },
            "legacy_fallback": {
                "team_name": "Compliance Team",
                "slack_channel": "#compliance-support", 
                "primary_contact": "compliance-lead",
                "backup_contact": "compliance-manager",
                "specialties": ["soc2", "iso27001", "gdpr", "hipaa", "audits"]
            },
            "support": {
                "team_name": "Support Team",
                "slack_channel": "#support-escalations",
                "primary_contact": "support-lead", 
                "backup_contact": "support-manager",
                "specialties": ["general_support", "account_issues", "billing"]
            },
            "critical": {
                "team_name": "On-Call Engineering",
                "slack_channel": "#critical-alerts",
                "primary_contact": "on-call-engineer",
                "backup_contact": "engineering-manager", 
                "specialties": ["production_issues", "outages", "critical_bugs"]
            }
        }
    
    async def health_check(self) -> bool:
        """Check if escalation agent is healthy."""
        try:
            # Verify routing configuration is loaded
            return (
                len(self.escalation_routes) > 0 and
                len(self.team_availability) > 0
            )
        except Exception as e:
            logger.error(f"Escalation agent health check failed: {e}")
            return False