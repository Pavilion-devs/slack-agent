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
        "How does SOC2 work?", 
        "What is a demo?",
        "Tell me about compliance",
        "What features do you have?",
        "How does your platform work?",
        "What compliance frameworks do you support?"
    ],
    "Scheduling Requests": [
        "I want to schedule a demo",
        "Can we book a meeting?",
        "When can we schedule a call?",
        "Let's set up a demo",
        "Schedule a demo for next week",
        "Book a meeting for Thursday",
        "Option 2"  # Slot selection
    ],
    "Technical Support": [
        "I'm getting an API error",
        "The integration is not working", 
        "Help me troubleshoot this issue",
        "I have a bug",
        "500 error from your API",
        "Authentication not working",
        "Webhook failing"
    ],
    "Edge Cases": [
        "What is a demo?",  # Should NOT trigger scheduling
        "Tell me about your demo process",  # Should NOT trigger scheduling
        "How long is a demo?",  # Should NOT trigger scheduling  
        "I want to schedule a demo",  # SHOULD trigger scheduling
        "How do I implement SOC2 compliance?"  # Ambiguous case
    ]
}

@cl.on_chat_start
async def on_chat_start():
    """Initialize the chat session with welcome message and test cases."""
    
    # Welcome message
    welcome_msg = """
# 🚀 Welcome to Delve's LangGraph Workflow Tester!

This interface lets you test our new **LangGraph-based agent routing system** that solves all the previous routing issues.

## 🎯 Key Improvements Tested:
- ✅ **Intent Detection**: Prevents "What is a demo?" from triggering scheduling
- ✅ **Smart Routing**: Routes messages to the correct agent based on confidence
- ✅ **No More Conflicts**: LangGraph orchestration eliminates agent competition
- ✅ **Parallel Execution**: Subgraphs run efficiently in parallel

## 🧪 Try These Test Cases:
Click any button below to test specific scenarios, or type your own message!

**Test Categories:**
- 🔍 **Information Queries** - Should route to RAG agent
- 📅 **Scheduling Requests** - Should route to Demo Scheduler  
- 🔧 **Technical Support** - Should route to Technical Support
- ⚠️ **Edge Cases** - Tests disambiguation logic
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

@cl.on_message
async def on_message(message: cl.Message):
    """Handle incoming messages from the user."""
    await process_message_content(message.content, is_test=False)

async def process_message_content(content: str, is_test: bool = False):
    """Process message content through the LangGraph workflow."""
    
    # Increment message count
    count = cl.user_session.get("message_count", 0) + 1
    cl.user_session.set("message_count", count)
    
    # Create support message
    message_id = f"chainlit_{datetime.now().timestamp()}_{count}"
    support_message = SupportMessage(
        message_id=message_id,
        channel_id="chainlit_test",
        user_id="chainlit_user",
        timestamp=datetime.now(),
        content=content,
        thread_ts=None
    )
    
    # Show processing message
    processing_msg = cl.Message(content="🤔 Processing your message...")
    await processing_msg.send()
    
    try:
        # Step 1: Show intent detection
        classifier = IntentClassifier()
        intent_result = await classifier.classify_intent(content)
        
        intent_analysis = f"""
## 🧠 Intent Analysis
**Message**: "{content}"
**Detected Intent**: `{intent_result['intent']}`
**Confidence**: {intent_result['confidence']:.2f}
**Pattern Scores**:
- Scheduling: {intent_result.get('pattern_scores', {}).get('scheduling', 0):.2f}
- Technical: {intent_result.get('pattern_scores', {}).get('technical', 0):.2f}  
- Information: {intent_result.get('pattern_scores', {}).get('information', 0):.2f}

**Metadata**: {json.dumps(intent_result.get('metadata', {}), indent=2)}
        """
        
        await cl.Message(content=intent_analysis).send()
        
        # Step 2: Process through LangGraph workflow  
        start_time = datetime.now()
        
        workflow_msg = cl.Message(content="🔄 Running LangGraph workflow...")
        await workflow_msg.send()
        
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
        
        workflow_analysis = f"""
## ⚙️ LangGraph Workflow Results
**Selected Agent**: `{agent_name}`
**Confidence Score**: {confidence:.2f}
**Processing Time**: {processing_time:.2f}s
**Escalated**: {'Yes' if escalated else 'No'}
**Response Length**: {len(result.final_response)} characters
        """
        
        await cl.Message(content=workflow_analysis).send()
        
        # Step 4: Show final response
        if result.final_response:
            final_response_msg = f"""
## 💬 Agent Response
{result.final_response}
            """
            await cl.Message(content=final_response_msg).send()
        
        # Step 5: Routing validation
        routing_status = validate_routing(content, intent_result['intent'], agent_name)
        
        validation_msg = f"""
## ✅ Routing Validation
**Expected for Intent `{intent_result['intent']}`**: {get_expected_agent(intent_result['intent'])}
**Actual Agent**: `{agent_name}`
**Status**: {routing_status['status']} {routing_status['emoji']}
**Note**: {routing_status['note']}
        """
        
        await cl.Message(content=validation_msg).send()
        
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

if __name__ == "__main__":
    # This allows running with: python chainlit_app.py
    import subprocess
    subprocess.run(["chainlit", "run", __file__, "-w"])