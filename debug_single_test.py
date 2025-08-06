#!/usr/bin/env python3
"""
Debug single test to understand workflow response structure
"""

import asyncio
import sys
import os
from datetime import datetime

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.models.schemas import SupportMessage
from src.workflows.langgraph_workflow import langgraph_workflow
from src.core.intent_classifier import IntentClassifier

async def debug_single_test():
    """Debug a single test case."""
    print("🧪 Debug Single Test Case")
    
    # Create test message
    test_message = SupportMessage(
        message_id=f"debug_test_{int(datetime.now().timestamp())}",
        channel_id="chainlit_test",
        user_id="test_user",
        timestamp=datetime.now(),
        content="What is Delve?",
        thread_ts=None,
        user_name="Test User",
        user_email="test@example.com"
    )
    
    print(f"Testing message: '{test_message.content}'")
    
    # Test intent classification
    classifier = IntentClassifier()
    intent_result = await classifier.classify_intent(test_message.content)
    print(f"Intent result: {intent_result}")
    
    # Process through workflow
    print("Processing through LangGraph workflow...")
    workflow_result = await langgraph_workflow.process_message(test_message)
    
    print(f"\nDEBUG - Workflow result type: {type(workflow_result)}")
    print(f"DEBUG - Workflow result: {workflow_result}")
    
    if hasattr(workflow_result, '__dict__'):
        print(f"DEBUG - Workflow attributes: {workflow_result.__dict__}")
    
    print(f"\nDEBUG - Available attributes: {[attr for attr in dir(workflow_result) if not attr.startswith('_')]}")

if __name__ == "__main__":
    asyncio.run(debug_single_test())