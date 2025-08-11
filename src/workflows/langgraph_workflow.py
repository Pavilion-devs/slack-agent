"""
LangGraph-based workflow system that replaces the current agent routing approach.
Implements the vision.md architecture with proper intent detection, planning, and execution.
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Literal
from datetime import datetime
from enum import Enum
import os

from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel, Field

from src.models.schemas import SupportMessage, AgentResponse

logger = logging.getLogger(__name__)


class IntentType(str, Enum):
    """Supported intent types for message classification."""
    SCHEDULING = "scheduling"
    INFORMATION = "information"
    TECHNICAL_SUPPORT = "technical_support"
    ESCALATION = "escalation"
    UNKNOWN = "unknown"


class WorkflowState(BaseModel):
    """State object that flows through the LangGraph workflow."""
    # Input
    message: SupportMessage
    
    # Intent Analysis
    intent: Optional[IntentType] = None
    intent_confidence: float = 0.0
    intent_metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Planning
    selected_subgraphs: List[str] = Field(default_factory=list)
    execution_plan: Dict[str, Any] = Field(default_factory=dict)
    
    # Execution Results
    subgraph_results: Dict[str, AgentResponse] = Field(default_factory=dict)
    
    # Final Output
    final_response: Optional[AgentResponse] = None
    requires_human_approval: bool = False
    
    # Metadata
    processing_started: datetime = Field(default_factory=datetime.now)
    processing_completed: Optional[datetime] = None
    error_details: Optional[str] = None
    
    class Config:
        arbitrary_types_allowed = True


class LangGraphWorkflow:
    """
    LangGraph-based workflow system that implements the vision.md architecture.
    
    Graph Structure:
    START -> intent_detector -> planner -> execute_subgraphs -> human_approval_gate -> finalize -> END
    """
    
    def __init__(self):
        self.workflow_name = "langgraph_multi_agent_workflow"
        self.graph = None
        self.responder_agent = None  # Will be initialized with dependency injection
        self.compiled_graph = None
        self.memory = MemorySaver()
        self._build_graph()
    
    def set_responder_agent(self, responder_agent):
        """Set responder agent for escalation handling (dependency injection)."""
        self.responder_agent = responder_agent
        logger.info("Responder agent connected to workflow")
        
    def _build_graph(self):
        """Build the LangGraph workflow."""
        # Create the state graph
        builder = StateGraph(WorkflowState)
        
        # Add nodes
        builder.add_node("intent_detector", self._detect_intent)
        builder.add_node("planner", self._plan_execution)
        builder.add_node("execute_subgraphs", self._execute_subgraphs)
        builder.add_node("human_approval_gate", self._human_approval_gate)
        builder.add_node("finalize", self._finalize_response)
        
        # Add edges
        builder.add_edge(START, "intent_detector")
        builder.add_edge("intent_detector", "planner")
        builder.add_edge("planner", "execute_subgraphs")
        
        # Conditional edge for human approval
        builder.add_conditional_edges(
            "execute_subgraphs",
            self._should_require_approval,
            {
                "approve": "human_approval_gate",
                "skip": "finalize"
            }
        )
        builder.add_edge("human_approval_gate", "finalize")
        builder.add_edge("finalize", END)
        
        # Compile the graph
        self.compiled_graph = builder.compile(checkpointer=self.memory)
        
        logger.info("LangGraph workflow compiled successfully")
    
    async def _detect_intent(self, state: WorkflowState) -> WorkflowState:
        """Node 1: Detect intent from the message using sophisticated analysis with moderation."""
        logger.info(f"Intent detection for message: {state.message.message_id}")
        
        try:
            # First, run moderation check
            from src.utils.moderation import moderation_filter
            moderation_result = moderation_filter.analyze_message(state.message.content)
            state.intent_metadata = {"moderation": moderation_result}
            
            # If hostile, handle immediately
            if moderation_result['is_hostile']:
                state.intent = IntentType.ESCALATION
                state.intent_confidence = 1.0
                state.intent_metadata.update({
                    "escalation_type": "moderation", 
                    "suggested_response": moderation_result['suggested_response']
                })
                logger.info("Message flagged as hostile - escalating")
                return state
            
            content_lower = state.message.content.lower()
            
            # Import the intent classifier
            from src.core.intent_classifier import IntentClassifier
            classifier = IntentClassifier()
            
            # Use AI-powered intent classification
            intent_result = await classifier.classify_intent(state.message.content)
            
            state.intent = IntentType(intent_result.get('intent', 'unknown'))
            state.intent_confidence = intent_result.get('confidence', 0.0)
            state.intent_metadata.update(intent_result.get('metadata', {}))
            
            # Override scheduling for connection requests
            if moderation_result.get('is_connection_request') and state.intent == IntentType.SCHEDULING:
                state.intent = IntentType.ESCALATION
                state.intent_metadata["escalation_type"] = "connection_request"
                logger.info("Connection request detected - escalating instead of scheduling")
            
            logger.info(f"Intent detected: {state.intent} (confidence: {state.intent_confidence})")
            
        except Exception as e:
            logger.error(f"Intent detection failed: {e}")
            # Fallback to rule-based classification
            state.intent, state.intent_confidence = self._fallback_intent_detection(state.message.content.lower())
            state.intent_metadata = {"fallback": True, "error": str(e)}
        
        return state
    
    def _fallback_intent_detection(self, content_lower: str) -> tuple[IntentType, float]:
        """Fallback rule-based intent detection."""
        # Very explicit scheduling patterns (much more restrictive)
        explicit_scheduling = [
            r'\b(?:can|could|would)\s+(?:we|you|i)\s+(?:schedule|book)\s+(?:a|an|the)\s*(?:demo|meeting|call)',
            r'\bi\s+(?:want|need|would like)\s+to\s+(?:schedule|book)\s+(?:a|an|the)\s*(?:demo|meeting|call)',
            r'\bschedule\s+(?:a|an|the)\s+(?:demo|meeting|call)\s*(?:with|for)',
            r'\bbook\s+(?:a|an|the)\s+(?:demo|meeting|call)\s*(?:with|for)',
            r'\b(?:when|what time)\s+(?:can|could|are)\s+(?:we|you)\s+(?:meet|schedule|have)\s+(?:a|the)\s*(?:demo|call)',
        ]
        
        # Technical support patterns
        technical_patterns = [
            r'\b(?:error|bug|issue|problem|not working|broken|failed)',
            r'\b(?:api|integration|technical|code|implementation)',
            r'\b(?:troubleshoot|debug|fix|resolve)',
        ]
        
        # Information seeking patterns (not scheduling)
        info_patterns = [
            r'\b(?:what is|what does|how does|tell me about|explain)',
            r'\b(?:documentation|docs|guide|tutorial)',
            r'\b(?:compliance|soc2|iso|gdpr|hipaa)\b.*(?:work|process)',
        ]
        
        import re
        
        # Check scheduling first (but lower confidence if mixed with other concerns)
        for pattern in explicit_scheduling:
            if re.search(pattern, content_lower):
                # Lower confidence if it mentions audit, compliance issues
                if any(word in content_lower for word in ['audit', 'compliance', 'certificate', 'done in', 'months', 'weeks']):
                    return IntentType.INFORMATION, 0.75  # Treat as information request instead
                return IntentType.SCHEDULING, 0.85
        
        # Check technical support
        for pattern in technical_patterns:
            if re.search(pattern, content_lower):
                return IntentType.TECHNICAL_SUPPORT, 0.80
        
        # Check information seeking
        for pattern in info_patterns:
            if re.search(pattern, content_lower):
                return IntentType.INFORMATION, 0.75
        
        # Default to information with low confidence
        return IntentType.INFORMATION, 0.60
    
    def _detect_multi_intent(self, content_lower: str) -> bool:
        """Detect if message contains multiple intents that should be handled sequentially."""
        # Common multi-intent patterns
        multi_patterns = [
            # Information + scheduling
            (r'\b(send|give|show|provide)\s+.*\b(guide|doc|info|material|link)\b.*\b(schedule|demo|book|meeting)\b', True),
            (r'\b(if\s+.*\s+looks?\s+good|if\s+.*\s+works?)\s+.*\b(schedule|demo|book|meeting)\b', True),
            # Multiple requests with "and"
            (r'\b(can\s+you|could\s+you)\s+.*\s+and\s+.*\b(schedule|demo|book|meeting)\b', True),
        ]
        
        import re
        for pattern, _ in multi_patterns:
            if re.search(pattern, content_lower):
                logger.info(f"Multi-intent pattern matched: {pattern}")
                return True
        
        return False
    
    async def _plan_execution(self, state: WorkflowState) -> WorkflowState:
        """Node 2: Plan which subgraphs to execute based on intent and confidence."""
        logger.info(f"Planning execution for intent: {state.intent}")
        
        state.selected_subgraphs = []
        state.execution_plan = {
            "primary_subgraph": None,
            "fallback_subgraph": None,
            "parallel_execution": False,
            "confidence_threshold": 0.70,
            "sequential_execution": False,
            "multi_intent": False
        }
        
        # Check for multi-intent queries
        content_lower = state.message.content.lower()
        is_multi_intent = self._detect_multi_intent(content_lower)
        
        if is_multi_intent:
            state.execution_plan["multi_intent"] = True
            state.execution_plan["sequential_execution"] = True
            # For "send guide + schedule demo", do RAG first then scheduler
            if any(word in content_lower for word in ['guide', 'doc', 'documentation', 'info', 'material']) and \
               any(word in content_lower for word in ['schedule', 'demo', 'book', 'meeting']):
                state.selected_subgraphs = ["rag_agent", "demo_scheduler"]
                state.execution_plan["primary_subgraph"] = "rag_agent"
                state.execution_plan["secondary_subgraph"] = "demo_scheduler"
                logger.info("Multi-intent detected: information + scheduling")
                return state
        
        # Plan based on single intent
        if state.intent == IntentType.SCHEDULING and state.intent_confidence > 0.70:
            state.selected_subgraphs = ["demo_scheduler"]
            state.execution_plan["primary_subgraph"] = "demo_scheduler"
            
        elif state.intent == IntentType.ESCALATION:
            # Handle escalation (including moderation cases)
            state.selected_subgraphs = ["escalation"]
            state.execution_plan["primary_subgraph"] = "escalation"
            
        elif state.intent == IntentType.TECHNICAL_SUPPORT and state.intent_confidence > 0.70:
            state.selected_subgraphs = ["technical_support"]
            state.execution_plan["primary_subgraph"] = "technical_support"
            
        elif state.intent == IntentType.INFORMATION or state.intent_confidence < 0.70:
            # For information queries or low confidence, use RAG
            state.selected_subgraphs = ["rag_agent"]
            state.execution_plan["primary_subgraph"] = "rag_agent"
            
        else:
            # Unknown intent - use RAG as fallback
            state.selected_subgraphs = ["rag_agent"]
            state.execution_plan["primary_subgraph"] = "rag_agent"
            state.execution_plan["fallback_subgraph"] = "rag_agent"
        
        # Add RAG as fallback for all non-information intents
        if state.intent != IntentType.INFORMATION and "rag_agent" not in state.selected_subgraphs:
            state.execution_plan["fallback_subgraph"] = "rag_agent"
        
        logger.info(f"Execution plan: {state.execution_plan}")
        logger.info(f"Selected subgraphs: {state.selected_subgraphs}")
        
        return state
    
    async def _execute_subgraphs(self, state: WorkflowState) -> WorkflowState:
        """Node 3: Execute the selected subgraphs in parallel."""
        logger.info(f"Executing subgraphs: {state.selected_subgraphs}")
        
        # Execute subgraphs in parallel using asyncio.gather
        tasks = []
        subgraph_names = []
        
        for subgraph_name in state.selected_subgraphs:
            if subgraph_name == "demo_scheduler":
                tasks.append(self._execute_demo_scheduler_subgraph(state))
            elif subgraph_name == "escalation":
                tasks.append(self._execute_escalation_subgraph(state))
            elif subgraph_name == "technical_support":
                tasks.append(self._execute_technical_support_subgraph(state))
            elif subgraph_name == "rag_agent":
                tasks.append(self._execute_rag_subgraph(state))
            subgraph_names.append(subgraph_name)
        
        try:
            # Execute all subgraphs in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(results):
                subgraph_name = subgraph_names[i]
                if isinstance(result, Exception):
                    logger.error(f"Subgraph {subgraph_name} failed: {result}")
                    # Create error response
                    error_response = AgentResponse(
                        agent_name=f"{subgraph_name}_error",
                        response_text="I encountered an error processing your request.",
                        confidence_score=0.0,
                        sources=[],
                        should_escalate=True,
                        escalation_reason=f"Subgraph execution error: {str(result)}",
                        metadata={"error": True}
                    )
                    state.subgraph_results[subgraph_name] = error_response
                else:
                    state.subgraph_results[subgraph_name] = result
            
            logger.info(f"Subgraph execution completed. Results: {len(state.subgraph_results)}")
            
        except Exception as e:
            logger.error(f"Critical error in subgraph execution: {e}")
            state.error_details = str(e)
        
        return state
    
    async def _execute_demo_scheduler_subgraph(self, state: WorkflowState) -> AgentResponse:
        """Execute the demo scheduler subgraph."""
        from src.agents.demo_scheduler import DemoSchedulerAgent
        
        agent = DemoSchedulerAgent()
        return await agent.process_message(state.message)
    
    async def _execute_escalation_subgraph(self, state: WorkflowState) -> AgentResponse:
        """Execute the escalation subgraph for moderation and human handoff."""
        from src.agents.escalation_agent import EscalationAgent
        
        # Check for suggested response from moderation
        moderation_data = state.intent_metadata.get('moderation', {})
        suggested_response = moderation_data.get('suggested_response')
        
        if suggested_response:
            # Use moderation's suggested response
            from src.models.schemas import AgentResponse
            return AgentResponse(
                agent_name="moderation_escalation",
                response_text=suggested_response,
                confidence_score=1.0,
                sources=["Moderation System"],
                should_escalate=True,
                escalation_reason="Content moderation - user requires human assistance",
                requires_human_input=True,
                metadata={"escalation_type": "moderation", "moderation_data": moderation_data}
            )
        else:
            # Regular escalation
            agent = EscalationAgent()
            return await agent.process_message(state.message)
    
    async def _execute_technical_support_subgraph(self, state: WorkflowState) -> AgentResponse:
        """Execute the technical support subgraph."""
        from src.agents.technical_support import TechnicalSupportAgent
        
        agent = TechnicalSupportAgent()
        return await agent.process_message(state.message)
    
    async def _execute_rag_subgraph(self, state: WorkflowState) -> AgentResponse:
        """Execute the RAG subgraph."""
        from src.agents.enhanced_rag_agent import EnhancedRAGAgent
        
        agent = EnhancedRAGAgent()
        await agent.initialize()  # Ensure RAG is initialized
        return await agent.process_message(state.message)
    
    def _should_require_approval(self, state: WorkflowState) -> Literal["approve", "skip"]:
        """Conditional edge: Determine if human approval is needed."""
        
        # Check if any subgraph result requires approval
        for subgraph_name, result in state.subgraph_results.items():
            # Require approval for scheduling actions
            if subgraph_name == "demo_scheduler" and not result.should_escalate:
                if "booking" in result.metadata.get("action_type", ""):
                    return "approve"
            
            # Require approval for high-stakes technical responses
            if result.should_escalate and "critical" in result.escalation_reason.lower():
                return "approve"
        
        return "skip"
    
    async def _human_approval_gate(self, state: WorkflowState) -> WorkflowState:
        """Node 4: Human approval gate with responder agent integration."""
        logger.info("Human approval gate - checking for escalation needs")
        
        # Check if we need to escalate based on subgraph results
        should_escalate = False
        escalation_reason = None
        best_response = None
        
        if state.subgraph_results:
            # Find any result that requires escalation
            for subgraph_name, result in state.subgraph_results.items():
                if result.should_escalate:
                    should_escalate = True
                    escalation_reason = result.escalation_reason
                    best_response = result
                    break
            
            # If no explicit escalation, check for low confidence responses
            if not should_escalate:
                best_response = self._select_best_response(state)
                if best_response and best_response.confidence_score < 0.5:
                    should_escalate = True
                    escalation_reason = f"Low confidence response ({best_response.confidence_score:.2f}) from {best_response.agent_name}"
        else:
            # No subgraph results - definitely need escalation
            should_escalate = True
            escalation_reason = "No valid responses from any agent"
        
        # If escalation needed and responder agent available, escalate
        if should_escalate and self.responder_agent:
            try:
                logger.info(f"Escalating to responder agent: {escalation_reason}")
                
                # Prepare conversation history from workflow state
                conversation_history = []
                if hasattr(state, 'conversation_history'):
                    conversation_history = state.conversation_history
                else:
                    # Build history from current message and any context
                    conversation_history = [
                        {
                            'sender': 'User',
                            'content': state.message.content,
                            'timestamp': state.message.timestamp.isoformat(),
                            'message_type': 'user_message'
                        }
                    ]
                    
                    # Add subgraph results as context
                    for subgraph_name, result in state.subgraph_results.items():
                        if result.response_text:
                            conversation_history.append({
                                'sender': f'AI Agent ({result.agent_name})',
                                'content': result.response_text,
                                'confidence': result.confidence_score,
                                'message_type': 'ai_response'
                            })
                
                # Escalate through responder agent
                escalation_response = await self.responder_agent.process_escalation_request(
                    support_message=state.message,
                    escalation_reason=escalation_reason,
                    conversation_history=conversation_history
                )
                
                # Update state with escalation response
                state.final_response = escalation_response
                state.requires_human_approval = True
                
                logger.info(f"Escalation processed with session ID: {escalation_response.metadata.get('session_id')}")
                
            except Exception as e:
                logger.error(f"Error during escalation: {e}")
                # Fallback to standard escalation response
                state.final_response = AgentResponse(
                    agent_name="langgraph_workflow",
                    response_text="I'm connecting you with our support team. You'll hear back from a human agent shortly.",
                    confidence_score=1.0,
                    should_escalate=True,
                    escalation_reason=f"Escalation system error: {str(e)}",
                    requires_human_input=True
                )
                state.requires_human_approval = True
        
        elif should_escalate and not self.responder_agent:
            # No responder agent available - use fallback escalation
            logger.warning("Escalation needed but no responder agent available")
            state.final_response = AgentResponse(
                agent_name="langgraph_workflow",
                response_text="I'm unable to fully assist with your request. Please contact our support team for help.",
                confidence_score=0.5,
                should_escalate=True,
                escalation_reason="No responder agent available",
                requires_human_input=True
            )
            state.requires_human_approval = True
        
        else:
            # No escalation needed - continue with best response
            state.requires_human_approval = False
            if not state.final_response and best_response:
                state.final_response = best_response
        
        return state
    
    async def _finalize_response(self, state: WorkflowState) -> WorkflowState:
        """Node 5: Aggregate results and create final response."""
        logger.info("Finalizing response")
        
        try:
            # Handle multi-intent sequential responses
            if state.execution_plan.get("multi_intent") and state.execution_plan.get("sequential_execution"):
                combined_response = self._combine_sequential_responses(state)
                if combined_response:
                    state.final_response = combined_response
                else:
                    # Fallback to best single response
                    state.final_response = self._select_best_response(state)
            else:
                # Select the best response from subgraph results
                best_response = self._select_best_response(state)
                
                if best_response:
                    state.final_response = best_response
                else:
                    # Create fallback response
                    state.final_response = AgentResponse(
                        agent_name="langgraph_workflow",
                        response_text="I'm unable to process your request at the moment. Let me connect you with our support team.",
                        confidence_score=0.0,
                        sources=[],
                        should_escalate=True,
                        escalation_reason="No valid subgraph results",
                        metadata={"workflow_error": True}
                    )
            
            state.processing_completed = datetime.now()
            
            # Log final metrics
            processing_time = (state.processing_completed - state.processing_started).total_seconds()
            logger.info(
                f"Workflow completed in {processing_time:.2f}s. "
                f"Final agent: {state.final_response.agent_name}, "
                f"Confidence: {state.final_response.confidence_score:.2f}"
            )
            
        except Exception as e:
            logger.error(f"Error in finalize_response: {e}")
            state.error_details = str(e)
        
        return state
    
    def _select_best_response(self, state: WorkflowState) -> Optional[AgentResponse]:
        """Select the best response from subgraph results."""
        if not state.subgraph_results:
            return None
        
        # Get primary subgraph result first
        primary_subgraph = state.execution_plan.get("primary_subgraph")
        if primary_subgraph and primary_subgraph in state.subgraph_results:
            primary_result = state.subgraph_results[primary_subgraph]
            
            # Always use primary result if available (including escalations)
            # The primary subgraph was selected for a reason by the intent classifier
            return primary_result
        
        # Fallback: select highest confidence result
        best_result = None
        best_score = -1.0  # Allow negative scores to ensure we always pick something
        
        for subgraph_name, result in state.subgraph_results.items():
            # Score based on confidence, with slight bonus for non-escalating results
            score = result.confidence_score
            if not result.should_escalate:
                score += 0.1  # Small bonus for direct answers
            
            if score > best_score:
                best_score = score
                best_result = result
        
        return best_result
    
    def _combine_sequential_responses(self, state: WorkflowState) -> Optional[AgentResponse]:
        """Combine responses from sequential multi-intent execution."""
        rag_response = state.subgraph_results.get("rag_agent")
        scheduler_response = state.subgraph_results.get("demo_scheduler")
        
        if not rag_response or not scheduler_response:
            return None
        
        # For "send guide + schedule demo" pattern
        if rag_response and scheduler_response:
            # Check if RAG has good information to share
            if rag_response.confidence_score >= 0.5 and not rag_response.should_escalate:
                # Combine: RAG info + scheduling
                combined_text = (
                    f"{rag_response.response_text}\n\n"
                    f"---\n\n"
                    f"{scheduler_response.response_text}"
                )
                
                from src.models.schemas import AgentResponse
                return AgentResponse(
                    agent_name="multi_intent_workflow",
                    response_text=combined_text,
                    confidence_score=min(rag_response.confidence_score, scheduler_response.confidence_score),
                    sources=rag_response.sources + scheduler_response.sources,
                    should_escalate=rag_response.should_escalate or scheduler_response.should_escalate,
                    escalation_reason=None,
                    requires_human_input=scheduler_response.requires_human_input,
                    metadata={
                        "multi_intent": True,
                        "combined_agents": ["rag_agent", "demo_scheduler"],
                        "rag_confidence": rag_response.confidence_score,
                        "scheduler_confidence": scheduler_response.confidence_score
                    }
                )
            else:
                # RAG didn't have good info, just do scheduling
                return scheduler_response
        
        return None
    
    async def process_message(self, message: SupportMessage) -> WorkflowState:
        """Main entry point: Process a message through the LangGraph workflow."""
        logger.info(f"Processing message {message.message_id} through LangGraph workflow")
        
        try:
            # Create initial state
            initial_state = WorkflowState(message=message)
            
            # Run the workflow
            config = {"configurable": {"thread_id": f"msg_{message.message_id}"}}
            final_state = await self.compiled_graph.ainvoke(initial_state, config=config)
            
            return final_state
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            
            # Return error state
            error_state = WorkflowState(
                message=message,
                error_details=str(e),
                processing_completed=datetime.now()
            )
            error_state.final_response = AgentResponse(
                agent_name="langgraph_workflow_error",
                response_text="I'm experiencing technical difficulties. Let me connect you with our support team.",
                confidence_score=0.0,
                sources=[],
                should_escalate=True,
                escalation_reason=f"Workflow execution error: {str(e)}",
                metadata={"workflow_error": True}
            )
            
            return error_state
    
    async def health_check(self) -> Dict[str, Any]:
        """Check workflow health."""
        try:
            # Test that the graph is compiled
            if not self.compiled_graph:
                return {"healthy": False, "error": "Graph not compiled"}
            
            # Test subgraph agents
            agent_health = {}
            
            # Test demo scheduler
            try:
                from src.agents.demo_scheduler import DemoSchedulerAgent
                demo_agent = DemoSchedulerAgent()
                agent_health["demo_scheduler"] = await demo_agent.health_check()
            except Exception as e:
                agent_health["demo_scheduler"] = False
                logger.error(f"Demo scheduler health check failed: {e}")
            
            # Test RAG agent
            try:
                from src.agents.enhanced_rag_agent import EnhancedRAGAgent
                rag_agent = EnhancedRAGAgent()
                agent_health["rag_agent"] = await rag_agent.health_check()
            except Exception as e:
                agent_health["rag_agent"] = False
                logger.error(f"RAG agent health check failed: {e}")
            
            # Test technical support
            try:
                from src.agents.technical_support import TechnicalSupportAgent
                tech_agent = TechnicalSupportAgent()
                agent_health["technical_support"] = await tech_agent.health_check()
            except Exception as e:
                agent_health["technical_support"] = False
                logger.error(f"Technical support health check failed: {e}")
            
            overall_healthy = all(agent_health.values())
            
            return {
                "healthy": overall_healthy,
                "workflow_compiled": True,
                "agent_health": agent_health,
                "workflow_name": self.workflow_name
            }
            
        except Exception as e:
            logger.error(f"Workflow health check failed: {e}")
            return {"healthy": False, "error": str(e)}


# Global instance
langgraph_workflow = LangGraphWorkflow()