#!/usr/bin/env python3
"""
Simple shard reorganization - copy content from original files to collection-based files.
"""

import json
import os
import re
from collections import defaultdict
from pathlib import Path

def extract_collection_from_url(url):
    """Extract collection name from URL using segment_index: 1 logic."""
    try:
        if 'jgengineering.ie' in url:
            path = url.split('jgengineering.ie', 1)[1]
        else:
            path = url
            
        segments = [s for s in path.split('/') if s]
        
        if len(segments) >= 2 and segments[0] == 'collections':
            return segments[1]
        
        return None
    except Exception as e:
        print(f"Error extracting collection from {url}: {e}")
        return None

def reorganize_shards(domain):
    """Reorganize shards by copying content from original files."""
    print(f"🔧 Reorganizing shards for {domain}...")
    
    base_path = Path(f"out/{domain}")
    
    # Load original manifest
    with open(base_path / f"llms-{domain}-manifest.json") as f:
        manifest = json.load(f)
    
    # Group URLs by collection
    collection_urls = defaultdict(list)
    
    print("📊 Analyzing URLs by collection...")
    
    for shard_name, urls in manifest.items():
        print(f"  Processing shard: {shard_name} ({len(urls)} URLs)")
        
        for url in urls:
            collection = extract_collection_from_url(url)
            if collection:
                collection_urls[collection].append(url)
            else:
                # Keep original shard name for non-collection URLs
                collection_urls[shard_name].append(url)
    
    print(f"\n📈 Found {len(collection_urls)} collections:")
    for collection, urls in sorted(collection_urls.items()):
        print(f"  {collection}: {len(urls)} URLs")
    
    # Create new shard files by copying content from originals
    print(f"\n📝 Creating new shard files...")
    new_manifest = {}
    
    for collection, urls in collection_urls.items():
        if not urls:
            continue
            
        # Create shard file
        shard_filename = f"llms-{domain}-{collection}.txt"
        shard_path = base_path / shard_filename
        
        new_manifest[collection] = urls
        
        # Find which original shard contains these URLs
        original_shard = None
        for orig_shard, orig_urls in manifest.items():
            if any(url in orig_urls for url in urls):
                original_shard = orig_shard
                break
        
        if original_shard:
            # Copy content from original shard
            original_file = base_path / f"llms-{domain}-{original_shard}.txt"
            if original_file.exists():
                with open(original_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract only the content for URLs in this collection
                url_content_map = {}
                sections = re.split(r'<\|(https?://[^|]+)\|>', content)
                
                for i in range(1, len(sections), 2):
                    if i + 1 < len(sections):
                        url = sections[i].strip()
                        content_section = sections[i + 1]
                        if url in urls:
                            url_content_map[url] = f"<|{url}|>{content_section}"
                
                # Write the filtered content
                with open(shard_path, 'w', encoding='utf-8') as f:
                    for url in urls:
                        if url in url_content_map:
                            f.write(url_content_map[url])
                            if url != urls[-1]:  # Not the last URL
                                f.write("\n\n")
                        else:
                            # Placeholder if content not found
                            f.write(f"<|{url}|>\n## Content not found\n\n")
                
                print(f"  ✅ Created: {shard_filename} ({len(urls)} URLs) from {original_shard}")
            else:
                print(f"  ⚠️  Original file not found: {original_file}")
        else:
            print(f"  ⚠️  No original shard found for collection: {collection}")
    
    # Update manifest
    manifest_path = base_path / f"llms-{domain}-manifest.json"
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(new_manifest, f, indent=2)
    
    print(f"\n🎉 Reorganization complete!")
    print(f"   Old shards: {len(manifest)}")
    print(f"   New shards: {len(new_manifest)}")
    print(f"   Updated manifest: {manifest_path}")
    
    return new_manifest

def main():
    domain = "jgengineering-ie"
    new_manifest = reorganize_shards(domain)
    
    print(f"\n📊 Final Results:")
    print(f"   Total collections: {len(new_manifest)}")
    print(f"   Total URLs: {sum(len(urls) for urls in new_manifest.values())}")
    
    # Show top 10 collections by size
    sorted_collections = sorted(new_manifest.items(), key=lambda x: len(x[1]), reverse=True)
    print(f"\n🏆 Top 10 collections by URL count:")
    for i, (collection, urls) in enumerate(sorted_collections[:10], 1):
        print(f"   {i:2d}. {collection}: {len(urls)} URLs")

if __name__ == "__main__":
    main()
