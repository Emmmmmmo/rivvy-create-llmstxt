#!/usr/bin/env python3
"""
Split large shard files to stay under 300k character limit.
"""

import json
import re
from pathlib import Path
from collections import defaultdict

def split_shard_file(shard_path: Path, max_size: int = 300000):
    """Split a large shard file into smaller chunks."""
    
    with open(shard_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if file needs splitting
    if len(content) <= max_size:
        print(f"✅ {shard_path.name} is {len(content):,} chars - no splitting needed")
        return
    
    print(f"🔪 Splitting {shard_path.name} ({len(content):,} chars)")
    
    # Extract all URL blocks
    url_blocks = re.split(r'(<\|https?://[^|]+\|>)', content)
    
    # Group into URL + content pairs
    products = []
    for i in range(1, len(url_blocks), 2):
        if i + 1 < len(url_blocks):
            url_delimiter = url_blocks[i]
            content_block = url_blocks[i + 1].strip()
            products.append(url_delimiter + '\n' + content_block)
    
    print(f"  📦 Found {len(products)} products to split")
    
    # Split into chunks
    chunks = []
    current_chunk = []
    current_size = 0
    
    for product in products:
        product_size = len(product) + 2  # +2 for newlines
        
        # If adding this product would exceed limit, start new chunk
        if current_size + product_size > max_size and current_chunk:
            chunks.append('\n\n'.join(current_chunk))
            current_chunk = [product]
            current_size = product_size
        else:
            current_chunk.append(product)
            current_size += product_size
    
    # Add final chunk
    if current_chunk:
        chunks.append('\n\n'.join(current_chunk))
    
    print(f"  ✂️  Split into {len(chunks)} chunks")
    
    # Write chunk files
    base_name = shard_path.stem
    base_dir = shard_path.parent
    
    for i, chunk in enumerate(chunks, 1):
        chunk_filename = f"{base_name}_part{i}.txt"
        chunk_path = base_dir / chunk_filename
        
        with open(chunk_path, 'w', encoding='utf-8') as f:
            f.write(chunk)
        
        print(f"    ✅ Created {chunk_filename} ({len(chunk):,} chars)")
    
    # Remove original file
    shard_path.unlink()
    print(f"  🗑️  Removed original {shard_path.name}")
    
    return len(chunks)

def update_manifest_for_split_shard(manifest_path: Path, shard_key: str, num_chunks: int):
    """Update manifest to reflect split shard."""
    
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)
    
    if shard_key not in manifest:
        print(f"⚠️  Shard key '{shard_key}' not found in manifest")
        return
    
    original_urls = manifest[shard_key]
    urls_per_chunk = len(original_urls) // num_chunks
    
    # Remove original shard
    del manifest[shard_key]
    
    # Add split shards
    for i in range(num_chunks):
        start_idx = i * urls_per_chunk
        if i == num_chunks - 1:  # Last chunk gets remaining URLs
            end_idx = len(original_urls)
        else:
            end_idx = (i + 1) * urls_per_chunk
        
        chunk_urls = original_urls[start_idx:end_idx]
        chunk_key = f"{shard_key}_part{i+1}"
        manifest[chunk_key] = chunk_urls
    
    # Write updated manifest
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"  📝 Updated manifest with {num_chunks} split shards")

def split_large_shards(domain: str, max_size: int = 300000):
    """Find and split all shards over the size limit."""
    
    base_path = Path(f"out/{domain}")
    manifest_path = base_path / f"llms-{domain}-manifest.json"
    
    if not manifest_path.exists():
        print(f"❌ Manifest file not found: {manifest_path}")
        return
    
    # Find all shard files
    shard_files = list(base_path.glob("llms-*.txt"))
    
    print(f"🔍 Checking {len(shard_files)} shard files for size limit ({max_size:,} chars)")
    print("=" * 80)
    
    large_shards = []
    for shard_file in shard_files:
        size = shard_file.stat().st_size
        if size > max_size:
            large_shards.append((shard_file, size))
            print(f"⚠️  {shard_file.name}: {size:,} chars (OVER LIMIT)")
        else:
            print(f"✅ {shard_file.name}: {size:,} chars")
    
    if not large_shards:
        print(f"\n🎉 All shards are under {max_size:,} character limit!")
        return
    
    print(f"\n🔪 Splitting {len(large_shards)} large shards...")
    print("=" * 80)
    
    for shard_file, size in large_shards:
        # Extract shard key from filename
        shard_key = shard_file.stem.replace(f"llms-{domain}-", "")
        
        print(f"\n📦 Processing: {shard_file.name}")
        num_chunks = split_shard_file(shard_file, max_size)
        
        if num_chunks:
            update_manifest_for_split_shard(manifest_path, shard_key, num_chunks)
    
    print(f"\n🎉 Splitting complete!")
    
    # Final verification
    print(f"\n🔍 Final size check:")
    final_shards = list(base_path.glob("llms-*.txt"))
    for shard_file in final_shards:
        size = shard_file.stat().st_size
        status = "✅" if size <= max_size else "❌"
        print(f"  {status} {shard_file.name}: {size:,} chars")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 split_large_shard.py <domain> [max_size]")
        print("Example: python3 split_large_shard.py jgengineering-ie 300000")
        sys.exit(1)
    
    domain = sys.argv[1]
    max_size = int(sys.argv[2]) if len(sys.argv) > 2 else 300000
    
    split_large_shards(domain, max_size)
