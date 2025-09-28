#!/usr/bin/env python3
"""
Update LLMs.txt files with sharding support using Firecrawl v2 API.

This script supports:
- Full crawl (--full) to scrape everything
- Incremental updates (--added, --changed, --removed) for specific URLs
- Sharding by product category (first path segment)
- Per-URL metadata storage in llms-index.json
- Manifest tracking of shard -> URL mappings
"""

import os
import sys
import json
import time
import argparse
import logging
import re
from typing import Dict, List, Optional, Set, Any
from urllib.parse import urlparse, urljoin, urlunparse
import requests
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ShardedLLMsUpdater:
    """Update LLMs.txt files with sharding support using Firecrawl v2 API."""
    
    def __init__(self, firecrawl_api_key: str, base_url: str, base_root: Optional[str] = None, output_dir: str = "out", max_characters: int = 300000):
        """Initialize the updater with API key and base URL."""
        self.firecrawl_api_key = firecrawl_api_key
        self.base_url = base_url.rstrip('/')
        self.base_root = base_root
        self.max_characters = max_characters  # ElevenLabs 300K character limit
        self.firecrawl_base_url = "https://api.firecrawl.dev/v2"
        self.headers = {
            "Authorization": f"Bearer {self.firecrawl_api_key}",
            "Content-Type": "application/json"
        }
        
        # Extract site name from URL for file naming
        from urllib.parse import urlparse
        parsed = urlparse(self.base_url)
        self.site_name = parsed.netloc.replace('www.', '').replace('.', '-')
        
        # Ensure output directory exists with site-specific subfolder
        self.output_dir = output_dir
        self.site_output_dir = os.path.join(self.output_dir, self.site_name)
        os.makedirs(self.site_output_dir, exist_ok=True)
        
        # File paths
        self.index_file = os.path.join(self.site_output_dir, f"llms-{self.site_name}-index.json")
        self.manifest_file = os.path.join(self.site_output_dir, f"llms-{self.site_name}-manifest.json")
        
        # Load existing data
        self.url_index = self._load_url_index()
        self.manifest = self._load_manifest()
    
    def _load_url_index(self) -> Dict[str, Dict[str, Any]]:
        """Load existing URL index from file."""
        if os.path.exists(self.index_file):
            try:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load URL index: {e}")
        return {}
    
    def _load_manifest(self) -> Dict[str, List[str]]:
        """Load existing manifest from file."""
        if os.path.exists(self.manifest_file):
            try:
                with open(self.manifest_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load manifest: {e}")
        return {}
    
    def _save_url_index(self):
        """Save URL index to file."""
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(self.url_index, f, indent=2, ensure_ascii=False)
    
    def _save_manifest(self):
        """Save manifest to file with stable ordering."""
        # Sort URLs within each shard and sort shard keys
        for k in list(self.manifest.keys()):
            self.manifest[k] = sorted(set(self.manifest[k]))
        self.manifest = dict(sorted(self.manifest.items()))
        
        with open(self.manifest_file, 'w', encoding='utf-8') as f:
            json.dump(self.manifest, f, indent=2, ensure_ascii=False)
    
    def _sanitize_shard(self, s: str) -> str:
        """Sanitize shard key for filesystem-safe filenames."""
        s = s.lower().strip().replace(" ", "-")
        s = re.sub(r"[^a-z0-9\-_\\.]", "-", s)
        s = re.sub(r"-{2,}", "-", s).strip("-")
        return s or "misc"
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL by removing query parameters and fragments."""
        p = urlparse(url)
        return urlunparse((p.scheme, p.netloc, p.path, "", "", ""))
    
    def _ensure_eur_currency(self, url: str) -> str:
        """Ensure URL has EUR currency parameter for proper pricing."""
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
        
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        
        # Add or update currency parameter to EUR
        query_params['currency'] = ['EUR']
        
        # Reconstruct URL with EUR currency
        new_query = urlencode(query_params, doseq=True)
        eur_url = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment
        ))
        
        logger.debug(f"EUR currency URL: {url} -> {eur_url}")
        return eur_url
    
    def _extract_product_urls(self, markdown_content: str, base_url: str) -> List[str]:
        """Extract product URLs from category page markdown content."""
        import re
        from urllib.parse import urlparse
        
        # Look for product URLs in the markdown content
        # Pattern matches URLs like /products/product-name (including extensions)
        product_pattern = r'https://[^/]+/products/[^/\s\)]+'
        urls = re.findall(product_pattern, markdown_content)
        
        # Also look for relative URLs and convert them to absolute
        relative_pattern = r'/products/[^/\s\)]+'
        relative_urls = re.findall(relative_pattern, markdown_content)
        
        # Filter out image URLs (common image extensions)
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp']
        urls = [url for url in urls if not any(url.lower().endswith(ext) for ext in image_extensions)]
        relative_urls = [url for url in relative_urls if not any(url.lower().endswith(ext) for ext in image_extensions)]
        
        # Convert relative URLs to absolute
        for rel_url in relative_urls:
            # If rel_url starts with /products/, we need to preserve the collection path
            if rel_url.startswith('/products/'):
                # Extract the collection path from base_url
                parsed_base = urlparse(base_url)
                if '/collections/' in parsed_base.path:
                    # Keep the collection path and append the product path
                    collection_path = parsed_base.path.rstrip('/')
                    absolute_url = f"{parsed_base.scheme}://{parsed_base.netloc}{collection_path}{rel_url}"
                else:
                    absolute_url = urljoin(base_url, rel_url)
            else:
                absolute_url = urljoin(base_url, rel_url)
            urls.append(absolute_url)
        
        # Remove duplicates and normalize
        unique_urls = list(set(urls))
        normalized_urls = [self._normalize_url(url) for url in unique_urls]
        
        logger.info(f"Extracted {len(normalized_urls)} product URLs from category page")
        return normalized_urls
    
    def _get_shard_key(self, url: str) -> str:
        """Extract improved shard key from URL for better categorization."""
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        
        if self.base_root:
            # Remove base_root from path if it exists
            if path.startswith(self.base_root.strip('/')):
                path = path[len(self.base_root.strip('/')):].strip('/')
        
        if not path:
            return 'root'
        
        segments = path.split('/')
        
        # For e-commerce sites, use the second segment for products/collections
        if len(segments) >= 2 and segments[0] in ['products', 'collections', 'shop', 'catalog', 'items']:
            # Use second segment for better categorization
            category = segments[1]
            
            # For products within collections, use the collection name
            if segments[0] == 'collections' and len(segments) >= 4 and segments[2] == 'products':
                category = segments[1]  # Use collection name
            elif segments[0] in ['products', 'shop', 'catalog', 'items']:
                # For direct products, try to extract category from product name
                product_name = segments[1]
                # Use generic categorization based on common patterns
                return self._categorize_product(product_name)
            
            return self._sanitize_shard(category)
        
        # For other paths, use first segment
        return self._sanitize_shard(segments[0])
    
    def _categorize_product(self, product_name: str) -> str:
        """Categorize product based on name patterns."""
        name_lower = product_name.lower()
        
        # Common product categorization patterns
        if any(word in name_lower for word in ['kit', 'set', 'combo']):
            return 'kits_sets'
        elif any(word in name_lower for word in ['insert', 'thread', 'repair']):
            return 'thread_repair'
        elif any(word in name_lower for word in ['tap', 'die', 'threading']):
            return 'taps_dies'
        elif any(word in name_lower for word in ['drill', 'bit', 'hole']):
            return 'drill_bits'
        elif any(word in name_lower for word in ['clip', 'ring', 'retainer']):
            return 'clips_rings'
        elif any(word in name_lower for word in ['tool', 'wrench', 'driver']):
            return 'tools'
        elif any(word in name_lower for word in ['screw', 'bolt', 'fastener']):
            return 'fasteners'
        elif any(word in name_lower for word in ['bearing', 'bushing', 'spacer']):
            return 'bearings_bushings'
        elif any(word in name_lower for word in ['seal', 'gasket', 'o-ring']):
            return 'seals_gaskets'
        else:
            return 'other_products'
    
    def _filter_product_urls(self, urls: List[str]) -> List[str]:
        """Filter URLs to keep only product-related ones."""
        filtered = []
        excluded_patterns = [
            'sitemap', 'robots.txt', 'blog', 'news', 'about', 'contact', 
            'privacy', 'terms', 'help', 'faq', 'search', 'cart', 'checkout',
            'account', 'login', 'register', 'admin', 'api', 'feed', 'rss'
        ]
        
        for url in urls:
            url_lower = url.lower()
            # Skip if URL contains excluded patterns
            if any(pattern in url_lower for pattern in excluded_patterns):
                continue
            
            # Keep product-related URLs
            if any(pattern in url_lower for pattern in ['product', 'collection', 'shop', 'catalog', 'item']):
                filtered.append(url)
            # Keep main pages and category pages
            elif url.count('/') <= 3:  # Keep shallow URLs (likely categories)
                filtered.append(url)
        
        return filtered
    
    def _map_website(self, limit: int = 10000) -> List[str]:
        """Map a website to get all URLs using Firecrawl v2 API."""
        logger.info(f"Mapping website: {self.base_url} (limit: {limit})")
        
        try:
            response = requests.post(
                f"{self.firecrawl_base_url}/map",
                headers=self.headers,
                json={
                    "url": self.base_url,
                    "limit": limit
                }
            )
            response.raise_for_status()
            
            data = response.json()
            # Handle both array format and object format
            if isinstance(data, list):
                urls = [item.get("url", "") for item in data if item.get("url")]
            else:
                urls = data.get("links", []) or data.get("data", [])
                if isinstance(urls, list) and urls and isinstance(urls[0], dict):
                    urls = [item.get("url", "") for item in urls if item.get("url")]
            
            if urls:
                # Filter out non-product URLs
                filtered_urls = self._filter_product_urls(urls)
                logger.info(f"Found {len(urls)} URLs, filtered to {len(filtered_urls)} product URLs")
                return filtered_urls
            else:
                logger.error(f"Failed to map website: {data}")
                return []
                
        except Exception as e:
            logger.error(f"Error mapping website: {e}")
            return []
    
    def _scrape_url(self, url: str, pre_scraped_content: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Scrape a single URL using Firecrawl v2 API with retry logic, or use pre-scraped content."""
        logger.debug(f"Scraping URL: {url}")
        
        # Use original URL to get the latest content (EUR currency forcing was causing stale content)
        eur_url = url
        
        # If pre-scraped content is provided, use it instead of scraping
        if pre_scraped_content:
            logger.info(f"Using pre-scraped content for {url}")
            return {
                "url": url,
                "markdown": pre_scraped_content,
                "metadata": {"title": url.split('/')[-1]},  # Basic title from URL
                "title": url.split('/')[-1],
                "updated_at": datetime.now().isoformat()
            }
        
        for i in range(3):
            try:
                response = requests.post(
                    f"{self.firecrawl_base_url}/scrape",
                    headers=self.headers,
                    json={
                        "url": eur_url,  # Use EUR currency URL
                        "formats": ["markdown"],
                        "onlyMainContent": os.getenv("ONLY_MAIN_CONTENT", "false").lower() == "true",
                        "timeout": 30000
                    }
                )
                response.raise_for_status()
                
                data = response.json()
                # Handle both v2 response formats
                md = data.get("markdown") or data.get("content") or data.get("data", {}).get("markdown", "")
                meta = data.get("metadata") or data.get("data", {}).get("metadata", {}) or {}
                title = meta.get("title") or ""
                
                if md:
                    return {
                        "url": url,
                        "markdown": md,
                        "metadata": meta,
                        "title": title,
                        "updated_at": datetime.now().isoformat()
                    }
                else:
                    logger.error(f"Failed to scrape {url}: {data}")
                    return None
                    
            except Exception as e:
                if i < 2:  # Don't log warning on final attempt
                    logger.warning(f"Retry {i+1}/3 for {url}: {e}")
                    time.sleep(2*(i+1))
                else:
                    logger.error(f"Error scraping {url} after 3 attempts: {e}")
                    return None
    
    def _update_url_data(self, url: str, scraped_data: Dict[str, Any]) -> str:
        """Update URL data in index and return shard key."""
        # Normalize URL to prevent duplicates
        normalized_url = self._normalize_url(url)
        shard_key = self._get_shard_key(normalized_url)
        
        # Update URL index
        self.url_index[normalized_url] = {
            "title": scraped_data.get("title", ""),
            "markdown": scraped_data["markdown"],
            "shard": shard_key,
            "updated_at": scraped_data["updated_at"]
        }
        
        # Update manifest
        if shard_key not in self.manifest:
            self.manifest[shard_key] = []
        
        if normalized_url not in self.manifest[shard_key]:
            self.manifest[shard_key].append(normalized_url)
        
        return shard_key
    
    def _remove_url_data(self, url: str):
        """Remove URL data from index and manifest."""
        normalized_url = self._normalize_url(url)
        if normalized_url in self.url_index:
            shard_key = self.url_index[normalized_url]["shard"]
            del self.url_index[normalized_url]
            
            # Remove from manifest
            if shard_key in self.manifest and normalized_url in self.manifest[shard_key]:
                self.manifest[shard_key].remove(normalized_url)
                if not self.manifest[shard_key]:  # Remove empty shard
                    del self.manifest[shard_key]
    
    def _split_large_content(self, content: str, base_filename: str) -> List[str]:
        """Split large content into smaller chunks with intelligent breaks."""
        char_count = len(content)
        
        if char_count <= self.max_characters:
            return [content]
        
        logger.info(f"📦 Splitting large content ({char_count:,} characters) into smaller chunks...")
        
        chunks = []
        chunk_size = self.max_characters
        start = 0
        
        while start < len(content):
            end = start + chunk_size
            
            # Try to find a good break point (end of a product section)
            if end < len(content):
                chunk_content = content[start:end]
                
                # Find the last complete product section
                last_product_end = chunk_content.rfind('\n\n## ')
                if last_product_end > chunk_size * 0.7:  # If we found a good break point
                    end = start + last_product_end
                else:
                    # Look for other good break points
                    last_section_end = chunk_content.rfind('\n\n---\n')
                    if last_section_end > chunk_size * 0.7:
                        end = start + last_section_end
                    else:
                        # Look for double newlines
                        last_break = chunk_content.rfind('\n\n')
                        if last_break > chunk_size * 0.8:
                            end = start + last_break
            
            chunk_content = content[start:end]
            chunks.append(chunk_content)
            start = end
        
        logger.info(f"✅ Split content into {len(chunks)} chunks")
        return chunks
    
    def _write_shard_file(self, shard_key: str, urls: List[str]) -> List[str]:
        """Write LLMs file for a specific shard, automatically splitting if too large."""
        base_filename = f"llms-{self.site_name}-{shard_key}.txt"
        base_filepath = os.path.join(self.site_output_dir, base_filename)
        
        # Remove empty shard files
        if not urls:
            if os.path.exists(base_filepath):
                os.remove(base_filepath)
                logger.info(f"Removed empty shard file: {base_filepath}")
            return []
        
        # Build content
        content_parts = []
        for url in sorted(urls):  # Deterministic ordering
            if url in self.url_index:
                data = self.url_index[url]
                # Include EUR currency URL in block tag for reference
                eur_url = self._ensure_eur_currency(url)
                content_parts.append(f"<|{eur_url}-lllmstxt|>\n")
                content_parts.append(f"## {data['title']}\n")
                content_parts.append(f"{data['markdown']}\n\n")
        
        full_content = ''.join(content_parts)
        
        # Check if content needs splitting
        if len(full_content) <= self.max_characters:
            # Write single file
            with open(base_filepath, 'w', encoding='utf-8') as f:
                f.write(full_content)
            logger.info(f"Written shard file: {base_filepath}")
            return [base_filepath]
        else:
            # Split content and write multiple files
            chunks = self._split_large_content(full_content, base_filename)
            written_files = []
            
            for i, chunk in enumerate(chunks):
                if len(chunks) == 1:
                    # Single chunk, use original filename
                    filepath = base_filepath
                else:
                    # Multiple chunks, add part number
                    filename = f"llms-{self.site_name}-{shard_key}_part{i+1}.txt"
                    filepath = os.path.join(self.site_output_dir, filename)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(chunk)
                written_files.append(filepath)
                logger.info(f"Written shard file: {filepath} ({len(chunk):,} characters)")
            
            return written_files
    
    def full_crawl(self, limit: int = 10000) -> Dict[str, Any]:
        """Perform a full crawl of the website."""
        logger.info("Starting full crawl")
        
        # Map all URLs
        urls = self._map_website(limit)
        if not urls:
            raise ValueError("No URLs found for the website")
        
        # Filter to product paths (optional)
        urls = [u for u in urls if urlparse(u).path.strip("/")]
        
        # Process each URL
        touched_shards = set()
        processed_count = 0
        
        for i, url in enumerate(urls):
            logger.info(f"Processing {i+1}/{len(urls)}: {url}")
            
            scraped_data = self._scrape_url(url)
            if scraped_data:
                shard_key = self._update_url_data(url, scraped_data)
                touched_shards.add(shard_key)
                processed_count += 1
            
            # Small delay to avoid rate limiting
            time.sleep(0.1)
        
        # Write shard files for all touched shards
        written_files = []
        for shard_key in touched_shards:
            if shard_key in self.manifest:
                filepaths = self._write_shard_file(shard_key, self.manifest[shard_key])
                written_files.extend(filepaths)
        
        # Save index and manifest
        self._save_url_index()
        self._save_manifest()
        
        return {
            "operation": "full_crawl",
            "processed_urls": processed_count,
            "total_urls": len(urls),
            "touched_shards": list(touched_shards),
            "written_files": written_files
        }
    
    def auto_discover_products(self, category_url: str, max_products: int = 50) -> Dict[str, Any]:
        """Automatically discover and scrape all product pages from a category page."""
        logger.info(f"Auto-discovering products from category: {category_url}")
        
        # First, scrape the category page to get product listings
        category_data = self._scrape_url(category_url)
        if not category_data:
            raise ValueError(f"Failed to scrape category page: {category_url}")
        
        # Extract product URLs from the category page content
        product_urls = self._extract_product_urls(category_data["markdown"], category_url)
        
        if not product_urls:
            logger.warning(f"No product URLs found in category page: {category_url}")
            return {
                "operation": "auto_discover_products",
                "category_url": category_url,
                "discovered_products": 0,
                "processed_products": 0,
                "touched_shards": [],
                "written_files": []
            }
        
        # Limit the number of products to process
        if len(product_urls) > max_products:
            logger.info(f"Limiting to first {max_products} products out of {len(product_urls)} discovered")
            product_urls = product_urls[:max_products]
        
        # Process each product URL
        touched_shards = set()
        processed_count = 0
        written_files = []
        
        for i, product_url in enumerate(product_urls):
            logger.info(f"Processing product {i+1}/{len(product_urls)}: {product_url}")
            
            product_data = self._scrape_url(product_url)
            if product_data:
                shard_key = self._update_url_data(product_url, product_data)
                touched_shards.add(shard_key)
                processed_count += 1
            
            # Small delay to avoid rate limiting
            time.sleep(0.1)
        
        # Write shard files for all touched shards
        for shard_key in touched_shards:
            if shard_key in self.manifest:
                filepaths = self._write_shard_file(shard_key, self.manifest[shard_key])
                written_files.extend(filepaths)
        
        # Save index and manifest
        self._save_url_index()
        self._save_manifest()
        
        return {
            "operation": "auto_discover_products",
            "category_url": category_url,
            "discovered_products": len(product_urls),
            "processed_products": processed_count,
            "touched_shards": list(touched_shards),
            "written_files": written_files
        }
    
    def discover_new_products(self, category_url: str, pre_scraped_content: str, max_products: int = 20) -> Dict[str, Any]:
        """Discover and scrape only newly added products by comparing current vs previous collection page."""
        logger.info(f"Discovering new products from category: {category_url}")
        
        # Extract product URLs from the current (pre-scraped) content
        current_product_urls = set(self._extract_product_urls(pre_scraped_content, category_url))
        
        # Get previously known products for this collection from our index
        # We'll look for products that belong to the same collection
        collection_name = self._get_shard_key(category_url)
        previously_known_products = set()
        
        if collection_name in self.manifest:
            for url in self.manifest[collection_name]:
                if url in self.url_index and '/products/' in url:
                    previously_known_products.add(url)
        
        # Find newly added products (in current but not in previously known)
        new_product_urls = list(current_product_urls - previously_known_products)
        
        logger.info(f"Found {len(current_product_urls)} total products, {len(previously_known_products)} previously known, {len(new_product_urls)} new products")
        
        if not new_product_urls:
            logger.info("No new products found in collection")
            return {
                "operation": "discover_new_products",
                "category_url": category_url,
                "total_products": len(current_product_urls),
                "previously_known": len(previously_known_products),
                "new_products": 0,
                "processed_products": 0,
                "touched_shards": [],
                "written_files": []
            }
        
        # Limit the number of new products to process
        if len(new_product_urls) > max_products:
            logger.info(f"Limiting to first {max_products} new products out of {len(new_product_urls)} discovered")
            new_product_urls = new_product_urls[:max_products]
        
        # Process each new product URL
        touched_shards = set()
        processed_count = 0
        written_files = []
        
        for i, product_url in enumerate(new_product_urls):
            logger.info(f"Processing new product {i+1}/{len(new_product_urls)}: {product_url}")
            
            product_data = self._scrape_url(product_url)
            if product_data:
                shard_key = self._update_url_data(product_url, product_data)
                touched_shards.add(shard_key)
                processed_count += 1
            
            # Small delay to avoid rate limiting
            time.sleep(0.1)
        
        # Write shard files for all touched shards
        for shard_key in touched_shards:
            if shard_key in self.manifest:
                filepaths = self._write_shard_file(shard_key, self.manifest[shard_key])
                written_files.extend(filepaths)
        
        # Save index and manifest
        self._save_url_index()
        self._save_manifest()
        
        return {
            "operation": "discover_new_products",
            "category_url": category_url,
            "total_products": len(current_product_urls),
            "previously_known": len(previously_known_products),
            "new_products": len(new_product_urls),
            "processed_products": processed_count,
            "touched_shards": list(touched_shards),
            "written_files": written_files
        }
    
    def incremental_update(self, urls: List[str], operation: str, pre_scraped_content: Optional[str] = None) -> Dict[str, Any]:
        """Perform incremental update for specific URLs."""
        logger.info(f"Starting incremental update: {operation} for {len(urls)} URLs")
        
        touched_shards = set()
        processed_count = 0
        written_files = []
        
        if operation in ["added", "changed"]:
            # Process URLs to add/update
            for i, url in enumerate(urls):
                logger.info(f"Processing {operation}: {url}")
                
                # Use pre-scraped content for the first URL if provided
                content_to_use = pre_scraped_content if i == 0 and pre_scraped_content else None
                scraped_data = self._scrape_url(url, content_to_use)
                if scraped_data:
                    shard_key = self._update_url_data(url, scraped_data)
                    touched_shards.add(shard_key)
                    processed_count += 1
                
                time.sleep(0.1)
        
        elif operation == "removed":
            # Remove URLs
            for url in urls:
                logger.info(f"Removing: {url}")
                normalized_url = self._normalize_url(url)
                if normalized_url in self.url_index:
                    shard_key = self.url_index[normalized_url]["shard"]
                    touched_shards.add(shard_key)
                self._remove_url_data(url)
                processed_count += 1
        
        # Write shard files for all touched shards
        for shard_key in touched_shards:
            if shard_key in self.manifest:
                filepaths = self._write_shard_file(shard_key, self.manifest[shard_key])
                written_files.extend(filepaths)
        
        # Save index and manifest
        self._save_url_index()
        self._save_manifest()
        
        return {
            "operation": f"incremental_{operation}",
            "processed_urls": processed_count,
            "total_urls": len(urls),
            "touched_shards": list(touched_shards),
            "written_files": written_files
        }


def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(
        description="Update LLMs.txt files with sharding support using Firecrawl v2 API"
    )
    parser.add_argument("base_url", help="The base URL to process")
    
    # Operation modes (mutually exclusive)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--full", action="store_true", help="Perform full crawl")
    group.add_argument("--auto-discover", type=str, help="Auto-discover and scrape all products from a category page URL")
    group.add_argument("--discover-new", type=str, help="Discover and scrape only newly added products from a category page URL (requires --pre-scraped-content)")
    group.add_argument("--added", type=str, help="JSON array of URLs to add")
    group.add_argument("--changed", type=str, help="JSON array of URLs to update")
    group.add_argument("--removed", type=str, help="JSON array of URLs to remove")
    
    # Optional arguments
    parser.add_argument(
        "--base-root",
        help="Base root path to use for shard key extraction (env: BASE_ROOT)"
    )
    parser.add_argument(
        "--firecrawl-api-key",
        default=os.getenv("FIRECRAWL_API_KEY"),
        help="Firecrawl API key (default: from FIRECRAWL_API_KEY env var)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10000,
        help="Maximum number of URLs to process (default: 10000)"
    )
    parser.add_argument(
        "--max-products",
        type=int,
        default=50,
        help="Maximum number of products to auto-discover and scrape (default: 50)"
    )
    parser.add_argument(
        "--output-dir",
        default="out",
        help="Output directory for generated files (default: out)"
    )
    parser.add_argument(
        "--pre-scraped-content",
        help="Path to file containing pre-scraped content (for rivvy-observer integration)"
    )
    parser.add_argument(
        "--max-characters",
        type=int,
        default=300000,
        help="Maximum characters per file before splitting (default: 300000)"
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Validate API key
    if not args.firecrawl_api_key:
        logger.error("Firecrawl API key not provided. Set FIRECRAWL_API_KEY environment variable or use --firecrawl-api-key")
        sys.exit(1)
    
    # Get base_root from environment if not provided
    base_root = args.base_root or os.getenv("BASE_ROOT")
    
    # Create updater
    updater = ShardedLLMsUpdater(
        args.firecrawl_api_key,
        args.base_url,
        base_root,
        args.output_dir,
        args.max_characters
    )
    
    try:
        result = None
        
        if args.full:
            result = updater.full_crawl(args.limit)
        elif args.auto_discover:
            result = updater.auto_discover_products(args.auto_discover, args.max_products)
        elif args.discover_new:
            if not args.pre_scraped_content or not os.path.exists(args.pre_scraped_content):
                logger.error("--discover-new requires --pre-scraped-content with valid file path")
                sys.exit(1)
            with open(args.pre_scraped_content, 'r', encoding='utf-8') as f:
                pre_scraped_content = f.read()
            result = updater.discover_new_products(args.discover_new, pre_scraped_content, args.max_products)
        elif args.added:
            urls = json.loads(args.added)
            pre_scraped_content = None
            if args.pre_scraped_content and os.path.exists(args.pre_scraped_content):
                with open(args.pre_scraped_content, 'r', encoding='utf-8') as f:
                    pre_scraped_content = f.read()
            result = updater.incremental_update(urls, "added", pre_scraped_content)
        elif args.changed:
            urls = json.loads(args.changed)
            pre_scraped_content = None
            if args.pre_scraped_content and os.path.exists(args.pre_scraped_content):
                with open(args.pre_scraped_content, 'r', encoding='utf-8') as f:
                    pre_scraped_content = f.read()
            result = updater.incremental_update(urls, "changed", pre_scraped_content)
        elif args.removed:
            urls = json.loads(args.removed)
            result = updater.incremental_update(urls, "removed")
        
        # Print JSON summary for CI
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        logger.error(f"Failed to update LLMs files: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
