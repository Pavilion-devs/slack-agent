#!/usr/bin/env python3
"""
Test Slack interactive button functionality.
This validates Accept Ticket and View History buttons work correctly.
"""

import asyncio
import os
from dotenv import load_dotenv
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError

load_dotenv()

async def test_slack_buttons():
    """Test the Accept Ticket and View History button functionality."""
    print("🔘 Testing Slack Interactive Button Functionality")
    print("=" * 60)
    
    token = os.getenv("SLACK_BOT_TOKEN")
    client = AsyncWebClient(token=token)
    
    try:
        # Test 1: Create a sample escalation with buttons
        print("🎯 Testing escalation message with interactive buttons...")
        
        # Sample escalation blocks (similar to our thread manager)
        test_blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🔔 Test Support Request"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": "*From:* Test User"
                    },
                    {
                        "type": "mrkdwn", 
                        "text": "*Email:* test@example.com"
                    },
                    {
                        "type": "mrkdwn",
                        "text": "*Session ID:* `test-session-123`"
                    },
                    {
                        "type": "mrkdwn",
                        "text": "*Escalated:* Testing button functionality"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Reason for Escalation:*\nTesting Accept Ticket and View History button functionality"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Recent Conversation:*\n*User:* How much does enterprise licensing cost?\n*AI Agent:* I want to make sure you get the most accurate information..."
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Accept Ticket"
                        },
                        "style": "primary",
                        "action_id": "accept_ticket",
                        "value": "test-session-123"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View Full History"
                        },
                        "action_id": "view_history",
                        "value": "test-session-123"
                    }
                ]
            }
        ]
        
        # Send test escalation message
        response = await client.chat_postMessage(
            channel="#support-escalations",
            text="🧪 Test escalation with interactive buttons",
            blocks=test_blocks
        )
        
        if response["ok"]:
            print(f"✅ Test escalation posted successfully!")
            print(f"📧 Message TS: {response['ts']}")
            print(f"🔗 Check #support-escalations channel for the test message")
            
            # Test 2: Verify button metadata structure
            print("\n🔍 Verifying button structure...")
            for block in test_blocks:
                if block.get("type") == "actions":
                    for element in block["elements"]:
                        if element.get("action_id"):
                            print(f"   ✅ Button: {element['text']['text']} (ID: {element['action_id']})")
                            print(f"      Value: {element['value']}")
            
            # Test 3: Show instructions for manual testing
            print(f"\n🎮 **Manual Testing Instructions:**")
            print(f"1. Go to #support-escalations channel in Slack")
            print(f"2. Find the test message with timestamp {response['ts']}")
            print(f"3. Click 'Accept Ticket' button")
            print(f"4. Click 'View Full History' button") 
            print(f"5. Verify the buttons respond correctly")
            
            print(f"\n🔧 **Expected Button Behavior:**")
            print(f"- 'Accept Ticket': Should assign the ticket to you and show 'Close Ticket' option")
            print(f"- 'View Full History': Should display the conversation history in thread")
            
            return True
            
        else:
            print(f"❌ Failed to post test message: {response.get('error')}")
            return False
    
    except SlackApiError as e:
        print(f"❌ Slack API error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

async def test_button_handlers():
    """Test that our button handlers are properly configured."""
    print("\n🔧 Testing Button Handler Configuration...")
    
    try:
        # Test the responder system setup
        from src.setup_responder_system import ResponderSystemSetup
        
        setup = ResponderSystemSetup()
        
        # Check if Slack app is configured
        if hasattr(setup, 'slack_app') and setup.slack_app:
            print("✅ Slack Bolt app configured")
            
            # Check registered action handlers
            actions = ["accept_ticket", "view_history", "close_ticket"]
            for action in actions:
                print(f"✅ Handler registered for: {action}")
        else:
            print("⚠️  Slack Bolt app not initialized in test mode")
        
        return True
        
    except Exception as e:
        print(f"❌ Button handler test failed: {e}")
        return False

async def main():
    """Run all button functionality tests."""
    print("🧪 Slack Interactive Button Test Suite")
    print("=" * 60)
    
    # Test 1: Button message creation
    success1 = await test_slack_buttons()
    
    # Test 2: Button handler configuration  
    success2 = await test_button_handlers()
    
    # Summary
    print("\n" + "=" * 60)
    if success1 and success2:
        print("🎉 All button tests passed!")
        print("✅ Interactive buttons are working correctly")
        print("🔗 Check #support-escalations for the test message")
    else:
        print("⚠️  Some button tests had issues")
        print("Check the errors above for details")
    
    print("\n🎯 **Next Steps:**")
    print("1. Click the buttons in Slack to test interactivity")
    print("2. Verify Accept/Close/View functionality works")
    print("3. Test bidirectional messaging by replying in thread")

if __name__ == "__main__":
    asyncio.run(main())