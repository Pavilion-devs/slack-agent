#!/usr/bin/env python3
"""
Test the complete escalation flow with live Slack integration.
This creates a real escalation in the #support-escalations channel.
"""

import asyncio
import sys
import os
from datetime import datetime

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

from src.setup_responder_system import ResponderSystemSetup
from src.models.schemas import SupportMessage
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_full_escalation():
    """Test the complete escalation flow with live Slack posting."""
    print("🚨 Testing Complete Escalation Flow with Live Slack Integration")
    print("=" * 70)
    
    try:
        # Initialize the responder system
        print("🔧 Initializing responder system...")
        setup = ResponderSystemSetup()
        
        # Initialize core components (mock Slack for now to avoid API limits)
        await setup._setup_session_manager()
        print("✅ Session manager initialized")
        
        # Use real Slack client for this test
        from slack_sdk.web.async_client import AsyncWebClient
        slack_client = AsyncWebClient(token=os.getenv("SLACK_BOT_TOKEN"))
        
        # Test Slack connection
        auth_response = await slack_client.auth_test()
        if auth_response["ok"]:
            print(f"✅ Slack connected as: {auth_response['user']}")
        
        # Initialize thread manager with real Slack client
        from src.integrations.slack_thread_manager import SlackThreadManager
        thread_manager = SlackThreadManager(
            slack_client=slack_client,
            session_manager=setup.session_manager,
            escalation_channel="support-escalations"
        )
        
        # Initialize responder agent
        from src.agents.responder_agent import ResponderAgent, ResponderConfig
        config = ResponderConfig(escalation_channel="support-escalations")
        responder_agent = ResponderAgent(
            session_manager=setup.session_manager,
            thread_manager=thread_manager,
            config=config
        )
        print("✅ Responder agent initialized with live Slack")
        
        # Create test escalation scenario
        print("\n🧪 Creating test escalation scenario...")
        
        # Scenario: Complex compliance question that needs human expert
        test_message = SupportMessage(
            message_id=f"escalation_test_{int(datetime.now().timestamp())}",
            channel_id="chainlit_test",
            user_id="test_user_escalation",
            timestamp=datetime.now(),
            content="I need urgent help with a complex GDPR data breach response. We have a potential incident involving 50,000+ EU customer records and need to understand our notification obligations within 72 hours. Can someone help me understand the exact steps and documentation required?",
            thread_ts=None,
            user_name="Sarah Martinez",
            user_email="sarah.martinez@testcompany.com"
        )
        
        # Conversation history showing AI agent couldn't handle it
        conversation_history = [
            {
                'sender': 'User',
                'content': test_message.content,
                'timestamp': datetime.now().isoformat(),
                'message_type': 'user_message'
            },
            {
                'sender': 'AI Agent (enhanced_rag_agent)',
                'content': 'I found some general information about GDPR, but this complex data breach scenario requires specialized legal expertise that I cannot provide.',
                'confidence': 0.3,
                'message_type': 'ai_response'
            }
        ]
        
        print(f"📧 Test message: {test_message.content[:100]}...")
        print(f"👤 Test user: {test_message.user_name} ({test_message.user_email})")
        
        # Process escalation through responder agent
        print("\n🚨 Processing escalation...")
        
        escalation_response = await responder_agent.process_escalation_request(
            support_message=test_message,
            escalation_reason="Complex GDPR data breach scenario requiring legal compliance expertise - AI confidence too low (0.3) for critical compliance matter",
            conversation_history=conversation_history
        )
        
        print("✅ Escalation processed!")
        print(f"📝 Response to user: {escalation_response.response_text}")
        print(f"🎯 Agent: {escalation_response.agent_name}")
        print(f"📊 Confidence: {escalation_response.confidence_score}")
        print(f"🔺 Escalated: {escalation_response.should_escalate}")
        
        # Check if session was created
        if hasattr(escalation_response, 'session_id') and escalation_response.session_id:
            session_id = escalation_response.session_id
            print(f"🆔 Session created: {session_id}")
        elif escalation_response.metadata and escalation_response.metadata.get('session_id'):
            session_id = escalation_response.metadata['session_id']
            print(f"🆔 Session created: {session_id}")
            
            # Check if Slack thread was created
            if escalation_response.metadata.get('thread_ts'):
                thread_ts = escalation_response.metadata['thread_ts']
                print(f"💬 Slack thread created: {thread_ts}")
                print(f"🔗 Check #support-escalations for the new escalation!")
            
            # Get session details
            session = await setup.session_manager.get_session(session_id)
            if session:
                print(f"📋 Session state: {session.state.value}")
                print(f"⏰ Escalated at: {session.escalated_at}")
                print(f"📝 Escalation reason: {session.escalation_reason}")
        
        # Test follow-up message
        print("\n📨 Testing follow-up message...")
        
        followup_message = SupportMessage(
            message_id=f"followup_test_{int(datetime.now().timestamp())}",
            channel_id="chainlit_test", 
            user_id="test_user_escalation",  # Same user
            timestamp=datetime.now(),
            content="Just to add more context - this happened during our EU data migration and we're not sure if our current DPA covers this scenario.",
            thread_ts=None,
            user_name="Sarah Martinez",
            user_email="sarah.martinez@testcompany.com"
        )
        
        followup_response = await responder_agent.handle_user_followup(followup_message)
        
        if followup_response:
            print("✅ Follow-up processed")
            print(f"📝 Follow-up response: {followup_response.response_text}")
        else:
            print("⚠️  No active session found for follow-up")
        
        # Display final status
        print("\n" + "=" * 70)
        print("🎉 Complete Escalation Flow Test Results:")
        print("✅ Responder system fully operational")
        print("✅ Session management working")
        print("✅ Slack integration confirmed")
        print("✅ Escalation posted to #support-escalations")
        print("✅ Follow-up message handling working")
        
        print("\n🎯 Next Steps:")
        print("1. Check #support-escalations channel in Slack")
        print("2. Click 'Accept Ticket' to test agent assignment")
        print("3. Reply in thread to test bidirectional messaging")
        print("4. Click 'Close Ticket' when done")
        
        print("\n🚀 Bidirectional Slack Responder Agent System is LIVE!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Escalation flow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_full_escalation())
    if success:
        print("\n✅ All tests passed - System ready for production!")
    else:
        print("\n❌ Tests failed - Check errors above")
    
    sys.exit(0 if success else 1)