"""
Improved workflow using the new RAG-based architecture.
Simplified from complex multi-agent system to intelligent single-agent processing.
"""

import logging
from typing import Dict, Any
from datetime import datetime

from src.models.schemas import AgentState, SupportMessage
from src.agents.rag_agent import rag_agent
from src.integrations.slack_client import slack_client
from src.core.rag_system import rag_system


logger = logging.getLogger(__name__)


class ImprovedWorkflow:
    """
    Streamlined workflow using the new RAG-based architecture.
    Provides faster, more accurate responses with intelligent escalation.
    """
    
    def __init__(self):
        self.workflow_name = "improved_rag_workflow"
        self.knowledge_initialized = False
        logger.info("Improved RAG workflow initialized")
    
    async def process_message(self, message: SupportMessage) -> AgentState:
        """
        Process support message through the improved workflow.
        
        Args:
            message: The support message to process
            
        Returns:
            AgentState with processing results
        """
        try:
            # Initialize knowledge base if needed
            if not self.knowledge_initialized:
                await self._initialize_knowledge_base()
            
            # Create initial state
            state = AgentState(message=message)
            logger.info(f"Starting improved workflow for message {message.message_id}")
            
            # Step 1: Send immediate acknowledgment
            try:
                await slack_client.send_acknowledgment(message)
                logger.info(f"Acknowledgment sent for message {message.message_id}")
            except Exception as e:
                logger.warning(f"Could not send acknowledgment: {e}")
            
            # Step 2: Process through RAG agent
            rag_response = await rag_agent.process_message(message)
            state.agent_responses.append(rag_response)
            
            # Step 3: Determine final action based on RAG response
            if rag_response.should_escalate:
                # Escalate to human
                state.escalated = True
                state.final_response = self._create_escalation_message(rag_response)
                
                try:
                    await slack_client.send_escalation_notification(
                        message,
                        rag_response.escalation_reason or "RAG agent escalation"
                    )
                    logger.info(f"Escalation notification sent for message {message.message_id}")
                except Exception as e:
                    logger.warning(f"Could not send escalation notification: {e}")
            
            else:
                # Send RAG response directly
                state.final_response = rag_response.response_text
                
                try:
                    await slack_client.send_response(
                        message,
                        rag_response.response_text,
                        rag_response.sources
                    )
                    logger.info(f"RAG response sent for message {message.message_id}")
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
                f"Confidence: {rag_response.confidence_score:.2f}, "
                f"Escalated: {state.escalated}, "
                f"RAG processing time: {rag_response.processing_time:.2f}s"
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
    
    async def _initialize_knowledge_base(self):
        """Initialize the knowledge base if not already done."""
        try:
            logger.info("Initializing knowledge base...")
            
            # Path to knowledge file
            knowledge_file_path = "knowledge_restructured.txt"
            
            success = await rag_system.initialize_knowledge_base(knowledge_file_path)
            
            if success:
                self.knowledge_initialized = True
                logger.info("Knowledge base initialized successfully")
            else:
                logger.error("Failed to initialize knowledge base")
                # Continue without knowledge base - will escalate all queries
                
        except Exception as e:
            logger.error(f"Error initializing knowledge base: {e}")
            # Continue without knowledge base
    
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
            # Check RAG agent health
            rag_healthy = await rag_agent.health_check()
            
            # Check knowledge base initialization
            if not self.knowledge_initialized:
                logger.warning("Knowledge base not initialized")
                return False
            
            return rag_healthy
            
        except Exception as e:
            logger.error(f"Workflow health check failed: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get workflow statistics."""
        return {
            'workflow_name': self.workflow_name,
            'knowledge_initialized': self.knowledge_initialized,
            'rag_agent_stats': rag_agent.get_stats()
        }


# Global instance
improved_workflow = ImprovedWorkflow()