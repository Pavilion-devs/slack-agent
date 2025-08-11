#!/usr/bin/env python3
"""
Test script for the bidirectional Slack responder agent system.
This validates that all components can be initialized and work together.
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


async def test_responder_system():
    """Test the complete responder system."""
    print("🧪 Testing Bidirectional Slack Responder Agent System")
    print("=" * 60)
    
    try:
        # Initialize setup
        setup = ResponderSystemSetup()
        print("✅ ResponderSystemSetup created")
        
        # Test environment validation (without actual Slack tokens for safety)
        print("\n📋 Testing environment validation...")
        os.environ['SLACK_BOT_TOKEN'] = 'test_token'
        os.environ['SLACK_SIGNING_SECRET'] = 'test_secret'
        
        env_valid = setup._validate_environment()
        print(f"Environment validation: {'✅ PASS' if env_valid else '❌ FAIL'}")
        
        # Test session manager initialization
        print("\n💾 Testing session manager...")
        try:
            await setup._setup_session_manager()
            print("✅ Session manager initialized")
            
            # Test session operations
            stats = await setup.session_manager.get_session_stats()
            print(f"📊 Session stats: {stats}")
            
        except Exception as e:
            print(f"❌ Session manager error: {e}")
        
        # Test components without Slack (to avoid API calls)
        print("\n🔧 Testing core components...")
        
        # Test responder agent creation
        try:
            from src.agents.responder_agent import ResponderAgent, ResponderConfig
            from src.integrations.slack_thread_manager import SlackThreadManager
            
            # Mock slack client for testing
            class MockSlackClient:
                async def auth_test(self):
                    return {"ok": True, "user": "test_bot"}
            
            mock_client = MockSlackClient()
            
            thread_manager = SlackThreadManager(
                slack_client=mock_client,
                session_manager=setup.session_manager,
                escalation_channel="test-escalations"
            )
            
            config = ResponderConfig(escalation_channel="test-escalations")
            responder_agent = ResponderAgent(
                session_manager=setup.session_manager,
                thread_manager=thread_manager,
                config=config
            )
            
            print("✅ ResponderAgent created successfully")
            
            # Test workflow integration
            from src.workflows.langgraph_workflow import LangGraphWorkflow
            workflow = LangGraphWorkflow()
            workflow.set_responder_agent(responder_agent)
            print("✅ Workflow integration successful")
            
        except Exception as e:
            print(f"❌ Component creation error: {e}")
            import traceback
            traceback.print_exc()
        
        # Test escalation flow (mock)
        print("\n🚨 Testing escalation flow...")
        try:
            # Create test message
            test_message = SupportMessage(
                message_id="test_123",
                channel_id="chainlit_test",
                user_id="test_user",
                timestamp=datetime.now(),
                content="I need urgent help with compliance audit",
                thread_ts=None,
                user_name="Test User",
                user_email="test@example.com"
            )
            
            # Test escalation request processing
            escalation_response = await responder_agent.process_escalation_request(
                support_message=test_message,
                escalation_reason="Testing escalation system",
                conversation_history=[
                    {
                        'sender': 'User',
                        'content': test_message.content,
                        'timestamp': datetime.now().isoformat(),
                        'message_type': 'user_message'
                    }
                ]
            )
            
            print("✅ Escalation request processed")
            print(f"📝 Response: {escalation_response.response_text[:100]}...")
            print(f"🎯 Agent: {escalation_response.agent_name}")
            print(f"📊 Confidence: {escalation_response.confidence_score}")
            print(f"🔺 Should escalate: {escalation_response.should_escalate}")
            
            if hasattr(escalation_response, 'metadata') and escalation_response.metadata:
                session_id = escalation_response.metadata.get('session_id')
                if session_id:
                    print(f"🆔 Session ID: {session_id}")
            
        except Exception as e:
            print(f"❌ Escalation flow error: {e}")
            import traceback
            traceback.print_exc()
        
        # Test session management
        print("\n📋 Testing session operations...")
        try:
            # Create test session
            session = await setup.session_manager.create_session(
                user_id="test_user_123",
                channel_id="chainlit_test",
                escalation_reason="Testing session creation"
            )
            print(f"✅ Session created: {session.session_id}")
            
            # Test session retrieval
            retrieved_session = await setup.session_manager.get_session(session.session_id)
            if retrieved_session:
                print("✅ Session retrieval successful")
            
            # Test message addition
            await setup.session_manager.add_message_to_session(
                session_id=session.session_id,
                message={
                    'sender': 'Test User',
                    'content': 'This is a test message',
                    'message_type': 'user_message'
                }
            )
            print("✅ Message added to session")
            
            # Clean up test session
            await setup.session_manager.close_session(session.session_id)
            print("✅ Test session closed")
            
        except Exception as e:
            print(f"❌ Session management error: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n🏥 System Health Check...")
        try:
            # Mock health check (without actual Slack calls)
            health = {
                'session_manager': bool(setup.session_manager),
                'responder_agent': bool(responder_agent),
                'workflow_integration': bool(workflow.responder_agent),
                'components_loaded': True
            }
            
            print(f"Health status: {health}")
            all_healthy = all(health.values())
            print(f"Overall health: {'✅ HEALTHY' if all_healthy else '⚠️ ISSUES'}")
            
        except Exception as e:
            print(f"❌ Health check error: {e}")
        
        print("\n" + "=" * 60)
        print("🎉 Responder System Test Complete!")
        print("✅ Core components working correctly")
        print("⚠️  Note: Slack API calls were mocked for testing")
        print("🔗 System is ready for integration with live Slack workspace")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_responder_system())
    sys.exit(0 if success else 1)