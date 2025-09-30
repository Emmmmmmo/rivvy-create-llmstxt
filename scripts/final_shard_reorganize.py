#!/usr/bin/env python3
"""
Final shard reorganization - create proper collection-based shards from index.
"""

import json
import re
from collections import defaultdict
from pathlib import Path

def reorganize_shards(domain):
    """Reorganize shards by collection from the index file."""
    print(f"🔧 Reorganizing shards for {domain}...")
    
    base_path = Path(f"out/{domain}")
    
    # Load index
    with open(base_path / f"llms-{domain}-index.json") as f:
        index = json.load(f)
    
    print(f"📊 Loaded {len(index)} URLs from index")
    
    # Group URLs by collection
    collection_urls = defaultdict(list)
    
    for url in index:
        if 'jgengineering.ie' in url:
            path = url.split('jgengineering.ie', 1)[1]
            segments = [s for s in path.split('/') if s]
            if len(segments) >= 2 and segments[0] == 'collections':
                collection = segments[1]
                collection_urls[collection].append(url)
            else:
                collection_urls['other'].append(url)
        else:
            collection_urls['other'].append(url)
    
    print(f"📈 Found {len(collection_urls)} collections:")
    for collection, urls in sorted(collection_urls.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
        print(f"  {collection}: {len(urls)} URLs")
    
    # Create new shard files by extracting content from original files
    print(f"\n📝 Creating new shard files...")
    new_manifest = {}
    
    # Load all original shard content
    original_files = {
        'products': base_path / f"llms-{domain}-products.txt",
        'kits_sets': base_path / f"llms-{domain}-kits_sets.txt", 
        'thread_repair': base_path / f"llms-{domain}-thread_repair.txt",
        'clips_rings': base_path / f"llms-{domain}-clips_rings.txt",
        'taps_dies': base_path / f"llms-{domain}-taps_dies.txt",
        'drill_bits': base_path / f"llms-{domain}-drill_bits.txt",
        'fasteners': base_path / f"llms-{domain}-fasteners.txt",
        'seals_gaskets': base_path / f"llms-{domain}-seals_gaskets.txt",
        'other_products': base_path / f"llms-{domain}-other_products.txt"
    }
    
    # Load all content
    all_content = {}
    for shard_name, file_path in original_files.items():
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                all_content[shard_name] = f.read()
            print(f"  📄 Loaded {shard_name}: {len(all_content[shard_name])} chars")
        else:
            print(f"  ⚠️  File not found: {file_path}")
    
    # Create collection-based shard files
    for collection, urls in collection_urls.items():
        if not urls:
            continue
            
        shard_filename = f"llms-{domain}-{collection}.txt"
        shard_path = base_path / shard_filename
        
        new_manifest[collection] = urls
        
        # Extract content for these URLs from all original files
        url_content_map = {}
        
        for shard_name, content in all_content.items():
            sections = re.split(r'<\|(https?://[^|]+)\|>', content)
            
            for i in range(1, len(sections), 2):
                if i + 1 < len(sections):
                    content_url = sections[i].strip()
                    content_section = sections[i + 1]
                    
                    # Find matching URL in our collection (handle -lllmstxt suffix)
                    for url in urls:
                        if content_url.startswith(url):
                            url_content_map[url] = f"<|{content_url}|>{content_section}"
                            break
        
        # Write the collection shard file
        with open(shard_path, 'w', encoding='utf-8') as f:
            for i, url in enumerate(urls):
                if url in url_content_map:
                    f.write(url_content_map[url])
                    if i < len(urls) - 1:  # Not the last URL
                        f.write("\n\n")
                else:
                    # Placeholder if content not found
                    f.write(f"<|{url}|>\n## Content not found\n\n")
                    if i < len(urls) - 1:
                        f.write("\n")
        
        print(f"  ✅ Created: {shard_filename} ({len(urls)} URLs, {len(url_content_map)} with content)")
    
    # Update manifest
    manifest_path = base_path / f"llms-{domain}-manifest.json"
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(new_manifest, f, indent=2)
    
    print(f"\n🎉 Reorganization complete!")
    print(f"   Collections: {len(new_manifest)}")
    print(f"   Total URLs: {sum(len(urls) for urls in new_manifest.values())}")
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
