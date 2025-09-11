#!/usr/bin/env python3
"""
Re-shard existing LLMs data with improved sharding strategy.

This script reads the existing llms-index.json and manifest.json files
and re-organizes them into better, more granular shards.
"""

import os
import json
import re
from typing import Dict, List, Any
from urllib.parse import urlparse
from collections import defaultdict

def sanitize_shard_key(key: str) -> str:
    """Sanitize shard key for filename use."""
    # Remove special characters and replace with underscores
    sanitized = re.sub(r'[^\w\-]', '_', key.lower())
    # Remove multiple underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    # Remove leading/trailing underscores
    sanitized = sanitized.strip('_')
    return sanitized or 'unknown'

def get_improved_shard_key(url: str) -> str:
    """Extract improved shard key from URL."""
    parsed = urlparse(url)
    path = parsed.path.strip('/')
    
    if not path:
        return 'root'
    
    segments = path.split('/')
    
    # For products and collections, use the second segment (category)
    if len(segments) >= 2 and segments[0] in ['products', 'collections']:
        # Use second segment for better categorization
        category = segments[1]
        
        # For products within collections, use the collection name
        if segments[0] == 'collections' and len(segments) >= 4 and segments[2] == 'products':
            category = segments[1]  # Use collection name
        elif segments[0] == 'products':
            # For direct products, try to extract category from product name
            product_name = segments[1]
            # Look for common patterns in product names
            if 'baercoil' in product_name.lower():
                if 'kit' in product_name.lower():
                    return 'baercoil_kits'
                elif 'insert' in product_name.lower():
                    return 'baercoil_inserts'
                elif 'tap' in product_name.lower():
                    return 'baercoil_taps'
                else:
                    return 'baercoil_products'
            elif 'baerfix' in product_name.lower():
                return 'baerfix_products'
            elif 'circlip' in product_name.lower():
                return 'circlips'
            elif 'drill' in product_name.lower():
                return 'drill_bits'
            elif 'tap' in product_name.lower():
                return 'taps'
            else:
                return 'other_products'
        
        return sanitize_shard_key(category)
    
    # For other paths, use first segment
    return sanitize_shard_key(segments[0])

def reshuffle_data(input_dir: str, output_dir: str = None):
    """Re-shuffle existing data into better shards."""
    if output_dir is None:
        output_dir = input_dir
    
    # Read existing data
    index_file = os.path.join(input_dir, 'llms-index.json')
    manifest_file = os.path.join(input_dir, 'manifest.json')
    
    if not os.path.exists(index_file):
        print(f"Error: {index_file} not found")
        return
    
    if not os.path.exists(manifest_file):
        print(f"Error: {manifest_file} not found")
        return
    
    print("Loading existing data...")
    with open(index_file, 'r', encoding='utf-8') as f:
        url_index = json.load(f)
    
    with open(manifest_file, 'r', encoding='utf-8') as f:
        old_manifest = json.load(f)
    
    print(f"Loaded {len(url_index)} URLs from existing data")
    
    # Create new shard organization
    new_shards = defaultdict(list)
    new_url_index = {}
    
    print("Re-sharding URLs...")
    for url, data in url_index.items():
        # Get new shard key
        new_shard_key = get_improved_shard_key(url)
        
        # Add to new shard
        new_shards[new_shard_key].append(url)
        
        # Update shard in data
        data['shard'] = new_shard_key
        new_url_index[url] = data
    
    print(f"Created {len(new_shards)} new shards:")
    for shard, urls in new_shards.items():
        print(f"  {shard}: {len(urls)} URLs")
    
    # Write new shard files
    print("Writing new shard files...")
    for shard_key, urls in new_shards.items():
        shard_file = os.path.join(output_dir, f'llms-full.{shard_key}.txt')
        
        with open(shard_file, 'w', encoding='utf-8') as f:
            for url in urls:
                data = new_url_index[url]
                f.write(f'<|{url}-lllmstxt|>\n')
                f.write(f'## {data["title"]}\n')
                f.write(f'{data["markdown"]}\n\n')
        
        print(f"  Written: {shard_file} ({len(urls)} URLs)")
    
    # Write new manifest
    new_manifest = {shard: urls for shard, urls in new_shards.items()}
    manifest_output = os.path.join(output_dir, 'manifest.json')
    with open(manifest_output, 'w', encoding='utf-8') as f:
        json.dump(new_manifest, f, indent=2)
    
    # Write new index
    index_output = os.path.join(output_dir, 'llms-index.json')
    with open(index_output, 'w', encoding='utf-8') as f:
        json.dump(new_url_index, f, indent=2)
    
    print(f"\nRe-sharding complete!")
    print(f"New manifest: {manifest_output}")
    print(f"New index: {index_output}")
    
    # Show file sizes
    print(f"\nNew shard file sizes:")
    for shard_key in new_shards.keys():
        shard_file = os.path.join(output_dir, f'llms-full.{shard_key}.txt')
        if os.path.exists(shard_file):
            size = os.path.getsize(shard_file)
            lines = sum(1 for _ in open(shard_file, 'r', encoding='utf-8'))
            print(f"  {shard_key}: {size:,} bytes, {lines:,} lines")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 reshard_existing_data.py <input_directory> [output_directory]")
        print("Example: python3 reshard_existing_data.py out/jgengineering.ie")
        sys.exit(1)
    
    input_dir = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    reshuffle_data(input_dir, output_dir)
