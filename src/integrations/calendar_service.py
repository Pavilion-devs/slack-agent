"""
Google Calendar integration service for Delve Slack Support AI Agent.
Handles real calendar booking, availability checking, and meeting management.
"""

import os
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import json

import pytz
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..core.meeting_types import meeting_type_manager, MeetingTypeConfig

logger = logging.getLogger(__name__)


@dataclass
class TimeSlot:
    """Represents an available time slot for booking."""
    start_time: datetime
    end_time: datetime
    duration_minutes: int
    timezone_name: str = "America/New_York"
    
    def __str__(self) -> str:
        """Human-readable representation of the time slot."""
        # Convert to EST for display
        est = pytz.timezone('America/New_York')
        start_est = self.start_time.astimezone(est)
        end_est = self.end_time.astimezone(est)
        
        day_name = start_est.strftime("%A")
        date_str = start_est.strftime("%B %d")
        start_time_str = start_est.strftime("%I:%M %p")
        end_time_str = end_est.strftime("%I:%M %p")
        
        return f"{day_name}, {date_str} at {start_time_str} - {end_time_str} EST"


@dataclass
class MeetingRequest:
    """Represents a meeting booking request."""
    title: str
    description: str
    start_time: datetime
    duration_minutes: int
    attendee_emails: List[str]
    meeting_type: str = "demo"
    timezone_name: str = "America/New_York"
    
    @property
    def end_time(self) -> datetime:
        """Calculate end time based on start time and duration."""
        return self.start_time + timedelta(minutes=self.duration_minutes)


@dataclass
class MeetingResponse:
    """Response from creating a meeting."""
    success: bool
    event_id: Optional[str] = None
    event_link: Optional[str] = None
    error_message: Optional[str] = None
    calendar_invite_sent: bool = False


class GoogleCalendarService:
    """Service for Google Calendar integration."""
    
    def __init__(self, credentials_path: str = "calendar_token.json"):
        """Initialize the calendar service with credentials."""
        self.credentials_path = credentials_path
        self.service = None
        self.calendar_id = 'primary'  # Use primary calendar
        
        # Business hours configuration (9 AM - 6 PM EST)
        self.business_start_hour = 9
        self.business_end_hour = 18
        self.business_timezone = pytz.timezone('America/New_York')
        
        # Use the centralized meeting type manager
        self.meeting_type_manager = meeting_type_manager
        
        self._initialize_service()
    
    def _initialize_service(self) -> bool:
        """Initialize the Google Calendar API service."""
        try:
            if not os.path.exists(self.credentials_path):
                logger.error(f"Calendar credentials file not found: {self.credentials_path}")
                return False
            
            # Load credentials from token file
            with open(self.credentials_path, 'r') as f:
                creds_data = json.load(f)
            
            # Create credentials object
            creds = Credentials(
                token=creds_data['token'],
                refresh_token=creds_data.get('refresh_token'),
                token_uri=creds_data.get('token_uri'),
                client_id=creds_data.get('client_id'),
                client_secret=creds_data.get('client_secret'),
                scopes=creds_data.get('scopes')
            )
            
            # Build the service
            self.service = build('calendar', 'v3', credentials=creds)
            
            # Test the connection
            calendar_list = self.service.calendarList().list(maxResults=1).execute()
            logger.info(f"✅ Google Calendar service initialized successfully")
            logger.info(f"Connected to calendar: {calendar_list.get('items', [{}])[0].get('summary', 'Primary')}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Calendar service: {e}")
            return False
    
    def is_available(self) -> bool:
        """Check if the calendar service is available."""
        return self.service is not None
    
    async def get_available_slots(
        self, 
        days_ahead: int = 7, 
        meeting_type: str = "demo",
        max_slots: int = 5
    ) -> List[TimeSlot]:
        """
        Find available time slots in the next N days.
        
        Args:
            days_ahead: How many days ahead to search (default: 7)
            meeting_type: Type of meeting (demo, support, sales)
            max_slots: Maximum number of slots to return
            
        Returns:
            List of available TimeSlot objects
        """
        if not self.is_available():
            logger.error("Calendar service not available")
            return []
        
        try:
            # Get meeting type configuration from the centralized manager
            meeting_config = self.meeting_type_manager.get_meeting_type(meeting_type)
            if not meeting_config:
                # Fallback to demo if meeting type not found
                meeting_config = self.meeting_type_manager.get_meeting_type("demo")
            
            duration_minutes = meeting_config.duration_minutes
            buffer_minutes = meeting_config.buffer_minutes
            
            # Calculate search range
            now = datetime.now(self.business_timezone)
            # Start from next business hour (avoid booking too soon)
            start_search = self._get_next_business_hour(now + timedelta(hours=2))
            end_search = start_search + timedelta(days=days_ahead)
            
            logger.info(f"🔍 Searching for {duration_minutes}-min slots from {start_search} to {end_search}")
            
            # Get existing events in the time range
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=start_search.isoformat(),
                timeMax=end_search.isoformat(),
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            existing_events = events_result.get('items', [])
            logger.info(f"Found {len(existing_events)} existing events in the range")
            
            # Find available slots
            available_slots = self._find_slots_between_events(
                start_search, 
                end_search, 
                existing_events, 
                duration_minutes,
                buffer_minutes,
                max_slots
            )
            
            logger.info(f"✅ Found {len(available_slots)} available slots")
            return available_slots
            
        except HttpError as e:
            logger.error(f"Google Calendar API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Error finding available slots: {e}")
            return []
    
    def _get_next_business_hour(self, from_time: datetime) -> datetime:
        """Get the next business hour from the given time."""
        # Ensure we're in business timezone
        if from_time.tzinfo is None:
            from_time = self.business_timezone.localize(from_time)
        else:
            from_time = from_time.astimezone(self.business_timezone)
        
        # If it's weekend, move to Monday
        if from_time.weekday() >= 5:  # Saturday=5, Sunday=6
            days_until_monday = 7 - from_time.weekday()
            from_time = from_time + timedelta(days=days_until_monday)
            from_time = from_time.replace(hour=self.business_start_hour, minute=0, second=0, microsecond=0)
        
        # If before business hours, move to start of business day
        elif from_time.hour < self.business_start_hour:
            from_time = from_time.replace(hour=self.business_start_hour, minute=0, second=0, microsecond=0)
        
        # If after business hours, move to next business day
        elif from_time.hour >= self.business_end_hour:
            from_time = from_time + timedelta(days=1)
            from_time = from_time.replace(hour=self.business_start_hour, minute=0, second=0, microsecond=0)
            # Check if next day is weekend
            if from_time.weekday() >= 5:
                return self._get_next_business_hour(from_time)
        
        return from_time
    
    def _find_slots_between_events(
        self, 
        start_time: datetime, 
        end_time: datetime, 
        existing_events: List[Dict],
        duration_minutes: int,
        buffer_minutes: int,
        max_slots: int
    ) -> List[TimeSlot]:
        """Find available slots between existing events."""
        slots = []
        current_time = start_time
        
        # Parse existing events into (start, end) tuples
        busy_periods = []
        for event in existing_events:
            event_start = self._parse_datetime(event['start'])
            event_end = self._parse_datetime(event['end'])
            if event_start and event_end:
                busy_periods.append((event_start, event_end))
        
        # Sort busy periods by start time
        busy_periods.sort(key=lambda x: x[0])
        
        while current_time < end_time and len(slots) < max_slots:
            # Skip weekends
            if current_time.weekday() >= 5:
                current_time = self._get_next_business_hour(current_time + timedelta(days=1))
                continue
            
            # Check if current time is in business hours
            if (current_time.hour < self.business_start_hour or 
                current_time.hour >= self.business_end_hour):
                current_time = self._get_next_business_hour(current_time)
                continue
            
            # Calculate slot end time
            slot_end = current_time + timedelta(minutes=duration_minutes)
            
            # Check if slot fits in business hours
            if slot_end.hour > self.business_end_hour:
                # Move to next business day
                current_time = self._get_next_business_hour(current_time + timedelta(days=1))
                continue
            
            # Check for conflicts with existing events
            conflict_found = False
            for busy_start, busy_end in busy_periods:
                # Add buffer time around existing events
                buffered_start = busy_start - timedelta(minutes=buffer_minutes)
                buffered_end = busy_end + timedelta(minutes=buffer_minutes)
                
                # Check if proposed slot overlaps with buffered busy period
                if (current_time < buffered_end and slot_end > buffered_start):
                    conflict_found = True
                    # Move current time to after this busy period
                    current_time = busy_end + timedelta(minutes=buffer_minutes)
                    current_time = self._get_next_business_hour(current_time)
                    break
            
            if not conflict_found:
                # Found a valid slot!
                slots.append(TimeSlot(
                    start_time=current_time,
                    end_time=slot_end,
                    duration_minutes=duration_minutes,
                    timezone_name=current_time.tzname()
                ))
                # Move to next potential slot (30 minutes later)
                current_time += timedelta(minutes=30)
            
        return slots
    
    def _parse_datetime(self, dt_dict: Dict) -> Optional[datetime]:
        """Parse datetime from Google Calendar API response."""
        try:
            if 'dateTime' in dt_dict:
                return datetime.fromisoformat(dt_dict['dateTime'].replace('Z', '+00:00'))
            elif 'date' in dt_dict:
                # All-day event - skip for availability
                return None
            return None
        except Exception as e:
            logger.warning(f"Failed to parse datetime: {dt_dict}, error: {e}")
            return None
    
    async def create_meeting(self, meeting_request: MeetingRequest) -> MeetingResponse:
        """
        Create a calendar event for the meeting.
        
        Args:
            meeting_request: Details of the meeting to create
            
        Returns:
            MeetingResponse with success status and event details
        """
        if not self.is_available():
            return MeetingResponse(
                success=False,
                error_message="Calendar service not available"
            )
        
        try:
            # Get meeting type configuration from the centralized manager
            meeting_config = self.meeting_type_manager.get_meeting_type(meeting_request.meeting_type)
            if not meeting_config:
                # Fallback to demo if meeting type not found
                meeting_config = self.meeting_type_manager.get_meeting_type("demo")
            
            # Create event object
            event = {
                'summary': meeting_request.title,
                'description': meeting_request.description,
                'start': {
                    'dateTime': meeting_request.start_time.isoformat(),
                    'timeZone': meeting_request.timezone_name,
                },
                'end': {
                    'dateTime': meeting_request.end_time.isoformat(),
                    'timeZone': meeting_request.timezone_name,
                },
                'attendees': [{'email': email} for email in meeting_request.attendee_emails],
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                        {'method': 'popup', 'minutes': 15},       # 15 min before
                    ],
                },
                'guestsCanModify': False,
                'guestsCanInviteOthers': False,
                'sendUpdates': 'all',  # Send invites to all attendees
            }
            
            # Create the event
            created_event = self.service.events().insert(
                calendarId=self.calendar_id, 
                body=event,
                sendUpdates='all'
            ).execute()
            
            logger.info(f"✅ Meeting created successfully: {created_event.get('id')}")
            
            return MeetingResponse(
                success=True,
                event_id=created_event.get('id'),
                event_link=created_event.get('htmlLink'),
                calendar_invite_sent=True
            )
            
        except HttpError as e:
            logger.error(f"Google Calendar API error creating meeting: {e}")
            return MeetingResponse(
                success=False,
                error_message=f"Calendar API error: {e}"
            )
        except Exception as e:
            logger.error(f"Error creating meeting: {e}")
            return MeetingResponse(
                success=False,
                error_message=f"Unexpected error: {e}"
            )
    
    async def check_availability(self, start_time: datetime, duration_minutes: int) -> bool:
        """
        Check if a specific time slot is available.
        
        Args:
            start_time: Proposed start time
            duration_minutes: Duration of the meeting
            
        Returns:
            True if the slot is available, False otherwise
        """
        if not self.is_available():
            return False
        
        try:
            end_time = start_time + timedelta(minutes=duration_minutes)
            
            # Query for events in this time range
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=start_time.isoformat(),
                timeMax=end_time.isoformat(),
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            existing_events = events_result.get('items', [])
            
            # If no events found, slot is available
            return len(existing_events) == 0
            
        except Exception as e:
            logger.error(f"Error checking availability: {e}")
            return False
    
    def get_meeting_types(self) -> Dict[str, Dict[str, Any]]:
        """Get available meeting types and their configurations."""
        return self.meeting_type_manager.get_all_meeting_types()
    
    def get_meeting_type_config(self, meeting_type: str) -> Optional[MeetingTypeConfig]:
        """Get specific meeting type configuration."""
        return self.meeting_type_manager.get_meeting_type(meeting_type)
    
    def detect_meeting_type(self, message_content: str) -> str:
        """Detect meeting type from message content."""
        return self.meeting_type_manager.detect_meeting_type(message_content)
    
    def format_meeting_selection_options(self) -> str:
        """Format meeting type options for user selection."""
        return self.meeting_type_manager.format_meeting_selection_options()
    
    def get_meeting_type_by_number(self, selection_number: int) -> str:
        """Get meeting type key by selection number (1-based)."""
        return self.meeting_type_manager.get_meeting_type_by_number(selection_number)
    
    async def get_busy_times(self, start_time: datetime, end_time: datetime) -> List[Tuple[datetime, datetime]]:
        """
        Get busy time periods from Google Calendar within the specified range.
        
        Args:
            start_time: Start of the time range to check
            end_time: End of the time range to check
            
        Returns:
            List of tuples (busy_start, busy_end) representing busy periods
        """
        if not self.is_available():
            logger.warning("Calendar service not available, returning empty busy times")
            return []
        
        try:
            # Convert times to RFC3339 format for Google Calendar API
            time_min = start_time.isoformat()
            time_max = end_time.isoformat()
            
            logger.info(f"🔍 Checking calendar busy times from {start_time} to {end_time}")
            
            # Query the freebusy API
            body = {
                'timeMin': time_min,
                'timeMax': time_max,
                'items': [{'id': self.calendar_id}],
                'timeZone': 'UTC'
            }
            
            freebusy_result = self.service.freebusy().query(body=body).execute()
            
            # Extract busy periods
            busy_times = []
            calendars = freebusy_result.get('calendars', {})
            primary_calendar = calendars.get(self.calendar_id, {})
            busy_periods = primary_calendar.get('busy', [])
            
            logger.info(f"Found {len(busy_periods)} busy periods in calendar")
            
            for period in busy_periods:
                busy_start_str = period.get('start')
                busy_end_str = period.get('end')
                
                if busy_start_str and busy_end_str:
                    # Parse the datetime strings
                    busy_start = datetime.fromisoformat(busy_start_str.replace('Z', '+00:00'))
                    busy_end = datetime.fromisoformat(busy_end_str.replace('Z', '+00:00'))
                    
                    busy_times.append((busy_start, busy_end))
                    logger.debug(f"Busy period: {busy_start} to {busy_end}")
            
            return busy_times
            
        except HttpError as e:
            logger.error(f"Google Calendar API error getting busy times: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting calendar busy times: {e}")
            return []


# Global instance
calendar_service = GoogleCalendarService()