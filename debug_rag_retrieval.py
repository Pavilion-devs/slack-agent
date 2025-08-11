#!/usr/bin/env python3
"""
Debug RAG Retrieval Script

This script will show us EXACTLY what documents are being retrieved
for the pricing query and WHY the system is giving generic responses.
"""

import asyncio
import sys
import os

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.core.rag_system import rag_system

async def debug_retrieval():
    """Debug what's being retrieved for the problematic query."""
    
    print("🔍 RAG Retrieval Debugger")
    print("=" * 50)
    
    # Initialize RAG system
    print("🔧 Initializing RAG system...")
    success = await rag_system.initialize()
    if not success:
        print("❌ Failed to initialize RAG system")
        return
    
    print("✅ RAG system initialized")
    
    # Test the problematic query
    query = "I work at a startup with 25 employees. What's your pricing for my company size?"
    
    print(f"\n🎯 Testing Query: '{query}'")
    print("-" * 60)
    
    try:
        # Get the retriever directly
        if hasattr(rag_system, 'retriever') and rag_system.retriever:
            print("📚 Retrieving relevant documents...")
            
            # Get relevant documents
            docs = await rag_system.retriever.aget_relevant_documents(query)
            
            print(f"\n📊 Retrieved {len(docs)} documents:")
            print("=" * 40)
            
            for i, doc in enumerate(docs, 1):
                print(f"\n📄 Document {i}:")
                print(f"Content: {doc.page_content[:200]}...")
                print(f"Source: {doc.metadata.get('source', 'Unknown')}")
                if 'score' in doc.metadata:
                    print(f"Relevance Score: {doc.metadata['score']:.3f}")
                print("-" * 30)
        
        # Now get the full RAG response
        print(f"\n🤖 Full RAG Response:")
        print("=" * 40)
        
        rag_result = await rag_system.query(query)
        
        print(f"Answer: {rag_result.get('answer', 'No answer')}")
        print(f"Confidence: {rag_result.get('confidence', 0.0)}")
        print(f"Should Escalate: {rag_result.get('should_escalate', False)}")
        print(f"Sources: {rag_result.get('sources', [])}")
        
        # Test a simpler query for comparison
        print(f"\n🔬 Comparison - Simple Query:")
        print("=" * 40)
        
        simple_query = "What is your pricing?"
        simple_result = await rag_system.query(simple_query)
        
        print(f"Simple Query: '{simple_query}'")
        print(f"Simple Answer: {simple_result.get('answer', 'No answer')[:150]}...")
        print(f"Simple Confidence: {simple_result.get('confidence', 0.0)}")
        
        # Analyze the difference
        print(f"\n🧠 Analysis:")
        print("=" * 40)
        
        if rag_result.get('answer') == simple_result.get('answer'):
            print("❌ PROBLEM IDENTIFIED: Both queries return identical answers!")
            print("   The system is NOT processing the '25 employees' context.")
            print("   It's treating both as generic 'pricing' queries.")
        else:
            print("✅ Queries return different answers - context is being processed")
        
        # Check if knowledge base has company-size-specific info
        size_specific_query = "pricing for 25 employees"
        size_result = await rag_system.query(size_specific_query)
        
        print(f"\n🎯 Size-Specific Query: '{size_specific_query}'")
        print(f"Size Answer: {size_result.get('answer', 'No answer')[:150]}...")
        print(f"Size Confidence: {size_result.get('confidence', 0.0)}")
        
        if size_result.get('answer') == rag_result.get('answer'):
            print("❌ CONFIRMED: System has NO size-specific pricing information!")
            print("   All pricing queries return the same generic response.")
        
    except Exception as e:
        print(f"❌ Error during debugging: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        asyncio.run(debug_retrieval())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)