"""
Delve LangGraph Workflow - The new main workflow system.
Replaces the problematic multi-agent routing system with a clean LangGraph implementation.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from src.models.schemas import SupportMessage, AgentState
from src.integrations.slack_client import slack_client
from src.workflows.langgraph_workflow import langgraph_workflow

logger = logging.getLogger(__name__)


class DelveLangGraphWorkflow:
    """
    Main workflow class that integrates LangGraph with Slack communication.
    
    This replaces the old ImprovedWorkflow and MultiAgentSystem with a clean,
    graph-based approach that solves the routing and priority issues.
    """
    
    def __init__(self, responder_agent=None):
        self.workflow_name = "delve_langgraph_workflow"
        self.system_initialized = False
        self.responder_agent = responder_agent  # New bidirectional responder system
        logger.info("Delve LangGraph Workflow initialized")
    
    async def process_message(self, message: SupportMessage) -> AgentState:
        """
        Process support message through the LangGraph workflow.
        
        This is the main entry point that replaces the old workflow logic.
        """
        try:
            logger.info(f"Processing message {message.message_id} through Delve LangGraph workflow")
            
            # Step 1: Send immediate acknowledgment
            try:
                await slack_client.send_acknowledgment(message)
                logger.info(f"Acknowledgment sent for message {message.message_id}")
            except Exception as e:
                logger.warning(f"Could not send acknowledgment: {e}")
            
            # Step 2: Process through LangGraph workflow
            workflow_state = await langgraph_workflow.process_message(message)
            
            # Step 3: Convert LangGraph state to legacy AgentState for compatibility
            agent_state = self._convert_to_agent_state(workflow_state)
            
            # Step 4: Send response to Slack
            final_response = workflow_state.get('final_response') if isinstance(workflow_state, dict) else getattr(workflow_state, 'final_response', None)
            
            if final_response:
                try:
                    await slack_client.send_response(
                        message,
                        final_response.response_text,
                        final_response.sources
                    )
                    logger.info(f"Response sent for message {message.message_id}")
                    
                    # Handle escalation through responder system if needed
                    if final_response.should_escalate:
                        if self.responder_agent:
                            # Use new bidirectional responder system
                            await self._handle_escalation_through_responder(
                                message, final_response
                            )
                        else:
                            # Fallback to legacy escalation for backward compatibility
                            await slack_client.send_escalation_notification(
                                message,
                                final_response.escalation_reason
                            )
                        logger.info(f"Escalation handled for message {message.message_id}")
                        
                except Exception as e:
                    logger.warning(f"Could not send response: {e}")
            
            # Log final metrics
            processing_completed = workflow_state.get('processing_completed') if isinstance(workflow_state, dict) else getattr(workflow_state, 'processing_completed', None)
            processing_started = workflow_state.get('processing_started') if isinstance(workflow_state, dict) else getattr(workflow_state, 'processing_started', None)
            intent = workflow_state.get('intent') if isinstance(workflow_state, dict) else getattr(workflow_state, 'intent', None)
            intent_confidence = workflow_state.get('intent_confidence') if isinstance(workflow_state, dict) else getattr(workflow_state, 'intent_confidence', 0.0)
            
            if processing_completed and processing_started:
                processing_time = (processing_completed - processing_started).total_seconds()
                
                logger.info(
                    f"Message {message.message_id} processed in {processing_time:.2f}s. "
                    f"Intent: {intent}, "
                    f"Confidence: {intent_confidence:.2f}, "
                    f"Final agent: {final_response.agent_name if final_response else 'none'}, "
                    f"Escalated: {final_response.should_escalate if final_response else False}"
                )
            
            return agent_state
            
        except Exception as e:
            logger.error(f"Error in Delve LangGraph workflow: {e}")
            
            # Create error state
            error_state = AgentState(
                message=message,
                agent_responses=[],
                escalated=True,
                final_response="I'm experiencing technical difficulties. Let me connect you with our support team immediately.",
                processing_completed=datetime.now()
            )
            
            # Try to notify about the error
            try:
                await slack_client.send_response(
                    message,
                    error_state.final_response
                )
                if self.responder_agent:
                    # Use responder system for error escalation
                    try:
                        await self.responder_agent.escalate_conversation(
                            support_message=message,
                            escalation_reason=f"LangGraph workflow error: {str(e)}",
                            conversation_history=[]
                        )
                    except:
                        # Ultimate fallback
                        await slack_client.send_escalation_notification(
                            message,
                            f"LangGraph workflow error: {str(e)}"
                        )
                else:
                    await slack_client.send_escalation_notification(
                        message,
                        f"LangGraph workflow error: {str(e)}"
                    )
            except Exception as fallback_error:
                logger.error(f"Even fallback notification failed: {fallback_error}")
            
            return error_state
    
    async def _handle_escalation_through_responder(
        self, 
        message: SupportMessage, 
        final_response
    ) -> None:
        """Handle escalation through the new bidirectional responder system."""
        try:
            # Build conversation history from any available context
            conversation_history = []
            
            # Extract conversation history if available (this could be enhanced)
            if hasattr(final_response, 'metadata') and final_response.metadata:
                conversation_history = final_response.metadata.get('conversation_history', [])
            
            # Add the current AI response to history
            conversation_history.append({
                'sender': 'AI Agent',
                'content': final_response.response_text,
                'timestamp': datetime.now().isoformat(),
                'confidence_score': getattr(final_response, 'confidence_score', 0.0),
                'agent_name': getattr(final_response, 'agent_name', 'unknown')
            })
            
            # Escalate through responder system
            escalation_response = await self.responder_agent.escalate_conversation(
                support_message=message,
                escalation_reason=final_response.escalation_reason,
                conversation_history=conversation_history
            )
            
            session_id = getattr(escalation_response, 'session_id', 'None')
            logger.info(f"Escalated through responder system: session_id={session_id}")
            
        except Exception as e:
            logger.error(f"Error escalating through responder system: {e}")
            # Fallback to legacy escalation
            await slack_client.send_escalation_notification(
                message,
                final_response.escalation_reason
            )
    
    def set_responder_agent(self, responder_agent):
        """Set the responder agent for handling escalations."""
        self.responder_agent = responder_agent
        logger.info("Responder agent configured for escalations")
    
    def _convert_to_agent_state(self, workflow_result) -> AgentState:
        """Convert LangGraph result to legacy AgentState for compatibility."""
        agent_responses = []
        
        # Handle both dict and WorkflowState object returns
        if isinstance(workflow_result, dict):
            # LangGraph returns a dict, extract the data
            subgraph_results = workflow_result.get('subgraph_results', {})
            final_response = workflow_result.get('final_response')
            message = workflow_result.get('message')
            processing_completed = workflow_result.get('processing_completed')
        else:
            # WorkflowState object
            subgraph_results = getattr(workflow_result, 'subgraph_results', {})
            final_response = getattr(workflow_result, 'final_response', None)
            message = getattr(workflow_result, 'message', None)
            processing_completed = getattr(workflow_result, 'processing_completed', None)
        
        # Convert subgraph results to agent responses
        for subgraph_name, result in subgraph_results.items():
            agent_responses.append(result)
        
        # Add final response if it exists
        if final_response:
            agent_responses.append(final_response)
        
        return AgentState(
            message=message,
            agent_responses=agent_responses,
            escalated=final_response.should_escalate if final_response else False,
            final_response=final_response.response_text if final_response else "",
            processing_completed=processing_completed or datetime.now()
        )
    
    async def health_check(self) -> bool:
        """Check if the workflow is healthy."""
        try:
            # Check LangGraph workflow health
            health_result = await langgraph_workflow.health_check()
            return health_result.get("healthy", False)
            
        except Exception as e:
            logger.error(f"Delve LangGraph workflow health check failed: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get workflow statistics."""
        return {
            'workflow_name': self.workflow_name,
            'system_initialized': self.system_initialized,
            'workflow_type': 'langgraph',
            'description': 'LangGraph-based workflow with intent detection, planning, and parallel execution'
        }


# Global instance
delve_langgraph_workflow = DelveLangGraphWorkflow()