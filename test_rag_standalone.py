#!/usr/bin/env python3
"""
Standalone RAG System Test Script

This script allows you to test the RAG system independently of the full workflow.
It provides an interactive interface to query the knowledge base and see detailed results.
"""

import asyncio
import sys
import os
from datetime import datetime
from typing import List, Dict, Any

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.core.rag_system import rag_system
from src.agents.rag_agent import rag_agent
from src.models.schemas import SupportMessage


class RAGTester:
    """Interactive RAG system tester."""
    
    def __init__(self):
        self.test_questions = [
            "What is Delve?",
            "How does SOC2 compliance work?",
            "How does Delve help with HIPAA compliance?",
            "What is the timeline for HIPAA implementation?",
            "Tell me about GDPR compliance",
            "What are the pricing options?",
            "How long does implementation take?",
            "What are the technical requirements?",
        ]
    
    async def initialize_rag(self) -> bool:
        """Initialize the RAG system."""
        print("🔧 Initializing RAG system...")
        try:
            success = await rag_system.initialize()
            if success:
                print("✅ RAG system initialized successfully!")
                return True
            else:
                print("❌ Failed to initialize RAG system")
                return False
        except Exception as e:
            print(f"❌ Error initializing RAG system: {e}")
            return False
    
    async def test_rag_query(self, question: str) -> Dict[str, Any]:
        """Test a single RAG query."""
        print(f"\n🔍 Testing RAG query: '{question}'")
        print("-" * 60)
        
        start_time = datetime.now()
        
        try:
            # Test direct RAG system query
            rag_result = await rag_system.query(question)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            print(f"⏱️  Processing time: {processing_time:.2f}s")
            print(f"🎯 Confidence: {rag_result['confidence']:.2f}")
            print(f"📚 Sources found: {len(rag_result['sources'])}")
            print(f"🚨 Should escalate: {rag_result['should_escalate']}")
            
            if rag_result['escalation_reason']:
                print(f"📋 Escalation reason: {rag_result['escalation_reason']}")
            
            print(f"\n💬 Answer:")
            print(rag_result['answer'])
            
            if rag_result['sources']:
                print(f"\n📖 Sources:")
                for i, source in enumerate(rag_result['sources'], 1):
                    print(f"  {i}. {source}")
            
            return rag_result
            
        except Exception as e:
            print(f"❌ Error during RAG query: {e}")
            return None
    
    async def test_rag_agent(self, question: str) -> Dict[str, Any]:
        """Test the RAG agent with a support message."""
        print(f"\n🤖 Testing RAG Agent with: '{question}'")
        print("-" * 60)
        
        start_time = datetime.now()
        
        try:
            # Create a test support message
            test_message = SupportMessage(
                message_id=f"test_{datetime.now().timestamp()}",
                channel_id="test_channel",
                user_id="test_user",
                timestamp=datetime.now(),
                content=question,
                thread_ts=None,
                user_name="Test User",
                user_email="test@example.com"
            )
            
            # Process through RAG agent
            response = await rag_agent.process_message(test_message)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            print(f"⏱️  Processing time: {processing_time:.2f}s")
            print(f"🎯 Confidence: {response.confidence_score:.2f}")
            print(f"🤖 Agent: {response.agent_name}")
            print(f"🚨 Should escalate: {response.should_escalate}")
            
            if response.escalation_reason:
                print(f"📋 Escalation reason: {response.escalation_reason}")
            
            print(f"\n💬 Response:")
            print(response.response_text)
            
            if response.sources:
                print(f"\n📖 Sources:")
                for i, source in enumerate(response.sources, 1):
                    print(f"  {i}. {source}")
            
            if response.metadata:
                print(f"\n📊 Metadata:")
                for key, value in response.metadata.items():
                    print(f"  {key}: {value}")
            
            return {
                'response': response,
                'processing_time': processing_time
            }
            
        except Exception as e:
            print(f"❌ Error during RAG agent test: {e}")
            return None
    
    async def run_predefined_tests(self):
        """Run predefined test questions."""
        print("\n🧪 Running predefined test questions...")
        print("=" * 80)
        
        results = []
        
        for i, question in enumerate(self.test_questions, 1):
            print(f"\n📝 Test {i}/{len(self.test_questions)}")
            result = await self.test_rag_query(question)
            if result:
                results.append({
                    'question': question,
                    'confidence': result['confidence'],
                    'escalate': result['should_escalate'],
                    'sources_count': len(result['sources'])
                })
        
        # Summary
        print("\n📊 Test Summary:")
        print("=" * 40)
        print(f"Total tests: {len(results)}")
        print(f"Average confidence: {sum(r['confidence'] for r in results) / len(results):.2f}")
        print(f"Escalations: {sum(1 for r in results if r['escalate'])}")
        print(f"Average sources: {sum(r['sources_count'] for r in results) / len(results):.1f}")
    
    async def interactive_mode(self):
        """Run interactive testing mode."""
        print("\n🎮 Interactive RAG Testing Mode")
        print("=" * 40)
        print("Type your questions and press Enter.")
        print("Type 'quit' to exit, 'help' for commands.")
        
        while True:
            try:
                question = input("\n❓ Your question: ").strip()
                
                if question.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break
                
                if question.lower() == 'help':
                    print("\n📖 Available commands:")
                    print("  help - Show this help")
                    print("  quit/exit/q - Exit the program")
                    print("  rag - Test RAG system directly")
                    print("  agent - Test RAG agent")
                    print("  both - Test both RAG system and agent")
                    continue
                
                if question.lower() == 'rag':
                    question = input("❓ Enter your question for RAG system: ").strip()
                    await self.test_rag_query(question)
                    continue
                
                if question.lower() == 'agent':
                    question = input("❓ Enter your question for RAG agent: ").strip()
                    await self.test_rag_agent(question)
                    continue
                
                if question.lower() == 'both':
                    question = input("❓ Enter your question for both tests: ").strip()
                    print("\n🔄 Testing both RAG system and agent...")
                    await self.test_rag_query(question)
                    await self.test_rag_agent(question)
                    continue
                
                if not question:
                    continue
                
                # Default: test both
                print("\n🔄 Testing both RAG system and agent...")
                await self.test_rag_query(question)
                await self.test_rag_agent(question)
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    
    async def health_check(self):
        """Run system health check."""
        print("\n🏥 RAG System Health Check")
        print("=" * 40)
        
        try:
            # Check RAG system health
            rag_healthy = await rag_system.health_check()
            print(f"🔧 RAG System: {'✅ Healthy' if rag_healthy else '❌ Unhealthy'}")
            
            # Check RAG agent health
            agent_healthy = await rag_agent.health_check()
            print(f"🤖 RAG Agent: {'✅ Healthy' if agent_healthy else '❌ Unhealthy'}")
            
            # Get stats
            rag_stats = rag_system.get_stats()
            agent_stats = rag_agent.get_stats()
            
            print(f"\n📊 RAG System Stats:")
            for key, value in rag_stats.items():
                print(f"  {key}: {value}")
            
            print(f"\n📊 RAG Agent Stats:")
            for key, value in agent_stats.items():
                if key != 'rag_system_stats':  # Avoid nested stats
                    print(f"  {key}: {value}")
            
        except Exception as e:
            print(f"❌ Health check failed: {e}")


async def main():
    """Main function."""
    print("🚀 RAG System Standalone Tester")
    print("=" * 50)
    
    tester = RAGTester()
    
    # Initialize RAG system
    if not await tester.initialize_rag():
        print("❌ Cannot proceed without RAG system initialization")
        return
    
    # Show menu
    while True:
        print("\n📋 Available Options:")
        print("1. Interactive testing (ask your own questions)")
        print("2. Run predefined test suite")
        print("3. System health check")
        print("4. Exit")
        
        choice = input("\n🎯 Select option (1-4): ").strip()
        
        if choice == '1':
            await tester.interactive_mode()
        elif choice == '2':
            await tester.run_predefined_tests()
        elif choice == '3':
            await tester.health_check()
        elif choice == '4':
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please select 1-4.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1) 