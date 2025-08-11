#!/usr/bin/env python3
"""
Debug why Chainlit gives fallback responses when standalone tests work
Compare the exact flow that Chainlit uses vs our working tests
"""
import os
import sys
import asyncio
import logging
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.models.schemas import SupportMessage
from src.workflows.delve_langgraph_workflow import delve_langgraph_workflow

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_chainlit_flow():
    """Test exactly what Chainlit does when processing a message."""
    
    print("🔍 Debugging Chainlit vs Test Difference")
    print("=" * 60)
    
    # The exact question from the screenshot
    test_question = "where is your office located?"
    
    print(f"1️⃣ Testing question: '{test_question}'")
    
    # Create SupportMessage exactly like Chainlit does in chainlit_app.py
    user_info = {
        "name": "Ola",
        "email": "olaboyefavour52@gmail.com",
        "company": "Google"
    }
    
    message_id = f"chainlit_{datetime.now().timestamp()}_1"
    
    # This is exactly what chainlit_app.py does in process_message_content()
    support_message = SupportMessage(
        message_id=message_id,
        channel_id="chainlit_production",  # Not chainlit_test
        user_id=f"chainlit_{user_info.get('email', 'unknown')}",
        timestamp=datetime.now(),
        content=test_question,  # No conversation context added in this test
        thread_ts=None,
        user_name=user_info.get("name", "Anonymous User"),
        user_email=user_info.get("email", "not-provided@example.com")
    )
    
    print(f"2️⃣ Created SupportMessage like Chainlit:")
    print(f"   Message ID: {support_message.message_id}")
    print(f"   Channel ID: {support_message.channel_id}")
    print(f"   User ID: {support_message.user_id}")
    print(f"   Content: {support_message.content}")
    
    # Process through delve_langgraph_workflow (exactly like Chainlit)
    print(f"\n3️⃣ Processing through delve_langgraph_workflow...")
    result = await delve_langgraph_workflow.process_message(support_message)
    
    print(f"4️⃣ Results:")
    print(f"   Final Response: {result.final_response[:100]}...")
    print(f"   Agent Responses Count: {len(result.agent_responses) if result.agent_responses else 0}")
    
    if result.agent_responses:
        latest_response = result.agent_responses[-1]
        print(f"   Latest Agent: {latest_response.agent_name}")
        print(f"   Confidence: {latest_response.confidence_score}")
        print(f"   Should Escalate: {latest_response.should_escalate}")
        print(f"   Escalation Reason: {latest_response.escalation_reason}")
        
        # Check if this is the fallback response
        if "unable to process" in result.final_response.lower():
            print("   🚨 FOUND THE ISSUE: Getting fallback response!")
            return "fallback"
        else:
            print("   ✅ Got proper response (not fallback)")
            return "proper"
    else:
        print("   🚨 No agent responses at all")
        return "no_response"

async def test_direct_rag():
    """Test RAG system directly like our working tests."""
    
    print(f"\n5️⃣ Testing RAG system directly (like our working tests)...")
    
    from src.core.rag_system import rag_system
    
    # Initialize RAG system
    success = await rag_system.initialize()
    if not success:
        print("   ❌ Failed to initialize RAG system")
        return "failed"
    
    # Query directly
    test_question = "where is your office located?"
    result = await rag_system.query(test_question)
    
    print(f"   Direct RAG Answer: {result['answer'][:100]}...")
    print(f"   Direct RAG Confidence: {result['confidence']}")
    print(f"   Should Escalate: {result['should_escalate']}")
    
    if result['should_escalate']:
        print("   ✅ RAG correctly identifies this should escalate")
        return "escalates"
    else:
        print("   ✅ RAG provides answer")
        return "answers"

async def test_workflow_with_conversation_context():
    """Test if conversation context is causing issues."""
    
    print(f"\n6️⃣ Testing with conversation context (like real Chainlit usage)...")
    
    # Simulate conversation history like Chainlit adds
    conversation_history = [
        {"sender": "User", "content": "Hello", "timestamp": datetime.now().isoformat()},
        {"sender": "AI Assistant", "content": "Hi! How can I help you?", "timestamp": datetime.now().isoformat()}
    ]
    
    # Add context like chainlit_app.py does
    test_question = "where is your office located?"
    context_summary = "\\n".join([
        f"{msg['sender']}: {msg['content'][:200]}" 
        for msg in conversation_history
    ])
    enriched_content = f"CONVERSATION CONTEXT:\\n{context_summary}\\n\\nCURRENT USER MESSAGE: {test_question}"
    
    print(f"   Content with context: {enriched_content[:100]}...")
    
    support_message = SupportMessage(
        message_id=f"context_test_{datetime.now().timestamp()}",
        channel_id="chainlit_production",
        user_id="chainlit_test@example.com",
        timestamp=datetime.now(),
        content=enriched_content,  # With context
        thread_ts=None,
        user_name="Test User",
        user_email="test@example.com"
    )
    
    # Process through workflow
    result = await delve_langgraph_workflow.process_message(support_message)
    
    print(f"   Context Test Result: {result.final_response[:100]}...")
    
    if "unable to process" in result.final_response.lower():
        print("   🚨 CONTEXT IS CAUSING THE ISSUE!")
        return "context_issue"
    else:
        print("   ✅ Context doesn't cause issues")
        return "context_ok"

async def main():
    """Main debug function."""
    
    print("🐛 Root Cause Analysis: Chainlit vs Test Differences")
    print("=" * 60)
    
    # Test 1: Exact Chainlit flow
    chainlit_result = await test_chainlit_flow()
    
    # Test 2: Direct RAG (our working tests)
    rag_result = await test_direct_rag()
    
    # Test 3: With conversation context
    context_result = await test_workflow_with_conversation_context()
    
    print(f"\n📊 Debug Results:")
    print(f"   Chainlit Flow: {chainlit_result}")
    print(f"   Direct RAG: {rag_result}")
    print(f"   With Context: {context_result}")
    
    print(f"\n🔍 Analysis:")
    if chainlit_result == "fallback":
        print("   🚨 Chainlit is getting fallback - workflow issue")
        print("   🔧 Need to debug why delve_langgraph_workflow fails")
    
    if rag_result in ["answers", "escalates"]:
        print("   ✅ RAG system works correctly")
    
    if context_result == "context_issue":
        print("   🚨 Conversation context is breaking the workflow")
    
    # Recommendations
    print(f"\n💡 Next Steps:")
    print(f"   1. Compare workflow vs direct RAG behavior")
    print(f"   2. Check if conversation context breaks intent classification")
    print(f"   3. Debug delve_langgraph_workflow processing")

if __name__ == "__main__":
    asyncio.run(main())