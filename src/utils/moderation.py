"""Moderation and sentiment analysis utilities."""

import logging
import re
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)


class ModerationFilter:
    """Content moderation and sentiment analysis for user messages."""
    
    def __init__(self):
        # Hostile/abusive patterns
        self.hostile_patterns = [
            r'\b(trash|garbage|shit|suck|awful|terrible|horrible|worst)\b',
            r'\b(stupid|dumb|idiotic|moronic|useless|pathetic)\b',
            r'\b(hate|despise|loathe|disgusting|awful)\b',
            r'\b(fuck|fucking|damn|damn it|wtf|bullshit)\b',
            r'\b(you guys are|this service is)\s+(trash|garbage|shit|awful|terrible|horrible|worst|stupid|useless)\b',
        ]
        
        # Legal/privacy patterns - should suppress sales CTAs
        self.legal_patterns = [
            r'\b(gdpr|ccpa|hipaa|data protection|privacy policy|terms of service)\b',
            r'\b(delete|deletion|remove|removal).*\b(my|our|user)?\s*(data|information|account|profile)\b',
            r'\brequest.*deletion.*data\b',
            r'\b(data subject rights|right to erasure|right to be forgotten|data portability)\b',
            r'\b(legal|compliance|audit|regulatory|regulation)\s+(requirement|obligation|question)\b',
        ]
        
        # Sales connection patterns (should escalate, not demo)
        self.connection_patterns = [
            r'\b(connect me|put me in touch|speak with|talk to|contact)\s+(with\s+)?(sales|team|someone|support|rep|representative)\b',
            r'\bconnect me\s+(for|to get|to)\s+(a\s+)?(quote|pricing|sales)\b',
            r'\b(get a quote|pricing quote|custom quote|personalized pricing)\b',
            r'\b(need to speak|want to talk|would like to discuss)\b',
        ]
    
    def analyze_message(self, message: str) -> Dict[str, Any]:
        """Analyze message for moderation and categorization."""
        content_lower = message.lower().strip()
        
        result = {
            'is_hostile': False,
            'is_legal_privacy': False,
            'is_connection_request': False,  # Wants human contact, not demo
            'sentiment': 'neutral',
            'moderation_action': 'allow',
            'suggested_response': None
        }
        
        # Check for hostile content
        for pattern in self.hostile_patterns:
            if re.search(pattern, content_lower):
                result['is_hostile'] = True
                result['sentiment'] = 'negative'
                result['moderation_action'] = 'escalate_politely'
                result['suggested_response'] = (
                    "I'm sorry you're having a frustrating experience. "
                    "Would you like me to connect you with our support team who can help address your concerns?"
                )
                logger.info(f"Hostile content detected: {pattern}")
                break
        
        # Check for legal/privacy queries
        for pattern in self.legal_patterns:
            if re.search(pattern, content_lower):
                result['is_legal_privacy'] = True
                logger.info(f"Legal/privacy query detected: {pattern}")
                break
        
        # Check for connection requests (human contact, not demo)
        for pattern in self.connection_patterns:
            if re.search(pattern, content_lower):
                result['is_connection_request'] = True
                logger.info(f"Connection request detected: {pattern}")
                break
        
        return result
    
    def should_suppress_sales_cta(self, moderation_result: Dict[str, Any]) -> bool:
        """Determine if sales CTAs should be suppressed for this message."""
        return (
            moderation_result.get('is_hostile', False) or
            moderation_result.get('is_legal_privacy', False)
        )
    
    def should_escalate_not_demo(self, moderation_result: Dict[str, Any]) -> bool:
        """Determine if this should escalate to human instead of demo."""
        return (
            moderation_result.get('is_hostile', False) or
            moderation_result.get('is_connection_request', False)
        )


# Global instance
moderation_filter = ModerationFilter()