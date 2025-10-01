#!/usr/bin/env python3
"""
Clean the index file by removing collection pages and regenerate shards.
"""

import json
import os
from pathlib import Path
from collections import defaultdict

def clean_and_regenerate(domain: str):
    """Clean index and regenerate shard files."""
    base_path = Path(f"out/{domain}")
    index_path = base_path / f"llms-{domain}-index.json"
    manifest_path = base_path / f"llms-{domain}-manifest.json"
    
    if not index_path.exists():
        print(f"❌ Index file not found: {index_path}")
        return
    
    print(f"📖 Loading index from: {index_path}")
    
    with open(index_path, 'r', encoding='utf-8') as f:
        index = json.load(f)
    
    print(f"✅ Loaded {len(index)} URLs from index")
    
    # Clean index - remove collection/category pages
    cleaned_index = {}
    removed_urls = []
    
    for url, data in index.items():
        # Only keep URLs with /products/ in them
        if '/products/' in url.lower():
            cleaned_index[url] = data
        else:
            removed_urls.append(url)
            print(f"  🗑️  Removing collection page: {url}")
    
    print(f"\n📊 Cleaning results:")
    print(f"  ✅ Kept: {len(cleaned_index)} product URLs")
    print(f"  🗑️  Removed: {len(removed_urls)} collection/category pages")
    
    # Delete old shard files
    print(f"\n🗑️  Deleting old shard files...")
    for shard_file in base_path.glob("llms-*.txt"):
        shard_file.unlink()
        print(f"  Deleted: {shard_file.name}")
    
    # Group URLs by shard
    shard_urls = defaultdict(list)
    for url, data in cleaned_index.items():
        shard_key = data.get("shard", "other_products")
        shard_urls[shard_key].append({
            "url": url,
            "title": data.get("title", ""),
            "markdown": data.get("markdown", "")
        })
    
    print(f"\n📂 Creating {len(shard_urls)} clean shard files...")
    
    # Recreate each shard file
    manifest = {}
    for shard_key, urls in shard_urls.items():
        shard_filename = f"llms-{domain}-{shard_key}.txt"
        shard_path = base_path / shard_filename
        
        content_parts = []
        url_list = []
        
        for url_data in urls:
            url = url_data["url"]
            title = url_data["title"]
            markdown = url_data["markdown"]
            
            url_list.append(url)
            
            # Create the content block
            header = f"<|{url}|>\n## {title}\n\n"
            content_block = header + markdown + "\n\n"
            content_parts.append(content_block)
        
        # Write shard file
        with open(shard_path, 'w', encoding='utf-8') as f:
            f.write(''.join(content_parts))
        
        manifest[shard_key] = url_list
        
        print(f"  ✅ Created: {shard_filename} ({len(urls)} products, {len(''.join(content_parts))} chars)")
    
    # Update index with cleaned data
    print(f"\n💾 Updating index file...")
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(cleaned_index, f, indent=2, ensure_ascii=False)
    
    # Update manifest
    print(f"💾 Updating manifest file...")
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    print(f"\n🎉 Cleanup and regeneration complete!")
    print(f"📊 Final stats:")
    print(f"  ✅ {len(shard_urls)} shard files created")
    print(f"  ✅ {len(cleaned_index)} clean product URLs")
    print(f"  🗑️  {len(removed_urls)} collection pages removed")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python3 clean_index_and_regenerate.py <domain>")
        print("Example: python3 clean_index_and_regenerate.py jgengineering-ie")
        sys.exit(1)
    
    domain = sys.argv[1]
    clean_and_regenerate(domain)

