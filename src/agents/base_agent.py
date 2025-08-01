"""Base agent class for all AI agents in the system."""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from src.models.schemas import SupportMessage, AgentResponse
from src.core.config import settings


logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for all AI agents."""
    
    def __init__(self, name: str):
        self.name = name
        self.confidence_threshold = settings.confidence_threshold
    
    @abstractmethod
    async def process_message(self, message: SupportMessage) -> AgentResponse:
        """Process a support message and return an agent response.
        
        Args:
            message: The support message to process
            
        Returns:
            AgentResponse with the agent's response and metadata
        """
        pass
    
    def should_escalate(self, confidence_score: float, message: SupportMessage) -> bool:
        """Determine if the message should be escalated based on confidence and other factors.
        
        Args:
            confidence_score: The confidence score of the response
            message: The original support message
            
        Returns:
            True if the message should be escalated
        """
        # Basic escalation logic
        if confidence_score < self.confidence_threshold:
            return True
        
        # Escalate critical urgency messages for human review
        if message.urgency_level.value == "critical":
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