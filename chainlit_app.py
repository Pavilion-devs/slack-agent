"""
Chainlit Interface for Delve LangGraph Workflow Testing
Interactive UI to test the new LangGraph-based agent routing system
"""

import os
import sys
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import json

import chainlit as cl
from langchain.schema.runnable.config import RunnableConfig
from fastapi import Request
from fastapi.responses import JSONResponse
from threading import Thread
import json as json_lib

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.models.schemas import SupportMessage
from src.workflows.delve_langgraph_workflow import delve_langgraph_workflow
from src.core.intent_classifier import IntentClassifier

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test cases for quick testing
TEST_CASES = {
    "Information Queries": [
        "What is Delve?",
        "What features do you have?",
        "How does your platform work?",
        "What compliance frameworks do you support?"
    ],
    "Scheduling Requests": [
        "I want to schedule a demo",
        "Can we book a meeting?",
    ],
    "Technical Support": [
        "500 error from your API",
        "Authentication not working",
        "Webhook failing"
    ],
    "Edge Cases": [
        "How do I implement SOC2 compliance?"  # Ambiguous case
    ]
}

@cl.on_chat_start
async def on_chat_start():
    """Initialize the chat session with welcome message and test cases."""
    
    # Note: Slack webhook integration runs on separate server (port 8001)
    
    # Initialize responder system for escalations (if not already done)
    try:
        from src.setup_responder_system import ResponderSystemSetup
        responder_setup = ResponderSystemSetup()
        success = await responder_setup.initialize_system()
        responder_agent = responder_setup.responder_agent if success else None
        
        if responder_agent:
            delve_langgraph_workflow.set_responder_agent(responder_agent)
            logger.info("Chainlit: Responder system connected to workflow")
    except Exception as e:
        logger.warning(f"Chainlit: Could not initialize responder system: {e}")
    
    # Hardcoded user information for testing
    user_info = {
        "name": "Ola",
        "email": "olaboyefavour52@gmail.com",
        "company": "Google"
    }
    cl.user_session.set("user_info", user_info)
    
    # Welcome message
    welcome_msg = """
# Welcome to Delve's Bot!

    """
    
    await cl.Message(content=welcome_msg).send()
    
    # Create test case actions
    actions = []
    
    for category, cases in TEST_CASES.items():
        for case in cases:
            actions.append(
                cl.Action(
                    name=f"test_{case}",
                    value=case,
                    label=case,
                    description=f"Test case from {category}",
                    payload={"test_case": case, "category": category}
                )
            )
    
    # Send test case buttons
    await cl.Message(
        content="**Quick Test Cases** (click to test):",
        actions=actions[:15]  # Limit to avoid UI clutter
    ).send()
    
    # Initialize session data
    cl.user_session.set("message_count", 0)
    cl.user_session.set("conversation_history", [])  # Track conversation history
    cl.user_session.set("session_stats", {
        "total_messages": 0,
        "intent_accuracy": [],
        "routing_accuracy": [],
        "processing_times": []
    })

@cl.action_callback("test_")
async def on_test_action(action):
    """Handle test case button clicks."""
    test_message = action.value
    
    # Create a message object and process it
    await process_message_content(test_message, is_test=True)

@cl.action_callback("book_demo_slot")
async def on_slot_booking(action):
    """Handle demo slot booking button clicks."""
    try:
        # Import the slot booking handler
        from src.integrations.slot_booking_handler import slot_booking_handler
        
        # Get user info from session
        user_info = cl.user_session.get("user_info", {
            "name": "Ola", 
            "email": "olaboyefavour52@gmail.com",
        })
        
        # Debug the action object to see available attributes
        logger.info(f"Debug: Action object type: {type(action)}")
        logger.info(f"Debug: Action attributes: {dir(action)}")
        
        # Get the slot data from the action payload
        slot_payload = None
        if hasattr(action, 'payload') and action.payload and 'slot_data' in action.payload:
            slot_payload = action.payload['slot_data']  # This is the JSON string we stored
        elif hasattr(action, 'value'):
            slot_payload = action.value
        else:
            logger.error(f"Cannot find slot data in action payload: {action.payload if hasattr(action, 'payload') else 'No payload'}")
            await cl.Message(content="❌ **Error**: Cannot process slot selection").send()
            return
            
        logger.info(f"Debug: Using slot payload: {slot_payload}")

        # Process the slot booking
        confirmation = await slot_booking_handler.handle_slot_selection(
            slot_payload=slot_payload,
            user_id="chainlit_user",
            user_email=user_info.get("email", "chainlit@example.com"),
            user_name=user_info.get("name", "Chainlit User"),
            platform="chainlit",
            session_id=cl.user_session.get("session_id")
        )
        
        # Send confirmation message
        if confirmation.success:
            await cl.Message(
                content=f"✅ **Booking Confirmed!**\n\n{confirmation.message}",
                actions=[]
            ).send()
        else:
            await cl.Message(
                content=f"❌ **Booking Failed**\n\n{confirmation.message}",
                actions=[]
            ).send()
            
    except Exception as e:
        await cl.Message(
            content=f"❌ **Error**: Failed to book slot. {str(e)}",
            actions=[]
        ).send()

# Create individual action callbacks for each test case
@cl.action_callback("test_What is Delve?")
async def on_test_what_is_delve(action):
    await process_test_action(action)

@cl.action_callback("test_How does SOC2 work?")
async def on_test_soc2(action):
    await process_test_action(action)

@cl.action_callback("test_What is a demo?")
async def on_test_demo(action):
    await process_test_action(action)

@cl.action_callback("test_Tell me about compliance")
async def on_test_compliance(action):
    await process_test_action(action)

@cl.action_callback("test_What features do you have?")
async def on_test_features(action):
    await process_test_action(action)

@cl.action_callback("test_How does your platform work?")
async def on_test_platform(action):
    await process_test_action(action)

@cl.action_callback("test_What compliance frameworks do you support?")
async def on_test_frameworks(action):
    await process_test_action(action)

@cl.action_callback("test_I want to schedule a demo")
async def on_test_schedule_demo(action):
    await process_test_action(action)

@cl.action_callback("test_Can we book a meeting?")
async def on_test_book_meeting(action):
    await process_test_action(action)

@cl.action_callback("test_When can we schedule a call?")
async def on_test_schedule_call(action):
    await process_test_action(action)

@cl.action_callback("test_Let's set up a demo")
async def on_test_setup_demo(action):
    await process_test_action(action)

@cl.action_callback("test_Schedule a demo for next week")
async def on_test_schedule_next_week(action):
    await process_test_action(action)

@cl.action_callback("test_Book a meeting for Thursday")
async def on_test_book_thursday(action):
    await process_test_action(action)

@cl.action_callback("test_Option 2")
async def on_test_option2(action):
    await process_test_action(action)

@cl.action_callback("test_I'm getting an API error")
async def on_test_api_error(action):
    await process_test_action(action)

async def process_test_action(action):
    """Common handler for all test actions."""
    try:
        # Debug the action object to find the correct attribute
        logger.info(f"Debug: Test action object type: {type(action)}")
        logger.info(f"Debug: Test action attributes: {dir(action)}")
        
        # Try different ways to get the test message
        test_message = None
        if hasattr(action, 'value'):
            test_message = action.value
        elif hasattr(action, 'payload') and action.payload:
            test_message = action.payload.get('test_case', action.name.replace('test_', ''))
        elif hasattr(action, 'label'):
            test_message = action.label
        else:
            # Fallback: extract from action name
            test_message = action.name.replace('test_', '') if action.name else "Unknown test"
            
        logger.info(f"Debug: Using test message: {test_message}")
        
        await cl.Message(content=f"{test_message}").send()
        await process_message_content(test_message, is_test=True)
        
    except Exception as e:
        logger.error(f"Error handling test action {action.name if hasattr(action, 'name') else 'unknown'}: {e}")
        await cl.Message(content=f"❌ **Error**: Failed to run test case - {str(e)}").send()

@cl.on_message
async def on_message(message: cl.Message):
    """Handle incoming messages from the user."""
    await process_message_content(message.content, is_test=False)

async def process_message_content(content: str, is_test: bool = False):
    """Process message content through the LangGraph workflow."""
    
    # Increment message count
    count = cl.user_session.get("message_count", 0) + 1
    cl.user_session.set("message_count", count)
    
    # Get user info and conversation history from session
    user_info = cl.user_session.get("user_info", {
        "name": "Ola", 
        "email": "olaboyefavour52@gmail.com",
        "company": "Google"
    })
    
    # Get conversation history
    conversation_history = cl.user_session.get("conversation_history", [])
    
    # Create support message with real user info and conversation context
    message_id = f"chainlit_{datetime.now().timestamp()}_{count}"
    
    # Add conversation context to the content if there's history
    enriched_content = content
    if conversation_history:
        # Add recent context (last 4 messages) to help with continuity
        recent_context = conversation_history[-4:] if len(conversation_history) > 4 else conversation_history
        context_summary = "\\n".join([
            f"{msg['sender']}: {msg['content'][:200]}{'...' if len(msg['content']) > 200 else ''}" 
            for msg in recent_context
        ])
        enriched_content = f"CONVERSATION CONTEXT:\\n{context_summary}\\n\\nCURRENT USER MESSAGE: {content}"
    
    support_message = SupportMessage(
        message_id=message_id,
        channel_id="chainlit_production" if not is_test else "chainlit_test",
        user_id=f"chainlit_{user_info.get('email', 'unknown')}",
        timestamp=datetime.now(),
        content=enriched_content,
        thread_ts=None,
        user_name=user_info.get("name", "Anonymous User"),
        user_email=user_info.get("email", "not-provided@example.com")
    )
    
    # Show processing message
    processing_msg = cl.Message(content="🤔 Processing your message...")
    await processing_msg.send()
    
    try:
        # Step 1: Show intent detection (COMMENTED OUT FOR PRODUCTION)
        classifier = IntentClassifier()
        intent_result = await classifier.classify_intent(content)
        
        # intent_analysis = f"""
        # ## 🧠 Intent Analysis
        # **Message**: "{content}"
        # **Detected Intent**: `{intent_result['intent']}`
        # **Confidence**: {intent_result['confidence']:.2f}
        # **Pattern Scores**:
        # - Scheduling: {intent_result.get('pattern_scores', {}).get('scheduling', 0):.2f}
        # - Technical: {intent_result.get('pattern_scores', {}).get('technical', 0):.2f}  
        # - Information: {intent_result.get('pattern_scores', {}).get('information', 0):.2f}
        # 
        # **Metadata**: {json.dumps(intent_result.get('metadata', {}), indent=2)}
        #         """
        #         
        # await cl.Message(content=intent_analysis).send()
        
        # Step 2: Process through LangGraph workflow  
        start_time = datetime.now()
        
        # workflow_msg = cl.Message(content="🔄 Running LangGraph workflow...")
        # await workflow_msg.send()
        
        # Process through the workflow
        result = await delve_langgraph_workflow.process_message(support_message)
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        # Step 3: Show workflow results
        agent_name = ""
        confidence = 0.0
        escalated = False
        
        if result.agent_responses:
            latest_response = result.agent_responses[-1]
            agent_name = latest_response.agent_name
            confidence = latest_response.confidence_score
            escalated = latest_response.should_escalate
        
        # workflow_analysis = f"""
        # ## ⚙️ LangGraph Workflow Results
        # **Selected Agent**: `{agent_name}`
        # **Confidence Score**: {confidence:.2f}
        # **Processing Time**: {processing_time:.2f}s
        # **Escalated**: {'Yes' if escalated else 'No'}
        # **Response Length**: {len(result.final_response)} characters
        #         """
        #         
        # await cl.Message(content=workflow_analysis).send()
        
        # Step 4: Show final response with interactive elements if available
        if result.final_response:
            actions = []
            
            # Check if this is a demo scheduler response with slot data
            if result.agent_responses:
                latest_response = result.agent_responses[-1]
                if (latest_response.agent_name == "demo_scheduler" and 
                    hasattr(latest_response, 'metadata') and 
                    latest_response.metadata and
                    'interactive_elements' in latest_response.metadata):
                    
                    interactive_elements = latest_response.metadata.get('interactive_elements', {})
                    chainlit_actions = interactive_elements.get('chainlit_actions', [])
                    
                    logger.info(f"Debug: Interactive elements found: {bool(interactive_elements)}")
                    logger.info(f"Debug: Chainlit actions count: {len(chainlit_actions) if chainlit_actions else 0}")
                    if chainlit_actions:
                        logger.info(f"Debug: First action: {chainlit_actions[0] if chainlit_actions else 'None'}")
                    
                    if chainlit_actions:
                        # Create Chainlit actions for slot selection
                        for action_data in chainlit_actions:
                            # Create Chainlit action - store JSON data in payload for access
                            action_payload = action_data.get('payload', {})
                            action_payload['slot_data'] = action_data['value']  # Store the JSON string
                            
                            actions.append(cl.Action(
                                name=action_data['name'],
                                value=action_data['value'],  # Keep original value 
                                label=action_data['label'],
                                description=action_data.get('description', ''),
                                payload=action_payload
                            ))
            
            # Send the message with or without actions
            await cl.Message(content=result.final_response, actions=actions).send()
            
            # Update conversation history
            conversation_history.append({
                "sender": "User",
                "content": content,
                "timestamp": datetime.now().isoformat(),
                "message_id": message_id
            })
            conversation_history.append({
                "sender": "AI Assistant",
                "content": result.final_response,
                "timestamp": datetime.now().isoformat(),
                "agent_name": agent_name,
                "confidence": confidence
            })
            
            # Keep only last 10 messages to prevent memory bloat
            if len(conversation_history) > 10:
                conversation_history = conversation_history[-10:]
            
            cl.user_session.set("conversation_history", conversation_history)
        
        # Step 5: Routing validation (COMMENTED OUT FOR PRODUCTION)
        # routing_status = validate_routing(content, intent_result['intent'], agent_name)
        # 
        # validation_msg = f"""
        # ## ✅ Routing Validation
        # **Expected for Intent `{intent_result['intent']}`**: {get_expected_agent(intent_result['intent'])}
        # **Actual Agent**: `{agent_name}`
        # **Status**: {routing_status['status']} {routing_status['emoji']}
        # **Note**: {routing_status['note']}
        #         """
        #         
        # await cl.Message(content=validation_msg).send()
        
        # For production, just update stats without showing validation
        routing_status = validate_routing(content, intent_result['intent'], agent_name)
        
        # Update session stats
        update_session_stats(intent_result, agent_name, processing_time, routing_status)
        
        # Show session summary periodically  
        if count % 5 == 0:
            await show_session_summary()
            
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        error_msg = f"""
## ❌ Error Processing Message
**Error**: {str(e)}
**Type**: {type(e).__name__}

This helps us identify issues with the workflow system.
        """
        await cl.Message(content=error_msg).send()
    
    finally:
        # Remove processing message
        await processing_msg.remove()

def validate_routing(content: str, detected_intent: str, actual_agent: str) -> Dict[str, Any]:
    """Validate if the routing was correct."""
    
    expected_agent = get_expected_agent(detected_intent)
    
    # Check if routing matches expectation
    if expected_agent.lower() in actual_agent.lower():
        return {
            "status": "CORRECT",
            "emoji": "✅",
            "note": "Perfect routing! Intent matched expected agent."
        }
    
    # Special cases for edge cases
    edge_cases = {
        "what is a demo?": "enhanced_rag_agent",
        "tell me about your demo process": "enhanced_rag_agent", 
        "how long is a demo?": "enhanced_rag_agent"
    }
    
    if content.lower() in edge_cases:
        expected_edge = edge_cases[content.lower()]
        if expected_edge in actual_agent.lower():
            return {
                "status": "CORRECT",
                "emoji": "✅", 
                "note": "Excellent! Disambiguation prevented false scheduling trigger."
            }
        else:
            return {
                "status": "INCORRECT",
                "emoji": "❌",
                "note": f"Edge case failed - should have gone to {expected_edge}"
            }
    
    return {
        "status": "UNEXPECTED",
        "emoji": "⚠️",
        "note": f"Unexpected routing. Expected {expected_agent}, got {actual_agent}"
    }

def get_expected_agent(intent: str) -> str:
    """Get the expected agent for an intent."""
    mapping = {
        "information": "enhanced_rag_agent",
        "scheduling": "demo_scheduler", 
        "technical_support": "technical_support"
    }
    return mapping.get(intent, "enhanced_rag_agent")

def update_session_stats(intent_result: Dict, agent_name: str, processing_time: float, routing_status: Dict):
    """Update session statistics."""
    stats = cl.user_session.get("session_stats", {})
    
    stats["total_messages"] += 1
    stats["processing_times"].append(processing_time)
    
    # Track routing accuracy
    is_correct = routing_status["status"] == "CORRECT"
    stats["routing_accuracy"].append(is_correct)
    
    cl.user_session.set("session_stats", stats)

async def show_session_summary():
    """Show session performance summary."""
    stats = cl.user_session.get("session_stats", {})
    
    if not stats or stats.get("total_messages", 0) == 0:
        return
    
    avg_processing_time = sum(stats["processing_times"]) / len(stats["processing_times"])
    routing_accuracy = (sum(stats["routing_accuracy"]) / len(stats["routing_accuracy"])) * 100
    
    summary = f"""
## 📊 Session Performance Summary
**Messages Processed**: {stats["total_messages"]}
**Average Processing Time**: {avg_processing_time:.2f}s
**Routing Accuracy**: {routing_accuracy:.1f}%
**Fastest Response**: {min(stats["processing_times"]):.2f}s
**Slowest Response**: {max(stats["processing_times"]):.2f}s

{'🎉 Excellent performance!' if routing_accuracy >= 90 else '⚠️ Some routing issues detected'}
    """
    
    await cl.Message(content=summary).send()

@cl.on_chat_end
async def on_chat_end():
    """Handle chat session end."""
    await show_session_summary()
    
    final_msg = """
## 👋 Session Complete!

Thanks for testing the Delve LangGraph Workflow! 

**Key Achievements**:
- ✅ Tested intent detection accuracy
- ✅ Validated agent routing logic  
- ✅ Measured processing performance
- ✅ Verified disambiguation works

The LangGraph system successfully solves all the previous routing issues!
    """
    
    await cl.Message(content=final_msg).send()

async def collect_user_info():
    """DISABLED: Using hardcoded user info instead for testing convenience."""
    # Function disabled - using hardcoded user info in on_chat_start()
    # Hardcoded values: Ola, ola@gmail.com, Google
    return {
        "name": "Ola",
        "email": "olaboyefavour52@gmail.com",
        "company": "Google",
        "platform": "Chainlit"
    }

# ============================================================================
# SLACK WEBHOOK INTEGRATION
# Register Slack routes when Chainlit starts up
# ============================================================================

# Store Slack routes to be registered later
_slack_routes_registered = False

def register_slack_routes():
    """Register Slack webhook endpoints with Chainlit's FastAPI app."""
    global _slack_routes_registered
    
    if _slack_routes_registered:
        return
    
    try:
        # Import the app instance differently - Chainlit may not have exposed cl.app yet
        from chainlit.server import app
        
        @app.post("/slack/events")
        async def slack_events(request: Request):
            """Handle Slack Events API webhooks."""
            try:
                data = await request.json()
                logger.info(f"Slack event received: {data.get('type')}")
                
                # Handle URL verification challenge
                if data.get('type') == 'url_verification':
                    challenge = data.get('challenge')
                    logger.info(f"URL verification challenge: {challenge}")
                    return JSONResponse({"challenge": challenge})
                
                # Handle actual events
                if data.get('type') == 'event_callback':
                    event = data.get('event', {})
                    
                    # Skip bot messages and handle user messages
                    if event.get('type') == 'message' and not event.get('bot_id'):
                        # Process message asynchronously
                        Thread(target=lambda: asyncio.run(process_slack_message(event))).start()
                
                return JSONResponse({"status": "ok"})
                
            except Exception as e:
                logger.error(f"Error handling Slack event: {e}")
                return JSONResponse({"error": "Internal server error"}, status_code=500)

        @app.post("/slack/interactive")  # This is what your Slack app is configured for
        @app.post("/slack/interactions") # Also support plural just in case
        async def slack_interactions(request: Request):
            """Handle Slack Interactive Components (button clicks)."""
            logger.info(f"Slack interactive endpoint called: POST {request.url.path}")
            
            try:
                # Get form data (Slack sends as application/x-www-form-urlencoded)
                form = await request.form()
                
                # Parse payload from Slack
                payload = form.get('payload')
                if payload:
                    try:
                        data = json_lib.loads(payload)
                        logger.info(f"Received Slack interaction: {data.get('type')}")
                        logger.info(f"Action: {data.get('actions', [{}])[0].get('action_id', 'unknown')}")
                        
                        # Handle button interactions asynchronously AFTER responding
                        if data.get('type') == 'block_actions':
                            Thread(target=lambda: asyncio.run(process_slack_interaction(data))).start()
                        
                    except json_lib.JSONDecodeError as e:
                        logger.error(f"Failed to parse Slack payload: {e}")
                else:
                    logger.warning("No payload found in form data")
                
                # Always return success immediately (within 3 seconds requirement)
                return JSONResponse({"status": "ok", "message": "Interaction acknowledged"})
                
            except Exception as e:
                logger.error(f"Error handling Slack interaction: {e}")
                # Still return 200 to prevent user-facing error
                return JSONResponse({"error": "Processing error", "details": str(e)}, status_code=200)

        @app.get("/health")
        async def health_check():
            """Health check endpoint for monitoring."""
            return JSONResponse({
                "status": "healthy",
                "service": "Delve AI Agent - Chainlit + Slack Integration",
                "timestamp": datetime.now().isoformat(),
                "slack_endpoints": ["/slack/events", "/slack/interactive", "/slack/interactions"]
            })
        
        _slack_routes_registered = True
        logger.info("✅ Slack webhook routes registered successfully!")
        
    except Exception as e:
        logger.error(f"❌ Failed to register Slack routes: {e}")

# Slack route registration is now handled in the main on_chat_start function above

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
            user_name=f"slack_user_{event['user'][:8]}",
            user_email=None
        )
        
        logger.info(f"Processing Slack message: {support_message.content[:50]}...")
        
        # Process through the workflow
        result = await delve_langgraph_workflow.process_message(support_message)
        logger.info("Slack message processed successfully")
        
    except Exception as e:
        logger.error(f"Error processing Slack message: {e}")

async def process_slack_interaction(data):
    """Process Slack button interactions."""
    try:
        logger.info(f"Processing Slack interaction: {data.get('type')}")
        
        actions = data.get('actions', [])
        if actions:
            action = actions[0]
            action_id = action.get('action_id')
            logger.info(f"Button clicked: {action_id}")
            
            # TODO: Route to proper button handlers in slack_client.py
            # For now, just log the interaction
            
        logger.info("Slack interaction processing completed")
        
    except Exception as e:
        logger.error(f"Error processing Slack interaction: {e}")

if __name__ == "__main__":
    # This allows running with: python chainlit_app.py
    import subprocess
    subprocess.run(["chainlit", "run", __file__, "-w"])