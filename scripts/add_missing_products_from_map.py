#!/usr/bin/env python3
"""
Add Missing Products from Site MAP

This script uses Firecrawl's MAP API to discover ALL product URLs
on the site, then adds any missing ones to the pending queue.
"""

import os
import sys
import json
import requests
from datetime import datetime

def load_existing_urls(site_output_dir):
    """Load all URLs we already know about (scraped + queued)."""
    existing = set()
    
    # Load from manifest (already scraped)
    manifest_file = os.path.join(site_output_dir, "llms-mydiy-ie-manifest.json")
    if os.path.exists(manifest_file):
        with open(manifest_file, 'r') as f:
            manifest = json.load(f)
            existing.update(manifest.keys())
    
    # Load from queue (waiting to be scraped)
    queue_file = os.path.join(site_output_dir, "pending-queue.json")
    if os.path.exists(queue_file):
        with open(queue_file, 'r') as f:
            data = json.load(f)
            for item in data.get('pending', []):
                existing.add(item.get('normalized_url', ''))
    
    return existing

def get_all_product_urls(api_key):
    """Use MAP API to get all product URLs from the site."""
    print("🗺️  Fetching complete site map from MyDIY.ie...")
    
    response = requests.post(
        'https://api.firecrawl.dev/v1/map',
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        },
        json={
            'url': 'https://www.mydiy.ie/',
            'limit': 20000,
            'includeSubdomains': False
        },
        timeout=120
    )
    
    if response.status_code != 200:
        print(f"❌ Error fetching site map: {response.status_code}")
        print(response.text)
        return []
    
    data = response.json()
    all_links = data.get('links', [])
    
    # Filter for product URLs
    product_urls = []
    for link in all_links:
        url = link['url'] if isinstance(link, dict) else link
        if '/products/' in url:
            product_urls.append(url)
    
    print(f"✓ Found {len(product_urls)} total products on site")
    return product_urls

def add_missing_to_queue(missing_urls, queue_file):
    """Add missing URLs to the pending queue."""
    # Load existing queue
    if os.path.exists(queue_file):
        with open(queue_file, 'r') as f:
            data = json.load(f)
            queue = data.get('pending', [])
    else:
        queue = []
    
    # Add missing URLs
    print(f"\n📝 Adding {len(missing_urls)} missing products to queue...")
    for url in missing_urls:
        entry = {
            "url": url,
            "normalized_url": url,
            "metadata": {
                "attempts": 0,
                "category_shard_key": "uncategorized",  # Will be categorized during scrape
                "source_category": "site_map_discovery"
            },
            "discovered_at": datetime.now().isoformat()
        }
        queue.append(entry)
    
    # Save updated queue
    os.makedirs(os.path.dirname(queue_file), exist_ok=True)
    tmp_path = f"{queue_file}.tmp"
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump({"pending": queue}, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, queue_file)
    
    print(f"✓ Queue updated: {len(queue)} total products ready to scrape")

def main():
    print("═══════════════════════════════════════════════════════════")
    print("    ADD MISSING PRODUCTS FROM SITE MAP")
    print("═══════════════════════════════════════════════════════════\n")
    
    # Get API key
    api_key = os.getenv('FIRECRAWL_API_KEY')
    if not api_key:
        print("❌ Error: FIRECRAWL_API_KEY not found in environment")
        sys.exit(1)
    
    site_output_dir = "out/mydiy-ie"
    queue_file = os.path.join(site_output_dir, "pending-queue.json")
    
    # Step 1: Load existing URLs
    print("📂 Loading existing products...")
    existing_urls = load_existing_urls(site_output_dir)
    print(f"✓ Found {len(existing_urls)} products already known")
    
    # Step 2: Get all product URLs from site
    all_product_urls = get_all_product_urls(api_key)
    
    if not all_product_urls:
        print("❌ No products found on site")
        sys.exit(1)
    
    # Step 3: Find missing URLs
    print("\n🔍 Comparing with existing products...")
    missing_urls = []
    for url in all_product_urls:
        if url not in existing_urls:
            missing_urls.append(url)
    
    print(f"✓ Found {len(missing_urls)} missing products\n")
    
    # Step 4: Show summary
    print("═══════════════════════════════════════════════════════════")
    print("    SUMMARY")
    print("═══════════════════════════════════════════════════════════\n")
    print(f"Total products on site:        {len(all_product_urls):>6}")
    print(f"Already known (scraped/queued): {len(existing_urls):>6}")
    print(f"Missing (to be added):          {len(missing_urls):>6}")
    print(f"\nCoverage before: {len(existing_urls)/len(all_product_urls)*100:.1f}%")
    print(f"Coverage after:  100.0%\n")
    
    # Step 5: Add missing URLs to queue
    if missing_urls:
        add_missing_to_queue(missing_urls, queue_file)
        print("\n✅ SUCCESS! All missing products added to queue")
    else:
        print("\n✅ No missing products - queue is already complete!")
    
    print("\n═══════════════════════════════════════════════════════════")
    print("    NEXT STEP")
    print("═══════════════════════════════════════════════════════════\n")
    print("Ready to scrape the complete catalog:")
    print("\nCommand:")
    print("  source env.local && python3 scripts/update_llms_agnostic.py mydiy.ie \\")
    print("    --process-queue \\")
    print("    --batch-size 100 \\")
    print("    --max-batches 150")
    print("\n═══════════════════════════════════════════════════════════")

if __name__ == "__main__":
    main()

