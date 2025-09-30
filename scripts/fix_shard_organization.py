#!/usr/bin/env python3
"""
Fix shard organization for JG Engineering.
Reorganizes the existing 9 generic shards into 50+ collection-specific shards
without re-scraping the website.
"""

import json
import os
import re
from collections import defaultdict
from pathlib import Path

def extract_collection_from_url(url):
    """Extract collection name from URL using segment_index: 1 logic."""
    try:
        # Remove base URL
        if 'jgengineering.ie' in url:
            path = url.split('jgengineering.ie', 1)[1]
        else:
            path = url
            
        # Split into segments
        segments = [s for s in path.split('/') if s]
        
        # Find collections segment
        if len(segments) >= 2 and segments[0] == 'collections':
            return segments[1]  # This is segment_index: 1
        
        # Fallback for non-collection URLs
        return None
    except Exception as e:
        print(f"Error extracting collection from {url}: {e}")
        return None

def load_existing_data(domain):
    """Load existing index and manifest data."""
    base_path = Path(f"out/{domain}")
    
    # Load index
    with open(base_path / f"llms-{domain}-index.json") as f:
        index = json.load(f)
    
    # Load manifest
    with open(base_path / f"llms-{domain}-manifest.json") as f:
        manifest = json.load(f)
    
    return index, manifest

def reorganize_shards(domain):
    """Reorganize shards from generic categories to collection-specific."""
    print(f"🔧 Reorganizing shards for {domain}...")
    
    # Load existing data
    index, manifest = load_existing_data(domain)
    base_path = Path(f"out/{domain}")
    
    # Group URLs by collection
    collection_urls = defaultdict(list)
    collection_content = defaultdict(list)
    
    print("📊 Analyzing existing URLs...")
    
    # Process each shard
    for shard_name, urls in manifest.items():
        print(f"  Processing shard: {shard_name} ({len(urls)} URLs)")
        
        # Load shard content
        shard_file = base_path / f"llms-{domain}-{shard_name}.txt"
        if not shard_file.exists():
            print(f"    ⚠️  Shard file not found: {shard_file}")
            continue
            
        with open(shard_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split content by URL markers
        url_sections = re.split(r'^URL: https?://', content, flags=re.MULTILINE)
        
        for i, url in enumerate(urls):
            # Extract collection name
            collection = extract_collection_from_url(url)
            
            if collection:
                collection_urls[collection].append(url)
                
                # Find corresponding content
                if i < len(url_sections) - 1:
                    section_content = url_sections[i + 1] if i == 0 else f"URL: https://{url_sections[i + 1]}"
                    collection_content[collection].append(section_content)
                else:
                    print(f"    ⚠️  No content found for URL: {url}")
            else:
                # Fallback for non-collection URLs
                fallback_name = f"other_{shard_name}"
                collection_urls[fallback_name].append(url)
                if i < len(url_sections) - 1:
                    section_content = url_sections[i + 1] if i == 0 else f"URL: https://{url_sections[i + 1]}"
                    collection_content[fallback_name].append(section_content)
    
    print(f"\n📈 Found {len(collection_urls)} collections:")
    for collection, urls in sorted(collection_urls.items()):
        print(f"  {collection}: {len(urls)} URLs")
    
    # Create new shard files
    print(f"\n📝 Creating new shard files...")
    new_manifest = {}
    
    for collection, urls in collection_urls.items():
        if not urls:
            continue
            
        # Create shard file
        shard_filename = f"llms-{domain}-{collection}.txt"
        shard_path = base_path / shard_filename
        
        with open(shard_path, 'w', encoding='utf-8') as f:
            for i, (url, content) in enumerate(zip(urls, collection_content[collection])):
                f.write(content)
                if i < len(urls) - 1:
                    f.write("\n\n" + "="*80 + "\n\n")
        
        new_manifest[collection] = urls
        print(f"  ✅ Created: {shard_filename} ({len(urls)} URLs)")
    
    # Update manifest
    manifest_path = base_path / f"llms-{domain}-manifest.json"
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(new_manifest, f, indent=2)
    
    print(f"\n🎉 Reorganization complete!")
    print(f"   Old shards: 9")
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
