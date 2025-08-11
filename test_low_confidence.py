#!/usr/bin/env python3
"""
Test confidence extraction with a query that should have low confidence or escalate
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

async def test_low_confidence_queries():
    """Test queries that should result in escalation."""
    
    print("🧪 Testing Low Confidence Queries")
    print("=" * 50)
    
    # Initialize RAG system
    print("1️⃣ Initializing RAG system...")
    success = await rag_system.initialize()
    
    if not success:
        print("❌ Failed to initialize RAG system")
        return
    
    print("✅ RAG system initialized successfully")
    
    # Test queries that should have low confidence or escalate
    test_queries = [
        "What's the weather like today?",  # Completely unrelated
        "How do I get a job at Delve?",   # HR question not in knowledge base
        "What's your API rate limit?",    # Specific technical detail that might not be documented
        "Can you help me with my homework?"  # Personal request
    ]
    
    for i, test_question in enumerate(test_queries, 1):
        print(f"\n{i}️⃣ Testing: '{test_question}'")
        print("-" * 50)
        
        # Process the query
        result = await rag_system.query(test_question)
        
        print(f"   Answer: {result['answer'][:150]}...")
        print(f"   Confidence: {result['confidence']}")
        print(f"   Should Escalate: {result['should_escalate']}")
        print(f"   Escalation Reason: {result['escalation_reason']}")
        print(f"   Retrieved Docs: {result.get('retrieved_docs_count', 0)}")
        
        # Analyze results
        if result['should_escalate']:
            print(f"   ✅ Correctly identified for escalation")
        else:
            print(f"   ⚠️  Did not escalate (confidence: {result['confidence']})")

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_low_confidence_queries())