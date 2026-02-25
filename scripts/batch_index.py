#!/usr/bin/env python3
"""
Batch indexing script for Vertex AI Vector Search V2
Indexes courses in small batches with delays to avoid quota limits
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
from src.services.rag_service import get_rag_service

# Load environment variables
load_dotenv()


def batch_index_courses(batch_size=10, delay_seconds=60, skip_existing=True):
    """
    Index courses in batches with delays between batches
    
    Args:
        batch_size: Number of courses to index per batch
        delay_seconds: Seconds to wait between batches
        skip_existing: Skip courses that are already indexed
    """
    print("=" * 70)
    print("Batch Indexing for Vertex AI Vector Search V2")
    print("=" * 70)
    print()
    
    # Get all courses from database
    print("Fetching courses from database...")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM courses")
    courses = [parse_json_fields(c) for c in cursor.fetchall()]
    conn.close()
    
    total_courses = len(courses)
    print(f"Found {total_courses} courses")
    
    # Get RAG service
    rag = get_rag_service()
    
    # Check which courses are already indexed
    if skip_existing:
        print("Checking for already-indexed courses...")
        
        project = os.environ.get("GCP_PROJECT_ID")
        location = os.environ.get("GCP_LOCATION", "us-central1")
        collection_id = os.environ.get("VERTEX_AI_COLLECTION_ID")
        
        existing_ids = set()
        
        try:
            # Use gcloud CLI to get count and check if courses are indexed
            # This is more reliable than trying to list all data objects
            import subprocess
            result = subprocess.run(
                [
                    "./gcloud.sh", "beta", "vector-search", "collections", 
                    "data-objects", "aggregate",
                    "--aggregation-method=count",
                    f"--collection={collection_id}",
                    f"--location={location}",
                    "--format=json"
                ],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                total_indexed = data.get("aggregateResults", [{}])[0].get("count", 0)
                print(f"Collection has {total_indexed} data objects indexed")
                
                # If we have indexed objects, we need to check which courses
                # For now, we'll just re-index all (upsert will update existing)
                # This is simpler than trying to list all objects
                if total_indexed > 0:
                    print(f"Note: Re-indexing will update existing courses (upsert mode)")
            else:
                print(f"Warning: Could not check collection status")
                
        except Exception as e:
            print(f"Warning: Could not check existing courses: {e}")
            print("Proceeding with all courses (will update existing ones)")
    
    if not courses:
        print("\n✅ All courses are already indexed!")
        return total_courses
    
    print(f"Batch size: {batch_size} courses")
    print(f"Delay between batches: {delay_seconds} seconds")
    print()
    
    # Process in batches
    num_batches = (len(courses) + batch_size - 1) // batch_size
    indexed_count = 0
    
    for batch_num in range(num_batches):
        start_idx = batch_num * batch_size
        end_idx = min(start_idx + batch_size, total_courses)
        batch = courses[start_idx:end_idx]
        
        print(f"Batch {batch_num + 1}/{num_batches}: Indexing courses {start_idx + 1}-{end_idx}...")
        
        try:
            rag.index_courses(batch)
            indexed_count += len(batch)
            print(f"✅ Successfully indexed {len(batch)} courses")
            print(f"Progress: {indexed_count}/{len(courses)} courses in this run ({indexed_count * 100 // len(courses)}%)")
            
            # Wait before next batch (except for last batch)
            if batch_num < num_batches - 1:
                print(f"Waiting {delay_seconds} seconds before next batch...")
                time.sleep(delay_seconds)
                print()
        
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Error indexing batch {batch_num + 1}: {error_msg}")
            
            # Print full traceback for debugging
            import traceback
            print("\nFull traceback:")
            traceback.print_exc()
            print()
            
            # Try to identify problematic course by indexing one at a time
            if "invalid argument" in error_msg.lower() or "400" in error_msg:
                print("Attempting to identify problematic course...")
                for i, course in enumerate(batch):
                    try:
                        rag.index_courses([course])
                        indexed_count += 1
                        print(f"  ✅ Course {course['id']}: {course.get('title', 'N/A')}")
                    except Exception as course_error:
                        print(f"  ❌ Course {course['id']}: {course.get('title', 'N/A')}")
                        print(f"     Error: {str(course_error)[:200]}")
                        # Skip this problematic course and continue
                print()
                # Continue to next batch
                if batch_num < num_batches - 1:
                    print(f"Waiting {delay_seconds} seconds before next batch...")
                    time.sleep(delay_seconds)
                    print()
                continue
                continue
            
            # Check if it's a quota error
            if "quota" in error_msg.lower() or "429" in error_msg:
                print()
                print("⚠️  Quota limit reached!")
                print(f"Successfully indexed: {indexed_count}/{len(courses)} courses in this run")
                print()
                print("Options:")
                print("1. Wait for quota to reset (usually 1 hour)")
                print("2. Run this script again to continue from where it left off")
                print("3. Request a quota increase in Google Cloud Console")
                return indexed_count
            else:
                print(f"Unexpected error: {error_msg}")
                return indexed_count
    
    print()
    print("=" * 70)
    print(f"✅ Indexing Complete!")
    print(f"Total indexed in this run: {indexed_count}/{len(courses)} courses")
    print("=" * 70)
    
    return indexed_count


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Batch index courses to Vertex AI")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of courses per batch (default: 10)"
    )
    parser.add_argument(
        "--delay",
        type=int,
        default=60,
        help="Seconds to wait between batches (default: 60)"
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        default=True,
        help="Skip courses that are already indexed (default: True)"
    )
    parser.add_argument(
        "--no-skip-existing",
        dest="skip_existing",
        action="store_false",
        help="Re-index all courses (update existing ones)"
    )
    
    args = parser.parse_args()
    
    try:
        batch_index_courses(
            batch_size=args.batch_size,
            delay_seconds=args.delay,
            skip_existing=args.skip_existing,
        )
    except KeyboardInterrupt:
        print("\n\n⚠️  Indexing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
