#!/usr/bin/env python3
"""
Comprehensive Test Suite for Delve LangGraph Workflow System

This script runs realistic user scenarios to test:
- Intent classification accuracy
- Agent routing correctness  
- Context & memory management
- Response quality
- Performance metrics
- Edge case handling
"""

import asyncio
import sys
import os
import time
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.models.schemas import SupportMessage
from src.workflows.langgraph_workflow import langgraph_workflow
from src.core.intent_classifier import IntentClassifier


@dataclass
class TestResult:
    """Test result data structure."""
    test_name: str
    message: str
    expected_intent: str
    actual_intent: str
    expected_agent: str
    actual_agent: str
    response_text: str
    confidence: float
    processing_time: float
    escalated: bool
    success: bool
    error: Optional[str] = None


class ComprehensiveTestSuite:
    """Comprehensive test suite for the LangGraph workflow system."""
    
    def __init__(self):
        self.classifier = IntentClassifier()
        self.test_results: List[TestResult] = []
        self.session_context = {}  # For context tracking across tests
        
        # Define comprehensive test suites
        self.test_suites = {
            "customer_journey": [
                ("What is Delve?", "information", "enhanced_rag_agent"),
                ("How does SOC2 compliance work?", "information", "enhanced_rag_agent"),
                ("What are your pricing options?", "information", "enhanced_rag_agent"),
                ("Can I schedule a demo?", "scheduling", "demo_scheduler"),
                # Skip interactive slot selection for automated testing
            ],
            
            "technical_user_flow": [
                ("I'm getting a 401 error with your API", "technical_support", "technical_support"),
                ("How do I integrate Delve with existing tools?", "information", "enhanced_rag_agent"),
                ("What's the difference between SOC2 Type 1 and Type 2?", "information", "enhanced_rag_agent"),
                ("Do you support SAML SSO?", "information", "enhanced_rag_agent"),
                ("Can you help me troubleshoot this integration?", "technical_support", "technical_support"),
            ],
            
            "compliance_professional": [
                ("Tell me about HIPAA compliance automation", "information", "enhanced_rag_agent"),
                ("How long does ISO 27001 certification take?", "information", "enhanced_rag_agent"),
                ("What evidence do you collect automatically?", "information", "enhanced_rag_agent"),
                ("I need urgent help with an audit starting Monday", "technical_support", "technical_support"),
                ("Can we schedule a technical deep-dive?", "scheduling", "demo_scheduler"),
            ],
            
            "pricing_and_sales": [
                ("How much does Delve cost?", "information", "enhanced_rag_agent"),
                ("What's included in your enterprise plan?", "information", "enhanced_rag_agent"),
                ("Do you offer volume discounts?", "information", "enhanced_rag_agent"),
                ("Can I get a custom quote for 50 employees?", "information", "enhanced_rag_agent"),
                ("What's your renewal pricing structure?", "information", "enhanced_rag_agent"),
            ],
            
            "edge_cases": [
                ("Hello", "information", "enhanced_rag_agent"),
                ("Help", "information", "enhanced_rag_agent"),
                ("I'm frustrated with your service", "technical_support", "technical_support"),
                ("Can you do everything cheaper than competitors?", "information", "enhanced_rag_agent"),
                ("I need everything done by tomorrow", "information", "enhanced_rag_agent"),
            ],
            
            "language_variations": [
                ("Schedule demo", "scheduling", "demo_scheduler"),
                ("Could you perhaps help me understand pricing?", "information", "enhanced_rag_agent"),
                ("yo what's ur pricing lol", "information", "enhanced_rag_agent"),
                ("I would like to inquire about scheduling a demonstration", "scheduling", "demo_scheduler"),
                ("demo?", "information", "enhanced_rag_agent"),  # Ambiguous - could be info or scheduling
            ],
            
            "compliance_frameworks": [
                ("How does Delve help with GDPR compliance?", "information", "enhanced_rag_agent"),
                ("What's involved in SOC2 Type 2 audit?", "information", "enhanced_rag_agent"),
                ("Tell me about ISO 27001 implementation", "information", "enhanced_rag_agent"),
                ("HIPAA compliance requirements explanation", "information", "enhanced_rag_agent"),
                ("PCI DSS compliance automation", "information", "enhanced_rag_agent"),
            ]
        }
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all test suites and return comprehensive results."""
        print("🚀 Starting Comprehensive Test Suite")
        print("=" * 60)
        
        overall_start_time = time.time()
        suite_results = {}
        
        for suite_name, test_cases in self.test_suites.items():
            print(f"\n📋 Running Test Suite: {suite_name.upper()}")
            print("-" * 40)
            
            suite_start_time = time.time()
            suite_results[suite_name] = await self.run_test_suite(suite_name, test_cases)
            suite_time = time.time() - suite_start_time
            
            # Suite summary
            suite_success_rate = (sum(1 for r in suite_results[suite_name] if r.success) / 
                                len(suite_results[suite_name])) * 100
            print(f"✅ Suite '{suite_name}' completed in {suite_time:.2f}s")
            print(f"📊 Success Rate: {suite_success_rate:.1f}%")
        
        overall_time = time.time() - overall_start_time
        
        # Generate comprehensive report
        report = self.generate_comprehensive_report(suite_results, overall_time)
        
        # Save detailed results
        await self.save_results(suite_results, report)
        
        return report
    
    async def run_test_suite(self, suite_name: str, test_cases: List[tuple]) -> List[TestResult]:
        """Run a specific test suite."""
        results = []
        
        for i, (message, expected_intent, expected_agent) in enumerate(test_cases, 1):
            print(f"  🧪 Test {i}/{len(test_cases)}: '{message[:50]}{'...' if len(message) > 50 else ''}'")
            
            result = await self.run_single_test(
                test_name=f"{suite_name}_{i}",
                message=message,
                expected_intent=expected_intent,
                expected_agent=expected_agent
            )
            
            results.append(result)
            self.test_results.append(result)
            
            # Brief result display
            status = "✅" if result.success else "❌"
            print(f"    {status} Intent: {result.actual_intent} | Agent: {result.actual_agent[:20]} | Time: {result.processing_time:.2f}s")
            
            if result.error:
                print(f"    ⚠️  Error: {result.error}")
            
            # Small delay to avoid overwhelming the system
            await asyncio.sleep(0.5)
        
        return results
    
    async def run_single_test(self, test_name: str, message: str, expected_intent: str, expected_agent: str) -> TestResult:
        """Run a single test case."""
        start_time = time.time()
        
        try:
            # Create test message - use chainlit_test to avoid Slack API calls
            test_message = SupportMessage(
                message_id=f"test_{test_name}_{int(time.time())}",
                channel_id="chainlit_test",  # Use chainlit channel to avoid Slack API
                user_id="test_user",
                timestamp=datetime.now(),
                content=message,
                thread_ts=None,
                user_name="Test User",
                user_email="test@example.com"
            )
            
            # Test intent classification
            intent_result = await self.classifier.classify_intent(message)
            actual_intent = intent_result['intent']
            
            # Process through workflow - use direct LangGraph workflow
            workflow_result = await langgraph_workflow.process_message(test_message)
            
            processing_time = time.time() - start_time
            
            # Extract results - handle dictionary response structure
            actual_agent = "unknown"
            response_text = ""
            confidence = 0.0
            escalated = True
            
            # Handle dictionary response from LangGraph workflow
            if isinstance(workflow_result, dict):
                # Get final response
                if 'final_response' in workflow_result and workflow_result['final_response']:
                    final_resp = workflow_result['final_response']
                    actual_agent = final_resp.agent_name
                    confidence = final_resp.confidence_score
                    escalated = final_resp.should_escalate
                    response_text = final_resp.response_text
                
                # Fallback to subgraph results
                elif 'subgraph_results' in workflow_result:
                    for agent_key, result in workflow_result['subgraph_results'].items():
                        actual_agent = result.agent_name
                        confidence = result.confidence_score
                        escalated = result.should_escalate
                        response_text = result.response_text
                        break
            
            # Legacy object-based response handling
            elif hasattr(workflow_result, 'agent_responses') and workflow_result.agent_responses:
                latest_response = workflow_result.agent_responses[-1]
                actual_agent = latest_response.agent_name
                confidence = latest_response.confidence_score
                escalated = latest_response.should_escalate
                response_text = latest_response.response_text
            elif hasattr(workflow_result, 'final_response'):
                if hasattr(workflow_result.final_response, 'response_text'):
                    response_text = workflow_result.final_response.response_text
            
            # Determine success
            intent_correct = actual_intent == expected_intent
            agent_correct = expected_agent.lower() in actual_agent.lower()
            success = intent_correct and agent_correct and not (confidence < 0.3)
            
            return TestResult(
                test_name=test_name,
                message=message,
                expected_intent=expected_intent,
                actual_intent=actual_intent,
                expected_agent=expected_agent,
                actual_agent=actual_agent,
                response_text=response_text,
                confidence=confidence,
                processing_time=processing_time,
                escalated=escalated,
                success=success
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            return TestResult(
                test_name=test_name,
                message=message,
                expected_intent=expected_intent,
                actual_intent="error",
                expected_agent=expected_agent,
                actual_agent="error",
                response_text="",
                confidence=0.0,
                processing_time=processing_time,
                escalated=True,
                success=False,
                error=str(e)
            )
    
    def generate_comprehensive_report(self, suite_results: Dict[str, List[TestResult]], total_time: float) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        all_results = [result for results in suite_results.values() for result in results]
        
        # Overall metrics
        total_tests = len(all_results)
        successful_tests = sum(1 for r in all_results if r.success)
        success_rate = (successful_tests / total_tests) * 100 if total_tests > 0 else 0
        
        # Intent classification accuracy
        correct_intents = sum(1 for r in all_results if r.actual_intent == r.expected_intent)
        intent_accuracy = (correct_intents / total_tests) * 100 if total_tests > 0 else 0
        
        # Agent routing accuracy
        correct_agents = sum(1 for r in all_results if r.expected_agent.lower() in r.actual_agent.lower())
        agent_accuracy = (correct_agents / total_tests) * 100 if total_tests > 0 else 0
        
        # Performance metrics
        processing_times = [r.processing_time for r in all_results if r.processing_time > 0]
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
        min_time = min(processing_times) if processing_times else 0
        max_time = max(processing_times) if processing_times else 0
        
        # Confidence metrics
        confidences = [r.confidence for r in all_results if r.confidence > 0]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        # Error analysis
        errors = [r for r in all_results if r.error]
        escalations = [r for r in all_results if r.escalated]
        
        # Per-suite breakdown
        suite_breakdown = {}
        for suite_name, results in suite_results.items():
            suite_success = sum(1 for r in results if r.success)
            suite_breakdown[suite_name] = {
                'total': len(results),
                'successful': suite_success,
                'success_rate': (suite_success / len(results)) * 100,
                'avg_time': sum(r.processing_time for r in results) / len(results),
                'avg_confidence': sum(r.confidence for r in results if r.confidence > 0) / 
                                len([r for r in results if r.confidence > 0]) if any(r.confidence > 0 for r in results) else 0
            }
        
        return {
            'timestamp': datetime.now().isoformat(),
            'overall_metrics': {
                'total_tests': total_tests,
                'successful_tests': successful_tests,
                'success_rate': success_rate,
                'intent_accuracy': intent_accuracy,
                'agent_accuracy': agent_accuracy,
                'total_time': total_time
            },
            'performance_metrics': {
                'avg_processing_time': avg_processing_time,
                'min_processing_time': min_time,
                'max_processing_time': max_time,
                'avg_confidence': avg_confidence
            },
            'error_analysis': {
                'total_errors': len(errors),
                'total_escalations': len(escalations),
                'escalation_rate': (len(escalations) / total_tests) * 100,
                'error_messages': [e.error for e in errors if e.error]
            },
            'suite_breakdown': suite_breakdown,
            'failed_tests': [
                {
                    'test_name': r.test_name,
                    'message': r.message,
                    'expected_intent': r.expected_intent,
                    'actual_intent': r.actual_intent,
                    'expected_agent': r.expected_agent,
                    'actual_agent': r.actual_agent,
                    'error': r.error
                } for r in all_results if not r.success
            ]
        }
    
    async def save_results(self, suite_results: Dict[str, List[TestResult]], report: Dict[str, Any]):
        """Save test results to files."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save comprehensive report
        report_file = f"test_report_{timestamp}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Save detailed results
        detailed_results = {}
        for suite_name, results in suite_results.items():
            detailed_results[suite_name] = [
                {
                    'test_name': r.test_name,
                    'message': r.message,
                    'expected_intent': r.expected_intent,
                    'actual_intent': r.actual_intent,
                    'expected_agent': r.expected_agent,
                    'actual_agent': r.actual_agent,
                    'response_text': r.response_text[:200] + "..." if len(r.response_text) > 200 else r.response_text,
                    'confidence': r.confidence,
                    'processing_time': r.processing_time,
                    'escalated': r.escalated,
                    'success': r.success,
                    'error': r.error
                } for r in results
            ]
        
        results_file = f"detailed_results_{timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump(detailed_results, f, indent=2, default=str)
        
        print(f"\n💾 Results saved:")
        print(f"   📄 Report: {report_file}")
        print(f"   📄 Details: {results_file}")
    
    def print_summary_report(self, report: Dict[str, Any]):
        """Print a beautiful summary report."""
        print("\n" + "="*80)
        print("🏆 COMPREHENSIVE TEST SUITE RESULTS")
        print("="*80)
        
        overall = report['overall_metrics']
        performance = report['performance_metrics']
        errors = report['error_analysis']
        
        print(f"\n📊 OVERALL PERFORMANCE:")
        print(f"   Total Tests: {overall['total_tests']}")
        print(f"   Successful: {overall['successful_tests']} ({overall['success_rate']:.1f}%)")
        print(f"   Intent Accuracy: {overall['intent_accuracy']:.1f}%")
        print(f"   Agent Routing Accuracy: {overall['agent_accuracy']:.1f}%")
        print(f"   Total Runtime: {overall['total_time']:.2f}s")
        
        print(f"\n⚡ PERFORMANCE METRICS:")
        print(f"   Average Response Time: {performance['avg_processing_time']:.2f}s")
        print(f"   Fastest Response: {performance['min_processing_time']:.2f}s")
        print(f"   Slowest Response: {performance['max_processing_time']:.2f}s")
        print(f"   Average Confidence: {performance['avg_confidence']:.2f}")
        
        print(f"\n🚨 ERROR ANALYSIS:")
        print(f"   Total Errors: {errors['total_errors']}")
        print(f"   Escalations: {errors['total_escalations']} ({errors['escalation_rate']:.1f}%)")
        
        print(f"\n📋 SUITE BREAKDOWN:")
        for suite_name, metrics in report['suite_breakdown'].items():
            print(f"   {suite_name.upper()}: {metrics['successful']}/{metrics['total']} "
                  f"({metrics['success_rate']:.1f}%) - Avg: {metrics['avg_time']:.2f}s")
        
        if report['failed_tests']:
            print(f"\n❌ FAILED TESTS ({len(report['failed_tests'])}):")
            for i, test in enumerate(report['failed_tests'][:5], 1):  # Show first 5 failures
                print(f"   {i}. {test['message'][:50]}...")
                print(f"      Expected: {test['expected_intent']} -> {test['expected_agent']}")
                print(f"      Actual: {test['actual_intent']} -> {test['actual_agent']}")
                if test['error']:
                    print(f"      Error: {test['error'][:100]}")
        
        # Overall assessment
        if overall['success_rate'] >= 90:
            print(f"\n🎉 EXCELLENT! System performing at production level ({overall['success_rate']:.1f}% success rate)")
        elif overall['success_rate'] >= 80:
            print(f"\n👍 GOOD! System ready with minor improvements needed ({overall['success_rate']:.1f}% success rate)")
        elif overall['success_rate'] >= 70:
            print(f"\n⚠️  NEEDS WORK! Several issues to address ({overall['success_rate']:.1f}% success rate)")
        else:
            print(f"\n🚨 CRITICAL ISSUES! Major fixes required ({overall['success_rate']:.1f}% success rate)")
        
        print("="*80)


async def main():
    """Main function to run the comprehensive test suite."""
    print("🧪 Delve LangGraph Workflow - Comprehensive Test Suite")
    print("This will test all aspects of the system with realistic scenarios")
    print("Expected runtime: 5-10 minutes")
    
    # Auto-proceed for automated testing
    print("\nRunning automated comprehensive testing...")
    # confirm = input("\nProceed with comprehensive testing? (y/N): ").strip().lower()
    # if confirm != 'y':
    #     print("Testing cancelled.")
    #     return
    
    # Initialize and run tests
    test_suite = ComprehensiveTestSuite()
    
    try:
        report = await test_suite.run_all_tests()
        test_suite.print_summary_report(report)
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Testing interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Critical error during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())