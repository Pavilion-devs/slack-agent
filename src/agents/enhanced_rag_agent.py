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
        
        # Fast-path cache for common queries
        self.fast_cache = {
            "what is delve": {
                "answer": "Delve is the leading AI-native compliance automation platform, serving over 500 companies including AI unicorns like Lovable, Bland, and Wispr Flow. Founded in 2023 by 21-year-old MIT AI researchers Karun Kaushik and Selin Kocalar, Delve helps companies achieve SOC 2, HIPAA, GDPR, and ISO 27001 certifications in days rather than months through revolutionary AI agents that eliminate manual busywork.",
                "confidence": 0.95,
                "should_escalate": False,
                "sources": ["📖 Company Overview & Background"]
            },
            "what does delve do": {
                "answer": "Delve provides AI-native compliance automation that helps companies achieve SOC 2, HIPAA, GDPR, and ISO 27001 certifications quickly. Our AI agents can navigate any interface, capture screenshots automatically, and collect evidence from fragmented systems without integration limitations. Customers typically complete SOC 2 implementation in just 10-15 hours of actual work time, compared to 150+ hours with traditional approaches.",
                "confidence": 0.95,
                "should_escalate": False,
                "sources": ["📖 Revolutionary AI-First Approach", "📖 Service Offerings & Compliance Frameworks"]
            },
            "who founded delve": {
                "answer": "Delve was founded in 2023 by 21-year-old MIT AI researchers Karun Kaushik and Selin Kocalar. The company recently raised $32M Series A at a $300M valuation and is part of Y Combinator's Winter 2024 batch.",
                "confidence": 0.95,
                "should_escalate": False,
                "sources": ["📖 Company Overview & Background"]
            },
            "how fast is delve": {
                "answer": "Delve is remarkably fast! Customers typically complete SOC 2 implementation in just 10-15 hours of actual work time (compared to 150+ hours traditionally), with full compliance achieved in 30 minutes onboarding + 10-15 hours platform setup + 1-3 weeks audit completion. Our speed record shows customers completing in as little as 4-7 days.",
                "confidence": 0.95,
                "should_escalate": False,
                "sources": ["📖 SOC 2 Compliance (Flagship Offering)"]
            }
        }
    
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
            
            # Enhance response based on message analysis
            enhanced_response = await self._enhance_response(message, answer, confidence, sources)
            
            # Determine final escalation decision
            urgency = self.detect_urgency(message)
            intent = self.extract_message_intent(message)
            
            # Debug log the analysis
            logger.info(f"Message analysis - Urgency: {urgency}, Intent: {intent}")
            logger.info(f"Confidence threshold: {self.confidence_threshold}, Actual confidence: {confidence}")
            
            # Always escalate critical issues
            if urgency == 'critical':
                should_escalate = True
                escalation_reason = "Critical issue requiring immediate human attention"
                logger.info(f"Escalating due to critical urgency")
            # Always escalate sales inquiries to sales team
            elif intent.get('is_sales_inquiry'):
                should_escalate = True
                escalation_reason = "Sales inquiry requiring human attention"
                logger.info(f"Escalating due to sales inquiry")
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
            
            return self.format_response(
                response_text=enhanced_response,
                confidence_score=confidence,
                sources=sources,
                should_escalate=should_escalate,
                escalation_reason=escalation_reason,
                metadata={
                    "agent_type": "enhanced_rag",
                    "original_confidence": confidence,
                    "rag_escalation": should_escalate_rag,
                    "urgency": urgency,
                    "intent": intent
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
        sources: List[str]
    ) -> str:
        """Enhance the RAG response based on message context."""
        intent = self.extract_message_intent(message)
        
        # If this is actually a sales inquiry, redirect appropriately
        if intent.get('is_sales_inquiry'):
            return (
                "I can see you're interested in our pricing and licensing options! "
                "Let me connect you with our sales team who can provide detailed information about:\n\n"
                "• Custom pricing for your organization size\n"
                "• Enterprise features and licensing\n"
                "• Implementation timeline and support\n"
                "• Volume discounts and contract terms\n\n"
                "They'll reach out within 30 minutes to discuss your specific needs."
            )
        
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
        if confidence < 0.7:
            return (
                "I want to make sure you get the most accurate information for your question. "
                "Let me connect you with our support team who can provide detailed, personalized guidance.\n\n"
                f"In the meantime, here's what I found:\n\n{base_answer}"
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