📅 Calendar Integration Architecture Plan

  Based on your Google Calendar token and the current multi-agent system, here's my comprehensive plan:

  🎯 Goals:

  1. Real calendar integration - Actually book meetings, not just escalate
  2. Smart scheduling - Find available slots automatically
  3. Multiple meeting types - Demos, support calls, sales meetings
  4. Timezone handling - Support global customers
  5. Conflict detection - Avoid double-booking

  🏗️ Architecture Design:

  1. Calendar Service Layer (src/integrations/calendar_service.py)

  class GoogleCalendarService:
      def __init__(self, credentials_path: str)
      async def get_available_slots(self, date_range: DateRange, duration: int) -> List[TimeSlot]
      async def create_meeting(self, meeting_details: MeetingRequest) -> MeetingResponse
      async def check_availability(self, start_time: datetime, duration: int) -> bool
      async def get_calendar_events(self, date_range: DateRange) -> List[CalendarEvent]
      async def cancel_meeting(self, event_id: str) -> bool
      async def update_meeting(self, event_id: str, updates: Dict) -> bool

  2. Enhanced Demo Scheduler Agent (src/agents/demo_scheduler.py)

  Current State: Basic demo detection + escalation
  New Capabilities:
  - Parse scheduling requests (time, date, timezone)
  - Find available slots in real calendar
  - Create actual calendar events
  - Send calendar invites
  - Handle rescheduling requests

  3. Meeting Types & Templates

  MEETING_TYPES = {
      "demo": {
          "duration": 30,  # minutes
          "title_template": "Delve Product Demo - {company_name}",
          "description_template": "...",
          "attendees": ["sales@delve.ai"],
          "calendar_id": "primary"
      },
      "technical_support": {
          "duration": 60,
          "title_template": "Technical Support Call - {issue_type}",
          "attendees": ["support@delve.ai"],
      },
      "sales_call": {
          "duration": 45,
          "title_template": "Sales Discussion - {company_name}",
          "attendees": ["sales@delve.ai"],
      }
  }

  4. Smart Time Parsing (src/utils/time_parser.py)

  Handle natural language like:
  - "next week"
  - "tomorrow at 2pm PST"
  - "sometime this Friday"
  - "Monday morning"

  5. Enhanced User Flow:

  Current Flow:
  User: "Can we schedule a demo for next week?"
  → Demo Scheduler Agent detects request
  → Escalates to sales team

  New Flow:
  User: "Can we schedule a demo for next week?"
  → Demo Scheduler Agent detects request
  → Parses "next week" → finds available slots
  → "I found these available times for your demo:
     • Monday, Jan 8 at 2:00 PM EST
     • Tuesday, Jan 9 at 10:00 AM EST
     • Wednesday, Jan 10 at 3:00 PM EST
     Which works best for you?"
  → User selects time
  → Creates calendar event automatically
  → Sends confirmation with calendar invite

  🛠️ Implementation Phases:

  Phase 1: Core Calendar Integration (High Priority)

  1. Calendar Service Setup
    - Google Calendar API client
    - Authentication with your token
    - Basic CRUD operations (create, read, update, delete events)
  2. Time Slot Management
    - Find available slots algorithm
    - Timezone conversion utilities
    - Business hours configuration
  3. Enhanced Demo Scheduler
    - Integrate calendar service
    - Replace escalation with actual booking
    - Add slot finding logic

  Phase 2: Smart Parsing & UX (Medium Priority)

  1. Natural Language Time Parsing
    - "next week" → specific date ranges
    - "2pm PST" → timezone conversion
    - "Friday morning" → business hours slots
  2. Interactive Scheduling
    - Present multiple time options
    - Handle user selection
    - Confirmation workflow
  3. Multiple Meeting Types
    - Demo scheduling (30 min)
    - Technical support calls (60 min)
    - Sales calls (45 min)

  Phase 3: Advanced Features (Lower Priority)

  1. Rescheduling Support
    - "Can we move our Tuesday demo to Wednesday?"
    - Automatic conflict detection
    - Update existing events
  2. Calendar Sync
    - Check organizer availability
    - Block conflicting times
    - Buffer time between meetings
  3. Email Integration
    - Send calendar invites
    - Meeting reminders
    - Follow-up emails

  🔧 Technical Implementation Details:

  Dependencies Needed:

  pip install google-api-python-client google-auth google-auth-oauthlib
  pip install python-dateutil pytz

  Key Components:

  1. Calendar Client Setup:
  from google.oauth2.credentials import Credentials
  from googleapiclient.discovery import build

  creds = Credentials.from_authorized_user_file('calendar_token.json')
  service = build('calendar', 'v3', credentials=creds)

  2. Available Slots Algorithm:
  async def find_available_slots(self, date_range, duration):
      # Get existing events in range
      # Filter by business hours (9 AM - 6 PM)  
      # Find gaps >= duration
      # Return list of available TimeSlots

  3. Enhanced Agent Response:
  if intent.get('is_demo_request'):
      available_slots = await self.calendar_service.get_available_slots(...)
      if available_slots:
          return self.format_scheduling_response(available_slots)
      else:
          return self.format_no_availability_response()

  🎯 Success Metrics:

  - Booking Success Rate: % of demo requests that result in calendar events
  - User Experience: Reduce "I'll have someone contact you" responses
  - Automation Rate: % of scheduling handled without human intervention
  - Response Time: Keep under 5 seconds for slot finding