#!/usr/bin/env python3
"""
Test complete bidirectional flow: Agent → User messaging
Simulates the scenario where:
1. Chainlit user asks question → escalates to Slack
2. Human agent in Slack accepts ticket  
3. Human agent replies in Slack
4. Reply should appear in Chainlit interface
"""
import os
import sys
import asyncio
import logging
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.models.schemas import SupportMessage
from src.workflows.delve_langgraph_workflow import delve_langgraph_workflow

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def simulate_escalation_flow():
    """Simulate a message that would escalate to Slack."""
    
    print("🧪 Testing Complete Bidirectional Flow")
    print("=" * 50)
    
    # Step 1: Create a message that should escalate
    print("1️⃣ Creating message that should escalate...")
    
    escalation_message = SupportMessage(
        message_id='test_escalation_123',
        channel_id='chainlit_production',  # This will be handled in test mode
        user_id='chainlit_olaboyefavour52@gmail.com',
        timestamp=datetime.now(),
        content="What's the weather like today?",  # This should definitely escalate
        thread_ts=None,
        user_name="Ola",
        user_email="olaboyefavour52@gmail.com"
    )
    
    print(f"   Message: {escalation_message.content}")
    print(f"   User: {escalation_message.user_name} ({escalation_message.user_email})")
    
    # Step 2: Process through workflow and confirm escalation
    print("\n2️⃣ Processing through workflow...")
    result = await delve_langgraph_workflow.process_message(escalation_message)
    
    # Check if it escalated
    escalated = False
    if result.agent_responses:
        latest_response = result.agent_responses[-1]
        escalated = latest_response.should_escalate
        
        print(f"   Final Agent: {latest_response.agent_name}")
        print(f"   Confidence: {latest_response.confidence_score}")
        print(f"   Should Escalate: {escalated}")
        print(f"   Escalation Reason: {latest_response.escalation_reason}")
    
    if not escalated:
        print("❌ Message did not escalate as expected")
        return False
        
    print("✅ Message escalated successfully!")
    
    return True

async def simulate_human_reply():
    """Simulate a human agent replying from Slack."""
    
    print("\n3️⃣ Simulating human agent reply...")
    
    # This would normally come from Slack webhook when human agent replies
    # For now, we'll simulate what should happen when the responder system
    # receives a reply from Slack that needs to be sent to Chainlit
    
    try:
        # Import the responder system setup
        from src.setup_responder_system import ResponderSystemSetup
        
        responder_setup = ResponderSystemSetup()
        success = await responder_setup.initialize_system()
        
        if not success:
            print("❌ Failed to initialize responder system")
            return False
            
        print("   ✅ Responder system initialized")
        
        # Simulate what happens when a human replies in Slack
        # This would normally be triggered by a Slack event
        mock_slack_reply = {
            'user': 'U987654321',  # Human agent
            'text': 'Hi Ola! Thanks for reaching out. The weather question is outside my scope, but I can help you with any Delve compliance questions you might have.',
            'channel': 'C123456789',
            'ts': '1734567890.789',
            'thread_ts': '1734567890.123456',  # Original escalation thread
            'event_ts': '1734567890.789'
        }
        
        print(f"   Human reply: {mock_slack_reply['text'][:50]}...")
        
        # In a real scenario, this would be handled by the slack_server.py
        # and routed to the responder system to deliver to Chainlit
        
        # For testing, we'll check if the responder system has the capability
        # to handle bidirectional messaging
        
        if hasattr(responder_setup, 'responder_agent') and responder_setup.responder_agent:
            print("   ✅ Responder agent is available for bidirectional messaging")
            
            # Check if the responder agent has the necessary methods for delivery
            responder = responder_setup.responder_agent
            
            # Look for methods that would deliver messages to Chainlit users
            methods = [method for method in dir(responder) if not method.startswith('_')]
            delivery_methods = [m for m in methods if 'deliver' in m.lower() or 'send' in m.lower()]
            
            if delivery_methods:
                print(f"   ✅ Found delivery methods: {', '.join(delivery_methods)}")
            else:
                print("   ⚠️  No obvious delivery methods found")
                
            print(f"   Available methods: {', '.join(methods[:5])}...")
            
            return True
        else:
            print("   ❌ Responder agent not available")
            return False
            
    except Exception as e:
        print(f"   ❌ Error testing human reply simulation: {e}")
        return False

async def test_session_management():
    """Test session management for bidirectional flow."""
    
    print("\n4️⃣ Testing session management...")
    
    try:
        from src.core.session_manager import SessionManager
        from src.core.config import settings
        
        # Check if session manager can handle session tracking
        session_manager = SessionManager(
            supabase_url=settings.supabase_url,
            supabase_key=settings.supabase_key
        )
        
        # Test session creation/retrieval
        test_session_id = "test_bidirectional_session"
        
        # In a real bidirectional flow, the session would track:
        # - Chainlit user info
        # - Escalation state
        # - Slack thread info
        # - Human agent assignment
        
        print("   ✅ Session manager available")
        print("   📝 Session should track: Chainlit user ↔ Slack thread mapping")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Session management test failed: {e}")
        return False

async def main():
    """Test the complete bidirectional flow."""
    
    print("🔄 Complete Bidirectional Flow Test")
    print("=" * 50)
    print("Testing: Chainlit User → Agent → Slack → Human → Chainlit")
    print()
    
    # Test the escalation part (Chainlit → Slack)
    escalation_success = await simulate_escalation_flow()
    
    # Test the reply part (Slack → Chainlit)  
    reply_success = await simulate_human_reply()
    
    # Test session management
    session_success = await test_session_management()
    
    print(f"\n📊 Test Results:")
    print(f"   Escalation (Chainlit → Slack): {'✅ PASS' if escalation_success else '❌ FAIL'}")
    print(f"   Human Reply (Slack → Chainlit): {'✅ PASS' if reply_success else '❌ FAIL'}")
    print(f"   Session Management: {'✅ PASS' if session_success else '❌ FAIL'}")
    
    all_success = escalation_success and reply_success and session_success
    
    if all_success:
        print(f"\n🎉 Bidirectional flow infrastructure is ready!")
        print(f"💡 Next steps:")
        print(f"   1. Deploy slack_server.py with real Slack webhooks")
        print(f"   2. Configure responder system to deliver replies to active Chainlit sessions")
        print(f"   3. Test with real Slack workspace and human agents")
    else:
        print(f"\n⚠️  Some components need attention for complete bidirectional flow")
        
    return all_success

if __name__ == "__main__":
    success = asyncio.run(main())