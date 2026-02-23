#!/usr/bin/env python3
"""
Ingest PDF course files into the database via the API.

Usage:
    python scripts/ingest_pdfs.py /path/to/pdfs
    python scripts/ingest_pdfs.py ./pdfs
    python scripts/ingest_pdfs.py /path/to/pdfs --api-url https://your-api-url
"""

import argparse
import os
import sys
from pathlib import Path

import requests


def ingest_pdfs(pdf_dir: str, api_url: str = "http://localhost:5000"):
    pdf_path = Path(pdf_dir)

    if not pdf_path.exists():
        print(f"Error: Directory '{pdf_dir}' does not exist")
        sys.exit(1)

    if not pdf_path.is_dir():
        print(f"Error: '{pdf_dir}' is not a directory")
        sys.exit(1)

    pdf_files = list(pdf_path.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDF files found in '{pdf_dir}'")
        sys.exit(0)

    print(f"Found {len(pdf_files)} PDF files to ingest")
    print(f"Uploading to {api_url}...\n")

    # Build files list with open file handles
    file_handles = []
    files = []
    for f in pdf_files:
        fh = open(f, "rb")
        file_handles.append(fh)
        files.append(("files", (f.name, fh, "application/pdf")))

    try:
        response = requests.post(f"{api_url}/api/upload/batch", files=files)
    finally:
        for fh in file_handles:
            fh.close()

    if response.status_code == 200:
        result = response.json()
        print(f"Results: {result['successful']}/{result['total']} successful\n")

        for r in result.get("results", []):
            if r["success"]:
                print(f"  ✓ {r['filename']}: {r.get('title', 'N/A')}")
            else:
                print(f"  ✗ {r['filename']}: {r.get('error', 'Unknown error')}")
    else:
        print(f"Error: {response.status_code} - {response.text}")
        sys.exit(1)


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

    args = parser.parse_args()
    ingest_pdfs(args.path, args.api_url)


if __name__ == "__main__":
    main()
