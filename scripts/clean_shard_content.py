#!/usr/bin/env python3
"""
Clean up shard files by removing HTML content and keeping only product JSON data.
This fixes the issue where collection pages were included in shards.
"""

import os
import re
import json
from pathlib import Path

def clean_shard_file(file_path: Path) -> dict:
    """Clean a single shard file, removing HTML content and keeping only product JSON."""
    print(f"🧹 Cleaning: {file_path.name}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split content by URL markers
    sections = re.split(r'<\|(https?://[^|]+)\|>', content)
    
    clean_sections = []
    product_count = 0
    removed_count = 0
    
    for i in range(1, len(sections), 2):
        if i + 1 < len(sections):
            url = sections[i].strip()
            content_section = sections[i + 1]
            
            # Check if this is a product URL (contains /products/)
            if '/products/' in url.lower():
                # Check if content looks like clean JSON (starts with {)
                if content_section.strip().startswith('{'):
                    clean_sections.append(f"<|{url}|>{content_section}")
                    product_count += 1
                else:
                    print(f"  ⚠️  Skipping malformed product: {url}")
                    removed_count += 1
            else:
                # Skip collection/category pages
                print(f"  🗑️  Removing collection page: {url}")
                removed_count += 1
    
    # Write cleaned content back to file
    if clean_sections:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n\n'.join(clean_sections))
        
        print(f"  ✅ Kept {product_count} products, removed {removed_count} items")
        return {"kept": product_count, "removed": removed_count}
    else:
        # File has no valid product content, remove it
        file_path.unlink()
        print(f"  🗑️  Deleted empty file")
        return {"kept": 0, "removed": removed_count}

def clean_all_shards(domain: str):
    """Clean all shard files for a domain."""
    base_path = Path(f"out/{domain}")
    
    if not base_path.exists():
        print(f"❌ Directory not found: {base_path}")
        return
    
    shard_files = list(base_path.glob("llms-*.txt"))
    
    if not shard_files:
        print(f"❌ No shard files found in {base_path}")
        return
    
    print(f"🔍 Found {len(shard_files)} shard files to clean")
    
    total_kept = 0
    total_removed = 0
    files_processed = 0
    
    for shard_file in shard_files:
        if shard_file.name.endswith('.txt') and not shard_file.name.endswith('-manifest.json') and not shard_file.name.endswith('-index.json'):
            result = clean_shard_file(shard_file)
            total_kept += result["kept"]
            total_removed += result["removed"]
            files_processed += 1
    
    print(f"\n🎉 Cleanup complete!")
    print(f"📊 Processed {files_processed} files")
    print(f"✅ Kept {total_kept} products")
    print(f"🗑️  Removed {total_removed} items")
    
    # Update manifest to reflect cleaned data
    update_manifest(domain)

def update_manifest(domain: str):
    """Update manifest to only include URLs that still exist in cleaned shards."""
    base_path = Path(f"out/{domain}")
    manifest_path = base_path / f"llms-{domain}-manifest.json"
    
    if not manifest_path.exists():
        print("⚠️  No manifest file found")
        return
    
    # Load existing manifest
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)
    
    # Extract URLs from cleaned shard files
    existing_urls = set()
    shard_files = list(base_path.glob("llms-*.txt"))
    
    for shard_file in shard_files:
        if shard_file.name.endswith('.txt') and not shard_file.name.endswith('-manifest.json') and not shard_file.name.endswith('-index.json'):
            with open(shard_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract URLs from content
            url_matches = re.findall(r'<\|(https?://[^|]+)\|>', content)
            existing_urls.update(url_matches)
    
    # Update manifest to only include existing URLs
    updated_manifest = {}
    for shard_key, urls in manifest.items():
        existing_shard_urls = [url for url in urls if url in existing_urls]
        if existing_shard_urls:
            updated_manifest[shard_key] = existing_shard_urls
    
    # Write updated manifest
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(updated_manifest, f, indent=2)
    
    print(f"📝 Updated manifest with {len(existing_urls)} URLs across {len(updated_manifest)} shards")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python3 clean_shard_content.py <domain>")
        print("Example: python3 clean_shard_content.py jgengineering.ie")
        sys.exit(1)
    
    domain = sys.argv[1]
    clean_all_shards(domain)
