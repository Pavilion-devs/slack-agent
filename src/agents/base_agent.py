"""Base agent class for all AI agents in the system."""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime

from src.models.schemas import SupportMessage, AgentResponse
from src.core.config import settings


logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for all AI agents."""
    
    def __init__(self, name: str):
        self.name = name
        self.confidence_threshold = settings.confidence_threshold
    
    @abstractmethod
    def should_handle(self, message: SupportMessage) -> bool:
        """
        Determine if this agent should handle the given message.
        
        Args:
            message: The support message to evaluate
            
        Returns:
            bool: True if this agent can handle the message
        """
        pass
    
    @abstractmethod
    async def process_message(self, message: SupportMessage) -> AgentResponse:
        """Process a support message and return an agent response.
        
        Args:
            message: The support message to process
            
        Returns:
            AgentResponse with the agent's response and metadata
        """
        pass
    
    def extract_keywords(self, text: str, keyword_list: List[str]) -> List[str]:
        """
        Extract matching keywords from text.
        
        Args:
            text: Text to search in
            keyword_list: List of keywords to search for
            
        Returns:
            List of found keywords
        """
        text_lower = text.lower()
        return [keyword for keyword in keyword_list if keyword in text_lower]
    
    def detect_urgency(self, message: SupportMessage) -> str:
        """
        Detect urgency level of the message.
        
        Args:
            message: The support message
            
        Returns:
            str: 'critical', 'high', 'medium', or 'low'
        """
        critical_keywords = [
            'production down', 'api down', 'outage', '500 error', '404 error',
            'not working', 'broken', 'crashed', 'failing', 'emergency'
        ]
        
        urgent_keywords = [
            'urgent', 'asap', 'immediately', 'critical', 'priority'
        ]
        
        content_lower = message.content.lower()
        
        if any(keyword in content_lower for keyword in critical_keywords):
            return 'critical'
        elif any(keyword in content_lower for keyword in urgent_keywords):
            return 'high'
        else:
            return 'medium'

    def should_escalate(self, confidence_score: float, message: SupportMessage) -> bool:
        """Determine if the message should be escalated based on confidence and other factors.
        
        Args:
            confidence_score: The confidence score of the response
            message: The original support message
            
        Returns:
            True if the message should be escalated
        """
        # ALWAYS escalate critical issues regardless of confidence
        urgency = self.detect_urgency(message)
        if urgency == 'critical':
            return True
        
        # Basic escalation logic
        if confidence_score < self.confidence_threshold:
            return True
        
        # Escalate critical urgency messages for human review
        if hasattr(message, 'urgency_level') and message.urgency_level.value == "critical":
            return True
        
        return False
    
    def format_response(
        self, 
        response_text: str, 
        confidence_score: float,
        sources: Optional[list] = None,
        should_escalate: bool = False,
        escalation_reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """Format a standardized agent response.
        
        Args:
            response_text: The main response text
            confidence_score: Confidence score (0.0 to 1.0)
            sources: List of sources used
            should_escalate: Whether to escalate
            escalation_reason: Reason for escalation
            metadata: Additional metadata
            
        Returns:
            Formatted AgentResponse
        """
        return AgentResponse(
            agent_name=self.name,
            response_text=response_text,
            confidence_score=confidence_score,
            sources=sources or [],
            should_escalate=should_escalate,
            escalation_reason=escalation_reason,
            metadata=metadata or {}
        )
    
    async def health_check(self) -> bool:
        """Check if the agent is healthy and ready to process messages.
        
        Returns:
            True if healthy, False otherwise
        """
        return True
    
    def log_processing(self, message: SupportMessage, response: AgentResponse):
        """Log agent processing for monitoring and debugging."""
        logger.info(
            f"Agent {self.name} processed message {message.message_id} "
            f"with confidence {response.confidence_score:.2f}"
        )
    
    def extract_message_intent(self, message: SupportMessage) -> Dict[str, Any]:
        """Extract intent and key information from message."""
        content_lower = message.content.lower()
        
        intent_data = {
            "is_demo_request": any(word in content_lower for word in [
                'demo', 'schedule', 'meeting', 'call', 'presentation'
            ]),
            "is_technical_issue": any(word in content_lower for word in [
                'sso', 'saml', 'api', 'integration', 'oauth', 'error', 'not working'
            ]),
            "is_compliance_query": any(word in content_lower for word in [
                'soc2', 'iso27001', 'gdpr', 'hipaa', 'compliance', 'audit'
            ]),
            "is_sales_inquiry": any(word in content_lower for word in [
                'pricing', 'cost', 'license', 'enterprise', 'contract'
            ]),
            "has_urgent_keywords": any(word in content_lower for word in [
                'urgent', 'asap', 'immediately', 'critical', 'emergency'
            ])
        }
        
        return intent_data
    
    def calculate_response_priority(self, message: SupportMessage) -> int:
        """Calculate priority score (1-5, 5 being highest)."""
        urgency = self.detect_urgency(message)
        intent = self.extract_message_intent(message)
        
        if urgency == 'critical':
            return 5
        elif urgency == 'high' or intent.get('has_urgent_keywords'):
            return 4
        elif intent.get('is_technical_issue'):
            return 3
        elif intent.get('is_compliance_query'):
            return 3
        else:
            return 2