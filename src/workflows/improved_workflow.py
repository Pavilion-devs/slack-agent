"""
Enhanced workflow using the new multi-agent architecture.
Upgraded from single-agent to intelligent multi-agent system with specialized routing.
"""

import logging
from typing import Dict, Any
from datetime import datetime

from src.models.schemas import AgentState, SupportMessage
from src.integrations.slack_client import slack_client
# NOTE: Import multi_agent_system lazily to avoid circular imports


logger = logging.getLogger(__name__)


class ImprovedWorkflow:
    """
    Enhanced workflow using the new multi-agent architecture.
    Provides intelligent routing, specialized responses, and proper escalation.
    """
    
    def __init__(self):
        self.workflow_name = "enhanced_multi_agent_workflow"
        self.system_initialized = False
        logger.info("Enhanced multi-agent workflow initialized")
    
    async def process_message(self, message: SupportMessage) -> AgentState:
        """
        Process support message through the enhanced multi-agent workflow.
        
        Args:
            message: The support message to process
            
        Returns:
            AgentState with processing results
        """
        try:
            # Initialize multi-agent system if needed
            if not self.system_initialized:
                await self._initialize_system()
            
            # Create initial state
            state = AgentState(message=message)
            logger.info(f"Starting enhanced multi-agent workflow for message {message.message_id}")
            
            # Step 1: Send immediate acknowledgment
            try:
                await slack_client.send_acknowledgment(message)
                logger.info(f"Acknowledgment sent for message {message.message_id}")
            except Exception as e:
                logger.warning(f"Could not send acknowledgment: {e}")
            
            # Step 2: Process through multi-agent system
            # Lazy import to avoid circular imports
            from src.agents.multi_agent_system import multi_agent_system
            agent_response = await multi_agent_system.process_message(message)
            state.agent_responses.append(agent_response)
            
            # Step 3: Handle response - escalation is already handled by multi-agent system
            state.final_response = agent_response.response_text
            state.escalated = agent_response.should_escalate
            
            # Step 4: Send response to Slack
            try:
                if agent_response.should_escalate:
                    # Response already includes escalation message
                    await slack_client.send_response(
                        message,
                        agent_response.response_text,
                        agent_response.sources
                    )
                    logger.info(f"Escalation response sent for message {message.message_id}")
                else:
                    # Send normal response
                    await slack_client.send_response(
                        message,
                        agent_response.response_text,
                        agent_response.sources
                    )
                    logger.info(f"Agent response sent for message {message.message_id}")
            except Exception as e:
                logger.warning(f"Could not send response: {e}")
            
            # Mark processing as completed
            state.processing_completed = datetime.now()
            
            # Log final metrics
            processing_time = (
                state.processing_completed - state.processing_started
            ).total_seconds()
            
            logger.info(
                f"Message {message.message_id} processed in {processing_time:.2f}s. "
                f"Agent: {agent_response.agent_name}, "
                f"Confidence: {agent_response.confidence_score:.2f}, "
                f"Escalated: {state.escalated}"
            )
            
            return state
            
        except Exception as e:
            logger.error(f"Error in improved workflow: {e}")
            
            # Create error state with escalation
            error_state = AgentState(
                message=message,
                agent_responses=[],
                escalated=True,
                final_response="I'm experiencing technical difficulties. Let me get a human agent to help you immediately.",
                processing_completed=datetime.now()
            )
            
            # Try to notify about the error
            try:
                await slack_client.send_response(
                    message,
                    error_state.final_response
                )
                await slack_client.send_escalation_notification(
                    message,
                    f"Workflow processing error: {str(e)}"
                )
            except Exception as fallback_error:
                logger.error(f"Even fallback notification failed: {fallback_error}")
            
            return error_state
    
    async def _initialize_system(self):
        """Initialize the multi-agent system if not already done."""
        try:
            logger.info("Initializing multi-agent system...")
            
            # Lazy import to avoid circular imports
            from src.agents.multi_agent_system import multi_agent_system
            
            success = await multi_agent_system.initialize()
            
            if success:
                self.system_initialized = True
                logger.info("Multi-agent system initialized successfully")
            else:
                logger.error("Failed to initialize multi-agent system")
                # Continue with degraded functionality
                
        except Exception as e:
            logger.error(f"Error initializing multi-agent system: {e}")
            # Continue with degraded functionality
    
    def _create_escalation_message(self, rag_response) -> str:
        """Create an appropriate escalation message based on the RAG response."""
        
        base_message = "I've analyzed your question and want to make sure you get the most accurate help."
        
        # Customize based on confidence and reason
        if rag_response.confidence_score < 0.5:
            return f"{base_message} Your question requires specialized expertise that our human team can provide better. Someone will be with you shortly! 👩‍💼"
        
        elif "sales" in rag_response.escalation_reason.lower():
            return f"{base_message} For sales inquiries and demos, our sales team can provide personalized assistance and answer specific questions about pricing and implementation. Someone will reach out shortly! 💼"
        
        elif "technical" in rag_response.escalation_reason.lower():
            return f"{base_message} For technical integration questions, our engineering team can provide detailed guidance and custom solutions. A technical expert will be with you soon! 🔧"
        
        elif "urgent" in rag_response.escalation_reason.lower():
            return f"{base_message} I see this is urgent - I've prioritized your request and a team member will assist you immediately! ⚡"
        
        else:
            return f"{base_message} Our human experts will provide you with comprehensive assistance. Someone will be with you shortly! 🚀"
    
    async def health_check(self) -> bool:
        """Check if the workflow is healthy."""
        try:
            # Check system initialization first
            if not self.system_initialized:
                logger.warning("Multi-agent system not initialized")
                return False
            
            # Lazy import to avoid circular imports
            from src.agents.multi_agent_system import multi_agent_system
            
            # Check multi-agent system health
            multi_agent_health = await multi_agent_system.health_check()
            return multi_agent_health["system_healthy"]
            
        except Exception as e:
            logger.error(f"Workflow health check failed: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get workflow statistics."""
        multi_agent_stats = {}
        if self.system_initialized:
            # Lazy import to avoid circular imports
            from src.agents.multi_agent_system import multi_agent_system
            multi_agent_stats = multi_agent_system.get_performance_stats()
        
        return {
            'workflow_name': self.workflow_name,
            'system_initialized': self.system_initialized,
            'multi_agent_stats': multi_agent_stats
        }


# Global instance
improved_workflow = ImprovedWorkflow()