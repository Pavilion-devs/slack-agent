"""
Smart Time Parser using LLM for natural language understanding.
Falls back to traditional parsers for simple cases.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
import pytz
import dateparser
import re

logger = logging.getLogger(__name__)


class SmartTimeParser:
    """Intelligent time parser using LLM for complex natural language expressions."""
    
    def __init__(self, default_timezone: str = "America/New_York"):
        self.default_tz = pytz.timezone(default_timezone)
        
        # Simple patterns that don't need LLM
        self.simple_patterns = {
            r'\btomorrow\b': self._parse_tomorrow,
            r'\btoday\b': self._parse_today, 
            r'\byesterday\b': self._parse_yesterday,
            r'\bin (\d+) days?\b': self._parse_in_days,
            r'\bin (\d+) weeks?\b': self._parse_in_weeks,
        }
    
    async def parse_time_expression(self, text: str) -> Dict[str, Union[datetime, str, None]]:
        """
        Parse natural language time expression intelligently.
        
        Args:
            text: Natural language text containing time expressions
            
        Returns:
            Dict with parsed time information
        """
        text_lower = text.lower()
        
        result = {
            'preferred_datetime': None,
            'date_range': None,
            'time_preference': None,
            'timezone': None,
            'urgency': 'medium',
            'flexibility': 'flexible',
            'parsing_method': 'unknown'
        }
        
        try:
            # Step 1: Try simple patterns first (fast)
            for pattern, parser_func in self.simple_patterns.items():
                if re.search(pattern, text_lower):
                    result['preferred_datetime'] = parser_func(text_lower)
                    result['parsing_method'] = 'simple_pattern'
                    if result['preferred_datetime']:
                        break
            
            # Step 2: Try dateparser for standard expressions
            if not result['preferred_datetime']:
                parsed_dt = dateparser.parse(text, settings={
                    'PREFER_DATES_FROM': 'future',
                    'RETURN_AS_TIMEZONE_AWARE': True,
                    'TIMEZONE': str(self.default_tz)
                })
                if parsed_dt:
                    result['preferred_datetime'] = parsed_dt
                    result['parsing_method'] = 'dateparser'
            
            # Step 3: Use LLM for complex cases (like "next Tuesday")
            if not result['preferred_datetime'] or self._needs_llm_parsing(text_lower):
                llm_result = await self._parse_with_llm(text)
                if llm_result and llm_result.get('target_date'):
                    result.update(llm_result)
                    result['parsing_method'] = 'llm'
            
            # Extract additional context
            result['timezone'] = self._extract_timezone(text_lower)
            result['urgency'] = self._extract_urgency(text_lower)
            result['flexibility'] = self._extract_flexibility(text_lower)
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing time expression '{text}': {e}")
            return result
    
    def _needs_llm_parsing(self, text: str) -> bool:
        """Check if text needs LLM parsing due to complexity."""
        complex_patterns = [
            r'\b(next|this)\s+\w+day\b',  # "next Tuesday", "this Friday"
            r'\blast\s+\w+day\b',         # "last Monday"
            r'\bend of\s+\w+\b',          # "end of week"
            r'\bbeginning of\s+\w+\b',    # "beginning of month"
            r'\bmiddle of\s+\w+\b',       # "middle of next week"
        ]
        
        return any(re.search(pattern, text) for pattern in complex_patterns)
    
    async def _parse_with_llm(self, text: str) -> Optional[Dict]:
        """Use LLM to parse complex time expressions."""
        try:
            # Import here to avoid circular imports
            from src.integrations.ollama_client import ollama_client
            
            current_time = datetime.now()
            
            prompt = f"""Parse this time expression into a specific date and time.

Current context:
- Today is: {current_time.strftime('%A, %B %d, %Y')}
- Current time: {current_time.strftime('%I:%M %p %Z')}
- Default timezone: America/New_York (EST/EDT)

User input: "{text}"

Rules:
- "next Tuesday" means the Tuesday of NEXT week, not tomorrow
- "this Friday" means this week's Friday
- Always prefer future dates
- Default time is 10:00 AM if no time specified
- Respond ONLY with valid JSON

Return JSON format:
{{
    "target_date": "YYYY-MM-DD",
    "target_time": "HH:MM", 
    "timezone": "America/New_York",
    "confidence": 0.95,
    "reasoning": "next Tuesday means August 12th, not tomorrow"
}}"""

            response = await ollama_client.generate_response(
                prompt=prompt,
                max_tokens=200
            )
            
            # Parse JSON response
            if response and response.strip():
                # Clean up response (remove markdown if present)
                json_text = response.strip()
                if json_text.startswith('```json'):
                    json_text = json_text.split('```json')[1].split('```')[0].strip()
                elif json_text.startswith('```'):
                    json_text = json_text.split('```')[1].split('```')[0].strip()
                
                result = json.loads(json_text)
                
                # Convert to datetime object
                if result.get('target_date') and result.get('target_time'):
                    date_str = f"{result['target_date']} {result['target_time']}"
                    target_dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M')
                    
                    # Apply timezone
                    tz_str = result.get('timezone', 'America/New_York')
                    target_tz = pytz.timezone(tz_str)
                    target_dt = target_tz.localize(target_dt)
                    
                    result['preferred_datetime'] = target_dt
                    return result
                    
        except Exception as e:
            logger.error(f"LLM parsing failed: {e}")
        
        return None
    
    def _parse_tomorrow(self, text: str) -> datetime:
        """Parse 'tomorrow' expressions."""
        tomorrow = datetime.now(self.default_tz) + timedelta(days=1)
        
        # Extract time if present
        time_match = re.search(r'(\d{1,2})\s*(am|pm)', text)
        if time_match:
            hour = int(time_match.group(1))
            am_pm = time_match.group(2)
            if am_pm == 'pm' and hour != 12:
                hour += 12
            elif am_pm == 'am' and hour == 12:
                hour = 0
            tomorrow = tomorrow.replace(hour=hour, minute=0, second=0, microsecond=0)
        else:
            tomorrow = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)
            
        return tomorrow
    
    def _parse_today(self, text: str) -> datetime:
        """Parse 'today' expressions.""" 
        today = datetime.now(self.default_tz)
        
        # Extract time if present
        time_match = re.search(r'(\d{1,2})\s*(am|pm)', text)
        if time_match:
            hour = int(time_match.group(1))
            am_pm = time_match.group(2)
            if am_pm == 'pm' and hour != 12:
                hour += 12
            elif am_pm == 'am' and hour == 12:
                hour = 0
            today = today.replace(hour=hour, minute=0, second=0, microsecond=0)
        else:
            # Default to next business hour if current time has passed
            if today.hour >= 17:  # After 5 PM
                today = today.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
            else:
                today = today.replace(minute=0, second=0, microsecond=0)
        
        return today
    
    def _parse_yesterday(self, text: str) -> datetime:
        """Parse 'yesterday' expressions (usually not useful for scheduling)."""
        return datetime.now(self.default_tz) - timedelta(days=1)
    
    def _parse_in_days(self, text: str) -> datetime:
        """Parse 'in X days' expressions."""
        match = re.search(r'in (\d+) days?', text)
        if match:
            days = int(match.group(1))
            target = datetime.now(self.default_tz) + timedelta(days=days)
            return target.replace(hour=10, minute=0, second=0, microsecond=0)
        return None
    
    def _parse_in_weeks(self, text: str) -> datetime:
        """Parse 'in X weeks' expressions."""
        match = re.search(r'in (\d+) weeks?', text)
        if match:
            weeks = int(match.group(1))
            target = datetime.now(self.default_tz) + timedelta(weeks=weeks)
            return target.replace(hour=10, minute=0, second=0, microsecond=0)
        return None
    
    def _extract_timezone(self, text: str) -> Optional[str]:
        """Extract timezone from text."""
        timezone_map = {
            'est': 'America/New_York', 'eastern': 'America/New_York', 'et': 'America/New_York',
            'pst': 'America/Los_Angeles', 'pacific': 'America/Los_Angeles', 'pt': 'America/Los_Angeles',
            'cst': 'America/Chicago', 'central': 'America/Chicago', 'ct': 'America/Chicago',
            'mst': 'America/Denver', 'mountain': 'America/Denver', 'mt': 'America/Denver',
            'utc': 'UTC', 'gmt': 'GMT'
        }
        
        for tz_abbr, tz_full in timezone_map.items():
            if re.search(r'\b' + re.escape(tz_abbr) + r'\b', text, re.IGNORECASE):
                return tz_full
        return None
    
    def _extract_urgency(self, text: str) -> str:
        """Extract urgency level from text."""
        if any(word in text for word in ['urgent', 'asap', 'immediately', 'emergency', 'critical']):
            return 'high'
        elif any(word in text for word in ['soon', 'quickly', 'today', 'tomorrow']):
            return 'medium'
        elif any(word in text for word in ['later', 'whenever', 'no rush', 'flexible']):
            return 'low'
        return 'medium'
    
    def _extract_flexibility(self, text: str) -> str:
        """Extract flexibility level from text."""
        if any(word in text for word in ['exactly', 'specifically', 'must be', 'only']):
            return 'strict'
        elif any(word in text for word in ['around', 'roughly', 'approximately', 'about']):
            return 'flexible'
        elif any(word in text for word in ['anytime', 'whenever', 'flexible', 'open']):
            return 'very_flexible'
        return 'flexible'


# Global instance
smart_time_parser = SmartTimeParser()