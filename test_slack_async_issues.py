#!/usr/bin/env python3
"""
Test Slack async event loop issues that might be preventing agent→user messaging
"""
import os
import sys
import asyncio
import logging
from datetime import datetime
from threading import Thread
import json

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.models.schemas import SupportMessage
from src.workflows.delve_langgraph_workflow import delve_langgraph_workflow

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_slack_message_processing():
    """Test processing a Slack message like the slack_server.py would."""
    
    print("🧪 Testing Slack Message Processing (Async Event Loop)")
    print("=" * 60)
    
    # Simulate a Slack event like what would come from the webhook
    mock_slack_event = {
        'ts': '1734567890.123456',
        'channel': 'C1234567890',
        'user': 'U1234567890',
        'text': 'I need help with SOC 2 compliance',
        'type': 'message'
    }
    
    print(f"1️⃣ Simulating Slack event: {mock_slack_event['text']}")
    
    try:
        # Create SupportMessage from Slack event (like slack_server.py does)
        support_message = SupportMessage(
            message_id=mock_slack_event['ts'],
            channel_id=mock_slack_event['channel'],
            user_id=mock_slack_event['user'],
            timestamp=datetime.fromtimestamp(float(mock_slack_event['ts'])),
            content=mock_slack_event['text'],
            thread_ts=mock_slack_event.get('thread_ts'),
            user_name=f"slack_user_{mock_slack_event['user'][:8]}",
            user_email=None
        )
        
        print(f"2️⃣ Created SupportMessage: {support_message.message_id}")
        
        # Process through workflow (this is where async loop issues might occur)
        print("3️⃣ Processing through workflow...")
        result = await delve_langgraph_workflow.process_message(support_message)
        
        print(f"4️⃣ Workflow completed successfully!")
        print(f"   Final Response: {result.final_response[:100]}...")
        print(f"   Agent Responses: {len(result.agent_responses) if result.agent_responses else 0}")
        
        # Check if any agent responses triggered escalation
        if result.agent_responses:
            latest_response = result.agent_responses[-1]
            print(f"   Latest Agent: {latest_response.agent_name}")
            print(f"   Should Escalate: {latest_response.should_escalate}")
            
            if latest_response.should_escalate:
                print("5️⃣ Testing escalation flow...")
                # This is where the async loop error might occur when ResponderAgent tries to post to Slack
                print(f"   Escalation Reason: {latest_response.escalation_reason}")
                
        return True
        
    except Exception as e:
        print(f"❌ Error during workflow processing: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_async_loop_creation():
    """Test creating async loops in different contexts."""
    
    print(f"\n🔄 Testing Async Loop Creation")
    print("=" * 40)
    
    # Test 1: Check if we're in a running event loop
    try:
        loop = asyncio.get_running_loop()
        print(f"1️⃣ Currently in running event loop: {type(loop)}")
        
        # This might be the issue - trying to create new tasks in an existing loop
        print("2️⃣ Testing asyncio.create_task() within running loop...")
        
        async def test_task():
            await asyncio.sleep(0.1)
            return "Task completed"
        
        # This should work within an existing loop
        task = asyncio.create_task(test_task())
        result = await task
        print(f"   ✅ create_task() result: {result}")
        
    except RuntimeError as e:
        print(f"1️⃣ No running event loop: {e}")
        
        # Test creating a new event loop (this won't work in an async function)
        print("2️⃣ Cannot create new event loop within async function")

def test_thread_async_interaction():
    """Test async function calls from threads (like Flask does)."""
    
    print(f"\n🧵 Testing Thread → Async Interaction")
    print("=" * 40)
    
    # This simulates what happens in slack_server.py when Flask calls asyncio.run()
    def thread_function():
        try:
            print("1️⃣ Inside thread, calling asyncio.run()...")
            
            async def async_work():
                # Simulate the workflow processing
                await asyncio.sleep(0.1)
                return "Async work completed"
            
            result = asyncio.run(async_work())
            print(f"   ✅ Thread async result: {result}")
            return True
            
        except Exception as e:
            print(f"   ❌ Thread async error: {e}")
            return False
    
    # Start thread (like Flask would)
    thread = Thread(target=thread_function)
    thread.start()
    thread.join()
    
    print("2️⃣ Thread completed")

async def main():
    """Main test function."""
    
    print("🔬 Slack Async Loop Diagnostics")
    print("=" * 50)
    
    # Test 1: Basic async loop handling
    await test_async_loop_creation()
    
    # Test 2: Thread → async interaction
    test_thread_async_interaction()
    
    # Test 3: Actual Slack message processing
    success = await test_slack_message_processing()
    
    if success:
        print(f"\n✅ All tests passed - async event loop handling appears to be working")
    else:
        print(f"\n❌ Issues detected with async event loop handling")

if __name__ == "__main__":
    # Run the main test
    asyncio.run(main())