#!/usr/bin/env python3
"""
Script to create a Vertex AI Vector Search 2.0 Collection for the Dandori project.

This script creates a collection with the proper schema for storing course data
with filterable metadata fields.

Usage:
    python scripts/create_vertex_collection.py
    
Environment variables required:
    - GCP_PROJECT_ID: Your Google Cloud project ID
    - GCP_LOCATION: GCP region (e.g., europe-west2)
    - VERTEX_AI_COLLECTION_ID: Desired collection ID (e.g., dandori-courses-collection)
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def create_collection():
    """Create a Vertex AI Vector Search 2.0 Collection"""
    from google.cloud import vectorsearch_v1beta
    
    # Get configuration from environment
    project_id = os.environ.get("GCP_PROJECT_ID")
    location = os.environ.get("GCP_LOCATION", "us-central1")
    collection_id = os.environ.get("VERTEX_AI_COLLECTION_ID", "dandori-courses-collection")
    
    if not project_id:
        raise ValueError("GCP_PROJECT_ID environment variable is required")
    
    print(f"Creating Vertex AI Vector Search Collection...")
    print(f"  Project: {project_id}")
    print(f"  Location: {location}")
    print(f"  Collection ID: {collection_id}")
    print()
    
    # Create the Vector Search service client
    vector_search_service_client = vectorsearch_v1beta.VectorSearchServiceClient()
    
    # Define the data schema for course metadata
    data_schema = {
        "type": "object",
        "properties": {
            "id": {"type": "number"},
            "course_type": {"type": "string"},
            "location": {"type": "string"},
            "instructor": {"type": "string"},
            "cost": {"type": "string"},
            "page_content": {"type": "string"},
        },
    }
    
    # Define the vector schema with embedding field
    vector_schema = {
        "embedding": {
            "dense_vector": {
                "dimensions": 768  # For text-embedding-005
            }
        },
    }
    
    # Create the collection object
    collection = vectorsearch_v1beta.Collection(
        display_name="Dandori Courses Collection",
        description="Vector search collection for School of Dandori courses with semantic search and filtering",
        data_schema=data_schema,
        vector_schema=vector_schema,
    )
    
    # Create the request
    request = vectorsearch_v1beta.CreateCollectionRequest(
        parent=f"projects/{project_id}/locations/{location}",
        collection_id=collection_id,
        collection=collection,
    )
    
    print("Sending create collection request...")
    operation = vector_search_service_client.create_collection(request=request)
    print(f"Operation started: {operation.operation.name}")
    print("Waiting for operation to complete (this may take a few minutes)...")
    print()
    
    # Wait for the operation to complete
    result = operation.result()
    
    print("✅ Collection created successfully!")
    print(f"Resource name: {result.name}")
    print()
    print("You can now use this collection in your application.")
    print(f"Make sure your .env file has:")
    print(f"  VERTEX_AI_API_VERSION=v2")
    print(f"  VERTEX_AI_COLLECTION_ID={collection_id}")
    print()
    
    return result


def check_collection_exists():
    """Check if collection already exists"""
    from google.cloud import vectorsearch_v1beta
    from google.api_core import exceptions
    
    project_id = os.environ.get("GCP_PROJECT_ID")
    location = os.environ.get("GCP_LOCATION", "us-central1")
    collection_id = os.environ.get("VERTEX_AI_COLLECTION_ID", "dandori-courses-collection")
    
    if not project_id:
        return False
    
    try:
        client = vectorsearch_v1beta.VectorSearchServiceClient()
        collection_name = f"projects/{project_id}/locations/{location}/collections/{collection_id}"
        
        request = vectorsearch_v1beta.GetCollectionRequest(name=collection_name)
        collection = client.get_collection(request=request)
        
        print(f"✅ Collection already exists: {collection.name}")
        print(f"Display name: {collection.display_name}")
        print(f"Description: {collection.description}")
        print()
        return True
    except exceptions.NotFound:
        return False
    except Exception as e:
        print(f"Error checking collection: {e}")
        return False


if __name__ == "__main__":
    try:
        print("=" * 70)
        print("Vertex AI Vector Search 2.0 Collection Setup")
        print("=" * 70)
        print()
        
        # Check if collection already exists
        if check_collection_exists():
            print("Collection already exists. No action needed.")
            print("If you want to recreate it, delete the existing collection first.")
            sys.exit(0)
        
        # Create the collection
        create_collection()
        
        print("=" * 70)
        print("Setup complete!")
        print("=" * 70)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
