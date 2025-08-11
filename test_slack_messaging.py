#!/usr/bin/env python3
"""
Test Slack messaging permissions and bot functionality.
"""

import asyncio
import os
from dotenv import load_dotenv
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError

load_dotenv()

async def test_slack_bot():
    """Test Slack bot permissions and messaging."""
    print("🤖 Testing Slack Bot Permissions")
    print("=" * 40)
    
    token = os.getenv("SLACK_BOT_TOKEN")
    if not token:
        print("❌ No SLACK_BOT_TOKEN found in .env")
        return False
    
    client = AsyncWebClient(token=token)
    
    try:
        # Test 1: Bot authentication
        print("🔐 Testing bot authentication...")
        auth_response = await client.auth_test()
        
        if auth_response["ok"]:
            print(f"✅ Bot authenticated as: {auth_response['user']}")
            print(f"📱 Team: {auth_response['team']}")
            print(f"🆔 User ID: {auth_response['user_id']}")
        else:
            print(f"❌ Auth failed: {auth_response.get('error')}")
            return False
        
        # Test 2: List channels
        print("\n📋 Testing channel access...")
        try:
            channels_response = await client.conversations_list(
                exclude_archived=True,
                types="public_channel,private_channel"
            )
            
            if channels_response["ok"]:
                channels = channels_response["channels"]
                print(f"✅ Found {len(channels)} accessible channels")
                
                # Look for support-escalations channel
                support_channel = None
                for channel in channels:
                    if channel["name"] == "support-escalations":
                        support_channel = channel
                        break
                
                if support_channel:
                    print(f"✅ Found #support-escalations channel")
                    print(f"   ID: {support_channel['id']}")
                    print(f"   Is Member: {support_channel.get('is_member', False)}")
                else:
                    print("⚠️  #support-escalations channel not found")
                    print("Available channels:")
                    for channel in channels[:5]:  # Show first 5
                        print(f"   - #{channel['name']} (ID: {channel['id']})")
            
        except SlackApiError as e:
            print(f"⚠️  Channel list error: {e.response['error']}")
        
        # Test 3: Try to send a test message
        print("\n💬 Testing message sending...")
        try:
            test_channel = "support-escalations"  # or use a test channel
            
            # Try to send a simple message
            response = await client.chat_postMessage(
                channel=f"#{test_channel}",
                text="🧪 Test message from Delve Support AI Agent - responder system is working!",
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "🤖 *Responder Agent System Test*\n\nThis is a test message to verify the bidirectional Slack integration is working correctly.\n\n✅ Bot can send messages\n✅ Channel access confirmed\n✅ Ready for escalations"
                        }
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "Test Button"
                                },
                                "style": "primary",
                                "action_id": "test_button",
                                "value": "test_value"
                            }
                        ]
                    }
                ]
            )
            
            if response["ok"]:
                print(f"✅ Test message sent successfully!")
                print(f"📧 Message TS: {response['ts']}")
                
                # Try to add a reaction
                try:
                    await client.reactions_add(
                        channel=response["channel"],
                        timestamp=response["ts"],
                        name="white_check_mark"
                    )
                    print("✅ Reaction added successfully!")
                except:
                    print("⚠️  Could not add reaction (might need reactions:write scope)")
                
            else:
                print(f"❌ Message sending failed: {response.get('error')}")
                
        except SlackApiError as e:
            error_msg = e.response['error']
            print(f"❌ Message sending error: {error_msg}")
            
            if error_msg == "missing_scope":
                print("💡 Fix: Add 'chat:write' scope to your bot")
            elif error_msg == "not_in_channel":
                print("💡 Fix: Invite bot to #support-escalations channel")
            elif error_msg == "channel_not_found":
                print("💡 Fix: Create #support-escalations channel or use existing channel")
        
        # Test 4: Bot permissions summary
        print("\n📊 Bot Permissions Summary:")
        scopes = auth_response.get("response_metadata", {}).get("scopes", [])
        if scopes:
            print("Current scopes:")
            for scope in scopes:
                print(f"   ✅ {scope}")
        
        print("\n🔧 Required scopes for responder system:")
        required_scopes = [
            "chat:write", "chat:write.public", "channels:read",
            "users:read", "reactions:write", "files:write"
        ]
        for scope in required_scopes:
            status = "✅" if scope in scopes else "❌"
            print(f"   {status} {scope}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_slack_bot())