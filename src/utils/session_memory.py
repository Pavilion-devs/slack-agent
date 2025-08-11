"""Simple session memory to avoid repeating facts."""

import time
import logging
from typing import Dict, Set, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SessionFacts:
    """Track facts mentioned in a session."""
    mentioned_facts: Set[str]
    last_updated: float
    
    def add_fact(self, fact: str):
        """Add a fact to the session memory."""
        self.mentioned_facts.add(fact.lower().strip())
        self.last_updated = time.time()
    
    def has_mentioned(self, fact: str) -> bool:
        """Check if a fact was already mentioned."""
        return fact.lower().strip() in self.mentioned_facts


class SessionMemory:
    """Simple in-memory session tracking to avoid repetitive facts."""
    
    def __init__(self, session_timeout: int = 3600):  # 1 hour timeout
        self.sessions: Dict[str, SessionFacts] = {}
        self.session_timeout = session_timeout
        
        # Common facts that get repeated too often
        self.common_facts = {
            "4-7 days timeline": ["4-7 days", "speed record", "as little as 4", "customers have completed"],
            "30 min onboarding": ["30 minutes", "30-minute onboarding", "onboarding process"],
            "10-15 hours setup": ["10-15 hours", "platform setup", "hours of actual work"],
            "100% success rate": ["100% success", "100% of delve customers pass", "100% pass rate"],
            "150+ hours traditional": ["150+ hours", "traditional approaches", "compared to 150"],
            "white glove onboarding": ["white-glove", "white glove", "1:1 expert support"],
            "mit researchers": ["mit ai researchers", "founded by mit", "karun kaushik", "selin kocalar"],
        }
    
    def get_session(self, session_id: str) -> SessionFacts:
        """Get or create session facts."""
        # Clean up expired sessions
        self._cleanup_expired_sessions()
        
        if session_id not in self.sessions:
            self.sessions[session_id] = SessionFacts(
                mentioned_facts=set(),
                last_updated=time.time()
            )
        
        return self.sessions[session_id]
    
    def should_suppress_fact(self, session_id: str, response_text: str) -> bool:
        """Check if common facts should be suppressed to avoid repetition."""
        session = self.get_session(session_id)
        response_lower = response_text.lower()
        
        for fact_key, fact_patterns in self.common_facts.items():
            # Check if this fact is in the response
            fact_in_response = any(pattern in response_lower for pattern in fact_patterns)
            
            if fact_in_response and session.has_mentioned(fact_key):
                logger.info(f"Suppressing repeated fact: {fact_key}")
                return True
        
        return False
    
    def record_response_facts(self, session_id: str, response_text: str):
        """Record facts mentioned in a response."""
        session = self.get_session(session_id)
        response_lower = response_text.lower()
        
        for fact_key, fact_patterns in self.common_facts.items():
            # Check if this fact is in the response
            fact_in_response = any(pattern in response_lower for pattern in fact_patterns)
            
            if fact_in_response:
                session.add_fact(fact_key)
                logger.debug(f"Recorded fact in session {session_id}: {fact_key}")
    
    def suppress_repetitive_facts(self, session_id: str, response_text: str) -> str:
        """Remove repetitive facts from response text."""
        if self.should_suppress_fact(session_id, response_text):
            # Simple approach: remove sentences with repeated facts
            sentences = response_text.split('. ')
            filtered_sentences = []
            
            for sentence in sentences:
                sentence_lower = sentence.lower()
                should_keep = True
                
                for fact_key, fact_patterns in self.common_facts.items():
                    if self.get_session(session_id).has_mentioned(fact_key):
                        # If this fact was mentioned before and appears in this sentence
                        if any(pattern in sentence_lower for pattern in fact_patterns):
                            should_keep = False
                            logger.debug(f"Removing repetitive sentence: {sentence[:50]}...")
                            break
                
                if should_keep:
                    filtered_sentences.append(sentence)
            
            filtered_response = '. '.join(filtered_sentences)
            
            # Clean up any double periods or trailing issues
            filtered_response = filtered_response.replace('..', '.').strip()
            if filtered_response and not filtered_response.endswith('.'):
                filtered_response += '.'
            
            # Record the facts from the original response (before filtering)
            self.record_response_facts(session_id, response_text)
            
            return filtered_response
        else:
            # Record facts for future suppression
            self.record_response_facts(session_id, response_text)
            return response_text
    
    def _cleanup_expired_sessions(self):
        """Remove expired sessions."""
        current_time = time.time()
        expired_sessions = [
            session_id for session_id, session_facts in self.sessions.items()
            if current_time - session_facts.last_updated > self.session_timeout
        ]
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
            logger.debug(f"Cleaned up expired session: {session_id}")


# Global instance
session_memory = SessionMemory()