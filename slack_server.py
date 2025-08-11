#!/usr/bin/env python3
"""
Slack Event Handler Server
Runs alongside Chainlit to handle Slack webhooks via ngrok
"""

import asyncio
import logging
from flask import Flask, request, jsonify
import json
from threading import Thread
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.integrations.slack_client import slack_client
from src.models.schemas import SupportMessage
from src.workflows.delve_langgraph_workflow import delve_langgraph_workflow
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/slack/events', methods=['POST'])
def slack_events():
    """Handle Slack Events API webhooks."""
    try:
        data = request.get_json()
        
        # Handle URL verification challenge
        if data.get('type') == 'url_verification':
            return jsonify({'challenge': data.get('challenge')})
        
        # Handle actual events
        if data.get('type') == 'event_callback':
            event = data.get('event', {})
            
            # Skip bot messages and handle user messages
            if event.get('type') == 'message' and not event.get('bot_id'):
                # Process message asynchronously
                asyncio.create_task(process_slack_message(event))
        
        return jsonify({'status': 'ok'})
        
    except Exception as e:
        logger.error(f"Error handling Slack event: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/slack/interactions', methods=['POST'])
@app.route('/slack/interactive', methods=['POST'])  # Add both singular and plural
def slack_interactions():
    """Handle Slack Interactive Components (button clicks)."""
    try:
        # IMPORTANT: Respond immediately within 3 seconds (Slack requirement)
        response = jsonify({'status': 'ok'})
        
        # Parse payload from Slack
        payload = request.form.get('payload')
        if payload:
            data = json.loads(payload)
            logger.info(f"Received Slack interaction: {data.get('type')}")
            
            # Handle button interactions asynchronously AFTER responding
            if data.get('type') == 'block_actions':
                # Start async processing but don't wait
                Thread(target=lambda: asyncio.run(process_slack_interaction(data))).start()
        
        return response
        
    except Exception as e:
        logger.error(f"Error handling Slack interaction: {e}")
        # Still return 200 OK even on error to prevent user-facing error messages
        return jsonify({'error': 'Processing error, but acknowledged'}), 200

async def process_slack_message(event):
    """Process Slack message through the workflow."""
    try:
        # Create SupportMessage from Slack event
        support_message = SupportMessage(
            message_id=event['ts'],
            channel_id=event['channel'],
            user_id=event['user'],
            timestamp=datetime.fromtimestamp(float(event['ts'])),
            content=event['text'],
            thread_ts=event.get('thread_ts'),
            user_name=f"slack_user_{event['user'][:8]}",  # Will be enriched
            user_email=None  # Will be enriched from Slack API
        )
        
        # Process through workflow
        logger.info(f"Processing Slack message: {support_message.content[:50]}...")
        
        # This will automatically handle escalation through ResponderAgent
        result = await delve_langgraph_workflow.process_message(support_message)
        
        logger.info(f"Slack message processed successfully")
        
    except Exception as e:
        logger.error(f"Error processing Slack message: {e}")

async def process_slack_interaction(interaction_data):
    """Process Slack button interactions."""
    try:
        logger.info(f"Processing Slack interaction: {interaction_data.get('type')}")
        
        # Extract action info
        actions = interaction_data.get('actions', [])
        if actions:
            action = actions[0]
            action_id = action.get('action_id')
            
            logger.info(f"Button clicked: {action_id}")
            
            # Import here to avoid circular imports
            from src.setup_responder_system import ResponderSystemSetup
            
            # Initialize responder system if not already done
            responder_setup = ResponderSystemSetup()
            success = await responder_setup.initialize_system()
            
            if success and responder_setup.thread_manager:
                # Create async ack function
                async def noop_ack():
                    return None
                
                # Create mock Slack client from the interaction data
                from slack_sdk.web.async_client import AsyncWebClient
                from src.core.config import settings
                slack_client_instance = AsyncWebClient(token=settings.slack_bot_token)
                
                # Route to appropriate handler based on action_id
                if action_id in ["accept_ticket", "take_ownership"]:
                    await responder_setup.thread_manager.handle_accept_ticket(
                        noop_ack, interaction_data, slack_client_instance
                    )
                elif action_id in ["view_history", "view_context"]:
                    await responder_setup.thread_manager.handle_view_history(
                        noop_ack, interaction_data, slack_client_instance
                    )
                elif action_id == "close_ticket":
                    await responder_setup.thread_manager.handle_close_ticket(
                        noop_ack, interaction_data, slack_client_instance
                    )
                else:
                    logger.warning(f"Unknown action_id: {action_id}")
            else:
                logger.error("Responder system not available for button handling")
            
        logger.info("Slack interaction processed")
        
    except Exception as e:
        logger.error(f"Error processing Slack interaction: {e}")

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'slack_enabled': slack_client.enabled,
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    print("🚀 Starting Slack Event Handler Server...")
    print(f"📡 Make sure your ngrok is forwarding to http://localhost:8001")
    print(f"🔗 Configure Slack app with these URLs:")
    print(f"   - Events: https://YOUR_NGROK_URL/slack/events")
    print(f"   - Interactions: https://YOUR_NGROK_URL/slack/interactions")
    
    app.run(host='0.0.0.0', port=8001, debug=True)