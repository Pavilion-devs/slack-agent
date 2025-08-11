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
from src.utils.message_origin import MessageOriginDetector
from src.core.session_manager import SessionManager
from src.core.config import settings
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize components for message origin detection
message_detector = MessageOriginDetector()

# Initialize session manager with error handling
session_manager = None
try:
    if settings.supabase_url and settings.supabase_key:
        session_manager = SessionManager(
            supabase_url=settings.supabase_url,
            supabase_key=settings.supabase_key
        )
        logger.info("Session manager initialized successfully")
    else:
        logger.warning("Supabase credentials not found - session management disabled")
except Exception as e:
    logger.error(f"Failed to initialize session manager: {e}")
    session_manager = None

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
                # Process message asynchronously using Thread (Flask is sync)
                Thread(target=lambda: asyncio.run(process_slack_message(event))).start()
        
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
    """Process Slack message through the workflow with origin detection."""
    try:
        # Detect message origin (human agent vs customer vs unknown)
        if session_manager:
            origin_type, origin_info = await message_detector.detect_message_origin(event, session_manager)
        else:
            origin_type, origin_info = "unknown", None
            logger.warning("Session manager not available - treating as unknown message origin")
        
        logger.info(f"Message origin: {origin_type} from user {event.get('user')}")
        
        # Handle human agent messages (route to customer platform)
        if origin_type == "human_agent" and origin_info:
            logger.info(f"Processing human agent message for session {origin_info['session_id']}")
            
            # Route human agent message to Chainlit (bidirectional flow)
            await route_human_message_to_chainlit(origin_info)
            return
        
        # Handle regular messages (unknown users, non-escalated conversations)
        if origin_type == "unknown":
            # ADDITIONAL CHECK: Verify this user isn't a human agent before processing through AI
            user_id = event.get('user')
            is_human_agent = False
            
            if session_manager and user_id:
                # Check if this user is assigned to any sessions
                assigned_sessions = await session_manager.get_sessions_by_state("assigned")
                for session in assigned_sessions:
                    if session.assigned_to == user_id:
                        is_human_agent = True
                        logger.info(f"🚫 BLOCKING AI processing - user {user_id} is assigned human agent for session {session.session_id}")
                        
                        # Route this as human agent message even though origin detection failed
                        agent_info = {
                            'session_id': session.session_id,
                            'agent_id': user_id,
                            'agent_name': session.assigned_agent_name or 'Human Agent',
                            'customer_channel': session.channel_id,
                            'message_text': event.get('text', ''),
                            'timestamp': datetime.now().isoformat()
                        }
                        await route_human_message_to_chainlit(agent_info)
                        return
            
            if not is_human_agent:
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

async def route_human_message_to_chainlit(agent_info: dict):
    """Route human agent message to Chainlit interface."""
    try:
        logger.info(f"Routing human agent message to Chainlit for session {agent_info['session_id']}")
        
        # Add message to session history
        message_data = {
            'sender': 'human_agent',
            'sender_name': agent_info['agent_name'],
            'content': agent_info['message_text'],
            'timestamp': agent_info['timestamp'],
            'platform': 'slack'
        }
        
        if session_manager:
            await session_manager.add_message_to_session(agent_info['session_id'], message_data)
        else:
            logger.warning("Session manager not available - cannot store message")
        
        # Notify active Chainlit sessions about new human message
        await notify_chainlit_new_message(agent_info['session_id'], message_data)
        logger.info(f"Human agent message added to session history: {agent_info['session_id']}")
        
    except Exception as e:
        logger.error(f"Error routing human message to Chainlit: {e}")

async def notify_chainlit_new_message(session_id: str, message_data: dict):
    """Notify Chainlit interface about new human agent message."""
    try:
        import json
        import os
        from datetime import datetime
        
        # Create notifications directory if it doesn't exist
        notifications_dir = "/tmp/chainlit_notifications"
        os.makedirs(notifications_dir, exist_ok=True)
        
        # Create notification file for this message
        notification = {
            'type': 'human_message',
            'session_id': session_id,
            'message': message_data,
            'timestamp': datetime.now().isoformat()
        }
        
        # Write notification to file (Chainlit will poll for these)
        notification_file = f"{notifications_dir}/{session_id}_{datetime.now().timestamp()}.json"
        with open(notification_file, 'w') as f:
            json.dump(notification, f)
            
        logger.info(f"Created notification file for session {session_id}: {notification_file}")
        
    except Exception as e:
        logger.error(f"Error creating Chainlit notification: {e}")

async def notify_chainlit_session_closed(session_id: str):
    """Notify Chainlit interface that a session has been closed."""
    try:
        logger.info(f"Notifying Chainlit that session {session_id} has been closed")
        
        # Add closure notification to session history
        closure_message = {
            'sender': 'system',
            'content': 'This conversation has been closed by our support team. Thank you for contacting us!',
            'timestamp': datetime.now().isoformat(),
            'platform': 'system',
            'message_type': 'session_closure'
        }
        
        if session_manager:
            await session_manager.add_message_to_session(session_id, closure_message)
        else:
            logger.warning("Session manager not available - cannot add closure message")
        
        # TODO: Implement real-time notification to active Chainlit sessions
        # This would show the closure message and disable the input
        logger.info(f"Session closure notification added for session: {session_id}")
        
    except Exception as e:
        logger.error(f"Error notifying Chainlit of session closure: {e}")

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
                    # Extract session info and assign human agent
                    user_info = interaction_data.get('user', {})
                    agent_id = user_info.get('id')
                    agent_name = user_info.get('username', 'Human Agent')
                    
                    # Extract session_id from the message or metadata
                    session_id = None
                    if 'message' in interaction_data and 'blocks' in interaction_data['message']:
                        # Look for session_id in message metadata
                        for block in interaction_data['message']['blocks']:
                            if block.get('type') == 'section' and 'fields' in block:
                                for field in block['fields']:
                                    text = field.get('text', '')
                                    logger.info(f"DEBUG: Processing field text: '{text}'")
                                    if 'Session ID:' in text:
                                        # More robust parsing
                                        session_part = text.split('Session ID:')[1].strip()
                                        logger.info(f"DEBUG: Session part after split: '{session_part}'")
                                        # Extract UUID pattern (8-4-4-4-12 characters)
                                        import re
                                        uuid_match = re.search(r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})', session_part)
                                        if uuid_match:
                                            session_id = uuid_match.group(1)
                                            logger.info(f"DEBUG: Extracted session_id: '{session_id}'")
                                        else:
                                            logger.warning(f"DEBUG: No UUID found in session part: '{session_part}'")
                                    if session_id:
                                        break
                            if session_id:
                                break
                    
                    if session_id and agent_id and session_manager:
                        # Assign human agent and disable AI
                        success = await session_manager.assign_human_agent(session_id, agent_id, agent_name)
                        if success:
                            logger.info(f"Human agent {agent_name} assigned to session {session_id}")
                    elif not session_manager:
                        logger.warning("Session manager not available - cannot assign human agent")
                    
                    # Continue with existing handler
                    await responder_setup.thread_manager.handle_accept_ticket(
                        noop_ack, interaction_data, slack_client_instance
                    )
                elif action_id in ["view_history", "view_context"]:
                    await responder_setup.thread_manager.handle_view_history(
                        noop_ack, interaction_data, slack_client_instance
                    )
                elif action_id == "close_ticket":
                    # Handle ticket closure with session management
                    user_info = interaction_data.get('user', {})
                    agent_id = user_info.get('id')
                    
                    # Extract session_id from the message
                    session_id = None
                    if 'message' in interaction_data and 'blocks' in interaction_data['message']:
                        for block in interaction_data['message']['blocks']:
                            if block.get('type') == 'section' and 'fields' in block:
                                for field in block['fields']:
                                    text = field.get('text', '')
                                    logger.info(f"DEBUG: Processing close ticket field text: '{text}'")
                                    if 'Session ID:' in text:
                                        # More robust parsing
                                        session_part = text.split('Session ID:')[1].strip()
                                        logger.info(f"DEBUG: Close ticket session part: '{session_part}'")
                                        # Extract UUID pattern
                                        import re
                                        uuid_match = re.search(r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})', session_part)
                                        if uuid_match:
                                            session_id = uuid_match.group(1)
                                            logger.info(f"DEBUG: Close ticket extracted session_id: '{session_id}'")
                                        else:
                                            logger.warning(f"DEBUG: Close ticket no UUID found: '{session_part}'")
                                    if session_id:
                                        break
                            if session_id:
                                break
                    
                    if session_id and agent_id and session_manager:
                        # Close the session
                        success = await session_manager.close_session(session_id, agent_id)
                        if success:
                            logger.info(f"Session {session_id} closed by agent {agent_id}")
                            
                            # TODO: Notify Chainlit interface that conversation has ended
                            await notify_chainlit_session_closed(session_id)
                    elif not session_manager:
                        logger.warning("Session manager not available - cannot close session")
                    
                    # Continue with existing handler
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