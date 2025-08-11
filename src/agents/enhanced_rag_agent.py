"""Enhanced RAG Agent that replaces the single-agent system."""

import logging
from typing import Dict, Any, List, Optional
import asyncio

from src.agents.base_agent import BaseAgent
from src.models.schemas import SupportMessage, AgentResponse
from src.core.rag_system import rag_system
from src.core.config import settings

logger = logging.getLogger(__name__)


class EnhancedRAGAgent(BaseAgent):
    """Enhanced RAG agent that provides intelligent knowledge retrieval."""
    
    def __init__(self):
        super().__init__("enhanced_rag_agent")
        self.min_confidence_for_auto_response = 0.80
        self.rag_initialized = False
        
        # No hardcoded cache - let RAG system with OpenAI handle all questions intelligently
        self.fast_cache = {}
    
    async def initialize(self) -> bool:
        """Initialize the RAG system."""
        if not self.rag_initialized:
            try:
                logger.info("Initializing RAG system...")
                result = await rag_system.initialize()
                self.rag_initialized = result
                return result
            except Exception as e:
                logger.error(f"Failed to initialize RAG system: {e}")
                return False
        return True
    
    def should_handle(self, message: SupportMessage) -> bool:
        """RAG agent can handle knowledge queries but not specialized requests."""
        intent = self.extract_message_intent(message)
        
        # Don't handle specialized requests that have dedicated agents
        if intent.get('is_demo_request'):
            return False
        if intent.get('is_technical_issue'):
            return False
        if intent.get('is_sales_inquiry'):
            return False
            
        # Handle general knowledge and compliance queries
        return True
    
    async def process_message(self, message: SupportMessage) -> AgentResponse:
        """Process message using RAG system."""
        logger.info(f"Enhanced RAG agent processing message: {message.message_id}")
        
        # Check fast-path cache first (normalize for flexible matching)
        query_normalized = message.content.lower().strip().rstrip('?!.')
        if query_normalized in self.fast_cache:
            logger.info(f"Fast-path cache hit for query: {query_normalized}")
            cached = self.fast_cache[query_normalized]
            return self.format_response(
                response_text=cached["answer"],
                confidence_score=cached["confidence"],
                sources=cached["sources"],
                should_escalate=cached["should_escalate"],
                escalation_reason=None,
                metadata={
                    "agent_type": "enhanced_rag",
                    "cache_hit": True,
                    "response_time": "fast_path"
                }
            )
        
        # Ensure RAG system is initialized
        if not await self.initialize():
            return self.format_response(
                response_text="I'm experiencing technical difficulties with my knowledge base. Let me escalate this to our support team.",
                confidence_score=0.0,
                should_escalate=True,
                escalation_reason="RAG system initialization failed"
            )
        
        try:
            # Log the query for debugging
            logger.info(f"RAG system processing query: '{message.content}'")
            
            # Query the RAG system
            rag_result = await rag_system.query(message.content)
            
            # Log the RAG result for debugging
            logger.info(f"RAG result - Answer length: {len(rag_result.get('answer', ''))}, "
                       f"Confidence: {rag_result.get('confidence', 0.0)}, "
                       f"Sources count: {len(rag_result.get('sources', []))}, "
                       f"Should escalate: {rag_result.get('should_escalate', False)}")
            
            # Extract results
            answer = rag_result.get('answer', '')
            confidence = rag_result.get('confidence', 0.0)
            sources = rag_result.get('sources', [])
            should_escalate_rag = rag_result.get('should_escalate', False)
            
            # Debug log the extracted values
            logger.debug(f"Extracted - Answer: '{answer[:100]}...', Confidence: {confidence}, "
                        f"RAG escalation: {should_escalate_rag}")
            
            # Check for moderation context
            from src.utils.moderation import moderation_filter
            moderation_result = moderation_filter.analyze_message(message.content)
            
            # Enhance response based on message analysis and moderation
            enhanced_response = await self._enhance_response(message, answer, confidence, sources, moderation_result)
            
            # Determine final escalation decision
            urgency = self.detect_urgency(message)
            intent = self.extract_message_intent(message)
            
            # Debug log the analysis
            logger.info(f"Message analysis - Urgency: {urgency}, Intent: {intent}")
            logger.info(f"Confidence threshold: {self.confidence_threshold}, Actual confidence: {confidence}")
            
            # Initialize escalation variables
            should_escalate = should_escalate_rag  # Default to RAG system's recommendation
            escalation_reason = ""  # Initialize empty escalation reason
            
            # Always escalate critical issues
            if urgency == 'critical':
                should_escalate = True
                escalation_reason = "Critical issue requiring immediate human attention"
                logger.info(f"Escalating due to critical urgency")
            # For sales inquiries, check if RAG has good information first
            elif intent.get('is_sales_inquiry'):
                if confidence < 0.70:  # Only escalate sales inquiries if RAG confidence is low
                    should_escalate = True
                    escalation_reason = "Sales inquiry with low RAG confidence - requires human attention"
                    logger.info(f"Escalating sales inquiry due to low RAG confidence ({confidence:.2f})")
                else:
                    # RAG has good information about pricing/sales questions - provide it first
                    should_escalate = False
                    escalation_reason = ""
                    logger.info(f"Sales inquiry but RAG has high confidence ({confidence:.2f}) - providing answer")
            # Escalate demo requests even if RAG has info
            elif intent.get('is_demo_request'):
                should_escalate = True
                escalation_reason = "Demo request requiring sales team engagement"
                logger.info(f"Escalating due to demo request")
            # Use RAG system's escalation decision for other cases
            else:
                should_escalate = should_escalate_rag or confidence < self.confidence_threshold
                escalation_reason = "Low confidence score or complex query requiring human review" if should_escalate else None
                logger.info(f"General case - RAG escalation: {should_escalate_rag}, "
                           f"Confidence escalation: {confidence < self.confidence_threshold}, "
                           f"Final decision: {should_escalate}")
            
            # Apply session memory to avoid repetitive facts
            from src.utils.session_memory import session_memory
            session_id = f"user_{message.user_id}"  # Simple session ID based on user
            final_response = session_memory.suppress_repetitive_facts(session_id, enhanced_response)
            
            return self.format_response(
                response_text=final_response,
                confidence_score=confidence,
                sources=sources,
                should_escalate=should_escalate,
                escalation_reason=escalation_reason,
                metadata={
                    "agent_type": "enhanced_rag",
                    "original_confidence": confidence,
                    "rag_escalation": should_escalate_rag,
                    "urgency": urgency,
                    "intent": intent,
                    "session_id": session_id
                }
            )
            
        except Exception as e:
            logger.error(f"Error in enhanced RAG agent: {e}")
            return self.format_response(
                response_text="I encountered an issue while searching for information. Let me connect you with our support team for assistance.",
                confidence_score=0.2,
                should_escalate=True,
                escalation_reason=f"RAG agent error: {str(e)}"
            )
    
    async def _enhance_response(
        self, 
        message: SupportMessage, 
        base_answer: str, 
        confidence: float,
        sources: List[str],
        moderation_result: dict = None
    ) -> str:
        """Enhance the RAG response based on message context and moderation."""
        intent = self.extract_message_intent(message)
        
        # Check if we should suppress sales CTAs
        suppress_sales = False
        if moderation_result:
            from src.utils.moderation import moderation_filter
            suppress_sales = moderation_filter.should_suppress_sales_cta(moderation_result)
        
        # For pricing/sales inquiries with good confidence, provide RAG answer 
        if intent.get('is_sales_inquiry') and confidence >= 0.70 and not suppress_sales:
            # Just provide the answer - no boilerplate prefix
            pricing_suffix = (
                "\n\nFor detailed pricing specific to your organization size and needs, "
                "I can also connect you with our sales team for a personalized quote."
            )
            return base_answer + pricing_suffix
        
        # If this is a demo request, handle appropriately  
        if intent.get('is_demo_request'):
            return (
                "I'd love to arrange a demo for you! Our demos are customized to show exactly how Delve "
                "can solve your specific compliance challenges.\n\n"
                "Let me connect you with our sales team who will:\n"
                "• Schedule a time that works for you\n"
                "• Customize the demo to your compliance needs\n"
                "• Answer any technical questions\n"
                "• Discuss implementation and pricing\n\n"
                "They'll reach out within 30 minutes to set everything up."
            )
        
        # For technical issues, acknowledge but don't claim to fix
        if intent.get('is_technical_issue'):
            technical_prefix = (
                "I can see you're experiencing a technical issue. While I have some general information, "
                "our technical team can provide specific troubleshooting for your situation.\n\n"
            )
            return technical_prefix + base_answer
        
        # For compliance queries, enhance with framework detection
        if intent.get('is_compliance_query'):
            compliance_frameworks = []
            content_lower = message.content.lower()
            
            if 'soc2' in content_lower or 'soc 2' in content_lower:
                compliance_frameworks.append('SOC2')
            if 'iso27001' in content_lower or 'iso 27001' in content_lower:
                compliance_frameworks.append('ISO27001')
            if 'gdpr' in content_lower:
                compliance_frameworks.append('GDPR')
            if 'hipaa' in content_lower:
                compliance_frameworks.append('HIPAA')
            
            if compliance_frameworks:
                framework_text = ", ".join(compliance_frameworks)
                compliance_prefix = f"Great question about {framework_text} compliance! "
                return compliance_prefix + base_answer
        
        # For general queries, check if we should be more helpful
        if confidence < 0.7 and not suppress_sales:
            return (
                f"{base_answer}"
            )
        
        # For legal/privacy queries, keep it clean without sales pitch
        if suppress_sales and confidence >= 0.4:
            return base_answer
        elif suppress_sales:
            return (
                f"{base_answer}\n\n"
                "If you need additional assistance with this matter, "
                "I can connect you with our support team."
            )
        
        # Return enhanced base answer for high-confidence responses
        return base_answer
    
    async def health_check(self) -> bool:
        """Check if the enhanced RAG agent is healthy."""
        try:
            # Check if RAG system is initialized and working
            if not self.rag_initialized:
                await self.initialize()
            
            if self.rag_initialized:
                # Test with a simple query
                test_result = await rag_system.query("What is Delve?")
                return test_result is not None and 'answer' in test_result
            
            return False
            
        except Exception as e:
            logger.error(f"Enhanced RAG agent health check failed: {e}")
            return False