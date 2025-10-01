#!/usr/bin/env python3
"""
Recover shard files from the index JSON file.
"""

import json
import os
from pathlib import Path
from collections import defaultdict

def recover_shards(domain: str):
    """Recover all shard files from the index."""
    base_path = Path(f"out/{domain}")
    index_path = base_path / f"llms-{domain}-index.json"
    
    if not index_path.exists():
        print(f"❌ Index file not found: {index_path}")
        return
    
    print(f"📖 Loading index from: {index_path}")
    
    with open(index_path, 'r', encoding='utf-8') as f:
        index = json.load(f)
    
    print(f"✅ Found {len(index)} URLs in index")
    
    # Group URLs by shard
    shard_urls = defaultdict(list)
    for url, data in index.items():
        shard_key = data.get("shard", "other_products")
        shard_urls[shard_key].append({
            "url": url,
            "title": data.get("title", ""),
            "markdown": data.get("markdown", "")
        })
    
    print(f"📂 Found {len(shard_urls)} shards to recover")
    
    # Recreate each shard file
    for shard_key, urls in shard_urls.items():
        shard_filename = f"llms-{domain}-{shard_key}.txt"
        shard_path = base_path / shard_filename
        
        content_parts = []
        for url_data in urls:
            url = url_data["url"]
            title = url_data["title"]
            markdown = url_data["markdown"]
            
            # Create the content block
            header = f"<|{url}|>\n## {title}\n\n"
            content_block = header + markdown + "\n\n"
            content_parts.append(content_block)
        
        # Write shard file
        with open(shard_path, 'w', encoding='utf-8') as f:
            f.write(''.join(content_parts))
        
        print(f"  ✅ Recovered: {shard_filename} ({len(urls)} products, {len(''.join(content_parts))} chars)")
    
    print(f"\n🎉 Recovery complete! Recovered {len(shard_urls)} shard files with {len(index)} products")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python3 recover_shards_from_index.py <domain>")
        print("Example: python3 recover_shards_from_index.py jgengineering-ie")
        sys.exit(1)
    
    domain = sys.argv[1]
    recover_shards(domain)

