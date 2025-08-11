#!/usr/bin/env python3
"""
Test script to debug confidence extraction returning 0.0
"""
import os
import sys
import asyncio
import logging

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.core.rag_system import rag_system

# Configure logging to see debug messages
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_confidence_extraction():
    """Test the confidence extraction with a simple SOC2 query."""
    
    print("🧪 Testing Confidence Extraction")
    print("=" * 50)
    
    # Initialize RAG system
    print("1️⃣ Initializing RAG system...")
    success = await rag_system.initialize()
    
    if not success:
        print("❌ Failed to initialize RAG system")
        return
    
    print("✅ RAG system initialized successfully")
    
    # Test query that should have good confidence
    test_question = "What is SOC 2?"
    
    print(f"\n2️⃣ Testing question: '{test_question}'")
    print("-" * 30)
    
    # Process the query
    result = await rag_system.query(test_question)
    
    print(f"\n3️⃣ Results:")
    print(f"   Answer: {result['answer'][:200]}...")
    print(f"   Confidence: {result['confidence']}")
    print(f"   Should Escalate: {result['should_escalate']}")
    print(f"   Escalation Reason: {result['escalation_reason']}")
    print(f"   Retrieved Docs Count: {result.get('retrieved_docs_count', 0)}")
    
    # Test the _extract_confidence_score method directly
    print(f"\n4️⃣ Testing confidence extraction directly:")
    
    # Create a sample response with CONFIDENCE: tag
    test_response_with_confidence = """SOC 2 is a security compliance framework that helps organizations demonstrate their commitment to data security.

CONFIDENCE: 0.8"""
    
    # Test with confidence tag
    extracted_confidence = rag_system._extract_confidence_score(test_response_with_confidence)
    print(f"   Response with CONFIDENCE tag: {extracted_confidence}")
    
    # Create a sample response without CONFIDENCE: tag
    test_response_without_confidence = """SOC 2 is a security compliance framework that helps organizations demonstrate their commitment to data security."""
    
    # Test without confidence tag
    extracted_confidence_no_tag = rag_system._extract_confidence_score(test_response_without_confidence)
    print(f"   Response without CONFIDENCE tag: {extracted_confidence_no_tag}")
    
    # Test the actual response from the query
    actual_extracted = rag_system._extract_confidence_score(result['answer'])
    print(f"   Actual query response confidence: {actual_extracted}")
    
    print(f"\n5️⃣ Analysis:")
    if result['confidence'] == 0.0:
        print("   🔍 Confidence is 0.0 - this indicates an issue")
        if "CONFIDENCE:" not in result['answer']:
            print("   📝 The LLM response does not contain CONFIDENCE: tag")
            print("   🤔 This suggests the LLM is not following the prompt template")
        else:
            print("   📝 The LLM response contains CONFIDENCE: tag but extraction failed")
    else:
        print("   ✅ Confidence extraction working correctly")
    
    return result

if __name__ == "__main__":
    # Run the test
    result = asyncio.run(test_confidence_extraction())