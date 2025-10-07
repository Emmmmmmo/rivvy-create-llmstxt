#!/usr/bin/env python3
"""
Simple script to process pending queue in batches.
Usage: python3 process_pending_batch.py --batch-size 10 --max-batches 1
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

from update_llms_agnostic import AgnosticLLMsUpdater
import argparse
import json

def main():
    parser = argparse.ArgumentParser(description='Process pending queue in batches')
    parser.add_argument('--batch-size', type=int, default=50, help='Batch size')
    parser.add_argument('--max-batches', type=int, default=1, help='Max batches to process')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    args = parser.parse_args()
    
    # Get Firecrawl API key
    api_key = os.environ.get('FIRECRAWL_API_KEY')
    if not api_key:
        print("Error: FIRECRAWL_API_KEY environment variable not set")
        sys.exit(1)
    
    # Initialize updater
    updater = AgnosticLLMsUpdater(
        firecrawl_api_key=api_key,
        domain='mydiy.ie',
        batch_size=args.batch_size,
        max_batches=args.max_batches,
        dry_run=args.dry_run,
        disable_discovery=True  # Don't discover new URLs
    )
    
    print(f"Pending queue has {len(updater.pending_queue)} items")
    print(f"Processing {args.batch_size} products per batch, max {args.max_batches} batches")
    
    # Process queue
    result = updater.process_queue_batch(args.batch_size)
    
    # Print results
    print("\nResults:")
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()

