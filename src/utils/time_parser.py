"""
Natural Language Time Parser for scheduling requests.
Converts human expressions like 'next week', '2pm PST', 'Friday morning' into specific datetime objects.
"""

import re
import logging
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional, Tuple, Union
import pytz
from dateutil import parser as dateutil_parser
from dateutil.relativedelta import relativedelta

logger = logging.getLogger(__name__)


class TimeParser:
    """Parses natural language time expressions into structured datetime objects."""
    
    def __init__(self, default_timezone: str = "America/New_York"):
        self.default_tz = pytz.timezone(default_timezone)
        self.business_start = time(9, 0)  # 9 AM
        self.business_end = time(18, 0)   # 6 PM
        
        # Common timezone mappings
        self.timezone_map = {
            'est': 'America/New_York',
            'eastern': 'America/New_York',
            'et': 'America/New_York',
            'pst': 'America/Los_Angeles', 
            'pacific': 'America/Los_Angeles',
            'pt': 'America/Los_Angeles',
            'cst': 'America/Chicago',
            'central': 'America/Chicago',
            'ct': 'America/Chicago',
            'mst': 'America/Denver',
            'mountain': 'America/Denver',
            'mt': 'America/Denver',
            'utc': 'UTC',
            'gmt': 'GMT'
        }
        
        # Timezone info mapping for dateutil parser to eliminate warnings
        self.tzinfos = {
            'EST': pytz.timezone('America/New_York'),
            'PST': pytz.timezone('America/Los_Angeles'),
            'CST': pytz.timezone('America/Chicago'),
            'MST': pytz.timezone('America/Denver'),
            'EDT': pytz.timezone('America/New_York'),  # Daylight time
            'PDT': pytz.timezone('America/Los_Angeles'),
            'CDT': pytz.timezone('America/Chicago'),
            'MDT': pytz.timezone('America/Denver')
        }
        
        # Day of week mappings
        self.day_names = {
            'monday': 0, 'mon': 0,
            'tuesday': 1, 'tue': 1, 'tues': 1,
            'wednesday': 2, 'wed': 2,
            'thursday': 3, 'thu': 3, 'thur': 3, 'thurs': 3,
            'friday': 4, 'fri': 4,
            'saturday': 5, 'sat': 5,
            'sunday': 6, 'sun': 6
        }
        
        # Time of day mappings
        self.time_periods = {
            'morning': (9, 12),
            'afternoon': (13, 17),
            'evening': (17, 20),
            'night': (20, 23)
        }
    
    def parse_time_expression(self, text: str) -> Dict[str, Union[datetime, List[datetime], str, None]]:
        """
        Parse natural language time expression into structured data.
        
        Args:
            text: Natural language text containing time expressions
            
        Returns:
            Dict with parsed time information:
            {
                'preferred_datetime': datetime or None,
                'date_range': (start_date, end_date) or None,
                'time_preference': 'morning'|'afternoon'|'evening' or None,
                'timezone': timezone string or None,
                'urgency': 'high'|'medium'|'low',
                'flexibility': 'strict'|'flexible'|'very_flexible'
            }
        """
        text_lower = text.lower()
        
        result = {
            'preferred_datetime': None,
            'date_range': None,
            'time_preference': None,
            'timezone': None,
            'urgency': 'medium',
            'flexibility': 'flexible'
        }
        
        try:
            # Extract timezone
            result['timezone'] = self._extract_timezone(text_lower)
            
            # Extract urgency
            result['urgency'] = self._extract_urgency(text_lower)
            
            # Extract flexibility
            result['flexibility'] = self._extract_flexibility(text_lower)
            
            # Extract time preference (morning/afternoon/evening)
            result['time_preference'] = self._extract_time_preference(text_lower)
            
            # Try to parse specific datetime
            specific_datetime = self._parse_specific_datetime(text, result['timezone'])
            if specific_datetime:
                result['preferred_datetime'] = specific_datetime
                return result
            
            # Parse relative time expressions
            date_range = self._parse_relative_time(text_lower)
            if date_range:
                result['date_range'] = date_range
            
            logger.info(f"Parsed time expression: '{text}' -> {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error parsing time expression '{text}': {e}")
            # Return default result for current week
            now = datetime.now(self.default_tz)
            end_of_week = now + timedelta(days=(6 - now.weekday()))
            result['date_range'] = (now.date(), end_of_week.date())
            return result
    
    def _extract_timezone(self, text: str) -> Optional[str]:
        """Extract timezone from text."""
        # First check for explicit timezone mentions with word boundaries
        for tz_abbr, tz_full in self.timezone_map.items():
            # Use word boundaries to avoid partial matches
            import re
            pattern = r'\b' + re.escape(tz_abbr) + r'\b'
            if re.search(pattern, text, re.IGNORECASE):
                return tz_full
        
        # Check for location-based timezone hints
        location_timezone_map = {
            'california': 'America/Los_Angeles',
            'west coast': 'America/Los_Angeles',
            'los angeles': 'America/Los_Angeles',
            'san francisco': 'America/Los_Angeles',
            'seattle': 'America/Los_Angeles',
            'portland': 'America/Los_Angeles',
            'vegas': 'America/Los_Angeles',
            
            'london': 'GMT',
            'uk': 'GMT',
            'britain': 'GMT',
            'england': 'GMT',
            'scotland': 'GMT',
            'ireland': 'GMT',
            
            'chicago': 'America/Chicago',
            'texas': 'America/Chicago',
            'dallas': 'America/Chicago',
            'houston': 'America/Chicago',
            'milwaukee': 'America/Chicago',
            'minneapolis': 'America/Chicago',
            
            'denver': 'America/Denver',
            'colorado': 'America/Denver',
            'utah': 'America/Denver',
            'arizona': 'America/Denver',
            'phoenix': 'America/Denver',
            
            'new york': 'America/New_York',
            'nyc': 'America/New_York',
            'boston': 'America/New_York',
            'washington': 'America/New_York',
            'atlanta': 'America/New_York',
            'miami': 'America/New_York',
            'philadelphia': 'America/New_York',
            'toronto': 'America/New_York',
            'montreal': 'America/New_York'
        }
        
        for location, timezone in location_timezone_map.items():
            if location in text.lower():
                return timezone
        
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
    
    def _extract_time_preference(self, text: str) -> Optional[str]:
        """Extract time of day preference."""
        for period in self.time_periods:
            if period in text:
                return period
        return None
    
    def _parse_specific_datetime(self, text: str, timezone_str: Optional[str]) -> Optional[datetime]:
        """Parse specific datetime expressions like 'tomorrow at 2pm', 'Friday at 10am'."""
        
        # Get target timezone
        target_tz = self.default_tz
        if timezone_str:
            try:
                target_tz = pytz.timezone(timezone_str)
            except:
                pass
        
        # First check for patterns that need manual parsing (next/this + day)
        if re.search(r'\b(next|this)\s+\w*day', text.lower()):
            # Skip dateutil for "next/this + day" patterns - handle manually
            pass
        else:
            try:
                # Try dateutil parser for other patterns with timezone info
                parsed_dt = dateutil_parser.parse(text, fuzzy=True, tzinfos=self.tzinfos)
                
                # If no timezone info, assume target timezone
                if parsed_dt.tzinfo is None:
                    parsed_dt = target_tz.localize(parsed_dt)
                
                # Only return if it's in the future
                now = datetime.now(target_tz)
                if parsed_dt > now:
                    return parsed_dt
                    
            except:
                pass
        
        # Try manual parsing for common patterns
        patterns = [
            # "next tuesday at 2pm", "this friday at 10am"  
            (r'(next|this)\s+(\w+day)\s+at\s+(\d{1,2})\s*(am|pm)', self._parse_relative_day_time),
            # "tomorrow at 2pm", "friday at 10am"
            (r'(tomorrow|today|\w+day)\s+at\s+(\d{1,2})\s*(am|pm)', self._parse_day_time),
            # "next friday", "this monday"
            (r'(next|this)\s+(\w+day)', self._parse_relative_day),
            # "2pm tomorrow", "10am friday"
            (r'(\d{1,2})\s*(am|pm)\s+(tomorrow|today|\w+day)', self._parse_time_day),
        ]
        
        for pattern, parser_func in patterns:
            match = re.search(pattern, text.lower())
            if match:
                result = parser_func(match, target_tz)
                if result:
                    return result
        
        return None
    
    def _parse_day_time(self, match, target_tz) -> Optional[datetime]:
        """Parse 'tomorrow at 2pm' style expressions."""
        day_expr, hour_str, am_pm = match.groups()
        
        hour = int(hour_str)
        if am_pm.lower() == 'pm' and hour != 12:
            hour += 12
        elif am_pm.lower() == 'am' and hour == 12:
            hour = 0
        
        base_date = datetime.now(target_tz).replace(hour=hour, minute=0, second=0, microsecond=0)
        
        if day_expr == 'today':
            target_date = base_date
        elif day_expr == 'tomorrow':
            target_date = base_date + timedelta(days=1)
        else:
            # Parse day name
            day_name = day_expr.replace('day', '').strip()
            if day_name in self.day_names:
                target_weekday = self.day_names[day_name]
                days_ahead = (target_weekday - base_date.weekday()) % 7
                if days_ahead == 0:  # Same day, move to next week
                    days_ahead = 7
                target_date = base_date + timedelta(days=days_ahead)
            else:
                return None
        
        # Only return if it's in the future
        if target_date > datetime.now(target_tz):
            return target_date
        
        return None
    
    def _parse_relative_day(self, match, target_tz) -> Optional[datetime]:
        """Parse 'next friday', 'this monday' expressions."""
        relative, day_name = match.groups()
        
        day_name_clean = day_name.replace('day', '').strip()
        if day_name_clean not in self.day_names:
            return None
        
        target_weekday = self.day_names[day_name_clean]
        now = datetime.now(target_tz)
        
        if relative == 'this':
            # This week
            days_ahead = (target_weekday - now.weekday()) % 7
            if days_ahead == 0:  # Today, set to business hours
                target_date = now.replace(hour=10, minute=0, second=0, microsecond=0)
                if target_date <= now:  # Already passed, move to next week
                    target_date += timedelta(days=7)
            else:
                target_date = now + timedelta(days=days_ahead)
                target_date = target_date.replace(hour=10, minute=0, second=0, microsecond=0)
        else:  # next
            # Next week - always go to the following week
            days_ahead = (target_weekday - now.weekday()) % 7
            if days_ahead == 0:  # Same day next week
                days_ahead = 7
            else:
                days_ahead += 7  # Always add 7 days for "next" week
            target_date = now + timedelta(days=days_ahead)
            target_date = target_date.replace(hour=10, minute=0, second=0, microsecond=0)
        
        return target_date
    
    def _parse_relative_day_time(self, match, target_tz) -> Optional[datetime]:
        """Parse 'next tuesday at 2pm', 'this friday at 10am' expressions."""
        relative, day_name, hour_str, am_pm = match.groups()
        
        day_name_clean = day_name.replace('day', '').strip()
        if day_name_clean not in self.day_names:
            return None
        
        target_weekday = self.day_names[day_name_clean]
        now = datetime.now(target_tz)
        
        # Calculate the target date (same logic as _parse_relative_day)
        if relative == 'this':
            days_ahead = (target_weekday - now.weekday()) % 7
            if days_ahead == 0:  # Today
                target_date = now.replace(hour=10, minute=0, second=0, microsecond=0)
                if target_date <= now:  # Already passed, move to next week
                    target_date += timedelta(days=7)
            else:
                target_date = now + timedelta(days=days_ahead)
        else:  # next
            days_ahead = (target_weekday - now.weekday()) % 7
            if days_ahead == 0:  # Same day next week
                days_ahead = 7
            else:
                days_ahead += 7  # Always add 7 days for "next" week
            target_date = now + timedelta(days=days_ahead)
        
        # Apply the specific time
        hour = int(hour_str)
        if am_pm.lower() == 'pm' and hour != 12:
            hour += 12
        elif am_pm.lower() == 'am' and hour == 12:
            hour = 0
            
        target_date = target_date.replace(hour=hour, minute=0, second=0, microsecond=0)
        return target_date
    
    def _parse_time_day(self, match, target_tz) -> Optional[datetime]:
        """Parse '2pm tomorrow' style expressions."""
        hour_str, am_pm, day_expr = match.groups()
        
        hour = int(hour_str)
        if am_pm.lower() == 'pm' and hour != 12:
            hour += 12
        elif am_pm.lower() == 'am' and hour == 12:
            hour = 0
        
        # Use the day_time parser logic
        day_time_match = type('Match', (), {
            'groups': lambda: (day_expr, hour_str, am_pm)
        })()
        
        return self._parse_day_time(day_time_match, target_tz)
    
    def _parse_relative_time(self, text: str) -> Optional[Tuple[datetime, datetime]]:
        """Parse relative time expressions like 'next week', 'this month'."""
        now = datetime.now(self.default_tz)
        
        if 'next week' in text:
            # Next week (Monday to Friday) - always go to the following week
            current_weekday = now.weekday()  # Monday=0, Sunday=6
            days_until_next_monday = 7 - current_weekday  # Always next week's Monday
            if current_weekday == 0:  # If today is Monday
                days_until_next_monday = 7  # Go to next Monday
            next_monday = now + timedelta(days=days_until_next_monday)
            next_friday = next_monday + timedelta(days=4)
            return (next_monday.date(), next_friday.date())
        
        elif 'this week' in text:
            # This week (today to Friday)
            days_until_friday = (4 - now.weekday()) % 7
            if days_until_friday == 0 and now.weekday() == 4:  # Today is Friday
                end_date = now.date()
            else:
                end_date = (now + timedelta(days=days_until_friday)).date()
            return (now.date(), end_date)
        
        elif 'tomorrow' in text:
            tomorrow = now + timedelta(days=1)
            return (tomorrow.date(), tomorrow.date())
        
        elif 'today' in text:
            return (now.date(), now.date())
        
        elif 'next month' in text:
            next_month_start = (now + relativedelta(months=1)).replace(day=1)
            next_month_end = (next_month_start + relativedelta(months=1)) - timedelta(days=1)
            return (next_month_start.date(), next_month_end.date())
        
        # Try to find specific day names for this/next week
        for day_name, day_num in self.day_names.items():
            if day_name in text:
                # Calculate days ahead to the target day
                days_ahead = (day_num - now.weekday()) % 7
                
                if 'next' in text and day_name in text:
                    # "next friday" - always go to next week's occurrence
                    if days_ahead == 0:  # Same day of week
                        days_ahead = 7  # Next week
                    else:
                        days_ahead += 7  # Add a week to get next week's occurrence
                    target_date = (now + timedelta(days=days_ahead)).date()
                else:
                    # Just "friday" - next occurrence this week or next
                    if days_ahead == 0:  # Today is that day
                        target_date = now.date()
                    else:
                        target_date = (now + timedelta(days=days_ahead)).date()
                
                return (target_date, target_date)
        
        return None
    
    def suggest_time_slots(self, parsed_time: Dict, available_slots: List) -> List:
        """
        Filter and rank available slots based on parsed time preferences.
        
        Args:
            parsed_time: Result from parse_time_expression()
            available_slots: List of TimeSlot objects from calendar service
            
        Returns:
            Ranked list of matching slots
        """
        if not available_slots:
            return []
        
        matching_slots = []
        
        for slot in available_slots:
            slot_datetime = slot.start_time
            score = 0
            
            # Check date range match
            if parsed_time.get('date_range'):
                start_date, end_date = parsed_time['date_range']
                slot_date = slot_datetime.date()
                
                if start_date <= slot_date <= end_date:
                    score += 10
                else:
                    continue  # Skip slots outside date range
            
            # Check specific datetime preference
            if parsed_time.get('preferred_datetime'):
                preferred = parsed_time['preferred_datetime']
                time_diff = abs((slot_datetime - preferred).total_seconds() / 3600)  # Hours
                
                if time_diff < 1:  # Within 1 hour
                    score += 20
                elif time_diff < 3:  # Within 3 hours
                    score += 15
                elif time_diff < 6:  # Within 6 hours
                    score += 10
                else:
                    score += 5
            
            # Check time of day preference
            if parsed_time.get('time_preference'):
                slot_hour = slot_datetime.hour
                pref = parsed_time['time_preference']
                
                if pref in self.time_periods:
                    start_hour, end_hour = self.time_periods[pref]
                    if start_hour <= slot_hour <= end_hour:
                        score += 15
            
            # Urgency bonus
            if parsed_time.get('urgency') == 'high':
                # Prefer earlier slots
                hours_from_now = (slot_datetime - datetime.now(slot_datetime.tzinfo)).total_seconds() / 3600
                if hours_from_now < 24:  # Within 24 hours
                    score += 10
                elif hours_from_now < 48:  # Within 48 hours
                    score += 5
            
            matching_slots.append((slot, score))
        
        # Sort by score (highest first)
        matching_slots.sort(key=lambda x: x[1], reverse=True)
        
        return [slot for slot, score in matching_slots]
    
    def format_time_in_timezone(self, dt: datetime, target_timezone: str = None) -> str:
        """
        Format datetime in target timezone with clear timezone indication.
        
        Args:
            dt: datetime object with timezone info
            target_timezone: target timezone string (e.g., 'America/Los_Angeles')
            
        Returns:
            Formatted time string with timezone
        """
        if not target_timezone:
            target_timezone = self.default_tz.zone
        
        try:
            target_tz = pytz.timezone(target_timezone)
            converted_dt = dt.astimezone(target_tz)
            
            # Format with timezone abbreviation
            tz_name = converted_dt.strftime('%Z')
            if tz_name == 'EST' or tz_name == 'EDT':
                tz_display = 'EST'
            elif tz_name == 'PST' or tz_name == 'PDT':
                tz_display = 'PST'
            elif tz_name == 'CST' or tz_name == 'CDT':
                tz_display = 'CST'
            elif tz_name == 'MST' or tz_name == 'MDT':
                tz_display = 'MST'
            elif tz_name == 'UTC' or tz_name == 'GMT':
                tz_display = 'UTC'
            else:
                tz_display = tz_name
            
            return f"{converted_dt.strftime('%A, %B %d at %I:%M %p')} {tz_display}"
            
        except Exception as e:
            logger.warning(f"Error formatting time in timezone {target_timezone}: {e}")
            # Fallback to default timezone
            return f"{dt.strftime('%A, %B %d at %I:%M %p')} EST"
    
    def format_dual_timezone(self, dt: datetime, user_timezone: str = None) -> str:
        """
        Format datetime showing both EST and user's timezone.
        
        Args:
            dt: datetime object with timezone info
            user_timezone: user's preferred timezone
            
        Returns:
            Formatted string showing both timezones
        """
        # Always show EST first (our primary timezone)
        est_time = self.format_time_in_timezone(dt, 'America/New_York')
        
        if not user_timezone or user_timezone == 'America/New_York':
            return est_time
        
        # Add user's timezone if different
        user_time = self.format_time_in_timezone(dt, user_timezone)
        return f"{est_time} ({user_time})"


# Global instance
time_parser = TimeParser()