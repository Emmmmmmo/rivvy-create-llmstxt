#!/usr/bin/env python3
"""
Re-scrape only product URLs to get clean product data.
This fixes the issue where collection pages were scraped instead of individual products.
"""

import json
import os
import re
from collections import defaultdict
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import time

def extract_product_data(url):
    """Extract clean product data from a product URL."""
    try:
        print(f"  Scraping: {url}")
        
        # Add headers to avoid blocking
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract product information
        product_data = {}
        
        # Product name
        title_elem = soup.find('h1', class_='product-title') or soup.find('h1')
        if title_elem:
            product_data['product_name'] = title_elem.get_text().strip()
        
        # Price (look for EUR prices)
        price_elem = soup.find('span', class_='price') or soup.find('div', class_='price')
        if price_elem:
            price_text = price_elem.get_text().strip()
            # Convert USD to EUR if needed (rough conversion)
            if '$' in price_text:
                price_text = price_text.replace('$', '€')
            product_data['price'] = price_text
        
        # Description
        desc_elem = soup.find('div', class_='product-description') or soup.find('div', class_='description')
        if desc_elem:
            product_data['description'] = desc_elem.get_text().strip()
        
        # Availability
        availability_elem = soup.find('span', class_='availability') or soup.find('div', class_='stock')
        if availability_elem:
            product_data['availability'] = availability_elem.get_text().strip()
        
        # Specifications (look for lists or tables)
        specs = []
        spec_elem = soup.find('div', class_='specifications') or soup.find('ul', class_='specs')
        if spec_elem:
            for li in spec_elem.find_all('li'):
                specs.append(li.get_text().strip())
        product_data['specifications'] = specs
        
        return product_data
        
    except Exception as e:
        print(f"    Error scraping {url}: {e}")
        return None

def rescrape_products(domain):
    """Re-scrape only product URLs to get clean data."""
    print(f"🔧 Re-scraping product URLs for {domain}...")
    
    base_path = Path(f"out/{domain}")
    
    # Load index
    with open(base_path / f"llms-{domain}-index.json") as f:
        index = json.load(f)
    
    # Filter to only product URLs
    product_urls = [url for url in index if '/products/' in url]
    collection_urls = [url for url in index if '/collections/' in url and '/products/' not in url]
    
    print(f"📊 Found {len(product_urls)} product URLs and {len(collection_urls)} collection URLs")
    print(f"🎯 Re-scraping {len(product_urls)} product URLs...")
    
    # Group product URLs by collection
    collection_products = defaultdict(list)
    
    for url in product_urls:
        if 'jgengineering.ie' in url:
            path = url.split('jgengineering.ie', 1)[1]
            segments = [s for s in path.split('/') if s]
            if len(segments) >= 2 and segments[0] == 'collections':
                collection = segments[1]
                collection_products[collection].append(url)
            else:
                collection_products['other'].append(url)
        else:
            collection_products['other'].append(url)
    
    print(f"📈 Grouped into {len(collection_products)} collections")
    
    # Re-scrape each collection
    for collection, urls in collection_products.items():
        if not urls:
            continue
            
        print(f"\n📝 Re-scraping collection: {collection} ({len(urls)} products)")
        
        shard_filename = f"llms-{domain}-{collection}.txt"
        shard_path = base_path / shard_filename
        
        with open(shard_path, 'w', encoding='utf-8') as f:
            for i, url in enumerate(urls):
                product_data = extract_product_data(url)
                
                if product_data:
                    # Write clean product data
                    f.write(f"<|{url}|>\n")
                    f.write(f"## {product_data.get('product_name', 'Unknown Product')}\n\n")
                    f.write("{\n")
                    f.write(f'  "price": "{product_data.get("price", "N/A")}",\n')
                    f.write(f'  "description": "{product_data.get("description", "No description available")}",\n')
                    f.write(f'  "availability": "{product_data.get("availability", "Unknown")}",\n')
                    f.write(f'  "product_name": "{product_data.get("product_name", "Unknown")}",\n')
                    f.write(f'  "specifications": {json.dumps(product_data.get("specifications", []))}\n')
                    f.write("}\n")
                else:
                    # Write placeholder
                    f.write(f"<|{url}|>\n")
                    f.write("## Product data not available\n\n")
                    f.write("{\n")
                    f.write('  "price": "N/A",\n')
                    f.write('  "description": "Product data could not be scraped",\n')
                    f.write('  "availability": "Unknown",\n')
                    f.write('  "product_name": "Unknown Product",\n')
                    f.write('  "specifications": []\n')
                    f.write("}\n")
                
                if i < len(urls) - 1:
                    f.write("\n\n")
                
                # Rate limiting
                time.sleep(0.5)
        
        print(f"  ✅ Updated: {shard_filename}")
    
    print(f"\n🎉 Re-scraping complete!")
    print(f"   Product URLs processed: {len(product_urls)}")
    print(f"   Collections updated: {len(collection_products)}")

def main():
    domain = "jgengineering-ie"
    rescrape_products(domain)

if __name__ == "__main__":
    main()
