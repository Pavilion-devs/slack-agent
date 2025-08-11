#!/usr/bin/env python3
"""
Test Slack Interactive Button Endpoints
Tests the exact issue you're experiencing with 405 Method Not Allowed
"""

import requests
import json
import sys
import time

def test_slack_endpoints():
    """Test the Slack endpoints to diagnose the 405 issue."""
    
    # Your ngrok URL (update if different)
    base_url = "https://5052d2ce08cf.ngrok-free.app"
    
    print("🧪 Testing Slack Interactive Endpoints")
    print(f"📡 Base URL: {base_url}")
    print("-" * 50)
    
    # Test endpoints to check
    endpoints = [
        "/slack/events",
        "/slack/interactive", 
        "/slack/interactions",
        "/health"
    ]
    
    # Test GET requests first (should work for health, fail for others)
    print("1️⃣ Testing GET requests:")
    for endpoint in endpoints:
        url = f"{base_url}{endpoint}"
        try:
            response = requests.get(url, timeout=5)
            print(f"   GET {endpoint}: {response.status_code} {response.reason}")
        except Exception as e:
            print(f"   GET {endpoint}: ERROR - {e}")
    
    print("\n2️⃣ Testing POST requests:")
    
    # Test POST to /slack/interactive (what Slack is trying to do)
    test_payload = {
        "payload": json.dumps({
            "type": "block_actions",
            "user": {"id": "U123456", "name": "test_user"},
            "actions": [{
                "action_id": "accept_ticket",
                "value": "test_session_id"
            }],
            "message": {"ts": "1234567890.123"},
            "channel": {"id": "C123456"}
        })
    }
    
    for endpoint in ["/slack/interactive", "/slack/interactions"]:
        url = f"{base_url}{endpoint}"
        try:
            response = requests.post(
                url, 
                data=test_payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=5
            )
            print(f"   POST {endpoint}: {response.status_code} {response.reason}")
            if response.status_code == 200:
                print(f"      ✅ Response: {response.json()}")
            else:
                print(f"      ❌ Error: {response.text[:100]}")
        except Exception as e:
            print(f"   POST {endpoint}: ERROR - {e}")
    
    print("\n3️⃣ Testing server status:")
    try:
        health_response = requests.get(f"{base_url}/health", timeout=5)
        if health_response.status_code == 200:
            health_data = health_response.json()
            print(f"   ✅ Server is running: {health_data}")
        else:
            print(f"   ❌ Health check failed: {health_response.status_code}")
    except Exception as e:
        print(f"   ❌ Cannot reach server: {e}")
    
    print("\n4️⃣ Recommendations:")
    print("   - Check if slack_server.py is running")
    print("   - Check if ngrok is forwarding to port 8000") 
    print("   - Check Flask app routes are registered correctly")
    print("   - Check for any Flask app errors in the console")

def test_route_registration():
    """Test if our Flask routes are registered correctly."""
    print("\n🔍 Testing Route Registration:")
    
    # This simulates what our Flask app should have
    from flask import Flask
    
    app = Flask(__name__)
    
    @app.route('/slack/interactions', methods=['POST'])
    @app.route('/slack/interactive', methods=['POST'])  
    def test_interactive():
        return {"status": "ok"}
    
    @app.route('/health', methods=['GET'])
    def test_health():
        return {"status": "healthy"}
    
    # Check registered routes
    print("   📋 Registered routes:")
    for rule in app.url_map.iter_rules():
        methods = ','.join(rule.methods - {'HEAD', 'OPTIONS'})
        print(f"      {rule.rule} -> {methods}")
    
    return app

if __name__ == "__main__":
    print("🚀 Slack Interactive Button Diagnostics")
    print("=" * 50)
    
    # Test route registration locally
    test_route_registration()
    
    print("\n")
    
    # Test actual endpoints
    test_slack_endpoints()
    
    print("\n💡 Next steps if tests fail:")
    print("   1. Make sure slack_server.py is running on port 8000")
    print("   2. Make sure ngrok is forwarding to localhost:8000") 
    print("   3. Check Flask console for any startup errors")
    print("   4. Try manually testing: curl -X POST https://5052d2ce08cf.ngrok-free.app/slack/interactive")