"""
Slot Booking Handler - Processes slot selection clicks and creates calendar events.
Handles the booking flow when users click time slot buttons.
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
import pytz
from uuid import uuid4

from src.models.scheduling import (
    AvailableSlot, BookingRequest, BookingConfirmation, SlotStatus
)
from src.integrations.calendar_service import calendar_service, MeetingRequest
from src.integrations.slot_ui_generator import slot_ui_generator
from src.core.meeting_types import meeting_type_manager

logger = logging.getLogger(__name__)


class SlotBookingHandler:
    """Handles slot booking requests from interactive UI elements."""
    
    def __init__(self):
        """Initialize booking handler."""
        self.default_meeting_title = "Delve Demo"
        self.default_meeting_description = "Demo session to explore Delve's features and capabilities."
        
    async def handle_slot_selection(
        self,
        slot_payload: str,
        user_id: str,
        user_email: Optional[str] = None,
        user_name: Optional[str] = None,
        platform: str = "unknown",
        session_id: Optional[str] = None
    ) -> BookingConfirmation:
        """
        Handle slot selection from interactive UI elements.
        
        Args:
            slot_payload: JSON string from button click containing slot data
            user_id: ID of the user making the booking
            user_email: User's email address
            user_name: User's display name
            platform: Platform the request came from (Slack, Chainlit, etc.)
            session_id: Session ID for tracking
            
        Returns:
            BookingConfirmation with success status and details
        """
        logger.info(f"Processing slot booking from {platform} for user {user_id}")
        
        try:
            # Validate and parse the slot payload
            slot_data = slot_ui_generator.validate_slot_selection_payload(slot_payload)
            if not slot_data:
                return BookingConfirmation(
                    success=False,
                    message="Invalid slot selection. Please try again.",
                    error_code="INVALID_PAYLOAD",
                    error_details="Failed to parse slot selection data"
                )
            
            # Create booking request
            booking_request = BookingRequest(
                slot_id=slot_data["slot_id"],
                user_id=user_id,
                user_email=user_email or f"{user_id}@example.com",  # Fallback email
                user_name=user_name or f"User {user_id}",
                meeting_title=self.default_meeting_title,
                meeting_description=self.default_meeting_description,
                platform=platform,
                session_id=session_id
            )
            
            # Create AvailableSlot object from payload data
            booked_slot = AvailableSlot(
                slot_id=slot_data["slot_id"],
                start_time=datetime.fromisoformat(slot_data["start_time"]),
                end_time=datetime.fromisoformat(slot_data["end_time"]),
                display_text=slot_data["display_text"],
                display_date="",  # Will be populated if needed
                display_time="",  # Will be populated if needed
                status=SlotStatus.BOOKED
            )
            
            # Attempt to create calendar event
            calendar_result = await self._create_calendar_event(booking_request, booked_slot)
            
            # Generate success response
            if calendar_result["success"]:
                confirmation = BookingConfirmation(
                    success=True,
                    message=f"✅ Demo booked successfully for {slot_data['display_text']}! You'll receive a calendar invite shortly.",
                    calendar_event_id=calendar_result.get("event_id"),
                    meeting_url=calendar_result.get("meeting_url"),
                    calendar_invite_sent=True,
                    booked_slot=booked_slot
                )
            else:
                # Calendar failed but we still confirm the booking
                confirmation = BookingConfirmation(
                    success=True,
                    message=f"✅ Demo booked for {slot_data['display_text']}! Our team will send you the meeting details shortly.",
                    calendar_invite_sent=False,
                    booked_slot=booked_slot,
                    error_details=calendar_result.get("error", "Calendar integration temporarily unavailable")
                )
            
            logger.info(f"Slot booking completed successfully: {booking_request.slot_id}")
            return confirmation
            
        except Exception as e:
            logger.error(f"Error processing slot booking: {e}")
            return BookingConfirmation(
                success=False,
                message="Sorry, there was an error booking your demo slot. Let me connect you with our team to schedule manually.",
                error_code="BOOKING_ERROR",
                error_details=str(e)
            )
    
    async def _create_calendar_event(
        self, 
        booking_request: BookingRequest, 
        slot: AvailableSlot
    ) -> Dict[str, Any]:
        """
        Create calendar event for the booked slot.
        
        Args:
            booking_request: Booking request details
            slot: The slot being booked
            
        Returns:
            Dictionary with success status and event details
        """
        try:
            if not calendar_service.is_available():
                logger.warning("Calendar service not available")
                return {
                    "success": False,
                    "error": "Calendar service temporarily unavailable"
                }
            
            # Calculate duration in minutes
            duration_minutes = int((slot.end_time - slot.start_time).total_seconds() / 60)
            
            # Create meeting request
            meeting_request = MeetingRequest(
                title=booking_request.meeting_title,
                description=booking_request.meeting_description,
                start_time=slot.start_time,  # Correct parameter name
                duration_minutes=duration_minutes,  # Calculated duration
                attendee_emails=[booking_request.user_email] + booking_request.attendee_emails,
                meeting_type="demo"  # Default to demo type
            )
            
            # Create the calendar event
            meeting_response = await calendar_service.create_meeting(meeting_request)
            
            if meeting_response.success:
                logger.info(f"Calendar event created successfully: {meeting_response.event_id}")
                return {
                    "success": True,
                    "event_id": meeting_response.event_id,
                    "meeting_url": getattr(meeting_response, 'meeting_url', None),
                    "event_link": getattr(meeting_response, 'event_link', None)
                }
            else:
                logger.error(f"Calendar event creation failed: {meeting_response.error_message}")
                return {
                    "success": False,
                    "error": meeting_response.error_message
                }
                
        except Exception as e:
            logger.error(f"Error creating calendar event: {e}")
            return {
                "success": False,
                "error": f"Calendar error: {str(e)}"
            }
    
    def generate_booking_confirmation_response(
        self, 
        confirmation: BookingConfirmation, 
        platform: str = "unknown"
    ) -> Dict[str, Any]:
        """
        Generate platform-specific response for booking confirmation.
        
        Args:
            confirmation: Booking confirmation details
            platform: Target platform (slack, chainlit, web)
            
        Returns:
            Platform-specific response data
        """
        if platform.lower() == "slack":
            return self._generate_slack_confirmation(confirmation)
        elif platform.lower() == "chainlit":
            return self._generate_chainlit_confirmation(confirmation)
        else:
            return self._generate_generic_confirmation(confirmation)
    
    def _generate_slack_confirmation(self, confirmation: BookingConfirmation) -> Dict[str, Any]:
        """Generate Slack-specific confirmation response."""
        if confirmation.success and confirmation.booked_slot:
            blocks = slot_ui_generator.create_booking_confirmation_slack_blocks(
                booked_slot=confirmation.booked_slot,
                calendar_event_id=confirmation.calendar_event_id,
                meeting_url=confirmation.meeting_url
            )
            
            return {
                "response_type": "slack_blocks",
                "blocks": blocks,
                "text": confirmation.message  # Fallback text
            }
        else:
            # Error response
            return {
                "response_type": "text",
                "text": confirmation.message,
                "error": True
            }
    
    def _generate_chainlit_confirmation(self, confirmation: BookingConfirmation) -> Dict[str, Any]:
        """Generate Chainlit-specific confirmation response."""
        return {
            "response_type": "message",
            "content": confirmation.message,
            "success": confirmation.success,
            "metadata": {
                "booked_slot": confirmation.booked_slot.dict() if confirmation.booked_slot else None,
                "calendar_event_id": confirmation.calendar_event_id,
                "meeting_url": confirmation.meeting_url
            }
        }
    
    def _generate_generic_confirmation(self, confirmation: BookingConfirmation) -> Dict[str, Any]:
        """Generate generic confirmation response."""
        return {
            "response_type": "json",
            "success": confirmation.success,
            "message": confirmation.message,
            "data": confirmation.dict()
        }
    
    async def handle_slot_selection_from_text(
        self,
        message_content: str,
        available_slots: list,
        user_id: str,
        user_email: Optional[str] = None,
        user_name: Optional[str] = None,
        platform: str = "unknown"
    ) -> Optional[BookingConfirmation]:
        """
        Handle slot selection from text input (e.g., "3" for slot #3).
        This is a fallback for when interactive buttons aren't supported.
        
        Args:
            message_content: User's message (e.g., "3", "option 2")
            available_slots: List of available slots
            user_id: User ID
            user_email: User email
            user_name: User name
            platform: Platform name
            
        Returns:
            BookingConfirmation if valid selection, None otherwise
        """
        try:
            # Extract number from message
            import re
            number_match = re.search(r'\b(\d+)\b', message_content.strip())
            if not number_match:
                return None
            
            slot_number = int(number_match.group(1))
            
            # Validate slot number
            if slot_number < 1 or slot_number > len(available_slots):
                logger.warning(f"Invalid slot number {slot_number}, available: 1-{len(available_slots)}")
                return None
            
            # Get the selected slot
            selected_slot = available_slots[slot_number - 1]
            
            # Create payload for booking
            slot_payload = json.dumps({
                "slot_id": selected_slot.slot_id,
                "start_time": selected_slot.start_time.isoformat(),
                "end_time": selected_slot.end_time.isoformat(),
                "display_text": selected_slot.display_text
            })
            
            # Process the booking
            return await self.handle_slot_selection(
                slot_payload=slot_payload,
                user_id=user_id,
                user_email=user_email,
                user_name=user_name,
                platform=platform
            )
            
        except Exception as e:
            logger.error(f"Error handling text slot selection: {e}")
            return None


# Global instance
slot_booking_handler = SlotBookingHandler()