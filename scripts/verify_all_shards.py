#!/usr/bin/env python3
"""
Verify all shard files against the website data.
"""

import json
import re
from pathlib import Path
from collections import defaultdict

def verify_shard_file(shard_path: Path) -> dict:
    """Verify a single shard file."""
    with open(shard_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract all URLs
    urls = re.findall(r'<\|(https?://[^|]+)\|>', content)
    
    # Count products
    product_count = len(urls)
    
    # Check for HTML pollution
    html_indicators = [
        'Skip to content',
        'Welcome to our new website',
        'New collections added',
        'Country/Region',
        'Filter & Sort',
        'Sort by',
        'Alphabetically',
        'Applied Filters',
        'Show.*results',
        'View as List Grid',
        'Newsletter',
        'Sign up for exclusive',
        'Payment methods accepted'
    ]
    
    html_pollution = []
    for indicator in html_indicators:
        if re.search(indicator, content, re.IGNORECASE):
            html_pollution.append(indicator)
    
    # Check for EUR pricing
    eur_prices = len(re.findall(r'"price":\s*"€[0-9,]+\.[0-9]{2}"', content))
    
    # Check for USD pricing (should be 0)
    usd_prices = len(re.findall(r'\$[0-9]+\.[0-9]{2}', content))
    
    # Check for clean JSON structure
    json_blocks = re.findall(r'\{[^}]+\}', content, re.DOTALL)
    valid_json_count = 0
    for block in json_blocks[:5]:  # Sample first 5
        try:
            json.loads(block)
            valid_json_count += 1
        except:
            pass
    
    # Check file size
    file_size = len(content)
    
    # Check for product URLs
    product_urls = [url for url in urls if '/products/' in url]
    collection_urls = [url for url in urls if '/products/' not in url]
    
    return {
        'shard_name': shard_path.stem,
        'total_urls': len(urls),
        'product_urls': len(product_urls),
        'collection_urls': len(collection_urls),
        'eur_prices': eur_prices,
        'usd_prices': usd_prices,
        'html_pollution': html_pollution,
        'file_size': file_size,
        'valid_json_samples': valid_json_count,
        'urls': urls
    }

def verify_all_shards(domain: str):
    """Verify all shard files for a domain."""
    base_path = Path(f"out/{domain}")
    
    shard_files = sorted(base_path.glob("llms-*.txt"))
    
    print(f"🔍 Verifying {len(shard_files)} shard files for {domain}")
    print("=" * 100)
    
    total_products = 0
    total_eur_prices = 0
    total_usd_prices = 0
    total_collection_urls = 0
    shards_with_html = []
    shards_with_usd = []
    shards_with_collections = []
    
    all_results = []
    
    for shard_file in shard_files:
        result = verify_shard_file(shard_file)
        all_results.append(result)
        
        total_products += result['product_urls']
        total_eur_prices += result['eur_prices']
        total_usd_prices += result['usd_prices']
        total_collection_urls += result['collection_urls']
        
        if result['html_pollution']:
            shards_with_html.append(result['shard_name'])
        
        if result['usd_prices'] > 0:
            shards_with_usd.append(result['shard_name'])
        
        if result['collection_urls'] > 0:
            shards_with_collections.append(result['shard_name'])
    
    # Print summary
    print(f"\n📊 OVERALL SUMMARY")
    print("=" * 100)
    print(f"✅ Total Shards: {len(shard_files)}")
    print(f"✅ Total Products: {total_products}")
    print(f"✅ EUR Prices Found: {total_eur_prices}")
    print(f"❌ USD Prices Found: {total_usd_prices}")
    print(f"❌ Collection URLs: {total_collection_urls}")
    print(f"❌ Shards with HTML: {len(shards_with_html)}")
    
    if shards_with_html:
        print(f"\n⚠️  Shards with HTML pollution: {', '.join(shards_with_html)}")
    
    if shards_with_usd:
        print(f"\n⚠️  Shards with USD pricing: {', '.join(shards_with_usd)}")
    
    if shards_with_collections:
        print(f"\n⚠️  Shards with collection URLs: {', '.join(shards_with_collections)}")
    
    # Print detailed results
    print(f"\n📋 DETAILED SHARD BREAKDOWN")
    print("=" * 100)
    print(f"{'Shard Name':<50} {'Products':<10} {'EUR':<8} {'USD':<8} {'Size (KB)':<12} {'Status'}")
    print("-" * 100)
    
    for result in all_results:
        status = "✅"
        if result['html_pollution']:
            status = "❌ HTML"
        elif result['usd_prices'] > 0:
            status = "⚠️ USD"
        elif result['collection_urls'] > 0:
            status = "⚠️ COLL"
        
        size_kb = result['file_size'] / 1024
        
        print(f"{result['shard_name']:<50} {result['product_urls']:<10} {result['eur_prices']:<8} "
              f"{result['usd_prices']:<8} {size_kb:<12.1f} {status}")
    
    # Top 10 largest shards
    print(f"\n📈 TOP 10 LARGEST SHARDS")
    print("=" * 100)
    sorted_by_size = sorted(all_results, key=lambda x: x['file_size'], reverse=True)[:10]
    for result in sorted_by_size:
        size_kb = result['file_size'] / 1024
        print(f"  {result['shard_name']:<50} {result['product_urls']:>4} products, {size_kb:>6.1f} KB")
    
    # Quality score
    print(f"\n🎯 QUALITY SCORE")
    print("=" * 100)
    
    score = 100
    if total_collection_urls > 0:
        score -= 30
        print(f"  ❌ Collection URLs found: -{30} points")
    
    if total_usd_prices > 0:
        score -= 20
        print(f"  ⚠️  USD pricing found: -{20} points")
    
    if shards_with_html:
        score -= 30
        print(f"  ❌ HTML pollution found: -{30} points")
    
    if score == 100:
        print(f"  ✅ Perfect data quality!")
    
    print(f"\n  Final Score: {score}/100")
    
    if score >= 90:
        print(f"  🎉 EXCELLENT - Ready for production!")
    elif score >= 70:
        print(f"  ⚠️  GOOD - Minor issues to fix")
    else:
        print(f"  ❌ NEEDS WORK - Major issues found")
    
    return all_results

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python3 verify_all_shards.py <domain>")
        print("Example: python3 verify_all_shards.py jgengineering-ie")
        sys.exit(1)
    
    domain = sys.argv[1]
    verify_all_shards(domain)

