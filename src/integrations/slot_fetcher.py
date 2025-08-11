"""
Slot Fetcher Service - Replaces complex time parsing with real availability checking.
Generates clickable time slots by querying Google Calendar for actual availability.
"""

import logging
from datetime import datetime, timedelta, time
from typing import List, Optional, Set
import pytz
from uuid import uuid4

from src.models.scheduling import (
    AvailableSlot, SlotGenerationConfig, SlotStatus
)
from src.integrations.calendar_service import calendar_service

logger = logging.getLogger(__name__)


class SlotFetcher:
    """Fetches and generates available time slots from calendar data."""
    
    def __init__(self, config: Optional[SlotGenerationConfig] = None):
        """Initialize slot fetcher with configuration."""
        self.config = config or SlotGenerationConfig()
        self.calendar = calendar_service
        
        # US holidays (simplified list - can be expanded)
        self.holidays_2025 = {
            "2025-01-01",  # New Year's Day
            "2025-01-20",  # Martin Luther King Jr. Day  
            "2025-02-17",  # Presidents Day
            "2025-05-26",  # Memorial Day
            "2025-07-04",  # Independence Day
            "2025-09-01",  # Labor Day
            "2025-11-27",  # Thanksgiving
            "2025-11-28",  # Black Friday
            "2025-12-25",  # Christmas
        }
        
        logger.info(f"SlotFetcher initialized with config: {self.config}")
    
    async def get_available_slots(
        self, 
        days_ahead: Optional[int] = None,
        timezone: Optional[str] = None
    ) -> List[AvailableSlot]:
        """
        Get available demo slots for the next N days.
        
        Args:
            days_ahead: Override config days_ahead
            timezone: Display timezone (defaults to config timezone)
            
        Returns:
            List of available slots with display formatting
        """
        days = days_ahead or self.config.days_ahead
        tz_str = timezone or self.config.timezone
        display_tz = pytz.timezone(tz_str)
        
        logger.info(f"Fetching available slots for next {days} days in {tz_str}")
        
        try:
            # Step 1: Generate potential time slots
            potential_slots = self._generate_potential_slots(days, display_tz)
            logger.info(f"Generated {len(potential_slots)} potential slots")
            
            # Step 2: Check calendar availability
            available_slots = await self._filter_by_calendar_availability(potential_slots)
            logger.info(f"Found {len(available_slots)} available slots after calendar check")
            
            # Step 3: Apply business rules and formatting
            final_slots = self._apply_business_rules_and_format(available_slots, display_tz)
            logger.info(f"Final {len(final_slots)} slots after business rules")
            
            return final_slots
            
        except Exception as e:
            logger.error(f"Error fetching available slots: {e}")
            # Return fallback slots if calendar fails
            return self._generate_fallback_slots(display_tz)
    
    def _generate_potential_slots(self, days_ahead: int, timezone: pytz.BaseTzInfo) -> List[datetime]:
        """Generate all potential time slots within business hours."""
        slots = []
        now = datetime.now(timezone)
        
        # Start from tomorrow (or today if it's early enough)
        start_date = now.date()
        if now.hour >= self.config.end_hour - 2:  # Too late today
            start_date = start_date + timedelta(days=1)
        
        for day_offset in range(days_ahead):
            current_date = start_date + timedelta(days=day_offset)
            
            # Skip weekends if configured
            if self.config.exclude_weekends and current_date.weekday() >= 5:
                continue
            
            # Skip holidays if configured
            if self.config.exclude_holidays and current_date.strftime("%Y-%m-%d") in self.holidays_2025:
                continue
            
            # Generate slots for this day
            day_slots = self._generate_day_slots(current_date, timezone, now)
            slots.extend(day_slots)
            
            # Limit slots per day
            if len(day_slots) >= self.config.max_slots_per_day:
                slots = slots[:self.config.max_slots_per_day]
        
        return slots
    
    def _generate_day_slots(self, date, timezone: pytz.BaseTzInfo, now: datetime) -> List[datetime]:
        """Generate time slots for a specific day."""
        slots = []
        
        # Business hours for this day
        start_time = timezone.localize(datetime.combine(date, time(self.config.start_hour, 0)))
        end_time = timezone.localize(datetime.combine(date, time(self.config.end_hour, 0)))
        
        current_slot = start_time
        while current_slot + timedelta(minutes=self.config.slot_duration_minutes) <= end_time:
            # Check minimum advance booking time
            if current_slot >= now + timedelta(hours=self.config.min_advance_hours):
                slots.append(current_slot)
            
            # Move to next slot (duration + buffer)
            current_slot += timedelta(
                minutes=self.config.slot_duration_minutes + self.config.buffer_minutes
            )
        
        return slots
    
    async def _filter_by_calendar_availability(self, potential_slots: List[datetime]) -> List[datetime]:
        """Filter slots by checking Google Calendar availability."""
        if not potential_slots:
            return []
        
        try:
            # Get busy times from calendar for the date range
            start_time = potential_slots[0]
            end_time = potential_slots[-1] + timedelta(minutes=self.config.slot_duration_minutes)
            
            busy_times = await self.calendar.get_busy_times(start_time, end_time)
            logger.info(f"Found {len(busy_times)} busy periods in calendar")
            
            # Filter out slots that conflict with busy times
            available_slots = []
            for slot_start in potential_slots:
                slot_end = slot_start + timedelta(minutes=self.config.slot_duration_minutes)
                
                # Check if this slot conflicts with any busy time
                is_available = True
                for busy_start, busy_end in busy_times:
                    if self._slots_overlap(slot_start, slot_end, busy_start, busy_end):
                        is_available = False
                        break
                
                if is_available:
                    available_slots.append(slot_start)
            
            return available_slots
            
        except Exception as e:
            logger.warning(f"Calendar availability check failed: {e}, using all potential slots")
            return potential_slots
    
    def _slots_overlap(self, slot_start, slot_end, busy_start, busy_end) -> bool:
        """Check if two time ranges overlap."""
        return slot_start < busy_end and slot_end > busy_start
    
    def _apply_business_rules_and_format(
        self, 
        available_slots: List[datetime], 
        timezone: pytz.BaseTzInfo
    ) -> List[AvailableSlot]:
        """Apply final business rules and format slots for display."""
        formatted_slots = []
        
        for slot_start in available_slots:
            slot_end = slot_start + timedelta(minutes=self.config.slot_duration_minutes)
            
            # Create AvailableSlot object
            slot = AvailableSlot(
                slot_id=f"demo_{uuid4().hex[:8]}",
                start_time=slot_start.astimezone(pytz.UTC),  # Store in UTC
                end_time=slot_end.astimezone(pytz.UTC),
                duration_minutes=self.config.slot_duration_minutes,
                timezone=timezone.zone,
                display_date=slot_start.strftime(self.config.date_format),
                display_time=self._format_time_range(slot_start, slot_end),
                display_text=self._create_display_text(slot_start, slot_end)
            )
            
            formatted_slots.append(slot)
        
        # Limit total slots returned
        return formatted_slots[:12]  # Show max 12 slots to avoid UI clutter
    
    def _format_time_range(self, start: datetime, end: datetime) -> str:
        """Format time range for display."""
        start_str = start.strftime(self.config.time_format)
        end_str = end.strftime(self.config.time_format)
        
        # Add timezone abbreviation
        tz_abbr = start.strftime('%Z')
        if tz_abbr in ['EST', 'EDT']:
            tz_display = 'EST'
        elif tz_abbr in ['PST', 'PDT']:
            tz_display = 'PST'
        elif tz_abbr in ['CST', 'CDT']:
            tz_display = 'CST'
        elif tz_abbr in ['MST', 'MDT']:
            tz_display = 'MST'
        else:
            tz_display = tz_abbr
        
        return f"{start_str}–{end_str} {tz_display}"
    
    def _create_display_text(self, start: datetime, end: datetime) -> str:
        """Create full display text for buttons."""
        date_str = start.strftime(self.config.date_format)
        time_str = self._format_time_range(start, end)
        return f"{date_str}, {time_str}"
    
    def _generate_fallback_slots(self, timezone: pytz.BaseTzInfo) -> List[AvailableSlot]:
        """Generate fallback slots if calendar service fails."""
        logger.warning("Generating fallback demo slots")
        
        fallback_slots = []
        now = datetime.now(timezone)
        
        # Generate a few basic slots for tomorrow
        tomorrow = now.date() + timedelta(days=1)
        base_times = [
            time(10, 0),   # 10:00 AM
            time(14, 0),   # 2:00 PM
            time(16, 0),   # 4:00 PM
        ]
        
        for base_time in base_times:
            slot_start = timezone.localize(datetime.combine(tomorrow, base_time))
            slot_end = slot_start + timedelta(minutes=30)
            
            slot = AvailableSlot(
                slot_id=f"fallback_{uuid4().hex[:8]}",
                start_time=slot_start.astimezone(pytz.UTC),
                end_time=slot_end.astimezone(pytz.UTC),
                duration_minutes=30,
                timezone=timezone.zone,
                display_date=slot_start.strftime("%b %d"),
                display_time=self._format_time_range(slot_start, slot_end),
                display_text=self._create_display_text(slot_start, slot_end)
            )
            
            fallback_slots.append(slot)
        
        return fallback_slots


# Global instance
slot_fetcher = SlotFetcher()