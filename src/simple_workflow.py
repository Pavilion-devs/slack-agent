"""Simplified workflow for testing without LangGraph dependencies."""

import logging
from typing import Dict, Any, List
from datetime import datetime

from src.models.schemas import AgentState, SupportMessage, AgentResponse
from src.agents.intake_agent import IntakeAgent
from src.agents.knowledge_agent import KnowledgeAgent
from src.integrations.slack_client import slack_client
from src.integrations.knowledge_loader import initialize_knowledge_base


logger = logging.getLogger(__name__)


class SimpleWorkflow:
    """Simplified workflow for processing support messages without LangGraph."""
    
    def __init__(self):
        # Initialize agents
        self.intake_agent = IntakeAgent()
        self.knowledge_agent = KnowledgeAgent()
        self.knowledge_initialized = False
        
        logger.info("Simple workflow initialized successfully")
    
    async def process_message(self, message: SupportMessage) -> AgentState:
        """Process a support message through the simplified workflow."""
        try:
            # Initialize knowledge base if not already done
            if not self.knowledge_initialized:
                logger.info("Initializing knowledge base...")
                success = await initialize_knowledge_base()
                if success:
                    self.knowledge_initialized = True
                    logger.info("Knowledge base initialized successfully")
                else:
                    logger.warning("Failed to initialize knowledge base")
            
            # Create initial state
            state = AgentState(message=message)
            
            logger.info(f"Starting workflow for message {message.message_id}")
            
            # Step 1: Intake processing
            intake_response = await self.intake_agent.process_message(message)
            state.agent_responses.append(intake_response)
            
            # Send acknowledgment
            try:
                await slack_client.send_acknowledgment(message)
            except Exception as e:
                logger.warning(f"Could not send acknowledgment: {e}")
            
            # Step 2: Check if immediate escalation is needed (only for critical cases)
            if intake_response.should_escalate and intake_response.confidence_score < 0.3:
                state.escalated = True
                state.final_response = "I've escalated your question to our human support team. Someone will be with you shortly."
                
                # Send escalation notification
                try:
                    await slack_client.send_escalation_notification(
                        message,
                        intake_response.escalation_reason or "Manual escalation"
                    )
                except Exception as e:
                    logger.warning(f"Could not send escalation: {e}")
                
                state.processing_completed = datetime.now()
                return state
            
            # Step 3: Knowledge processing
            knowledge_response = await self.knowledge_agent.process_message(message)
            state.agent_responses.append(knowledge_response)
            
            # Step 4: Determine final action
            if knowledge_response.should_escalate:
                state.escalated = True
                state.final_response = "I've escalated your question to our human support team. Someone will be with you shortly."
                
                # Send escalation notification
                try:
                    await slack_client.send_escalation_notification(
                        message,
                        knowledge_response.escalation_reason or "Knowledge agent escalation"
                    )
                except Exception as e:
                    logger.warning(f"Could not send escalation: {e}")
            else:
                # Send the knowledge response
                state.final_response = knowledge_response.response_text
                
                try:
                    await slack_client.send_response(
                        message,
                        knowledge_response.response_text,
                        knowledge_response.sources
                    )
                except Exception as e:
                    logger.warning(f"Could not send response: {e}")
            
            # Mark processing as completed
            state.processing_completed = datetime.now()
            
            # Log final metrics
            processing_time = (
                state.processing_completed - state.processing_started
            ).total_seconds()
            
            logger.info(
                f"Message {message.message_id} processed in {processing_time:.2f}s, "
                f"escalated: {state.escalated}, agents used: {len(state.agent_responses)}"
            )
            
            return state
            
        except Exception as e:
            logger.error(f"Error processing message through workflow: {e}")
            
            # Return error state
            error_response = AgentResponse(
                agent_name="workflow_error",
                response_text="I'm experiencing technical difficulties. Let me get a human agent to help you.",
                confidence_score=0.0,
                should_escalate=True,
                escalation_reason=f"Workflow processing error: {str(e)}"
            )
            
            error_state = AgentState(
                message=message,
                agent_responses=[error_response],
                escalated=True,
                final_response=error_response.response_text,
                processing_completed=datetime.now()
            )
            
            return error_state
    
    async def health_check(self) -> bool:
        """Check if workflow and all agents are healthy."""
        try:
            intake_healthy = await self.intake_agent.health_check()
            knowledge_healthy = await self.knowledge_agent.health_check()
            
            return intake_healthy and knowledge_healthy
            
        except Exception as e:
            logger.error(f"Workflow health check failed: {e}")
            return False


# Global simple workflow instance
simple_workflow = SimpleWorkflow()