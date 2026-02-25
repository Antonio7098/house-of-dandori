#!/usr/bin/env python3
"""Test V2 vector search functionality"""

import os
from dotenv import load_dotenv

load_dotenv()

# Test the vector search
from src.services.rag_service import get_rag_service

print("=" * 70)
print("Testing Vertex AI V2 Vector Search")
print("=" * 70)
print()

# Initialize RAG service
print("Initializing RAG service...")
rag = get_rag_service()
print(f"✅ RAG service initialized")
print(f"   Provider: {rag.vector_store.__class__.__name__}")
print(f"   API Version: {rag.vector_store.api_version}")
print(f"   Collection: {rag.vector_store.collection_id}")
print()

# Test queries
test_queries = [
    "Baking courses",
    "Poetry classes",
    "Art workshops",
    "Cooking lessons",
    "Dance classes"
]

for query in test_queries:
    print(f"Query: '{query}'")
    print("-" * 70)
    
    try:
        results = rag.search(query, n_results=5)
        
        if results and results.get('ids') and results['ids'][0]:
            print(f"✅ Found {len(results['ids'][0])} results:")
            for i, (doc_id, doc, metadata, distance) in enumerate(zip(
                results['ids'][0],
                results['documents'][0],
                results['metadatas'][0],
                results['distances'][0]
            ), 1):
                print(f"\n  {i}. ID: {doc_id}")
                print(f"     Distance: {distance:.4f}")
                print(f"     Title: {metadata.get('title', 'N/A')}")
                print(f"     Type: {metadata.get('course_type', 'N/A')}")
                print(f"     Location: {metadata.get('location', 'N/A')}")
                print(f"     Content: {doc[:100]}...")
        else:
            print("❌ No results found")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print()

print("=" * 70)
print("Test Complete!")
print("=" * 70)
