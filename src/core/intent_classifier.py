"""
AI-powered intent classifier that replaces the problematic agent routing logic.
Uses sophisticated pattern matching and optional LLM enhancement for accurate intent detection.
"""

import logging
import re
from typing import Dict, Any, Optional
import asyncio

from src.core.config import settings

logger = logging.getLogger(__name__)


class IntentClassifier:
    """
    Sophisticated intent classifier that solves the routing priority issues.
    
    Key improvements over the old system:
    1. Clear separation between scheduling requests and information queries
    2. Confidence scoring to prevent false positives
    3. Context-aware analysis
    4. Optional LLM enhancement for edge cases
    """
    
    def __init__(self):
        self.llm_available = bool(settings.openai_api_key)
        
        # Highly specific patterns for each intent
        self.scheduling_patterns = [
            # Explicit booking language
            (r'\b(?:can|could|would|let\'s)\s+(?:we|you|i)\s+(?:schedule|book|arrange|set up)', 0.95),
            (r'\bi\s+(?:want|need|would like)\s+to\s+(?:schedule|book|arrange|set up)', 0.95),
            (r'\bschedule\s+(?:a|an|the)?\s*(?:demo|meeting|call|appointment)', 0.90),
            (r'\bbook\s+(?:a|an|the)?\s*(?:demo|meeting|call|appointment)', 0.90),
            (r'\b(?:set up|setup)\s+(?:a|an|the)?\s*(?:demo|meeting|call)', 0.90),
            
            # Time-based scheduling
            (r'\bwhen\s+(?:can|could|are)\s+(?:we|you)\s+(?:meet|schedule|available)', 0.85),
            (r'\bwhat.*time.*(?:work|available|free).*(?:you|meeting|demo)', 0.85),
            (r'\b(?:available|free)\s+(?:for|to)\s+(?:meet|demo|call)', 0.85),
            
            # Calendar/time references with action
            (r'\b(?:next|this)\s+(?:week|monday|tuesday|wednesday|thursday|friday).*\b(?:demo|meeting|call)', 0.80),
            (r'\b(?:tomorrow|today).*\b(?:demo|meeting|call)', 0.80),
            
            # Slot selection (user responding to scheduling options)
            (r'\boption\s*\d+', 0.95),
            (r'\bslot\s*\d+', 0.95),
            (r'^\d+$', 0.90),  # Just a number
            (r'\bi\'?ll\s+take\s+(?:the\s+)?(?:tuesday|wednesday|thursday|friday)', 0.90),
            (r'\byes.*(?:to\s+)?(?:tuesday|wednesday|thursday|friday)', 0.85),
            (r'\bthat.*(?:works|perfect|good)', 0.80),
            (r'\bconfirm.*(?:booking|meeting)', 0.85),
        ]
        
        self.technical_patterns = [
            # Error and problem language - specific technical terms only
            (r'\b(?:error|bug|issue|problem|not working|broken|failed|failure).*\b(?:api|integration|code|implementation|system|login)', 0.90),
            (r'\b(?:api|integration|technical|code|implementation).*(?:error|issue|problem)', 0.95),
            (r'\b(?:troubleshoot|debug|fix|resolve).*(?:error|bug|api|integration)', 0.85),
            (r'\b(?:500|404|401|403|timeout|connection).*(?:error|issue)', 0.95),
            
            # Technical implementation - specific implementation help
            (r'\bhow\s+(?:do|to)\s+(?:implement|integrate|configure|set up).*\b(?:api|sdk|integration|webhook)', 0.90),
            (r'\b(?:webhook|api key|authentication|oauth).*(?:not working|issue|error)', 0.95),
            (r'\bsso.*(?:not working|issue|error|setup|configuration)', 0.90),
            
            # System status
            (r'\bis.*(?:down|offline|not responding)', 0.90),
            (r'\b(?:login|access).*(?:not working|issue|problem)', 0.85),
        ]
        
        self.information_patterns = [
            # General information seeking
            (r'\bwhat\s+is\s+(?:delve|your platform|this service)', 0.90),
            (r'\bwhat\s+does\s+(?:delve|your platform|this)\s+do', 0.90),
            (r'\bhow\s+does\s+(?:delve|your platform|this|it)\s+work', 0.90),
            (r'\btell\s+me\s+about\s+(?:delve|your platform|compliance)', 0.85),
            (r'\bexplain\s+(?:how|what|the)', 0.80),
            
            # Documentation requests
            (r'\b(?:documentation|docs|guide|tutorial|manual)', 0.85),
            (r'\bwhere\s+(?:can i find|is the)\s+(?:documentation|docs|guide)', 0.90),
            
            # Compliance information - HIGH PRIORITY patterns that should override technical
            (r'\bhow\s+does\s+(?:delve|your platform)\s+help\s+with\s+(?:soc2|iso|gdpr|hipaa|compliance)', 0.95),
            (r'\bhow\s+does\s+(?:soc2|iso|gdpr|hipaa|compliance)\s+work', 0.90),
            (r'\bwhat\s+(?:is|are)\s+(?:soc2|iso|gdpr|hipaa|compliance)', 0.90),
            (r'\b(?:soc2|iso|gdpr|hipaa)\s+(?:process|requirements|certification)', 0.85),
            (r'\btell\s+me\s+about\s+(?:soc2|iso|gdpr|hipaa|compliance)', 0.90),
            (r'\bexplain\s+(?:soc2|iso|gdpr|hipaa|compliance)', 0.90),
            
            # Pricing information - should go to RAG, not technical support
            (r'\bwhat\s+(?:are|is)\s+(?:your|the)\s+(?:pricing|price|cost|rates?)', 0.95),
            (r'\bhow\s+much\s+(?:does|do)\s+(?:it|you|delve|this)\s+cost', 0.95),
            (r'\bpricing\s+(?:plans?|options?|tiers?|models?)', 0.95),
            (r'\b(?:subscription|license|licensing)\s+(?:cost|price|fee)', 0.90),
            (r'\b(?:enterprise|business)\s+pricing', 0.90),
            
            # Feature information
            (r'\bwhat\s+features\s+(?:do you have|does delve offer)', 0.85),
            (r'\bcan\s+(?:delve|your platform|it)\s+(?:help with|handle|support)', 0.80),
        ]
    
    async def classify_intent(self, message_content: str) -> Dict[str, Any]:
        """
        Classify the intent of a message with confidence scoring.
        
        Returns:
            Dict with 'intent', 'confidence', and 'metadata'
        """
        content_lower = message_content.lower().strip()
        
        # Calculate confidence for each intent type
        scheduling_confidence = self._calculate_pattern_confidence(content_lower, self.scheduling_patterns)
        technical_confidence = self._calculate_pattern_confidence(content_lower, self.technical_patterns)
        information_confidence = self._calculate_pattern_confidence(content_lower, self.information_patterns)
        
        logger.info(f"Intent confidence scores - Scheduling: {scheduling_confidence:.2f}, "
                   f"Technical: {technical_confidence:.2f}, Information: {information_confidence:.2f}")
        
        # Apply disambiguation rules to prevent false positives
        scheduling_confidence = self._apply_scheduling_disambiguation(content_lower, scheduling_confidence)
        technical_confidence = self._apply_technical_disambiguation(content_lower, technical_confidence)
        
        # Determine best intent
        max_confidence = max(scheduling_confidence, technical_confidence, information_confidence)
        
        if max_confidence < 0.60:
            # Low confidence - use LLM enhancement if available
            if self.llm_available:
                try:
                    llm_result = await self._enhance_with_llm(message_content)
                    if llm_result and llm_result.get('confidence', 0) > max_confidence:
                        return llm_result
                except Exception as e:
                    logger.warning(f"LLM enhancement failed: {e}")
            
            # Default to information seeking
            intent = "information"
            confidence = max(information_confidence, 0.60)
        
        elif scheduling_confidence == max_confidence:
            intent = "scheduling"
            confidence = scheduling_confidence
        elif technical_confidence == max_confidence:
            intent = "technical_support"
            confidence = technical_confidence
        else:
            intent = "information"
            confidence = information_confidence
        
        # Extract metadata
        metadata = self._extract_metadata(content_lower, intent)
        
        result = {
            "intent": intent,
            "confidence": confidence,
            "metadata": metadata,
            "pattern_scores": {
                "scheduling": scheduling_confidence,
                "technical": technical_confidence,
                "information": information_confidence
            }
        }
        
        logger.info(f"Final intent classification: {intent} (confidence: {confidence:.2f})")
        return result
    
    def _calculate_pattern_confidence(self, content: str, patterns: list) -> float:
        """Calculate confidence score based on pattern matching."""
        max_confidence = 0.0
        
        for pattern, base_confidence in patterns:
            if re.search(pattern, content):
                # Boost confidence if multiple patterns match
                current_confidence = base_confidence
                max_confidence = max(max_confidence, current_confidence)
        
        return max_confidence
    
    def _apply_scheduling_disambiguation(self, content: str, scheduling_confidence: float) -> float:
        """
        Apply disambiguation rules to prevent scheduling false positives.
        
        Key insight: Questions ABOUT demos/meetings should not trigger scheduling.
        """
        
        # Reduce confidence for information-seeking patterns about demos
        info_about_demo_patterns = [
            r'\bwhat\s+(?:is|are)\s+(?:a\s+)?(?:demo|demonstration)',  # "What is a demo?"
            r'\bhow\s+(?:long|much time)\s+(?:is|does)\s+(?:a\s+)?(?:demo|meeting)',  # "How long is a demo?"
            r'\bwhat\s+(?:happens|occurs)\s+(?:in|during)\s+(?:a\s+)?(?:demo|meeting)',  # "What happens in a demo?"
            r'\bhow\s+does\s+(?:the\s+)?(?:demo|meeting)\s+work',  # "How does the demo work?"
            r'\bwhat\s+(?:will|would)\s+(?:we|you)\s+(?:cover|discuss)\s+(?:in|during)',  # "What will we cover?"
            r'\btell\s+me\s+about\s+(?:your\s+)?(?:demo|meeting|presentation)',  # "Tell me about your demo"
        ]
        
        for pattern in info_about_demo_patterns:
            if re.search(pattern, content):
                # This is asking ABOUT demos, not trying to schedule one
                logger.info(f"Disambiguation: Reducing scheduling confidence due to info-seeking pattern: {pattern}")
                scheduling_confidence = max(0.0, scheduling_confidence - 0.30)
        
        # Reduce confidence for compliance information queries
        compliance_info_patterns = [
            r'\bhow\s+does\s+(?:soc2|iso|gdpr|hipaa|compliance)\s+work',
            r'\bwhat\s+(?:is|are)\s+(?:soc2|iso|gdpr|hipaa|compliance)',
            r'\bexplain\s+(?:soc2|iso|gdpr|hipaa|compliance)',
        ]
        
        for pattern in compliance_info_patterns:
            if re.search(pattern, content):
                logger.info(f"Disambiguation: Reducing scheduling confidence for compliance info query")
                scheduling_confidence = max(0.0, scheduling_confidence - 0.25)
        
        return scheduling_confidence
    
    def _apply_technical_disambiguation(self, content: str, technical_confidence: float) -> float:
        """
        Apply disambiguation rules to prevent technical support false positives.
        
        Key insight: Information-seeking questions about compliance/features should 
        not trigger technical support, even if they contain words like "help".
        """
        
        # Reduce confidence for compliance/pricing information queries
        info_seeking_patterns = [
            r'\bhow\s+does\s+(?:delve|your platform)\s+help\s+with\s+(?:soc2|iso|gdpr|hipaa|compliance)',
            r'\bwhat\s+(?:are|is)\s+(?:your|the)\s+(?:pricing|price|cost)',
            r'\btell\s+me\s+about\s+(?:soc2|iso|gdpr|hipaa|compliance|pricing)',
            r'\bexplain\s+(?:soc2|iso|gdpr|hipaa|compliance|pricing)',
            r'\bhow\s+much\s+(?:does|do)\s+(?:it|you|delve|this)\s+cost',
            r'\bwhat\s+features\s+(?:do you have|does delve offer)',
            r'\bcan\s+(?:delve|your platform)\s+(?:help with|handle|support)\s+(?:soc2|iso|gdpr|hipaa|compliance)',
        ]
        
        for pattern in info_seeking_patterns:
            if re.search(pattern, content):
                logger.info(f"Technical disambiguation: Reducing confidence for info-seeking pattern: {pattern}")
                technical_confidence = max(0.0, technical_confidence - 0.40)
        
        return technical_confidence
    
    def _extract_metadata(self, content: str, intent: str) -> Dict[str, Any]:
        """Extract metadata relevant to the classified intent."""
        metadata = {"classified_by": "pattern_matching"}
        
        if intent == "scheduling":
            # Extract urgency indicators
            if any(word in content for word in ['urgent', 'asap', 'immediately', 'today', 'now']):
                metadata['urgency'] = 'high'
            elif any(word in content for word in ['soon', 'quickly', 'this week']):
                metadata['urgency'] = 'medium'
            else:
                metadata['urgency'] = 'normal'
            
            # Extract time preferences
            if any(word in content for word in ['morning', 'am']):
                metadata['time_preference'] = 'morning'
            elif any(word in content for word in ['afternoon', 'pm']):
                metadata['time_preference'] = 'afternoon'
            elif any(word in content for word in ['evening', 'night']):
                metadata['time_preference'] = 'evening'
            
            # Detect if this is a slot selection response
            if re.search(r'\b(?:option|slot|choice|number)\s*\d+', content) or re.search(r'^\d+$', content):
                metadata['is_slot_selection'] = True
        
        elif intent == "technical_support":
            # Extract error types
            if any(word in content for word in ['api', 'integration', 'webhook']):
                metadata['support_type'] = 'api'
            elif any(word in content for word in ['login', 'access', 'authentication']):
                metadata['support_type'] = 'authentication'
            elif any(word in content for word in ['error', 'bug', 'issue']):
                metadata['support_type'] = 'error'
            else:
                metadata['support_type'] = 'general'
        
        elif intent == "information":
            # Extract information categories
            if any(word in content for word in ['soc2', 'iso', 'gdpr', 'hipaa', 'compliance']):
                metadata['info_category'] = 'compliance'
            elif any(word in content for word in ['feature', 'capability', 'functionality']):
                metadata['info_category'] = 'features'
            elif any(word in content for word in ['pricing', 'cost', 'price']):
                metadata['info_category'] = 'pricing'
            else:
                metadata['info_category'] = 'general'
        
        return metadata
    
    async def _enhance_with_llm(self, message_content: str) -> Optional[Dict[str, Any]]:
        """
        Use LLM to enhance intent classification for edge cases.
        Only called when pattern matching has low confidence.
        """
        try:
            import openai
            
            client = openai.OpenAI(api_key=settings.openai_api_key)
            
            prompt = f"""
            Classify the intent of this support message. Focus on what the user actually wants to DO, not just topics mentioned.

            Message: "{message_content}"

            Categories:
            - scheduling: User wants to book/schedule a demo, meeting, or call
            - technical_support: User has a technical problem, error, or needs implementation help  
            - information: User wants to learn about features, compliance, or how things work
            - escalation: User is frustrated or needs immediate human help

            Important distinctions:
            - "What is a demo?" = information (asking ABOUT demos)
            - "Schedule a demo" = scheduling (wants to BOOK a demo)
            - "How does SOC2 work?" = information (learning about compliance)
            - "SOC2 isn't working" = technical_support (has a problem)

            Respond with only:
            Intent: [intent]
            Confidence: [0.0-1.0]
            Reasoning: [brief explanation]
            """
            
            response = await asyncio.to_thread(
                client.chat.completions.create,
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert at classifying customer support intents."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.1
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Parse the result
            intent_match = re.search(r'Intent:\s*(\w+)', result_text)
            confidence_match = re.search(r'Confidence:\s*(0?\.\d+|1\.0)', result_text)
            reasoning_match = re.search(r'Reasoning:\s*(.+)', result_text)
            
            if intent_match and confidence_match:
                intent = intent_match.group(1).lower()
                confidence = float(confidence_match.group(1))
                reasoning = reasoning_match.group(1) if reasoning_match else "LLM classification"
                
                # Map to our intent types
                intent_mapping = {
                    'scheduling': 'scheduling',
                    'technical_support': 'technical_support',
                    'information': 'information',
                    'escalation': 'escalation'
                }
                
                mapped_intent = intent_mapping.get(intent, 'information')
                
                return {
                    "intent": mapped_intent,
                    "confidence": confidence,
                    "metadata": {
                        "classified_by": "llm",
                        "reasoning": reasoning,
                        "raw_response": result_text
                    }
                }
            
        except Exception as e:
            logger.warning(f"LLM intent classification failed: {e}")
            return None
    
    def classify_intent_sync(self, message_content: str) -> Dict[str, Any]:
        """Synchronous version for backward compatibility."""
        return asyncio.run(self.classify_intent(message_content))