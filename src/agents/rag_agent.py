"""
Improved RAG Agent using the new FAISS-based RAG system.
Replaces the complex multi-agent architecture with a single intelligent agent.
"""

import re
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.models.schemas import SupportMessage, AgentResponse
from src.core.rag_system import rag_system


logger = logging.getLogger(__name__)


class RAGAgent:
    """
    Intelligent RAG agent that handles knowledge retrieval and response generation.
    Uses the advanced FAISS-based RAG system with confidence scoring.
    """
    
    def __init__(self):
        self.agent_name = "rag_agent"
        self.framework_patterns = {
            'SOC2': r'\b(?:soc\s*2|soc2|service organization control)\b',
            'HIPAA': r'\b(?:hipaa|protected health information|phi)\b',
            'GDPR': r'\b(?:gdpr|general data protection|data subject rights)\b',
            'ISO27001': r'\b(?:iso\s*27001|iso27001|information security management)\b',
            'PCI_DSS': r'\b(?:pci\s*dss|payment card industry)\b'
        }
        
        # Intent classification patterns
        self.intent_patterns = {
            'pricing': r'\b(?:cost|price|pricing|subscription|billing|fee)\b',
            'timeline': r'\b(?:how long|timeline|duration|when|time)\b',
            'implementation': r'\b(?:setup|implement|install|configure|onboard)\b',
            'technical': r'\b(?:integration|api|technical|architecture|system)\b',
            'comparison': r'\b(?:vs|versus|compare|difference|better)\b',
            'support': r'\b(?:help|support|assistance|contact)\b'
        }
    
    async def process_message(self, message: SupportMessage) -> AgentResponse:
        """
        Process support message using the RAG system.
        
        Args:
            message: The support message to process
            
        Returns:
            AgentResponse with generated response and metadata
        """
        try:
            start_time = datetime.now()
            logger.info(f"RAG agent processing message: {message.message_id}")
            
            # Extract frameworks and intent from message
            frameworks = self._extract_frameworks(message.content)
            intent = self._classify_intent(message.content)
            
            logger.info(f"Detected frameworks: {frameworks}, intent: {intent}")
            
            # Query the RAG system
            rag_result = await rag_system.query(
                question=message.content,
                frameworks=frameworks if frameworks else None
            )
            
            # Format response with sources
            formatted_response = self._format_response(
                rag_result['answer'], 
                rag_result['sources'],
                frameworks,
                intent
            )
            
            # Determine escalation
            should_escalate = rag_result['should_escalate']
            escalation_reason = rag_result.get('escalation_reason', '')
            
            # Adjust escalation based on additional factors
            if not should_escalate:
                should_escalate, additional_reason = self._check_additional_escalation_factors(
                    message.content, rag_result['confidence'], intent
                )
                if should_escalate:
                    escalation_reason = additional_reason
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            response = AgentResponse(
                agent_name=self.agent_name,
                response_text=formatted_response,
                confidence_score=rag_result['confidence'],
                processing_time=processing_time,
                should_escalate=should_escalate,
                escalation_reason=escalation_reason,
                sources=rag_result['sources'],
                metadata={
                    'frameworks_detected': frameworks,
                    'intent_classified': intent,
                    'retrieved_docs_count': rag_result['retrieved_docs_count'],
                    'rag_system_used': True
                }
            )
            
            logger.info(
                f"RAG agent completed processing in {processing_time:.2f}s. "
                f"Confidence: {rag_result['confidence']:.2f}, "
                f"Escalate: {should_escalate}"
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error in RAG agent processing: {e}")
            
            # Return error response with escalation
            return AgentResponse(
                agent_name=self.agent_name,
                response_text="I'm experiencing technical difficulties. Let me get a human agent to help you right away.",
                confidence_score=0.0,
                processing_time=0.0,
                should_escalate=True,
                escalation_reason=f"RAG agent processing error: {str(e)}",
                sources=[],
                metadata={'error': str(e)}
            )
    
    def _extract_frameworks(self, content: str) -> List[str]:
        """Extract compliance frameworks mentioned in the message."""
        frameworks = []
        content_lower = content.lower()
        
        for framework, pattern in self.framework_patterns.items():
            if re.search(pattern, content_lower, re.IGNORECASE):
                frameworks.append(framework)
        
        return frameworks
    
    def _classify_intent(self, content: str) -> Optional[str]:
        """Classify the intent of the message."""
        content_lower = content.lower()
        
        for intent, pattern in self.intent_patterns.items():
            if re.search(pattern, content_lower, re.IGNORECASE):
                return intent
        
        return None
    
    def _format_response(self, 
                        answer: str, 
                        sources: List[Dict[str, Any]], 
                        frameworks: List[str],
                        intent: Optional[str]) -> str:
        """Format the response with appropriate context and sources."""
        
        # Clean up the answer (remove confidence score if present)
        if "CONFIDENCE:" in answer:
            answer = answer.split("CONFIDENCE:")[0].strip()
        
        formatted_response = answer
        
        # Add framework-specific context if relevant
        if frameworks and intent in ['implementation', 'timeline']:
            framework_context = self._get_framework_context(frameworks)
            if framework_context:
                formatted_response += f"\n\n{framework_context}"
        
        # Add source information if available
        if sources and len(sources) > 0:
            formatted_response += "\n\n📚 **Relevant Information Sources:**"
            
            # Group sources by section
            sections = {}
            for source in sources[:3]:  # Limit to top 3 sources
                section = source['section']
                if section not in sections:
                    sections[section] = []
                sections[section].append(source)
            
            for section, section_sources in sections.items():
                formatted_response += f"\n• {section}"
                if len(section_sources) > 1:
                    formatted_response += f" ({len(section_sources)} related topics)"
        
        # Add call-to-action for specific intents
        if intent == 'pricing' and 'pricing' not in answer.lower():
            formatted_response += "\n\n💡 For specific pricing details, I can connect you with our sales team who can provide a customized quote based on your needs."
        
        elif intent == 'technical' and frameworks:
            formatted_response += f"\n\n🔧 For technical implementation support with {', '.join(frameworks)}, our team can provide same-day technical assistance."
        
        return formatted_response
    
    def _get_framework_context(self, frameworks: List[str]) -> str:
        """Get contextual information for specific frameworks."""
        context_lines = []
        
        for framework in frameworks:
            if framework == 'SOC2':
                context_lines.append("⚡ **SOC 2 Quick Facts**: 30-minute onboarding + 10-15 hours setup + 1-3 weeks audit = typically 4-7 days total")
            elif framework == 'HIPAA':
                context_lines.append("🏥 **HIPAA Implementation**: Can be completed in as little as 1 day with 10-15 hours of work")
            elif framework == 'GDPR':
                context_lines.append("🔒 **GDPR Compliance**: 10-15 hours implementation, faster if you already have some compliance measures")
            elif framework == 'ISO27001':
                context_lines.append("📋 **ISO 27001**: 10-15 hours (2x faster when combined with SOC 2 due to 80% control overlap)")
        
        return "\n".join(context_lines) if context_lines else ""
    
    def _check_additional_escalation_factors(self, 
                                           content: str, 
                                           confidence: float,
                                           intent: Optional[str]) -> tuple[bool, str]:
        """Check for additional factors that might require escalation."""
        
        # Sales-related queries (high value, needs human touch)
        sales_keywords = ['demo', 'sales', 'purchase', 'contract', 'enterprise', 'pricing quote']
        if any(keyword in content.lower() for keyword in sales_keywords):
            return True, "Sales inquiry requiring human attention"
        
        # Complex technical integrations
        complex_technical = ['custom integration', 'on-premise', 'api design', 'architecture review']
        if any(keyword in content.lower() for keyword in complex_technical):
            return True, "Complex technical requirements"
        
        # Compliance audit emergencies
        urgent_compliance = ['audit tomorrow', 'audit next week', 'auditor', 'compliance emergency']
        if any(keyword in content.lower() for keyword in urgent_compliance):
            return True, "Urgent compliance audit support needed"
        
        # Low confidence on critical topics
        if confidence < 0.7 and intent in ['implementation', 'technical']:
            return True, f"Low confidence ({confidence:.2f}) on critical topic"
        
        return False, ""
    
    async def health_check(self) -> bool:
        """Check if the RAG agent is healthy."""
        try:
            # Check RAG system health
            rag_healthy = await rag_system.health_check()
            
            if not rag_healthy:
                logger.warning("RAG system health check failed")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"RAG agent health check failed: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the RAG agent."""
        return {
            'agent_name': self.agent_name,
            'rag_system_stats': rag_system.get_stats(),
            'frameworks_supported': list(self.framework_patterns.keys()),
            'intents_supported': list(self.intent_patterns.keys())
        }


# Global instance
rag_agent = RAGAgent()