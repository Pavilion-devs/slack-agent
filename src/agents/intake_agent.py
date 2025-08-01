"""Intake agent for initial message processing and triage."""

import logging
from typing import Dict, Any

from src.agents.base_agent import BaseAgent
from src.models.schemas import SupportMessage, AgentResponse, MessageCategory, UrgencyLevel
from src.integrations.ollama_client import ollama_client


logger = logging.getLogger(__name__)


class IntakeAgent(BaseAgent):
    """Agent responsible for initial message processing and triage."""
    
    def __init__(self):
        super().__init__(name="intake_agent")
        self.acknowledgment_templates = {
            MessageCategory.TECHNICAL: "🔧 Technical question received! Looking into this for you...",
            MessageCategory.COMPLIANCE: "🛡️ Compliance query received! Checking our security documentation...",
            MessageCategory.BILLING: "💳 Billing question received! Let me get that information for you...",
            MessageCategory.DEMO: "🎬 Demo request received! Checking our calendar availability...",
            MessageCategory.GENERAL: "👋 Message received! Searching for the best answer..."
        }
    
    async def process_message(self, message: SupportMessage) -> AgentResponse:
        """Process incoming message for initial triage and routing."""
        try:
            # Analyze the message using Ollama
            analysis = await ollama_client.analyze_query_intent(message.content)
            
            # Update message with analysis results
            message.category = MessageCategory(analysis.get("category", "general"))
            message.urgency_level = UrgencyLevel(analysis.get("urgency", "medium"))
            
            # Extract key information
            confidence_score = analysis.get("confidence", 0.8)
            key_topics = analysis.get("key_topics", [])
            requires_escalation = analysis.get("requires_escalation", False)
            
            # Generate appropriate acknowledgment
            acknowledgment = self.acknowledgment_templates.get(
                message.category, 
                self.acknowledgment_templates[MessageCategory.GENERAL]
            )
            
            # Add estimated time based on category and urgency
            time_estimate = self._estimate_response_time(message.category, message.urgency_level)
            acknowledgment += f" Expected response time: {time_estimate}."
            
            # Determine routing decision
            routing_decision = self._determine_routing(message, analysis)
            
            # Only escalate if confidence is very low or explicitly required
            should_escalate = requires_escalation or confidence_score < 0.3
            escalation_reason = None
            if should_escalate:
                escalation_reason = self._get_escalation_reason(message, analysis)
            
            response = self.format_response(
                response_text=acknowledgment,
                confidence_score=confidence_score,
                should_escalate=should_escalate,
                escalation_reason=escalation_reason,
                metadata={
                    "routing_decision": routing_decision,
                    "key_topics": key_topics,
                    "estimated_response_time": time_estimate,
                    "analysis": analysis
                }
            )
            
            self.log_processing(message, response)
            return response
            
        except Exception as e:
            logger.error(f"Error in intake agent processing: {e}")
            
            # Fallback response
            return self.format_response(
                response_text="👋 Message received! Let me get someone to help you with this.",
                confidence_score=0.5,
                should_escalate=True,
                escalation_reason="Intake agent processing error",
                metadata={"error": str(e)}
            )
    
    def _estimate_response_time(self, category: MessageCategory, urgency: UrgencyLevel) -> str:
        """Estimate response time based on category and urgency."""
        base_times = {
            MessageCategory.TECHNICAL: "3-5 minutes",
            MessageCategory.COMPLIANCE: "5-10 minutes", 
            MessageCategory.BILLING: "2-3 minutes",
            MessageCategory.DEMO: "1-2 minutes",
            MessageCategory.GENERAL: "2-4 minutes"
        }
        
        base_time = base_times.get(category, "2-4 minutes")
        
        # Adjust for urgency
        if urgency == UrgencyLevel.CRITICAL:
            return "1-2 minutes"
        elif urgency == UrgencyLevel.HIGH:
            return base_time
        else:
            return base_time
    
    def _determine_routing(self, message: SupportMessage, analysis: Dict[str, Any]) -> str:
        """Determine which agent should handle the message next."""
        category = message.category
        
        # Route based on category
        if category == MessageCategory.COMPLIANCE:
            return "compliance_agent"
        elif category == MessageCategory.DEMO:
            return "demo_agent"
        elif category in [MessageCategory.TECHNICAL, MessageCategory.BILLING, MessageCategory.GENERAL]:
            return "knowledge_agent"
        else:
            return "knowledge_agent"  # Default routing
    
    def _get_escalation_reason(self, message: SupportMessage, analysis: Dict[str, Any]) -> str:
        """Generate escalation reason based on message analysis."""
        reasons = []
        
        if message.urgency_level == UrgencyLevel.CRITICAL:
            reasons.append("Critical urgency level")
        
        if analysis.get("confidence", 1.0) < self.confidence_threshold:
            reasons.append(f"Low confidence score ({analysis.get('confidence', 0.0):.2f})")
        
        if analysis.get("requires_escalation", False):
            reasons.append("Complex query requiring human expertise")
        
        # Check for specific escalation keywords
        escalation_keywords = ["legal", "contract", "lawsuit", "emergency", "outage", "data breach"]
        if any(keyword in message.content.lower() for keyword in escalation_keywords):
            reasons.append("Contains sensitive keywords requiring human review")
        
        return "; ".join(reasons) if reasons else "General escalation recommended"
    
    async def health_check(self) -> bool:
        """Check if intake agent dependencies are healthy."""
        try:
            # Test Ollama connection
            return await ollama_client.health_check()
        except Exception as e:
            logger.error(f"Intake agent health check failed: {e}")
            return False