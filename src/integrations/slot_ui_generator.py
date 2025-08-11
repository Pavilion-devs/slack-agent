"""
Slot UI Generator - Creates platform-specific interactive elements for slot selection.
Generates clickable buttons/actions for Slack, Chainlit, and web interfaces.
"""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.models.scheduling import AvailableSlot, SchedulerResponse

logger = logging.getLogger(__name__)


class SlotUIGenerator:
    """Generates interactive UI elements for slot selection across different platforms."""
    
    def __init__(self):
        """Initialize UI generator."""
        self.max_slots_per_row = 2  # For Slack button layouts
        self.max_total_slots = 6    # Maximum slots to show at once
        
    def generate_slack_blocks(self, scheduler_response: SchedulerResponse) -> List[Dict[str, Any]]:
        """
        Generate Slack Block Kit elements for slot selection.
        
        Args:
            scheduler_response: Scheduler response with available slots
            
        Returns:
            List of Slack block elements for interactive slot selection
        """
        logger.info(f"Generating Slack blocks for {len(scheduler_response.slots)} slots")
        
        blocks = []
        
        # Header message
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{scheduler_response.message}*"
            }
        })
        
        # Divider
        blocks.append({"type": "divider"})
        
        # Generate button blocks (2 buttons per row)
        slots_to_show = scheduler_response.slots[:self.max_total_slots]
        
        for i in range(0, len(slots_to_show), self.max_slots_per_row):
            row_slots = slots_to_show[i:i + self.max_slots_per_row]
            
            button_elements = []
            for slot in row_slots:
                button_elements.append({
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": slot.display_text,
                        "emoji": True
                    },
                    "style": "primary",
                    "action_id": "book_demo_slot",
                    "value": json.dumps({
                        "slot_id": slot.slot_id,
                        "start_time": slot.start_time.isoformat(),
                        "end_time": slot.end_time.isoformat(),
                        "display_text": slot.display_text
                    })
                })
            
            blocks.append({
                "type": "actions",
                "elements": button_elements
            })
        
        # Footer info
        if scheduler_response.show_timezone_info and slots_to_show:
            timezone_text = f"All times shown in {slots_to_show[0].timezone}"
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"📅 {timezone_text} | Click a time slot to book your demo"
                    }
                ]
            })
        
        logger.info(f"Generated {len(blocks)} Slack blocks")
        return blocks
    
    def generate_chainlit_actions(self, scheduler_response: SchedulerResponse) -> List[Dict[str, Any]]:
        """
        Generate Chainlit Action elements for slot selection.
        
        Args:
            scheduler_response: Scheduler response with available slots
            
        Returns:
            List of Chainlit action configurations
        """
        logger.info(f"Generating Chainlit actions for {len(scheduler_response.slots)} slots")
        
        actions = []
        slots_to_show = scheduler_response.slots[:self.max_total_slots]
        
        for slot in slots_to_show:
            action_value = json.dumps({
                "slot_id": slot.slot_id,
                "start_time": slot.start_time.isoformat(),
                "end_time": slot.end_time.isoformat(),
                "display_text": slot.display_text
            })
            
            actions.append({
                "name": "book_demo_slot",
                "value": action_value,
                "label": f"📅 {slot.display_text}",
                "description": f"Book demo for {slot.display_text}",
                "payload": {
                    "slot_id": slot.slot_id,
                    "demo_type": "standard",
                    "action_type": "book_slot"
                }
            })
        
        logger.info(f"Generated {len(actions)} Chainlit actions")
        return actions
    
    def generate_web_interface_data(self, scheduler_response: SchedulerResponse) -> Dict[str, Any]:
        """
        Generate data structure for web interface slot selection.
        
        Args:
            scheduler_response: Scheduler response with available slots
            
        Returns:
            Dictionary with web interface configuration
        """
        logger.info(f"Generating web interface data for {len(scheduler_response.slots)} slots")
        
        slots_to_show = scheduler_response.slots[:self.max_total_slots]
        
        web_data = {
            "message": scheduler_response.message,
            "slots": [
                {
                    "id": slot.slot_id,
                    "displayText": slot.display_text,
                    "startTime": slot.start_time.isoformat(),
                    "endTime": slot.end_time.isoformat(),
                    "timezone": slot.timezone,
                    "date": slot.display_date,
                    "time": slot.display_time
                }
                for slot in slots_to_show
            ],
            "timezone": slots_to_show[0].timezone if slots_to_show else "America/New_York",
            "showTimezoneInfo": scheduler_response.show_timezone_info,
            "maxSlotsDisplay": scheduler_response.max_slots_display
        }
        
        logger.info(f"Generated web interface data with {len(web_data['slots'])} slots")
        return web_data
    
    def generate_fallback_text(self, scheduler_response: SchedulerResponse) -> str:
        """
        Generate fallback text for platforms that don't support interactive elements.
        
        Args:
            scheduler_response: Scheduler response with available slots
            
        Returns:
            Formatted text message with numbered options
        """
        message_parts = [scheduler_response.message, ""]
        
        slots_to_show = scheduler_response.slots[:self.max_total_slots]
        for i, slot in enumerate(slots_to_show, 1):
            message_parts.append(f"{i}. {slot.display_text}")
        
        message_parts.extend([
            "",
            "Reply with the number of your preferred time (e.g., '3') to book that slot.",
            f"All times shown in {slots_to_show[0].timezone if slots_to_show else 'EST'}."
        ])
        
        return "\n".join(message_parts)
    
    def create_booking_confirmation_slack_blocks(
        self, 
        booked_slot: AvailableSlot, 
        calendar_event_id: Optional[str] = None,
        meeting_url: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate Slack blocks for booking confirmation.
        
        Args:
            booked_slot: The slot that was successfully booked
            calendar_event_id: Google Calendar event ID if created
            meeting_url: Meeting URL if applicable
            
        Returns:
            List of Slack blocks for confirmation message
        """
        blocks = []
        
        # Success header
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"✅ *Demo Booked Successfully!*\n\nYour demo is scheduled for *{booked_slot.display_text}*"
            }
        })
        
        # Divider
        blocks.append({"type": "divider"})
        
        # Details section
        details_text = f"📅 *Date & Time:* {booked_slot.display_text}\n"
        details_text += f"⏱️ *Duration:* {booked_slot.duration_minutes} minutes\n"
        
        if meeting_url:
            details_text += f"🔗 *Meeting Link:* {meeting_url}\n"
        
        details_text += "📧 *Calendar Invite:* Will be sent shortly"
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": details_text
            }
        })
        
        # Footer
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "Need to reschedule? Just let me know and I'll help you find another time! 🗓️"
                }
            ]
        })
        
        return blocks
    
    def validate_slot_selection_payload(self, payload_str: str) -> Optional[Dict[str, Any]]:
        """
        Validate and parse slot selection payload from button clicks.
        
        Args:
            payload_str: JSON string from button click
            
        Returns:
            Parsed slot data or None if invalid
        """
        try:
            payload = json.loads(payload_str)
            
            required_fields = ['slot_id', 'start_time', 'end_time', 'display_text']
            if not all(field in payload for field in required_fields):
                logger.error(f"Missing required fields in payload: {payload}")
                return None
            
            # Validate datetime formats
            try:
                datetime.fromisoformat(payload['start_time'])
                datetime.fromisoformat(payload['end_time'])
            except ValueError as e:
                logger.error(f"Invalid datetime format in payload: {e}")
                return None
            
            return payload
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in slot selection payload: {e}")
            return None
        except Exception as e:
            logger.error(f"Error validating slot selection payload: {e}")
            return None


# Global instance
slot_ui_generator = SlotUIGenerator()