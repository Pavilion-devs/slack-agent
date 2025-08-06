"""Demo Scheduler Agent for handling demo requests and calendar integration."""

import logging
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import asyncio
import pytz

from src.agents.base_agent import BaseAgent
from src.models.schemas import SupportMessage, AgentResponse
from src.core.config import settings
from src.integrations.calendar_service import calendar_service, MeetingRequest
from src.utils.time_parser import time_parser
from src.core.meeting_types import meeting_type_manager
import openai

logger = logging.getLogger(__name__)


class DemoSchedulerAgent(BaseAgent):
    """Agent specialized in handling demo scheduling requests."""
    
    def __init__(self):
        super().__init__("demo_scheduler")
        self.demo_keywords = [
            'demo', 'demonstration', 'schedule', 'meeting', 'call', 
            'presentation', 'walkthrough', 'overview', 'show me'
        ]
        self.est_timezone = pytz.timezone('America/New_York')
    
    def should_handle(self, message: SupportMessage) -> bool:
        """Determine if this agent should handle ACTUAL scheduling requests only."""
        content_lower = message.content.lower()
        
        # ONLY handle explicit scheduling requests - no more info questions!
        explicit_scheduling_patterns = [
            r'\b(?:can|could|would|let\'s)\s+(?:we|you|i)\s+(?:schedule|book|arrange)',  # "Can we schedule..."
            r'\bi\s+(?:want|need|would like)\s+to\s+(?:schedule|book|arrange)',  # "I want to schedule..."
            r'\bschedule\s+(?:a|an|the)?\s*(?:demo|meeting|call)',  # "Schedule a demo"
            r'\bbook\s+(?:a|an|the)?\s*(?:demo|meeting|call)',  # "Book a demo"
            r'\b(?:set up|setup)\s+(?:a|an|the)?\s*(?:demo|meeting|call)',  # "Set up a demo" 
            r'\bwhen\s+(?:can|could|are)\s+(?:we|you)\s+(?:meet|schedule)',  # "When can we meet?"
        ]
        
        # Check explicit scheduling language
        for pattern in explicit_scheduling_patterns:
            if re.search(pattern, content_lower):
                return True
        
        # Handle slot selection responses (user is already in booking flow)
        slot_selection_patterns = [
            r'option\s*\d+', r'slot\s*\d+', r'choice\s*\d+', r'number\s*\d+',
            r'book\s*\d+', r'select\s*\d+', r'pick\s*\d+', r'choose\s*\d+',
            r'^\d+$',  # Just a number like "3"
            r'yes.*(?:to\s+)?(?:tuesday|wednesday|thursday|friday|monday)',
            r'i\'?ll\s+take\s+(?:the\s+)?(?:tuesday|wednesday|thursday|friday|monday)',
            r'that.*(?:works|perfect|good)', r'confirm.*(?:booking|meeting)',
            r'sounds.*good', r'let\'s.*do.*it', r'book.*it'
        ]
        
        for pattern in slot_selection_patterns:
            if re.search(pattern, content_lower):
                return True
        
        # Handle follow-up questions in scheduling context (timezone, day preferences)
        if any(keyword in content_lower for keyword in ['timezone', 'pst', 'est', 'gmt', 'cst']):
            return True
        
        # Handle standalone day mentions (if user is responding to "what day?" question)
        standalone_days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        if any(day in content_lower for day in standalone_days) and len(content_lower.split()) <= 3:
            return True
            
        return False
    
    async def process_message(self, message: SupportMessage) -> AgentResponse:
        """Process demo scheduling requests."""
        logger.info(f"Demo scheduler processing message: {message.message_id}")
        
        intent = self.extract_message_intent(message)
        content_lower = message.content.lower()
        
        try:
            # Check if this is a slot selection response
            slot_selection = self._extract_slot_selection(message)
            if slot_selection:
                response_text, should_escalate, escalation_reason = await self._handle_slot_booking(message, slot_selection)
                confidence = 0.98
            else:
                # Extract scheduling preferences
                scheduling_info = self._extract_scheduling_preferences(message)
                
                # Check if calendar service is available
                if not calendar_service.is_available():
                    logger.warning("Calendar service not available, escalating")
                    return self.format_response(
                        response_text="I'd love to help schedule your demo! Our calendar system is currently being updated. Let me connect you with our sales team who can schedule your demo immediately.",
                        confidence_score=0.8,
                        should_escalate=True,
                        escalation_reason="Calendar service unavailable - escalating to sales team"
                    )
                
                # Conversational scheduling flow
                response_text, should_escalate, escalation_reason = await self._handle_conversational_scheduling(message, scheduling_info)
                confidence = 0.95
            
            # Get current available slots for metadata
            meeting_type_for_metadata = scheduling_info.get('meeting_type', 'demo') if 'scheduling_info' in locals() else 'demo'
            available_slots = await calendar_service.get_available_slots(days_ahead=7, meeting_type=meeting_type_for_metadata, max_slots=3)
            
            return self.format_response(
                response_text=response_text,
                confidence_score=confidence,
                sources=["Google Calendar Integration", "Demo Scheduling System", "Natural Language Time Parser"],
                should_escalate=should_escalate,
                escalation_reason=escalation_reason,
                metadata={
                    "agent_type": "demo_scheduler",
                    "scheduling_info": scheduling_info if 'scheduling_info' in locals() else {},
                    "available_slots": len(available_slots),
                    "calendar_integration": "google_calendar",
                    "time_parsing_enabled": True,
                    "response_enhancement": "smart_hybrid",
                    "llm_enhanced": len(response_text) > len(locals().get('base_response', response_text)),
                    "meeting_type_detection": True,
                    "parsed_preferences": {
                        "urgency": scheduling_info.get('urgency') if 'scheduling_info' in locals() else None,
                        "preferred_time": scheduling_info.get('preferred_time') if 'scheduling_info' in locals() else None,
                        "timezone": scheduling_info.get('timezone') if 'scheduling_info' in locals() else None,
                        "flexibility": scheduling_info.get('flexibility') if 'scheduling_info' in locals() else None,
                        "meeting_type": scheduling_info.get('meeting_type') if 'scheduling_info' in locals() else None,
                        "meeting_name": scheduling_info.get('meeting_config').name if 'scheduling_info' in locals() and scheduling_info.get('meeting_config') else None
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"Error in demo scheduler: {e}")
            return self.format_response(
                response_text="I encountered an issue while checking our calendar. Let me connect you with our sales team to schedule your demo.",
                confidence_score=0.3,
                should_escalate=True,
                escalation_reason=f"Demo scheduler error: {str(e)}"
            )
    
    def _extract_scheduling_preferences(self, message: SupportMessage) -> Dict[str, Any]:
        """Extract scheduling preferences from the message using natural language parsing."""
        content_lower = message.content.lower()
        
        # Use time parser for intelligent time extraction
        parsed_time = time_parser.parse_time_expression(message.content)
        
        # Detect meeting type using the centralized manager
        detected_meeting_type = meeting_type_manager.detect_meeting_type(message.content)
        meeting_config = meeting_type_manager.get_meeting_type(detected_meeting_type)
        
        preferences = {
            "urgency": parsed_time.get('urgency', 'normal'),
            "preferred_time": parsed_time.get('time_preference'),
            "timezone": parsed_time.get('timezone'),
            "meeting_type": detected_meeting_type,
            "meeting_config": meeting_config,
            "duration": f"{meeting_config.duration_minutes} minutes" if meeting_config else "30 minutes",
            "demo_type": "standard",  # Keep for backward compatibility
            "preferred_datetime": parsed_time.get('preferred_datetime'),
            "date_range": parsed_time.get('date_range'),
            "flexibility": parsed_time.get('flexibility', 'flexible'),
            "parsed_time_data": parsed_time  # Store full parsed data for slot ranking
        }
        
        # Legacy demo type detection for backward compatibility
        if any(word in content_lower for word in ['technical', 'integration', 'api']):
            preferences["demo_type"] = "technical"
        elif any(word in content_lower for word in ['compliance', 'security', 'audit']):
            preferences["demo_type"] = "compliance"
        
        logger.info(f"Extracted scheduling preferences: {preferences}")
        logger.info(f"Detected meeting type: {detected_meeting_type}")
        return preferences
    
    def _extract_slot_selection(self, message: SupportMessage) -> Optional[Dict[str, Any]]:
        """Extract slot selection from user response."""
        content_lower = message.content.lower()
        
        # Patterns to detect slot selection
        selection_patterns = [
            (r'option\s*(\d+)', 'option'),
            (r'slot\s*(\d+)', 'slot'), 
            (r'choice\s*(\d+)', 'choice'),
            (r'number\s*(\d+)', 'number'),
            (r'book\s*(\d+)', 'book'),
            (r'select\s*(\d+)', 'select'),
            (r'pick\s*(\d+)', 'pick'),
            (r'choose\s*(\d+)', 'choose'),
            (r'^(\d+)$', 'number_only'),  # Just a number like "2"
            (r'^(\d+)\s*$', 'number_only')  # Number with spaces
        ]
        
        # Check for numbered selections
        for pattern, selection_type in selection_patterns:
            match = re.search(pattern, content_lower)
            if match:
                slot_number = int(match.group(1))
                return {
                    'type': 'numbered_selection',
                    'slot_number': slot_number,
                    'selection_type': selection_type,
                    'confidence': 0.9
                }
        
        # Check for day-based selections
        day_patterns = [
            r'yes.*(?:to\s+)?(monday|tuesday|wednesday|thursday|friday)',
            r'book.*(?:the\s+)?(monday|tuesday|wednesday|thursday|friday)',
            r'(?:i.*want|take|pick).*(?:the\s+)?(monday|tuesday|wednesday|thursday|friday)'
        ]
        
        for pattern in day_patterns:
            match = re.search(pattern, content_lower)
            if match:
                day_name = match.group(1)
                return {
                    'type': 'day_selection',
                    'day_name': day_name,
                    'confidence': 0.8
                }
        
        # Check for confirmatory responses - ONLY respond to explicit confirmations
        # DO NOT match initial booking requests like "How can I book a demo?"
        confirmatory_patterns = [
            r'^yes$', r'^sure$', r'^ok$', r'^okay$',  # Only exact words
            r'sounds?\s+good$', r'perfect$',  # Only at end of message
            r'that.*works$', r'book.*it$', r'confirm$',  # Only at end
            r'let\'s.*do.*it$', r'go.*ahead$'  # Only at end
        ]
        
        # NEVER treat questions as confirmations
        if '?' in content_lower:
            return None
        
        # NEVER treat "how can i" or "how do i" as confirmations  
        if any(phrase in content_lower for phrase in ['how can i', 'how do i', 'how to']):
            return None
        
        for pattern in confirmatory_patterns:
            if re.search(pattern, content_lower):
                return {
                    'type': 'confirmation',
                    'confidence': 0.7
                }
        
        return None
    
    async def _handle_conversational_scheduling(self, message: SupportMessage, scheduling_info: Dict[str, Any]) -> tuple[str, bool, str]:
        """Handle scheduling with proper conversational flow - show slots first, then book."""
        content_lower = message.content.lower()
        
        # Check if user is asking for a specific day
        day_preference = self._extract_day_preference(content_lower)
        
        if day_preference:
            # User specified a day - check availability for that day
            return await self._handle_day_specific_request(day_preference, scheduling_info)
        
        # Check if this is an initial scheduling request
        if any(word in content_lower for word in ['schedule', 'book', 'demo', 'meeting']):
            # Show available slots first instead of asking for day preference
            return await self._show_available_slots(scheduling_info)
        
        # Default fallback
        return "I'd be happy to help schedule a demo! What day works best for you this week?", False, ""
    
    def _extract_day_preference(self, content_lower: str) -> Optional[str]:
        """Extract day preference from user message."""
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        for day in days:
            if day in content_lower:
                return day
        return None
    
    async def _show_available_slots(self, scheduling_info: Dict[str, Any]) -> tuple[str, bool, str]:
        """Show available time slots to user first before booking."""
        try:
            # Get available slots
            meeting_type = scheduling_info.get('meeting_type', 'demo')
            available_slots = await calendar_service.get_available_slots(
                days_ahead=7, 
                meeting_type=meeting_type, 
                max_slots=5
            )
            
            if not available_slots:
                response = (
                    "I'd love to schedule a demo for you! Unfortunately, our calendar is quite busy this week. "
                    "Let me connect you with our sales team who can find alternative times or check for cancellations."
                )
                return response, True, "No available slots - escalating to sales team"
            
            # Build response showing available slots
            meeting_config = scheduling_info.get('meeting_config')
            meeting_name = meeting_config.name if meeting_config else 'demo'
            
            response = f"I'd be happy to help schedule your {meeting_name}! 📅\n\n"
            response += "Here are our available time slots:\n\n"
            
            # Show top 3-4 slots
            for i, slot in enumerate(available_slots[:4], 1):
                # Format time nicely
                time_str = slot.start_time.strftime('%A, %B %d at %I:%M %p')
                end_time = slot.start_time + timedelta(minutes=slot.duration_minutes)
                end_str = end_time.strftime('%I:%M %p %Z')
                response += f"{i}. {time_str} - {end_str}\n"
            
            response += "\n💡 **To book your demo:**\n"
            response += "Simply reply with the option number (e.g., \"1\", \"Option 2\", or \"Book slot 3\")\n\n"
            response += "Which time works best for you?"
            
            return response, False, ""
            
        except Exception as e:
            logger.error(f"Error showing available slots: {e}")
            return (
                "I'd love to schedule a demo for you! I'm having trouble accessing our calendar right now. "
                "Let me connect you with our sales team who can schedule your demo immediately."
            ), True, f"Calendar error: {str(e)}"

    async def _initiate_day_selection(self) -> str:
        """Start the conversational flow by asking for day preference."""
        return (
            "I'd be happy to help schedule your demo! 📅\n\n"
            "What day works best for you this week? For example:\n"
            "• Monday\n"
            "• Tuesday\n" 
            "• Wednesday\n"
            "• Thursday\n"
            "• Friday\n\n"
            "Just let me know your preference and I'll check availability!"
        )
    
    async def _handle_day_specific_request(self, preferred_day: str, scheduling_info: Dict[str, Any]) -> tuple[str, bool, str]:
        """Handle request for a specific day."""
        try:
            # Get slots for the specific day
            available_slots = await self._get_slots_for_day(preferred_day, scheduling_info.get('meeting_type', 'demo'))
            
            if available_slots:
                response = f"Great choice! I have these time slots available on {preferred_day.title()}:\n\n"
                for i, slot in enumerate(available_slots[:5], 1):
                    time_str = slot.start_time.strftime('%I:%M %p')
                    response += f"{i}. {time_str} - {(slot.start_time + timedelta(minutes=slot.duration_minutes)).strftime('%I:%M %p')} EST\n"
                
                response += f"\nWhich time works best for you? Just reply with the number (e.g., '2') or the time (e.g., '{available_slots[0].start_time.strftime('%I:%M %p')}')."
                return response, False, ""
            else:
                # No slots available - find next available day
                return await self._suggest_alternative_days(preferred_day, scheduling_info)
                
        except Exception as e:
            logger.error(f"Error handling day-specific request: {e}")
            return (
                f"I'd love to schedule something for {preferred_day.title()}, but I'm having trouble checking our calendar right now. "
                "Let me connect you with our sales team who can find the perfect time for you!"
            ), True, "Calendar error during day-specific scheduling"
    
    async def _get_slots_for_day(self, day_name: str, meeting_type: str = 'demo') -> List[Any]:
        """Get available slots for a specific day."""
        # Get all slots for the week
        all_slots = await calendar_service.get_available_slots(
            days_ahead=7, 
            meeting_type=meeting_type, 
            max_slots=50  # Get more slots to filter by day
        )
        
        # Filter slots for the specific day
        day_slots = []
        for slot in all_slots:
            if slot.start_time.strftime('%A').lower() == day_name.lower():
                day_slots.append(slot)
        
        return day_slots
    
    async def _suggest_alternative_days(self, requested_day: str, scheduling_info: Dict[str, Any]) -> tuple[str, bool, str]:
        """Suggest alternative days when requested day is unavailable."""
        try:
            # Get slots for the next few days
            all_slots = await calendar_service.get_available_slots(
                days_ahead=10, 
                meeting_type=scheduling_info.get('meeting_type', 'demo'), 
                max_slots=20
            )
            
            if not all_slots:
                return (
                    f"I don't see any available slots for {requested_day.title()} or the rest of this week. "
                    "Let me connect you with our sales team to find a time that works!"
                ), True, "No available slots in calendar"
            
            # Group slots by day
            days_with_slots = {}
            for slot in all_slots:
                day = slot.start_time.strftime('%A')
                if day not in days_with_slots:
                    days_with_slots[day] = []
                days_with_slots[day].append(slot)
            
            # Remove the requested day if it has no slots
            if requested_day.title() in days_with_slots and not days_with_slots[requested_day.title()]:
                del days_with_slots[requested_day.title()]
            
            if days_with_slots:
                response = f"I don't have any available slots on {requested_day.title()}, but I do have availability on:\n\n"
                for day, slots in list(days_with_slots.items())[:3]:  # Show up to 3 alternative days
                    response += f"**{day}**: {len(slots)} slots available\n"
                
                response += f"\nWhich day would you prefer instead? I can show you the specific times once you choose!"
                return response, False, ""
            else:
                return (
                    f"Unfortunately, {requested_day.title()} and the next few days are fully booked. "
                    "Let me connect you with our sales team to find a time that works for you!"
                ), True, "Calendar fully booked"
                
        except Exception as e:
            logger.error(f"Error suggesting alternative days: {e}")
            return (
                f"I'm having trouble checking availability for {requested_day.title()}. "
                "Let me connect you with our sales team to schedule your demo!"
            ), True, "Calendar error during alternative day suggestion"
    
    async def _enhance_response_with_llm(self, base_response: str, user_message: str, context: Dict[str, Any]) -> str:
        """
        Enhance hardcoded response with LLM for more natural conversation.
        Keeps calendar data safe while improving conversational flow.
        """
        try:
            # Only enhance if we detect conversational elements that could benefit
            user_content_lower = user_message.lower()
            needs_enhancement = any([
                len(user_message.split()) > 10,  # Complex user message
                any(word in user_content_lower for word in ['excited', 'looking forward', 'thanks', 'appreciate']),
                context.get('demo_type') in ['technical', 'compliance'],  # Specialized demos
                context.get('urgency') == 'high',  # Urgent requests
                'timezone' in context and context['timezone']  # Cross-timezone scheduling
            ])
            
            if not needs_enhancement:
                return base_response
            
            enhancement_prompt = f"""
            You are Delve's AI scheduling assistant. A user just made a demo scheduling request.
            
            User's message: "{user_message}"
            
            Context:
            - Demo type: {context.get('demo_type', 'standard')}
            - Urgency: {context.get('urgency', 'normal')}
            - Timezone: {context.get('timezone', 'EST')}
            - Time preference: {context.get('preferred_time', 'flexible')}
            
            I have a base response with accurate calendar data. Please enhance ONLY the conversational introduction and closing while preserving all calendar information exactly as provided.
            
            Base response to enhance:
            {base_response}
            
            Enhancement guidelines:
            1. Keep ALL calendar slot information EXACTLY as provided - do not modify times, dates, or booking instructions
            2. Add a more personalized, conversational opening that acknowledges their specific needs
            3. Add a warm, professional closing that builds excitement for the demo
            4. Maintain Delve's professional but friendly tone
            5. Keep the response concise and actionable
            6. Do NOT hallucinate any calendar information
            
            Enhanced response:
            """
            
            # Use OpenAI directly for enhancement
            client = openai.OpenAI(api_key=settings.openai_api_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are Delve's AI scheduling assistant. You enhance responses while preserving all calendar data exactly as provided."},
                    {"role": "user", "content": enhancement_prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )
            enhanced = response.choices[0].message.content
            
            # Fallback to base response if enhancement fails
            if not enhanced or len(enhanced.strip()) == 0:
                logger.warning("LLM enhancement returned empty response, using base response")
                return base_response
            
            # Basic safety check - ensure calendar data is preserved
            if "Option 1" in base_response and "Option 1" not in enhanced:
                logger.warning("LLM enhancement removed calendar options, using base response")
                return base_response
                
            return enhanced.strip()
            
        except Exception as e:
            logger.warning(f"Failed to enhance response with LLM: {e}, using base response")
            return base_response
    
    async def _handle_slot_booking(self, message: SupportMessage, slot_selection: Dict[str, Any]) -> tuple[str, bool, str]:
        """Handle actual slot booking when user makes a selection."""
        try:
            # Get available slots to match against user selection (use session context if available)
            # TODO: In a real implementation, we'd store the meeting type from the previous interaction
            available_slots = await calendar_service.get_available_slots(
                days_ahead=7, 
                meeting_type="demo",  # Default to demo for now 
                max_slots=10
            )
            
            if not available_slots:
                response = (
                    "I apologize, but it looks like our calendar has become unavailable since we last checked. "
                    "Let me connect you with our sales team to schedule your demo."
                )
                return response, True, "No available slots during booking attempt"
            
            selected_slot = None
            selection_type = slot_selection.get('type')
            
            if selection_type == 'numbered_selection':
                slot_number = slot_selection.get('slot_number', 1)
                if 1 <= slot_number <= len(available_slots):
                    selected_slot = available_slots[slot_number - 1]
                    logger.info(f"User selected slot {slot_number}: {selected_slot}")
                else:
                    return (
                        f"I don't see option {slot_number} in our available slots. "
                        f"Please choose from options 1-{min(3, len(available_slots))} or let me know if you'd like to see more options.",
                        False, ""
                    )
            
            elif selection_type == 'day_selection':
                day_name = slot_selection.get('day_name', '').lower()
                # Find first slot matching the day
                for slot in available_slots:
                    if day_name in slot.start_time.strftime('%A').lower():
                        selected_slot = slot
                        logger.info(f"User selected {day_name}: {selected_slot}")
                        break
                
                if not selected_slot:
                    return (
                        f"I don't see any available slots for {day_name.title()} in our current calendar. "
                        "Would you like to see all available options or try a different day?",
                        False, ""
                    )
            
            elif selection_type == 'confirmation':
                # Use the first available slot for generic confirmations
                selected_slot = available_slots[0]
                logger.info(f"User confirmed, using first slot: {selected_slot}")
            
            if not selected_slot:
                return (
                    "I'm not sure which time slot you'd like to book. Could you please specify which option (1, 2, 3) "
                    "or let me know which day works best for you?",
                    False, ""
                )
            
            # Create the meeting
            user_email = getattr(message, 'user_email', None) or "no-email@example.com"
            user_name = getattr(message, 'user_name', None) or "Demo Attendee"
            
            booking_result = await self.create_demo_meeting(
                slot_choice=available_slots.index(selected_slot) + 1,
                user_email=user_email,
                user_name=user_name
            )
            
            if booking_result.get('success'):
                # Format time with user's timezone if available
                user_timezone = getattr(message, 'parsed_preferences', {}).get('timezone')
                if user_timezone and user_timezone != 'America/New_York':
                    formatted_time = time_parser.format_dual_timezone(selected_slot.start_time, user_timezone)
                else:
                    formatted_time = str(selected_slot)
                
                response = (
                    f"🎉 Perfect! I've successfully booked your demo for {formatted_time}.\n\n"
                    f"✅ **Confirmation Details:**\n"
                    f"• **When:** {formatted_time}\n"
                    f"• **Duration:** 30 minutes\n"
                    f"• **Type:** Product Demo\n"
                    f"• **Attendee:** {user_name} ({user_email})\n\n"
                    f"📧 You should receive a calendar invite shortly with the meeting link and agenda.\n\n"
                    f"🚀 **What to expect:**\n"
                    f"• Platform overview and key features\n"
                    f"• Discussion of your specific use case\n"
                    f"• Q&A session\n"
                    f"• Next steps for implementation\n\n"
                    f"If you need to reschedule or have any questions before the demo, just let me know!"
                )
                
                # Send Slack notification about the booking
                try:
                    from src.integrations.slack_client import slack_client
                    
                    meeting_details = {
                        'title': f"Delve Product Demo - {user_name}",
                        'start_time': formatted_time,
                        'duration_minutes': selected_slot.duration_minutes,
                        'meeting_type': 'demo',
                        'customer_name': user_name,
                        'customer_email': user_email,
                        'event_id': booking_result.get('event_id'),
                        'calendar_link': booking_result.get('event_link')
                    }
                    
                    await slack_client.send_meeting_notification(
                        meeting_details=meeting_details,
                        notification_type="booked"
                    )
                    
                    logger.info(f"Sent meeting booking notification to Slack for {user_email}")
                    
                except Exception as e:
                    logger.warning(f"Failed to send Slack meeting notification: {e}")
                    # Continue anyway - booking was successful
                
                # No escalation needed - booking successful
                return response, False, ""
            
            else:
                error_msg = booking_result.get('error', 'Unknown error')
                logger.error(f"Failed to create meeting: {error_msg}")
                response = (
                    f"I encountered an issue while booking your demo for {selected_slot}. "
                    "Let me connect you with our sales team who can complete the booking for you immediately."
                )
                return response, True, f"Meeting creation failed: {error_msg}"
                
        except Exception as e:
            logger.error(f"Error in slot booking: {e}")
            response = (
                "I encountered an issue while booking your demo. "
                "Let me connect you with our sales team to complete the booking."
            )
            return response, True, f"Slot booking error: {str(e)}"
    
    async def _handle_demo_scheduling(self, message: SupportMessage, scheduling_info: Dict[str, Any]) -> tuple[str, bool, str]:
        """Handle demo scheduling with real calendar integration and intelligent slot ranking."""
        try:
            # Get available slots from real calendar using detected meeting type
            meeting_type = scheduling_info.get('meeting_type', 'demo')
            available_slots = await calendar_service.get_available_slots(
                days_ahead=7, 
                meeting_type=meeting_type, 
                max_slots=10  # Get more slots for better ranking
            )
            
            if not available_slots:
                response = (
                    "I'd love to schedule a demo for you! Unfortunately, our calendar is quite busy this week. "
                    "Let me connect you with our sales team who can find alternative times or check for "
                    "cancellations that might work for you."
                )
                return response, True, "No available slots - escalating to sales team"
            
            # Use time parser to rank slots based on preferences
            parsed_time_data = scheduling_info.get('parsed_time_data', {})
            if parsed_time_data:
                logger.info(f"Ranking slots based on parsed preferences: {parsed_time_data}")
                ranked_slots = time_parser.suggest_time_slots(parsed_time_data, available_slots)
                if ranked_slots:
                    available_slots = ranked_slots
            
            urgency = scheduling_info.get('urgency', 'normal')
            meeting_type = scheduling_info.get('meeting_type', 'demo')
            meeting_config = scheduling_info.get('meeting_config')
            demo_type = scheduling_info.get('demo_type', 'standard')  # For backward compatibility
            preferred_time = scheduling_info.get('preferred_time')
            timezone = scheduling_info.get('timezone')
            flexibility = scheduling_info.get('flexibility', 'flexible')
            
            # Get meeting type name for display
            meeting_name = meeting_config.name if meeting_config else "Product Demo"
            meeting_duration = meeting_config.duration_minutes if meeting_config else 30
            
            # Build personalized response based on preferences and meeting type
            if urgency == 'high':
                response = f"🚀 I understand you need a {meeting_name.lower()} quickly! Great news - I found these available slots:\n\n"
            elif preferred_time:
                response = f"📅 Perfect! I see you prefer {preferred_time} meetings. Here are the best matching slots for your {meeting_name.lower()}:\n\n"
            elif timezone:
                response = f"📅 I found these {meeting_name.lower()} slots that work well for {timezone} timezone:\n\n"
            else:
                response = f"📅 I'd be happy to help schedule your {meeting_name.lower()}! Here are our available time slots:\n\n"
            
            # Add top 3 ranked slots with preference indicators and timezone conversion
            user_timezone = scheduling_info.get('timezone')
            
            for i, slot in enumerate(available_slots[:3], 1):
                # Format time with dual timezone if user has different timezone
                if user_timezone and user_timezone != 'America/New_York':
                    slot_time = time_parser.format_dual_timezone(slot.start_time, user_timezone)
                    duration_text = f" ({slot.duration_minutes} min)"
                else:
                    slot_time = str(slot)
                    duration_text = ""
                
                slot_info = f"{i}. {slot_time}{duration_text}"
                
                # Add preference match indicators
                if preferred_time and preferred_time in ['morning', 'afternoon', 'evening']:
                    slot_hour = slot.start_time.hour
                    if preferred_time == 'morning' and 9 <= slot_hour <= 12:
                        slot_info += " ✨ (Perfect for morning preference!)"
                    elif preferred_time == 'afternoon' and 13 <= slot_hour <= 17:
                        slot_info += " ✨ (Perfect for afternoon preference!)"
                    elif preferred_time == 'evening' and 17 <= slot_hour <= 20:
                        slot_info += " ✨ (Perfect for evening preference!)"
                
                if urgency == 'high' and i == 1:
                    slot_info += " ⚡ (Earliest available)"
                
                response += f"{slot_info}\n"
            
            # Add demo type specific information
            if demo_type == "technical":
                response += (
                    "\n🔧 Since you're interested in technical aspects, I'll ensure our technical team "
                    "joins to cover integrations, APIs, and implementation details."
                )
            elif demo_type == "compliance":
                response += (
                    "\n🛡️ Since you're interested in compliance features, I'll ensure our compliance "
                    "expert joins to cover SOC2, ISO27001, GDPR, and HIPAA capabilities."
                )
            
            # Add flexibility-based messaging
            if flexibility == 'strict':
                response += (
                    "\n\nI understand you need a specific time. If none of these work exactly, "
                    "let me connect you with our team to find the perfect slot."
                )
            elif flexibility == 'very_flexible':
                response += (
                    f"\n\nI have {len(available_slots)} total slots available this week. "
                    "These are the top recommendations, but I can show you more options if needed!"
                )
            else:
                response += (
                    "\n\n💡 **To book your demo:**\n"
                    "Simply reply with the option number (e.g., \"Option 1\", \"2\", or \"Book slot 3\")\n"
                    "or tell me the day (e.g., \"Yes to Tuesday\" or \"I'll take Friday\")\n\n"
                    "I'll create the meeting instantly and send you a calendar invite! 📅"
                )
            
            # Don't escalate - we can handle the booking ourselves
            return response, False, ""
            
        except Exception as e:
            logger.error(f"Error getting calendar slots: {e}")
            response = (
                "I'd love to schedule a demo for you! I'm having trouble accessing our calendar right now. "
                "Let me connect you with our sales team who can schedule your demo immediately."
            )
            return response, True, f"Calendar error: {str(e)}"
    
    async def _generate_demo_info_with_slots(self) -> str:
        """Generate a response for general demo inquiries with available slots."""
        try:
            # Get available slots
            available_slots = await calendar_service.get_available_slots(
                days_ahead=7, 
                meeting_type="demo", 
                max_slots=3
            )
            
            response = (
                "🎯 I'd love to show you how Delve can streamline your compliance process! "
                "\n\nOur demos typically cover:"
                "\n• 🚀 How to go from zero to SOC2 compliant in 4-7 days"
                "\n• 🤖 AI-powered compliance automation"
                "\n• 📊 Real-time audit preparation"
                "\n• 🔗 Seamless integrations with your existing tech stack"
                "\n• 💡 Personalized implementation strategy"
                "\n\nDemo sessions are 30 minutes and can be customized based on your specific needs."
            )
            
            if available_slots:
                response += "\n\n📅 I have these time slots available this week:"
                for i, slot in enumerate(available_slots, 1):
                    # Basic timezone formatting for general info (no user timezone detected yet)
                    response += f"\n{i}. {slot}"
                response += "\n\nWould you like to book one of these slots, or do you prefer a different time?"
                response += "\n\n💡 **Tip:** If you're in a different timezone, just let me know (e.g., 'I'm in PST') and I'll show times in your timezone too!"
            else:
                response += "\n\nOur calendar is quite busy this week, but I can connect you with our sales team to find a time that works perfectly for you!"
            
            return response
            
        except Exception as e:
            logger.error(f"Error getting slots for demo info: {e}")
            return (
                "🎯 I'd love to show you how Delve can streamline your compliance process! "
                "\n\nOur demos typically cover:"
                "\n• 🚀 How to go from zero to SOC2 compliant in 4-7 days"
                "\n• 🤖 AI-powered compliance automation"
                "\n• 📊 Real-time audit preparation"
                "\n• 🔗 Seamless integrations with your existing tech stack"
                "\n• 💡 Personalized implementation strategy"
                "\n\nDemo sessions are usually 30 minutes and can be customized based on your specific needs. "
                "Would you like me to connect you with our sales team to schedule a time that works for you?"
            )
    
    async def create_demo_meeting(self, slot_choice: int, user_email: str, user_name: str = "Demo Attendee") -> Dict[str, Any]:
        """Create a real demo meeting in the calendar."""
        try:
            # Get available slots
            available_slots = await calendar_service.get_available_slots(
                days_ahead=7, 
                meeting_type="demo", 
                max_slots=5
            )
            
            if not available_slots or slot_choice < 1 or slot_choice > len(available_slots):
                return {
                    "success": False,
                    "error": "Invalid slot selection or no slots available"
                }
            
            selected_slot = available_slots[slot_choice - 1]
            
            # Create meeting request
            meeting_request = MeetingRequest(
                title=f"Delve Product Demo - {user_name}",
                description=(
                    "Product demonstration call to showcase Delve's AI-native compliance automation platform.\n\n"
                    "Agenda:\n"
                    "• Platform overview\n"
                    "• Use case discussion\n"
                    "• Q&A session\n"
                    "• Next steps\n\n"
                    "Join URL will be provided before the meeting."
                ),
                start_time=selected_slot.start_time,
                duration_minutes=selected_slot.duration_minutes,
                attendee_emails=[user_email],
                meeting_type="demo"
            )
            
            # Create the meeting
            meeting_response = await calendar_service.create_meeting(meeting_request)
            
            return {
                "success": meeting_response.success,
                "event_id": meeting_response.event_id,
                "event_link": meeting_response.event_link,
                "error": meeting_response.error_message,
                "calendar_invite_sent": meeting_response.calendar_invite_sent,
                "slot_info": str(selected_slot)
            }
            
        except Exception as e:
            logger.error(f"Error creating demo meeting: {e}")
            return {
                "success": False,
                "error": f"Failed to create meeting: {str(e)}"
            }
    
    async def health_check(self) -> bool:
        """Check if demo scheduler is healthy."""
        try:
            # Check if calendar service is available
            if not calendar_service.is_available():
                logger.warning("Calendar service not available during health check")
                return False
            
            # Try to get available slots
            available_slots = await calendar_service.get_available_slots(
                days_ahead=7, 
                meeting_type="demo", 
                max_slots=1
            )
            
            logger.info(f"Demo scheduler health check: Calendar available, found {len(available_slots)} slots")
            return True
            
        except Exception as e:
            logger.error(f"Demo scheduler health check failed: {e}")
            return False