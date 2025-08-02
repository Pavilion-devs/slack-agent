#!/usr/bin/env python3
"""
Main Manual Testing Script for Delve Slack Support AI Agent

This script provides an easy way to manually test the improved RAG system.
Run this script to interactively test the system with your own questions.

Usage:
    python run_manual_test.py

Requirements:
    - Ollama running with llama3.2:3b model
    - Virtual environment activated with dependencies installed
"""

import asyncio
import sys
import os
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__)))

from src.core.rag_system import rag_system
from src.agents.rag_agent import RAGAgent
from src.workflows.improved_workflow import ImprovedWorkflow
from src.models.schemas import SupportMessage, MessageCategory, UrgencyLevel


class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m' 
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    """Print a colored header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}\n")


def print_success(text):
    """Print success message."""
    print(f"{Colors.OKGREEN}✅ {text}{Colors.ENDC}")


def print_error(text):
    """Print error message.""" 
    print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")


def print_warning(text):
    """Print warning message."""
    print(f"{Colors.WARNING}⚠️  {text}{Colors.ENDC}")


def print_info(text):
    """Print info message."""
    print(f"{Colors.OKBLUE}ℹ️  {text}{Colors.ENDC}")


async def check_system_setup():
    """Check if the system is properly set up."""
    print_header("SYSTEM SETUP CHECK")
    
    setup_ok = True
    
    # Check Ollama
    try:
        from src.core.rag_system import rag_system
        await rag_system.initialize()
        
        if rag_system.is_initialized:
            print_success("RAG System initialized successfully")
            print_success("FAISS vector database loaded")
            print_success("Ollama llama3.2:3b model ready")
        else:
            print_error("RAG System failed to initialize")
            setup_ok = False
    except Exception as e:
        print_error(f"RAG System error: {e}")
        setup_ok = False
    
    if not setup_ok:
        print_warning("Setup issues detected. Please ensure:")
        print("   1. Ollama is running: ollama serve")
        print("   2. llama3.2:3b model is available: ollama pull llama3.2:3b")
        print("   3. Virtual environment is activated")
        print("   4. Dependencies are installed: pip install -r requirements.txt")
        return False
    
    return True


async def interactive_testing():
    """Interactive testing mode."""
    print_header("INTERACTIVE TESTING MODE")
    
    agent = RAGAgent()
    
    print("🤖 Ready to answer your questions!")
    print("💡 Try asking about:")
    print("   • SOC2, HIPAA, GDPR, or ISO27001 compliance")
    print("   • Delve features and capabilities") 
    print("   • Technical configuration questions")
    print("   • Pricing and demo requests")
    print("\n📝 Type 'quit' to exit, 'examples' for sample questions")
    
    while True:
        print(f"\n{Colors.OKCYAN}{'─' * 60}{Colors.ENDC}")
        question = input(f"{Colors.BOLD}🤔 Your question: {Colors.ENDC}").strip()
        
        if question.lower() in ['quit', 'exit', 'q']:
            print_success("Thanks for testing! Goodbye! 👋")
            break
            
        if question.lower() == 'examples':
            show_example_questions()
            continue
            
        if not question:
            continue
        
        await process_question(agent, question)


def show_example_questions():
    """Show example questions."""
    print(f"\n{Colors.OKBLUE}📝 Example Questions:{Colors.ENDC}")
    
    examples = [
        "What is Delve?",
        "How does SOC2 compliance work with Delve?", 
        "What are the HIPAA requirements for healthcare data?",
        "How do I configure API authentication?",
        "Can you help with GDPR data subject rights?",
        "What are your pricing plans?",
        "How do I export audit logs?",
        "Can we schedule a demo?",
        "What compliance certifications do you have?",
        "How does data encryption work?"
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"   {i:2d}. {example}")


async def process_question(agent, question):
    """Process a single question."""
    print(f"\n{Colors.OKCYAN}🔄 Processing: {question}{Colors.ENDC}")
    
    try:
        start_time = datetime.now()
        
        # Create support message
        message = SupportMessage(
            message_id=f"manual_test_{start_time.timestamp()}",
            channel_id="test_channel",
            user_id="test_user",
            timestamp=start_time, 
            content=question
        )
        
        # Process with RAG agent
        response = await agent.process_message(message)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Display results with nice formatting
        print(f"\n{Colors.BOLD}📊 RESULTS:{Colors.ENDC}")
        print(f"   Agent: {response.agent_name}")
        print(f"   Processing Time: {processing_time:.2f}s")
        print(f"   Confidence: {response.confidence_score:.2f}")
        
        # Color-code confidence
        if response.confidence_score >= 0.8:
            confidence_color = Colors.OKGREEN
        elif response.confidence_score >= 0.6:
            confidence_color = Colors.WARNING
        else:
            confidence_color = Colors.FAIL
        
        print(f"   Confidence Level: {confidence_color}{response.confidence_score:.2f}{Colors.ENDC}")
        
        # Escalation status
        if response.should_escalate:
            print_warning(f"Escalation needed: {response.escalation_reason}")
        else:
            print_success("No escalation needed")
        
        # Frameworks detected
        if hasattr(response, 'metadata') and response.metadata:
            frameworks = response.metadata.get('frameworks_detected', [])
            if frameworks:
                print(f"   Frameworks Detected: {', '.join(frameworks)}")
        
        # Response
        print(f"\n{Colors.BOLD}💬 RESPONSE:{Colors.ENDC}")
        print(f"{response.response_text}")
        
        # Sources
        if response.sources:
            print(f"\n{Colors.BOLD}📚 SOURCES ({len(response.sources)}):{Colors.ENDC}")
            for i, source in enumerate(response.sources, 1):
                print(f"   {i}. {source}")
                
    except Exception as e:
        print_error(f"Error processing question: {e}")
        print_info("Make sure Ollama is running and the model is available")


async def run_test_suite():
    """Run a comprehensive test suite."""
    print_header("COMPREHENSIVE TEST SUITE")
    
    workflow = ImprovedWorkflow()
    
    test_cases = [
        {
            "question": "What is Delve?",
            "category": MessageCategory.GENERAL,
            "expected_confidence": 0.7,
            "description": "Basic product question"
        },
        {
            "question": "How does SOC2 Type II compliance work?",
            "category": MessageCategory.COMPLIANCE,
            "expected_confidence": 0.8,
            "description": "SOC2 compliance question"
        },
        {
            "question": "What HIPAA controls does Delve implement?",
            "category": MessageCategory.COMPLIANCE,
            "expected_confidence": 0.8,
            "description": "HIPAA specific question"
        },
        {
            "question": "How do I configure SAML SSO?",
            "category": MessageCategory.TECHNICAL,
            "expected_confidence": 0.6,
            "description": "Technical configuration"
        },
        {
            "question": "What is quantum computing?",
            "category": MessageCategory.GENERAL,
            "expected_confidence": 0.3,  # Should be low and escalate
            "description": "Out-of-scope question"
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 Test {i}: {test_case['description']}")
        print(f"   Question: {test_case['question']}")
        
        try:
            message = SupportMessage(
                message_id=f"test_{i}",
                channel_id="test_channel",
                user_id="test_user",
                timestamp=datetime.now(),
                content=test_case['question'],
                category=test_case['category']
            )
            
            start_time = datetime.now()
            response = await workflow.process_message(message)
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Evaluate results
            confidence_met = response.confidence_score >= test_case['expected_confidence']
            time_acceptable = processing_time < 30  # Under 30 seconds
            
            print(f"   ✅ Confidence: {response.confidence_score:.2f} (expected ≥ {test_case['expected_confidence']})")
            print(f"   ✅ Time: {processing_time:.2f}s")
            print(f"   ✅ Escalated: {response.should_escalate}")
            
            if confidence_met and time_acceptable:
                print_success(f"Test {i}: PASSED")
            else:
                print_warning(f"Test {i}: Review needed")
            
            results.append({
                'test': i,
                'confidence': response.confidence_score,
                'time': processing_time,
                'passed': confidence_met and time_acceptable
            })
            
        except Exception as e:
            print_error(f"Test {i} failed: {e}")
            results.append({'test': i, 'error': str(e), 'passed': False})
    
    # Summary
    print_header("TEST SUITE SUMMARY")
    
    passed = sum(1 for r in results if r.get('passed', False))
    total = len(results)
    
    if passed == total:
        print_success(f"All tests passed! ({passed}/{total})")
    else:
        print_warning(f"Tests passed: {passed}/{total}")
    
    # Performance metrics
    successful_results = [r for r in results if 'error' not in r]
    if successful_results:
        avg_confidence = sum(r['confidence'] for r in successful_results) / len(successful_results)
        avg_time = sum(r['time'] for r in successful_results) / len(successful_results)
        
        print(f"Average Confidence: {avg_confidence:.2f}")
        print(f"Average Response Time: {avg_time:.2f}s")
        
        if avg_time < 15:
            print_success("🚀 Performance: EXCELLENT")
        elif avg_time < 30:
            print_success("✅ Performance: GOOD")
        else:
            print_warning("⚠️  Performance: NEEDS IMPROVEMENT")


def main():
    """Main function."""
    print_header("DELVE AI SUPPORT AGENT - MANUAL TESTING")
    
    print("Welcome to the Delve AI Support Agent testing suite!")
    print("This tool helps you test the improved LangChain-based RAG system.")
    
    while True:
        print(f"\n{Colors.BOLD}📋 TESTING OPTIONS:{Colors.ENDC}")
        print("1. 🧪 Interactive Testing (Ask your own questions)")
        print("2. 🔬 Run Test Suite (Predefined test cases)")
        print("3. 🔧 System Setup Check")
        print("4. 📖 Show Example Questions")
        print("5. 🚪 Exit")
        
        choice = input(f"\n{Colors.BOLD}Select option (1-5): {Colors.ENDC}").strip()
        
        if choice == "1":
            if asyncio.run(check_system_setup()):
                asyncio.run(interactive_testing())
        elif choice == "2":
            if asyncio.run(check_system_setup()):
                asyncio.run(run_test_suite())
        elif choice == "3":
            asyncio.run(check_system_setup())
        elif choice == "4":
            show_example_questions()
        elif choice == "5":
            print_success("Goodbye! 👋")
            break
        else:
            print_warning("Invalid choice. Please select 1-5.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_warning("\nTesting interrupted by user. Goodbye! 👋")
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        print_info("Please check your setup and try again.")