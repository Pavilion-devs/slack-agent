"""
Interactive test script for the RAG system.
Run this to manually test the RAG system with custom questions.
"""

import asyncio
import sys
import os
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.core.rag_system import rag_system
from src.agents.rag_agent import RAGAgent
from src.models.schemas import SupportMessage, MessageCategory


async def test_rag_system():
    """Interactive test of the RAG system."""
    
    print("🚀 Starting RAG System Test")
    print("=" * 50)
    
    # Initialize the system
    print("🔄 Initializing RAG system...")
    await rag_system.initialize()
    
    if not rag_system.is_initialized:
        print("❌ RAG system failed to initialize")
        print("Make sure:")
        print("- Ollama is running: ollama serve")
        print("- llama3.2:3b model is available: ollama pull llama3.2:3b")
        return
    
    print("✅ RAG system initialized successfully!")
    print("✅ Vector database loaded with Delve knowledge")
    print("✅ Ollama llama3.2:3b ready for response generation")
    
    agent = RAGAgent()
    
    while True:
        print("\n" + "=" * 60)
        print("🤔 Enter your question (or 'quit' to exit):")
        question = input("> ").strip()
        
        if question.lower() in ['quit', 'exit', 'q']:
            print("👋 Goodbye!")
            break
            
        if not question:
            continue
        
        print(f"\n🔄 Processing: {question}")
        print("-" * 50)
        
        try:
            start_time = datetime.now()
            
            # Create a support message
            message = SupportMessage(
                message_id=f"test_{start_time.timestamp()}",
                channel_id="test_channel",
                user_id="test_user", 
                timestamp=start_time,
                content=question
            )
            
            # Process with RAG agent
            response = await agent.process_message(message)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Display results
            print(f"🤖 Agent: {response.agent_name}")
            print(f"⏱️  Processing Time: {processing_time:.2f}s")
            print(f"📊 Confidence: {response.confidence_score:.2f}")
            print(f"🎯 Should Escalate: {'Yes' if response.should_escalate else 'No'}")
            
            if response.should_escalate:
                print(f"⚠️  Escalation Reason: {response.escalation_reason}")
            
            print(f"\n💬 Response:")
            print(response.response_text)
            
            if response.sources:
                print(f"\n📚 Sources ({len(response.sources)}):")
                for i, source in enumerate(response.sources, 1):
                    print(f"   {i}. {source}")
            
            if hasattr(response, 'metadata') and response.metadata:
                print(f"\n🔍 Metadata:")
                for key, value in response.metadata.items():
                    print(f"   {key}: {value}")
                    
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            print("Please check your Ollama setup and try again.")


async def run_test_cases():
    """Run predefined test cases."""
    
    print("🧪 Running Predefined Test Cases")
    print("=" * 50)
    
    # Initialize the system
    print("🔄 Initializing RAG system...")
    await rag_system.initialize()
    
    if not rag_system.is_initialized:
        print("❌ RAG system failed to initialize")
        return
    
    # Test cases
    test_cases = [
        {
            "question": "What is Delve?",
            "category": MessageCategory.GENERAL,
            "expected_frameworks": [],
            "description": "Basic product information"
        },
        {
            "question": "How does SOC2 compliance work with Delve?",
            "category": MessageCategory.COMPLIANCE,
            "expected_frameworks": ["SOC2"],
            "description": "SOC2 compliance question"
        },
        {
            "question": "What are the HIPAA requirements for healthcare data?",
            "category": MessageCategory.COMPLIANCE,
            "expected_frameworks": ["HIPAA"],
            "description": "HIPAA specific question"
        },
        {
            "question": "How do I configure API authentication?",
            "category": MessageCategory.TECHNICAL,
            "expected_frameworks": [],
            "description": "Technical configuration"
        },
        {
            "question": "Can you help with GDPR data subject rights?",
            "category": MessageCategory.COMPLIANCE,
            "expected_frameworks": ["GDPR"],
            "description": "GDPR specific question"
        },
        {
            "question": "What is quantum computing?",
            "category": MessageCategory.GENERAL,
            "expected_frameworks": [],
            "description": "Out-of-scope question (should escalate)"
        }
    ]
    
    agent = RAGAgent()
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 Test Case {i}: {test_case['description']}")
        print(f"❓ Question: {test_case['question']}")
        print("-" * 40)
        
        try:
            message = SupportMessage(
                message_id=f"test_case_{i}",
                channel_id="test_channel",
                user_id="test_user",
                timestamp=datetime.now(),
                content=test_case['question'],
                category=test_case['category']
            )
            
            start_time = datetime.now()
            response = await agent.process_message(message)
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Analyze results
            frameworks_detected = response.metadata.get('frameworks_detected', []) if hasattr(response, 'metadata') else []
            
            print(f"✅ Confidence: {response.confidence_score:.2f}")
            print(f"⏱️  Time: {processing_time:.2f}s")
            print(f"🏷️  Frameworks: {frameworks_detected}")
            print(f"🎯 Escalate: {'Yes' if response.should_escalate else 'No'}")
            print(f"📝 Response: {response.response_text[:100]}...")
            
            # Check if expected frameworks were detected
            expected = set(test_case['expected_frameworks'])
            detected = set(frameworks_detected)
            
            if expected.issubset(detected):
                print("✅ Framework detection: PASSED")
            elif expected:
                print(f"⚠️  Framework detection: Expected {expected}, got {detected}")
            else:
                print("✅ Framework detection: N/A")
            
            results.append({
                'test_case': i,
                'question': test_case['question'],
                'confidence': response.confidence_score,
                'processing_time': processing_time,
                'frameworks_detected': frameworks_detected,
                'should_escalate': response.should_escalate,
                'passed': not expected or expected.issubset(detected)
            })
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            results.append({
                'test_case': i,
                'question': test_case['question'],
                'error': str(e),
                'passed': False
            })
    
    # Summary
    print("\n📊 Test Summary")
    print("=" * 50)
    passed = sum(1 for r in results if r.get('passed', False))
    total = len(results)
    
    print(f"Tests Passed: {passed}/{total}")
    print(f"Average Confidence: {sum(r.get('confidence', 0) for r in results if 'confidence' in r) / max(1, sum(1 for r in results if 'confidence' in r)):.2f}")
    print(f"Average Processing Time: {sum(r.get('processing_time', 0) for r in results if 'processing_time' in r) / max(1, sum(1 for r in results if 'processing_time' in r)):.2f}s")
    
    return results


def main():
    """Main function with menu."""
    print("🤖 Delve RAG System - Manual Testing")
    print("=" * 50)
    print("1. Interactive Testing")
    print("2. Run Test Cases")
    print("3. Exit")
    
    while True:
        choice = input("\nSelect option (1-3): ").strip()
        
        if choice == "1":
            asyncio.run(test_rag_system())
        elif choice == "2":
            asyncio.run(run_test_cases())
        elif choice == "3":
            print("👋 Goodbye!")
            break
        else:
            print("Invalid choice. Please select 1, 2, or 3.")


if __name__ == "__main__":
    main()