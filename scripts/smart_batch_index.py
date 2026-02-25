#!/usr/bin/env python3
"""
Smart batch indexing that skips already-indexed courses to save quota
"""

import os
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from src.core.utils import parse_json_fields
from src.models.database import get_db_connection

# Load environment variables
load_dotenv()


def get_indexed_course_ids():
    """Get list of course IDs that are already indexed"""
    import subprocess
    import json
    
    project = os.environ.get("GCP_PROJECT_ID")
    location = os.environ.get("GCP_LOCATION", "us-central1")
    collection_id = os.environ.get("VERTEX_AI_COLLECTION_ID")
    
    print("Fetching list of indexed courses from Vertex AI...")
    
    # Use gcloud to list data objects
    result = subprocess.run(
        [
            "./gcloud.sh", "beta", "vector-search", "collections",
            "data-objects", "list",
            f"--collection={collection_id}",
            f"--location={location}",
            "--format=json",
            "--limit=10000"
        ],
        capture_output=True,
        text=True
    )
    
    indexed_course_ids = set()
    
    if result.returncode == 0:
        try:
            data_objects = json.loads(result.stdout)
            for obj in data_objects:
                # Extract course ID from data object name
                # Format: projects/.../collections/.../dataObjects/course_123_chunk_0
                obj_name = obj.get("name", "")
                if "/dataObjects/" in obj_name:
                    obj_id = obj_name.split("/dataObjects/")[-1]
                    # Extract course ID from chunk ID (course_123_chunk_0 -> 123)
                    if obj_id.startswith("course_") and "_chunk_" in obj_id:
                        course_id = obj_id.split("_chunk_")[0].replace("course_", "")
                        try:
                            indexed_course_ids.add(int(course_id))
                        except ValueError:
                            pass
            
            print(f"Found {len(indexed_course_ids)} courses already indexed")
        except Exception as e:
            print(f"Warning: Could not parse indexed courses: {e}")
    else:
        print(f"Warning: Could not fetch indexed courses: {result.stderr}")
    
    return indexed_course_ids


def batch_index_courses(batch_size=20, delay_seconds=10):
    """Index only courses that aren't already indexed"""
    print("=" * 70)
    print("Smart Batch Indexing for Vertex AI Vector Search V2")
    print("=" * 70)
    print()
    
    # Get all courses from database
    print("Fetching courses from database...")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM courses")
    all_courses = [parse_json_fields(c) for c in cursor.fetchall()]
    conn.close()
    
    print(f"Found {len(all_courses)} total courses in database")
    
    # Get already-indexed course IDs
    indexed_ids = get_indexed_course_ids()
    
    # Filter to only courses that need indexing
    courses_to_index = [c for c in all_courses if c['id'] not in indexed_ids]
    
    if not courses_to_index:
        print("\n✅ All courses are already indexed!")
        return len(all_courses)
    
    print(f"Courses to index: {len(courses_to_index)}")
    print(f"Batch size: {batch_size} courses")
    print(f"Delay between batches: {delay_seconds} seconds")
    print()
    
    # Get RAG service
    from src.services.rag_service import get_rag_service
    rag = get_rag_service()
    
    # Process in batches
    num_batches = (len(courses_to_index) + batch_size - 1) // batch_size
    indexed_count = 0
    
    for batch_num in range(num_batches):
        start_idx = batch_num * batch_size
        end_idx = min(start_idx + batch_size, len(courses_to_index))
        batch = courses_to_index[start_idx:end_idx]
        
        print(f"Batch {batch_num + 1}/{num_batches}: Indexing courses {start_idx + 1}-{end_idx}...")
        print(f"  Course IDs: {[c['id'] for c in batch]}")
        
        try:
            rag.index_courses(batch)
            indexed_count += len(batch)
            print(f"✅ Successfully indexed {len(batch)} courses")
            print(f"Progress: {indexed_count}/{len(courses_to_index)} ({indexed_count * 100 // len(courses_to_index)}%)")
            
            # Wait before next batch
            if batch_num < num_batches - 1:
                print(f"Waiting {delay_seconds} seconds before next batch...")
                time.sleep(delay_seconds)
                print()
        
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Error indexing batch {batch_num + 1}: {error_msg}")
            
            # Check if it's a quota error
            if "quota" in error_msg.lower() or "429" in error_msg or "resource exhausted" in error_msg.lower():
                print()
                print("⚠️  Quota limit reached!")
                print(f"Successfully indexed: {indexed_count}/{len(courses_to_index)} new courses")
                print(f"Total in collection: {len(indexed_ids) + indexed_count}/{len(all_courses)}")
                print()
                print("Options:")
                print("1. Wait for quota to reset (usually 1 hour)")
                print("2. Run this script again to continue from where it left off")
                print("3. Request a quota increase in Google Cloud Console")
                return indexed_count
            else:
                print(f"Unexpected error: {error_msg}")
                import traceback
                traceback.print_exc()
                return indexed_count
    
    print()
    print("=" * 70)
    print(f"✅ Indexing Complete!")
    print(f"Newly indexed: {indexed_count}/{len(courses_to_index)} courses")
    print(f"Total in collection: {len(indexed_ids) + indexed_count}/{len(all_courses)}")
    print("=" * 70)
    
    return indexed_count


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Smart batch index courses to Vertex AI (skips already-indexed)")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=20,
        help="Number of courses per batch (default: 20)"
    )
    parser.add_argument(
        "--delay",
        type=int,
        default=10,
        help="Seconds to wait between batches (default: 10)"
    )
    
    args = parser.parse_args()
    
    try:
        batch_index_courses(
            batch_size=args.batch_size,
            delay_seconds=args.delay
        )
    except KeyboardInterrupt:
        print("\n\n⚠️  Indexing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
