"""
Test script for the complete workflow system.
Tests the full message processing pipeline.
"""

import asyncio
import sys
import os
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.models.schemas import SupportMessage, MessageCategory, UrgencyLevel
from src.workflows.improved_workflow import ImprovedWorkflow
from src.agents.intake_agent import IntakeAgent
from src.agents.rag_agent import RAGAgent


async def test_complete_workflow():
    """Test the complete workflow."""
    
    print("🔄 Testing Complete Workflow")
    print("=" * 50)
    
    workflow = ImprovedWorkflow()
    
    # Test messages with various scenarios
    test_messages = [
        {
            "content": "How do I set up SOC2 compliance with Delve?",
            "category": MessageCategory.COMPLIANCE,
            "urgency": UrgencyLevel.HIGH,
            "description": "High priority compliance question"
        },
        {
            "content": "What is Delve and how does it work?", 
            "category": MessageCategory.GENERAL,
            "urgency": UrgencyLevel.MEDIUM,
            "description": "General product information"
        },
        {
            "content": "The API is returning 500 errors and our production is down!",
            "category": MessageCategory.TECHNICAL,
            "urgency": UrgencyLevel.CRITICAL,
            "description": "Critical technical issue"
        },
        {
            "content": "Can we schedule a demo for next week?",
            "category": MessageCategory.DEMO,
            "urgency": UrgencyLevel.LOW,
            "description": "Demo request"
        },
        {
            "content": "What are your pricing plans for enterprise?",
            "category": MessageCategory.BILLING,
            "urgency": UrgencyLevel.MEDIUM,
            "description": "Pricing inquiry"
        }
    ]
    
    results = []
    
    for i, test_msg in enumerate(test_messages, 1):
        print(f"\n🧪 Test {i}: {test_msg['description']}")
        print(f"❓ Message: {test_msg['content']}")
        print(f"🏷️  Category: {test_msg['category'].value}")
        print(f"⚡ Urgency: {test_msg['urgency'].value}")
        print("-" * 40)
        
        try:
            # Create support message
            message = SupportMessage(
                message_id=f"workflow_test_{i}",
                channel_id="C123456",
                user_id="U123456",
                timestamp=datetime.now(),
                content=test_msg['content'],
                category=test_msg['category'],
                urgency_level=test_msg['urgency']
            )
            
            start_time = datetime.now()
            
            # Process through workflow
            result = await workflow.process_message(message)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            print(f"✅ Final Agent: {result.agent_name}")
            print(f"📊 Confidence: {result.confidence_score:.2f}")
            print(f"⏱️  Processing Time: {processing_time:.2f}s")
            print(f"🎯 Escalated: {'Yes' if result.should_escalate else 'No'}")
            
            if result.should_escalate:
                print(f"⚠️  Escalation Reason: {result.escalation_reason}")
            
            print(f"💬 Response Preview: {result.response_text[:100]}...")
            
            if result.sources:
                print(f"📚 Sources: {len(result.sources)} found")
            
            # Assess if the routing was appropriate
            expected_escalation = test_msg['urgency'] == UrgencyLevel.CRITICAL
            appropriate_routing = (
                (expected_escalation and result.should_escalate) or
                (not expected_escalation)
            )
            
            if appropriate_routing:
                print("✅ Routing: APPROPRIATE")
            else:
                print("⚠️  Routing: May need review")
            
            results.append({
                'test': i,
                'description': test_msg['description'],
                'category': test_msg['category'].value,
                'urgency': test_msg['urgency'].value,
                'confidence': result.confidence_score,
                'processing_time': processing_time,
                'escalated': result.should_escalate,
                'agent_used': result.agent_name,
                'appropriate_routing': appropriate_routing
            })
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            results.append({
                'test': i,
                'description': test_msg['description'],
                'error': str(e)
            })
    
    # Summary
    print("\n📊 Workflow Test Summary")
    print("=" * 50)
    
    successful_tests = [r for r in results if 'error' not in r]
    
    if successful_tests:
        avg_confidence = sum(r['confidence'] for r in successful_tests) / len(successful_tests)
        avg_time = sum(r['processing_time'] for r in successful_tests) / len(successful_tests)
        escalated_count = sum(1 for r in successful_tests if r['escalated'])
        appropriate_routing = sum(1 for r in successful_tests if r.get('appropriate_routing', False))
        
        print(f"Successful Tests: {len(successful_tests)}/{len(results)}")
        print(f"Average Confidence: {avg_confidence:.2f}")
        print(f"Average Processing Time: {avg_time:.2f}s")
        print(f"Messages Escalated: {escalated_count}/{len(successful_tests)}")
        print(f"Appropriate Routing: {appropriate_routing}/{len(successful_tests)}")
        
        # Performance assessment
        if avg_time < 30:  # Less than 30 seconds
            print("🚀 Performance: EXCELLENT (< 30s)")
        elif avg_time < 60:
            print("✅ Performance: GOOD (< 60s)")
        else:
            print("⚠️  Performance: NEEDS IMPROVEMENT (> 60s)")
    
    return results


async def test_individual_agents():
    """Test individual agents separately."""
    
    print("🔍 Testing Individual Agents")
    print("=" * 50)
    
    # Test Intake Agent
    print("\n1️⃣  Testing Intake Agent")
    print("-" * 30)
    
    intake_agent = IntakeAgent()
    
    intake_message = SupportMessage(
        message_id="intake_test",
        channel_id="C123456", 
        user_id="U123456",
        timestamp=datetime.now(),
        content="I need help with setting up GDPR compliance",
        category=MessageCategory.COMPLIANCE
    )
    
    try:
        intake_response = await intake_agent.process_message(intake_message)
        print(f"✅ Intake Agent Response: {intake_response.response_text[:100]}...")
        print(f"📊 Confidence: {intake_response.confidence_score:.2f}")
        print(f"🎯 Should Escalate: {intake_response.should_escalate}")
    except Exception as e:
        print(f"❌ Intake Agent Error: {e}")
    
    # Test RAG Agent
    print("\n2️⃣  Testing RAG Agent")
    print("-" * 30)
    
    rag_agent = RAGAgent()
    
    rag_message = SupportMessage(
        message_id="rag_test",
        channel_id="C123456",
        user_id="U123456", 
        timestamp=datetime.now(),
        content="How does Delve help with SOC2 Type II audits?",
        category=MessageCategory.COMPLIANCE
    )
    
    try:
        rag_response = await rag_agent.process_message(rag_message)
        print(f"✅ RAG Agent Response: {rag_response.response_text[:150]}...")
        print(f"📊 Confidence: {rag_response.confidence_score:.2f}")
        print(f"🎯 Should Escalate: {rag_response.should_escalate}")
        
        if rag_response.sources:
            print(f"📚 Sources Found: {len(rag_response.sources)}")
            
        if hasattr(rag_response, 'metadata') and rag_response.metadata:
            frameworks = rag_response.metadata.get('frameworks_detected', [])
            if frameworks:
                print(f"🏷️  Frameworks Detected: {frameworks}")
                
    except Exception as e:
        print(f"❌ RAG Agent Error: {e}")


def main():
    """Main function with options."""
    print("🤖 Delve Workflow Testing")
    print("=" * 50)
    print("1. Test Complete Workflow")
    print("2. Test Individual Agents")
    print("3. Both")
    print("4. Exit")
    
    while True:
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == "1":
            asyncio.run(test_complete_workflow())
        elif choice == "2":
            asyncio.run(test_individual_agents())
        elif choice == "3":
            asyncio.run(test_individual_agents())
            print("\n" + "=" * 60)
            asyncio.run(test_complete_workflow())
        elif choice == "4":
            print("👋 Goodbye!")
            break
        else:
            print("Invalid choice. Please select 1, 2, 3, or 4.")


if __name__ == "__main__":
    main()