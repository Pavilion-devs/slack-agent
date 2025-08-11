#!/usr/bin/env python3
"""
Debug Slack Server - Minimal version to test the 405 issue
"""

import logging
from flask import Flask, request, jsonify
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    logger.info("Health check requested")
    return jsonify({
        'status': 'healthy',
        'routes': [str(rule) for rule in app.url_map.iter_rules()],
        'message': 'Debug Slack server is running'
    })

@app.route('/slack/events', methods=['POST'])
def slack_events():
    """Handle Slack Events API webhooks."""
    logger.info("Slack events endpoint called")
    try:
        data = request.get_json()
        
        # Handle URL verification challenge
        if data and data.get('type') == 'url_verification':
            challenge = data.get('challenge')
            logger.info(f"URL verification challenge: {challenge}")
            return jsonify({'challenge': challenge})
        
        logger.info(f"Event received: {data}")
        return jsonify({'status': 'ok'})
        
    except Exception as e:
        logger.error(f"Error handling Slack event: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/slack/interactions', methods=['POST'])
@app.route('/slack/interactive', methods=['POST'])
def slack_interactions():
    """Handle Slack Interactive Components (button clicks)."""
    logger.info(f"Slack interactive endpoint called: {request.endpoint}")
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request path: {request.path}")
    
    try:
        # Log the raw request
        logger.info(f"Content-Type: {request.content_type}")
        logger.info(f"Form data keys: {list(request.form.keys())}")
        
        # Parse payload from Slack
        payload = request.form.get('payload')
        if payload:
            try:
                data = json.loads(payload)
                logger.info(f"Received Slack interaction: {data.get('type')}")
                logger.info(f"Action ID: {data.get('actions', [{}])[0].get('action_id', 'unknown')}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON payload: {e}")
        else:
            logger.warning("No payload found in form data")
        
        # Always return success immediately 
        return jsonify({'status': 'ok', 'message': 'Interaction received'})
        
    except Exception as e:
        logger.error(f"Error handling Slack interaction: {e}")
        return jsonify({'error': 'Processing error', 'message': str(e)}), 200

# Add a catch-all route to debug any routing issues
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def catch_all(path):
    logger.info(f"Catch-all route called: {request.method} /{path}")
    
    if path.startswith('slack/'):
        return jsonify({
            'error': 'Slack endpoint not found',
            'requested_path': f'/{path}',
            'method': request.method,
            'available_endpoints': [
                'GET /health',
                'POST /slack/events', 
                'POST /slack/interactive',
                'POST /slack/interactions'
            ]
        }), 404
    
    return jsonify({'message': f'Debug server - you called {request.method} /{path}'}), 200

if __name__ == '__main__':
    print("🚀 Starting DEBUG Slack Server...")
    print("📋 Registered routes:")
    
    # Wait for Flask to register routes, then print them
    with app.app_context():
        for rule in app.url_map.iter_rules():
            methods = ','.join(rule.methods - {'HEAD', 'OPTIONS'})
            print(f"   {rule.rule} -> {methods}")
    
    print(f"🔗 Test URLs:")
    print(f"   Health: GET http://localhost:8000/health")
    print(f"   Interactive: POST http://localhost:8000/slack/interactive") 
    print(f"   ngrok: Use your ngrok URL instead of localhost")
    
    # Start the server
    app.run(host='0.0.0.0', port=8000, debug=True)