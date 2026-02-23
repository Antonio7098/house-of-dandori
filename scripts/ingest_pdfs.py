#!/usr/bin/env python3
"""
Ingest PDF course files into the database via the API.

Usage:
    python scripts/ingest_pdfs.py /path/to/pdfs
    python scripts/ingest_pdfs.py ./pdfs --api-url https://your-api-url
"""

import argparse
import re
import sys
from pathlib import Path

import requests


def extract_original_filename(stored_filename: str) -> str:
    """Extract original filename from stored filename (strips UUID prefix)."""
    if not stored_filename:
        return ""
    match = re.match(r"^[a-f0-9]+_(.+)$", stored_filename)
    return match.group(1) if match else stored_filename


def get_existing_courses(api_url: str) -> set:
    """Get existing course filenames from the API (original names, without UUID prefix)."""
    existing = set()
    page = 1
    while True:
        try:
            response = requests.get(
                f"{api_url}/api/courses", params={"limit": 100, "page": page}
            )
            if response.status_code != 200:
                break
            data = response.json()
            courses = data.get("courses", [])
            if not courses:
                break
            for course in courses:
                if course.get("filename"):
                    original = extract_original_filename(course["filename"])
                    existing.add(original)
            page += 1
        except Exception as e:
            print(f"Warning: Could not fetch existing courses: {e}")
            break
    return existing


def upload_batch(api_url: str, pdf_files: list, existing: set) -> dict:
    """Upload a batch of PDFs, skipping existing ones."""
    files_to_upload = []
    for f in pdf_files:
        if f.name not in existing:
            files_to_upload.append(f)

    if not files_to_upload:
        return {"successful": 0, "failed": 0, "skipped": len(pdf_files), "results": []}

    files = []
    file_handles = []
    for f in files_to_upload:
        fh = open(f, "rb")
        file_handles.append(fh)
        files.append(("files", (f.name, fh, "application/pdf")))

    try:
        response = requests.post(
            f"{api_url}/api/upload/batch", files=files, timeout=120
        )
    finally:
        for fh in file_handles:
            fh.close()

    if response.status_code == 200:
        result = response.json()
        # Add skipped count
        result["skipped"] = len(pdf_files) - len(files_to_upload)
        return result
    else:
        return {
            "successful": 0,
            "failed": len(files_to_upload),
            "skipped": len(pdf_files) - len(files_to_upload),
            "results": [],
            "error": f"HTTP {response.status_code}",
        }


def ingest_pdfs(
    pdf_dir: str, api_url: str = "http://localhost:5000", batch_size: int = 10
):
    pdf_path = Path(pdf_dir)

    if not pdf_path.exists():
        print(f"Error: Directory '{pdf_dir}' does not exist")
        sys.exit(1)

    if not pdf_path.is_dir():
        print(f"Error: '{pdf_dir}' is not a directory")
        sys.exit(1)

    pdf_files = sorted(pdf_path.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDF files found in '{pdf_dir}'")
        sys.exit(0)

    print(f"Found {len(pdf_files)} PDF files")
    print(f"Fetching existing courses from API...")

    existing = get_existing_courses(api_url)
    print(f"Already in database: {len(existing)} courses\n")

    # Calculate batches
    total_to_upload = sum(1 for f in pdf_files if f.name not in existing)
    total_batches = (total_to_upload + batch_size - 1) // batch_size

    print(
        f"To upload: {total_to_upload} files ({total_batches} batches of {batch_size})\n"
    )

    successful = 0
    failed = 0
    skipped = 0

    batch_num = 0
    i = 0
    while i < len(pdf_files):
        batch = pdf_files[i : i + batch_size]
        batch_num += 1

        print(
            f"[Batch {batch_num}/{total_batches}] Processing {len(batch)} files...",
            end=" ",
            flush=True,
        )

        result = upload_batch(api_url, batch, existing)

        successful += result.get("successful", 0)
        failed += result.get("failed", 0)
        skipped += result.get("skipped", 0)

        print(
            f"✓{result.get('successful', 0)} ✗{result.get('failed', 0)} ⊘{result.get('skipped', 0)}"
        )

        # Show failures
        for r in result.get("results", []):
            if not r.get("success"):
                print(f"    ✗ {r['filename']}: {r.get('error', 'Unknown error')}")

        i += batch_size

    print(f"\n{'=' * 50}")
    print(f"Complete: {successful} succeeded, {failed} failed, {skipped} skipped")


def main():
    parser = argparse.ArgumentParser(
        description="Ingest PDF course files into the database"
    )
    parser.add_argument("path", help="Path to directory containing PDF files")
    parser.add_argument(
        "--api-url",
        default="http://localhost:5000",
        help="API URL (default: http://localhost:5000)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Number of PDFs per batch (default: 50)",
    )

    args = parser.parse_args()
    ingest_pdfs(args.path, args.api_url, args.batch_size)


if __name__ == "__main__":
    main()
