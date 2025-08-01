#!/usr/bin/env python3
"""Comprehensive test script for the AI agent workflow with real Delve data."""

import asyncio
import sys
import os
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.models.schemas import SupportMessage, MessageCategory, UrgencyLevel
from src.simple_workflow import simple_workflow


async def test_agent_with_prompt(prompt: str, description: str = None):
    """Test the AI agent with a specific prompt."""
    print(f"\n" + "="*80)
    print(f"🧪 TEST: {description or prompt}")
    print(f"📝 Prompt: '{prompt}'")
    print("="*80)
    
    # Create test message
    test_message = SupportMessage(
        message_id=f"test_{datetime.now().timestamp()}",
        channel_id="test_channel",
        user_id="test_user",
        timestamp=datetime.now(),
        content=prompt,
        thread_ts=None
    )
    
    start_time = datetime.now()
    
    try:
        # Process through workflow
        print("⏳ Processing through AI workflow...")
        final_state = await simple_workflow.process_message(test_message)
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        # Display results
        print(f"\n✅ RESULTS:")
        print(f"   ⏱️  Processing Time: {processing_time:.2f}s")
        print(f"   🚨 Escalated: {'Yes' if final_state.escalated else 'No'}")
        print(f"   🤖 Agents Used: {len(final_state.agent_responses)}")
        
        # Show agent responses
        for i, response in enumerate(final_state.agent_responses, 1):
            print(f"\n   {i}. 🤖 {response.agent_name}:")
            print(f"      📊 Confidence: {response.confidence_score:.2f}")
            print(f"      💬 Response: {response.response_text[:150]}...")
            if response.sources:
                print(f"      📚 Sources: {len(response.sources)} documents")
                for source in response.sources[:2]:  # Show first 2 sources
                    print(f"         • {source}")
            if response.should_escalate:
                print(f"      ⚠️  Escalation Reason: {response.escalation_reason}")
        
        print(f"\n   🎯 FINAL RESPONSE:")
        print(f"      {final_state.final_response}")
        
        # Analyze categorization
        print(f"\n   📋 MESSAGE ANALYSIS:")
        print(f"      Category: {test_message.category.value}")
        print(f"      Urgency: {test_message.urgency_level.value}")
        
        return {
            'success': True,
            'processing_time': processing_time,
            'escalated': final_state.escalated,
            'agents_used': len(final_state.agent_responses),
            'final_response': final_state.final_response,
            'category': test_message.category.value,
            'urgency': test_message.urgency_level.value
        }
        
    except Exception as e:
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        print(f"\n❌ ERROR:")
        print(f"   Processing Time: {processing_time:.2f}s")
        print(f"   Error: {str(e)}")
        
        return {
            'success': False,
            'processing_time': processing_time,
            'error': str(e)
        }


async def run_comprehensive_tests():
    """Run comprehensive tests covering different scenarios."""
    
    print("🚀 COMPREHENSIVE AI AGENT TESTING")
    print("Testing Delve Slack Support AI Agent with real company data")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test cases covering different scenarios
    test_cases = [
        # Company Overview Questions
        {
            "prompt": "What is Delve?",
            "description": "Basic company information query"
        },
        {
            "prompt": "Who founded Delve and when?",
            "description": "Company background details"
        },
        {
            "prompt": "How much funding has Delve raised?",
            "description": "Funding information query"
        },
        
        # SOC 2 Compliance Questions
        {
            "prompt": "How long does SOC 2 implementation take with Delve?",
            "description": "SOC 2 timeline query"
        },
        {
            "prompt": "What's included in your SOC 2 service?",
            "description": "SOC 2 service details"
        },
        {
            "prompt": "Can you help us get SOC 2 compliant in one week?",
            "description": "Urgent SOC 2 request"
        },
        
        # HIPAA Compliance Questions
        {
            "prompt": "We're a healthcare startup. How can Delve help with HIPAA compliance?",
            "description": "HIPAA compliance inquiry"
        },
        {
            "prompt": "What are the HIPAA safeguards you help implement?",
            "description": "Technical HIPAA details"
        },
        
        # GDPR Questions
        {
            "prompt": "Do you support GDPR compliance for EU customers?",
            "description": "GDPR support query"
        },
        {
            "prompt": "How do you handle data subject access requests under GDPR?",
            "description": "Specific GDPR requirement"
        },
        
        # Pricing and Business Questions
        {
            "prompt": "What does Delve cost?",
            "description": "Pricing inquiry"
        },
        {
            "prompt": "Is penetration testing included in the price?",
            "description": "Specific pricing component"
        },
        {
            "prompt": "Can your team join our sales calls?",
            "description": "Sales support request"
        },
        
        # Technical Integration Questions
        {
            "prompt": "We use AWS and GitHub. Do you integrate with these?",
            "description": "Technical integration query"
        },
        {
            "prompt": "How do your AI agents work for evidence collection?",
            "description": "Technical AI capabilities"
        },
        
        # Customer Success Questions
        {
            "prompt": "Can you show me case studies of companies like ours?",
            "description": "Social proof request"
        },
        {
            "prompt": "How did Lovable get compliant so quickly?",
            "description": "Specific customer story"
        },
        
        # Complex/Edge Cases
        {
            "prompt": "We need SOC 2, HIPAA, and GDPR all implemented before our Series A in 2 weeks. Can you help?",
            "description": "Complex multi-framework urgency"
        },
        {
            "prompt": "Our auditor is asking for specific evidence about our access controls. What can you provide?",
            "description": "Technical audit support"
        },
        
        # Unrelated/Off-topic Questions
        {
            "prompt": "What's the weather like today?",
            "description": "Completely unrelated query"
        },
        {
            "prompt": "Can you help me write Python code?",
            "description": "Off-topic technical request"
        }
    ]
    
    results = []
    successful_tests = 0
    
    # Run all test cases
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*20} TEST {i}/{len(test_cases)} {'='*20}")
        
        result = await test_agent_with_prompt(
            test_case["prompt"], 
            test_case["description"]
        )
        
        result['test_case'] = test_case["description"]
        result['prompt'] = test_case["prompt"]
        results.append(result)
        
        if result['success']:
            successful_tests += 1
        
        # Small delay between tests
        await asyncio.sleep(1)
    
    # Generate summary report
    print(f"\n" + "="*80)
    print("📊 TEST SUMMARY REPORT")
    print("="*80)
    
    print(f"✅ Successful Tests: {successful_tests}/{len(test_cases)}")
    print(f"❌ Failed Tests: {len(test_cases) - successful_tests}")
    
    # Categorize results
    escalated_count = sum(1 for r in results if r.get('escalated', False))
    auto_resolved_count = successful_tests - escalated_count
    
    print(f"🤖 Auto-Resolved: {auto_resolved_count}")
    print(f"🚨 Escalated: {escalated_count}")
    
    # Average processing time
    avg_time = sum(r['processing_time'] for r in results if 'processing_time' in r) / len(results)
    print(f"⏱️  Average Processing Time: {avg_time:.2f}s")
    
    # Category breakdown
    categories = {}
    for r in results:
        if 'category' in r:
            categories[r['category']] = categories.get(r['category'], 0) + 1
    
    print(f"\n📋 Category Breakdown:")
    for category, count in categories.items():
        print(f"   {category}: {count}")
    
    # Show escalated cases
    escalated_cases = [r for r in results if r.get('escalated', False)]
    if escalated_cases:
        print(f"\n🚨 Escalated Cases:")
        for case in escalated_cases:
            print(f"   • {case['test_case']}")
            print(f"     Prompt: {case['prompt'][:60]}...")
    
    # Show failed cases
    failed_cases = [r for r in results if not r['success']]
    if failed_cases:
        print(f"\n❌ Failed Cases:")
        for case in failed_cases:
            print(f"   • {case['test_case']}")
            print(f"     Error: {case.get('error', 'Unknown error')}")
    
    print(f"\n🎉 Testing completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return results


async def main():
    """Main test function."""
    try:
        results = await run_comprehensive_tests()
        
        # Success criteria
        success_rate = sum(1 for r in results if r['success']) / len(results)
        avg_processing_time = sum(r['processing_time'] for r in results if 'processing_time' in r) / len(results)
        
        print(f"\n🎯 FINAL ASSESSMENT:")
        print(f"   Success Rate: {success_rate:.1%}")
        print(f"   Average Response Time: {avg_processing_time:.2f}s")
        
        if success_rate >= 0.9 and avg_processing_time <= 60:
            print("   🟢 AI Agent: READY FOR PRODUCTION")
        elif success_rate >= 0.8:
            print("   🟡 AI Agent: GOOD - Minor improvements needed")
        else:
            print("   🔴 AI Agent: NEEDS WORK - Major improvements required")
        
        return success_rate >= 0.8
        
    except Exception as e:
        print(f"❌ Testing failed with error: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)