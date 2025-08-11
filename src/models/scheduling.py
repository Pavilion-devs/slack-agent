"""Scheduling data models for the demo slot picker system."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class SlotStatus(str, Enum):
    """Status of an available slot."""
    AVAILABLE = "available"
    BOOKED = "booked"
    TENTATIVE = "tentative"


class AvailableSlot(BaseModel):
    """Represents an available time slot for demo scheduling."""
    
    slot_id: str = Field(..., description="Unique identifier for this slot")
    start_time: datetime = Field(..., description="Start time of the slot (UTC)")
    end_time: datetime = Field(..., description="End time of the slot (UTC)")
    duration_minutes: int = Field(default=30, description="Duration in minutes")
    status: SlotStatus = Field(default=SlotStatus.AVAILABLE, description="Slot status")
    timezone: str = Field(default="America/New_York", description="Display timezone")
    
    # Display properties
    display_date: str = Field(..., description="Human-readable date (e.g., 'Aug 8')")
    display_time: str = Field(..., description="Human-readable time (e.g., '2:00-2:30 PM EST')")
    display_text: str = Field(..., description="Full display text for buttons")
    
    # Metadata
    meeting_type: str = Field(default="demo", description="Type of meeting")
    location: Optional[str] = Field(default=None, description="Meeting location/URL")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SchedulerResponse(BaseModel):
    """Response from the demo scheduler with available slots."""
    
    message: str = Field(..., description="Message to display to user")
    slots: List[AvailableSlot] = Field(default_factory=list, description="Available slots")
    response_type: str = Field(default="interactive_slots", description="Type of response")
    
    # Additional context
    requested_timeframe: Optional[str] = Field(default=None, description="User's original request")
    timezone_preference: Optional[str] = Field(default=None, description="User's timezone preference")
    
    # UI generation hints
    max_slots_display: int = Field(default=6, description="Maximum slots to show at once")
    show_timezone_info: bool = Field(default=True, description="Whether to show timezone info")


class BookingRequest(BaseModel):
    """Request to book a specific time slot."""
    
    slot_id: str = Field(..., description="ID of the slot to book")
    user_id: str = Field(..., description="ID of the user booking")
    user_email: str = Field(..., description="User's email address")
    user_name: Optional[str] = Field(default=None, description="User's name")
    
    # Meeting details
    meeting_title: str = Field(default="Delve Demo", description="Meeting title")
    meeting_description: Optional[str] = Field(default=None, description="Meeting description")
    attendee_emails: List[str] = Field(default_factory=list, description="Additional attendees")
    
    # Platform context
    platform: str = Field(..., description="Platform the request came from (Slack, Chainlit, etc.)")
    session_id: Optional[str] = Field(default=None, description="Session ID for tracking")


class BookingConfirmation(BaseModel):
    """Confirmation response after booking a slot."""
    
    success: bool = Field(..., description="Whether booking was successful")
    message: str = Field(..., description="Confirmation message")
    
    # Booking details
    calendar_event_id: Optional[str] = Field(default=None, description="Google Calendar event ID")
    meeting_url: Optional[str] = Field(default=None, description="Meeting URL if applicable")
    calendar_invite_sent: bool = Field(default=False, description="Whether calendar invite was sent")
    
    # Slot information
    booked_slot: Optional[AvailableSlot] = Field(default=None, description="The booked slot details")
    
    # Error handling
    error_code: Optional[str] = Field(default=None, description="Error code if booking failed")
    error_details: Optional[str] = Field(default=None, description="Error details if booking failed")


class SlotGenerationConfig(BaseModel):
    """Configuration for generating available slots."""
    
    # Time range
    days_ahead: int = Field(default=7, description="How many days ahead to look")
    start_hour: int = Field(default=9, description="Start of business hours (24-hour)")
    end_hour: int = Field(default=17, description="End of business hours (24-hour)")
    
    # Slot configuration  
    slot_duration_minutes: int = Field(default=30, description="Duration of each slot")
    buffer_minutes: int = Field(default=15, description="Buffer between meetings")
    max_slots_per_day: int = Field(default=8, description="Maximum slots per day")
    
    # Availability rules
    exclude_weekends: bool = Field(default=True, description="Exclude Saturday/Sunday")
    exclude_holidays: bool = Field(default=True, description="Exclude known holidays")
    min_advance_hours: int = Field(default=2, description="Minimum hours in advance to book")
    
    # Display preferences
    timezone: str = Field(default="America/New_York", description="Display timezone")
    date_format: str = Field(default="%b %d", description="Date format for display")
    time_format: str = Field(default="%-I:%M %p", description="Time format for display")