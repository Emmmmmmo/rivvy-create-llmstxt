#!/usr/bin/env python3
"""
Agnostic LLMs.txt Updater with Site Configuration Support

This script provides a unified interface for scraping any e-commerce website
by using site-specific configurations. It automatically adapts to different
URL patterns, categorization schemes, and filtering rules.

Usage:
  python3 scripts/update_llms_agnostic.py <domain> [options]
  
Examples:
  python3 scripts/update_llms_agnostic.py jgengineering.ie --full
  python3 scripts/update_llms_agnostic.py mydiy.ie --auto-discover https://www.mydiy.ie/power-tools/
  python3 scripts/update_llms_agnostic.py example.com --added '["https://example.com/product1"]'
"""

import os
import sys
import json
import time
import argparse
import logging
import re
from typing import Dict, List, Optional, Set, Any
from urllib.parse import urlparse, urljoin, urlunparse, parse_qs, urlencode
import requests
from datetime import datetime

# Add the scripts directory to the path to import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from site_config_manager import SiteConfigManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PendingQueue:
    """Persistent FIFO queue for pending product URLs."""

    def __init__(self, path: str):
        self.path = path
        self.items: List[Dict[str, Any]] = []
        self._index: Dict[str, int] = {}
        self._load()

    def _load(self):
        if not os.path.exists(self.path):
            self.items = []
            self._rebuild_index()
            return

        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.items = data.get("pending", []) if isinstance(data, dict) else []
        except Exception as exc:  # pragma: no cover - defensive, should not happen often
            logger.warning(f"Failed to load pending queue from {self.path}: {exc}")
            self.items = []
        self._rebuild_index()

    def _rebuild_index(self):
        self._index = {}
        for idx, item in enumerate(self.items):
            normalized = item.get("normalized_url")
            if normalized:
                self._index[normalized] = idx

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp_path = f"{self.path}.tmp"
        payload = {"pending": self.items}
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self.path)

    def enqueue(self, url: str, normalized_url: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Add a new URL to the tail of the queue if not already present."""
        if normalized_url in self._index:
            return False

        entry = {
            "url": url,
            "normalized_url": normalized_url,
            "metadata": metadata or {},
            "discovered_at": datetime.now().isoformat()
        }
        self.items.append(entry)
        self._index[normalized_url] = len(self.items) - 1
        return True

    def enqueue_entry(self, entry: Dict[str, Any]) -> bool:
        """Re-add an existing entry (e.g., after a failed scrape)."""
        normalized_url = entry.get("normalized_url")
        if not normalized_url:
            return False
        if normalized_url in self._index:
            return False
        self.items.append(entry)
        self._index[normalized_url] = len(self.items) - 1
        return True

    def dequeue_batch(self, size: int) -> List[Dict[str, Any]]:
        if size <= 0:
            return []
        batch = self.items[:size]
        self.items = self.items[size:]
        self._rebuild_index()
        return batch

    def peek_batch(self, size: int, offset: int = 0) -> List[Dict[str, Any]]:
        if size <= 0:
            return []
        start = max(offset, 0)
        end = start + size
        return self.items[start:end]

    def prune(self, existing_urls: Set[str]) -> int:
        """Remove any queued URLs already present in index/manifest."""
        before = len(self.items)
        if not existing_urls:
            return 0
        self.items = [item for item in self.items if item.get("normalized_url") not in existing_urls]
        removed = before - len(self.items)
        if removed:
            self._rebuild_index()
        return removed

    def __len__(self) -> int:
        return len(self.items)

    def as_list(self) -> List[Dict[str, Any]]:
        return list(self.items)

def retry_with_backoff(func, max_retries=3, initial_delay=2, backoff_multiplier=2):
    """
    Retry a function with exponential backoff.
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        backoff_multiplier: Multiplier for delay between retries
    
    Returns:
        Function result if successful, None if all retries failed
    """
    delay = initial_delay
    for attempt in range(max_retries):
        try:
            return func()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 502:
                if attempt < max_retries - 1:
                    logger.warning(f"Got 502 error, retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    delay *= backoff_multiplier
                else:
                    logger.error(f"Failed after {max_retries} attempts: {e}")
                    raise
            else:
                # For non-502 errors, raise immediately
                raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise
    return None


class AgnosticLLMsUpdater:
    """Agnostic LLMs.txt updater that works with any configured website."""
    
    def __init__(
        self,
        firecrawl_api_key: str,
        domain: str,
        output_dir: str = "out",
        max_characters: int = 300000,
        use_diff_extraction: bool = False,
        batch_size: Optional[int] = None,
        max_batches: Optional[int] = None,
        force_refresh: bool = False,
        dry_run: bool = False,
        pending_queue_path: Optional[str] = None,
        disable_discovery: bool = False,
        discovery_only: bool = False,
    ):
        """Initialize the updater with domain and configuration."""
        self.firecrawl_api_key = firecrawl_api_key
        self.domain = domain
        self.max_characters = max_characters
        self.use_diff_extraction = use_diff_extraction
        self.firecrawl_base_url = "https://api.firecrawl.dev/v2"
        self.headers = {
            "Authorization": f"Bearer {self.firecrawl_api_key}",
            "Content-Type": "application/json"
        }
        
        # Initialize site configuration manager
        self.config_manager = SiteConfigManager()
        self.site_config = self.config_manager.get_site_config(domain)
        
        # Extract site name for file naming
        self.site_name = domain.replace('www.', '').replace('.', '-')
        
        # Set up output directory
        self.output_dir = output_dir
        self.site_output_dir = os.path.join(self.output_dir, self.site_name)
        os.makedirs(self.site_output_dir, exist_ok=True)
        
        # File paths
        self.index_file = os.path.join(self.site_output_dir, f"llms-{self.site_name}-index.json")
        self.manifest_file = os.path.join(self.site_output_dir, f"llms-{self.site_name}-manifest.json")
        
        # Load existing data
        self.url_index = self._load_url_index()
        self.manifest = self._load_manifest()
        self.existing_urls: Set[str] = set(self.url_index.keys())
        
        # Batch handling + queue configuration
        self.force_refresh = force_refresh
        self.dry_run = dry_run
        self.disable_discovery = disable_discovery
        self.discovery_only = discovery_only
        self.max_batches = max_batches if max_batches and max_batches > 0 else 1

        effective_batch_size = batch_size
        if self.domain == "mydiy.ie" and effective_batch_size is None:
            # Default to conservative batches for mydiy.ie unless explicitly overridden
            effective_batch_size = 50
        if effective_batch_size is not None and effective_batch_size <= 0:
            effective_batch_size = None
        self.batch_size = effective_batch_size
        self.batch_mode = self.batch_size is not None

        queue_path = pending_queue_path or os.path.join(self.site_output_dir, "pending-queue.json")
        self.pending_queue_path = queue_path
        self.pending_queue = PendingQueue(queue_path)
        removed_from_queue = self.pending_queue.prune(self.existing_urls)
        if removed_from_queue:
            logger.info(f"Pruned {removed_from_queue} URLs already present in index from pending queue")

        # Initialize retry queue for failed URLs
        retry_queue_path = os.path.join(self.site_output_dir, "retry-queue.json")
        self.retry_queue_path = retry_queue_path
        self.retry_queue = PendingQueue(retry_queue_path)
        logger.info(f"Retry queue initialized with {len(self.retry_queue)} URLs")

        logger.info(f"Initialized for {self.site_config['name']} ({domain})")
    
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
        with open(self.manifest_file, 'w', encoding='utf-8') as f:
            json.dump(self.manifest, f, indent=2, ensure_ascii=False, sort_keys=True)
    
    def _clean_navigation_content(self, content: str) -> str:
        """Remove navigation and footer content from scraped content."""
        lines = content.split('\n')
        cleaned_lines = []
        skip_section = False
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # Skip navigation sections
            if any(nav_word in line_lower for nav_word in [
                'navigation', 'nav', 'menu', 'breadcrumb', 'breadcrumbs',
                'footer', 'sidebar', 'aside'
            ]):
                skip_section = True
                continue
            
            # Skip category navigation lists
            if line.startswith('- [') and any(cat in line_lower for cat in [
                'power tools', 'hand tools', 'garden tools', 'adhesives', 
                'decorating', 'security', 'drill bits', 'workwear', 'home leisure',
                'abrasives', 'ladders', 'uncategorised'
            ]):
                continue
            
            # Skip footer content
            if any(footer_word in line_lower for footer_word in [
                'newsletter sign up', 'contact us', 'about us', 'delivery',
                'returns', 'terms', 'privacy', 'weee recycling', 'all rights reserved',
                'facebook', 'twitter', 'google+', 'pinterest'
            ]):
                continue
            
            # Reset skip_section when we hit a new heading
            if line.startswith('#') and not skip_section:
                skip_section = False
            
            # Reset skip_section when we hit product content
            if any(product_word in line_lower for product_word in [
                'description', 'specification', 'price', '€', 'inc vat', 'in stock'
            ]):
                skip_section = False
            
            if not skip_section:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL for consistent indexing."""
        parsed = urlparse(url)
        
        # Preserve currency parameter if present
        query_params = parse_qs(parsed.query)
        if 'currency' in query_params:
            # Keep only currency parameter
            currency_query = urlencode({'currency': query_params['currency'][0]})
        else:
            currency_query = ''
        
        normalized = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            currency_query,  # Preserve currency parameter
            ''   # Remove fragment
        ))
        return normalized.rstrip('/')
    
    def _get_shard_key(self, url: str) -> str:
        """Get shard key for URL using site configuration."""
        return self.config_manager.get_shard_key(url, self.site_config)
    
    def _map_website(self, limit: int = 10000) -> List[str]:
        """Map website structure using Firecrawl."""
        logger.info(f"Mapping website structure for {self.domain}")
        
        try:
            response = requests.post(
                f"{self.firecrawl_base_url}/map",
                headers=self.headers,
                json={
                    "url": self.site_config["base_url"],
                    "limit": limit,
                    "includeSubdomains": True
                },
                timeout=90  # 90 second timeout for map operations
            )
            response.raise_for_status()
            
            data = response.json()
            urls = [link["url"] for link in data.get("links", [])]
            
            # Filter URLs using site configuration
            filtered_urls = self.config_manager.filter_urls(urls, self.site_config)
            
            logger.info(f"Found {len(urls)} total URLs, {len(filtered_urls)} after filtering")
            return filtered_urls
            
        except Exception as e:
            logger.error(f"Failed to map website: {e}")
            return []
    
    def _extract_product_url_from_diff(self, diff_text: str, removed_only: bool = False) -> List[str]:
        """
        Extract product URLs from a category page diff.
        When new products are added to a category page, extract all product URLs.
        By default, ONLY extracts URLs from ADDED lines (starting with +) to avoid existing products.
        If removed_only=True, extracts URLs from REMOVED lines (starting with -) instead.
        Returns a list of all valid product URLs found in the diff.
        """
        try:
            if removed_only:
                logger.info("Extracting REMOVED product URLs from category page diff")
            else:
                logger.info("Extracting ADDED product URLs from category page diff")
            
            # Image extensions to exclude
            image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.ico')
            
            # Split diff into lines and process ADDED or REMOVED lines
            target_lines = []
            if removed_only:
                # Process REMOVED lines (start with -)
                for line in diff_text.split('\n'):
                    if line.startswith('-') and not line.startswith('---'):  # - but not --- (file marker)
                        target_lines.append(line[1:])  # Remove the - prefix
            else:
                # Process ADDED lines (start with +)
                for line in diff_text.split('\n'):
                    if line.startswith('+') and not line.startswith('+++'):  # + but not +++ (file marker)
                        target_lines.append(line[1:])  # Remove the + prefix
            
            # Rejoin lines for processing
            content = '\n'.join(target_lines)
            logger.debug(f"Extracted {len(target_lines)} {'removed' if removed_only else 'added'} lines from diff")
            
            # Get product URL pattern from site config (agnostic approach)
            product_pattern = self.site_config.get('url_patterns', {}).get('product', '/products/')
            # Escape special regex characters in the pattern
            escaped_pattern = re.escape(product_pattern)
            
            # Look for product URLs in the target content (added or removed)
            # Pattern matches URLs like: https://domain.com/[product_pattern]/product-name
            # This is agnostic and works with any site's URL structure
            product_url_pattern = rf'https?://[^\s\)]+{escaped_pattern}[^\s\)\]"\'>]+'
            matches = re.findall(product_url_pattern, content)
            
            logger.debug(f"Using product pattern '{product_pattern}' from site config")
            
            all_valid_urls = []
            
            if matches:
                # Filter out image URLs and prefer actual product pages
                valid_urls = []
                for url in matches:
                    # Remove query parameters for checking
                    url_path = url.split('?')[0] if '?' in url else url
                    
                    # Skip if it's an image URL
                    if any(url_path.lower().endswith(ext) for ext in image_extensions):
                        logger.debug(f"Skipping image URL: {url}")
                        continue
                    
                    # Skip CDN URLs (they're usually images)
                    if '/cdn/' in url.lower() or '/cdn.' in url.lower():
                        logger.debug(f"Skipping CDN URL: {url}")
                        continue
                    
                    valid_urls.append(url)
                
                all_valid_urls.extend(valid_urls)
            
            # Also try to find relative product URLs (agnostic approach)
            # Get collection and product patterns from site config
            collection_pattern = self.site_config.get('url_patterns', {}).get('collection', '/collections/')
            # Build relative pattern using site config (more flexible)
            # Pattern: /[collection_pattern]/.../[product_pattern]/product-name or /[product_pattern]/product-name
            escaped_collection = re.escape(collection_pattern.strip('/'))
            escaped_product = re.escape(product_pattern.strip('/'))
            relative_pattern = rf'/(?:{escaped_collection}/[^/\s]+/)?{escaped_product}/[a-zA-Z0-9_-]+'
            relative_matches = re.findall(relative_pattern, content)
            
            if relative_matches:
                # Filter out any that might be part of image paths
                valid_relative = []
                for rel_url in relative_matches:
                    # Check the context around it to see if it's a link, not an image path
                    if rel_url in content:
                        # Get a snippet of context
                        idx = content.find(rel_url)
                        context = content[max(0, idx-50):min(len(content), idx+len(rel_url)+50)]
                        
                        # If it's in a markdown link or href, it's likely a product page
                        if '(' + rel_url + ')' in context or 'href="' + rel_url in context or "href='" + rel_url in context:
                            valid_relative.append(rel_url)
                
                if valid_relative:
                    # Construct full URLs using the base URL for all relative URLs
                    base_url = self.site_config["base_url"]
                    for relative_url in valid_relative:
                        product_url = urljoin(base_url, relative_url)
                        all_valid_urls.append(product_url)
            
            # Remove duplicates while preserving order
            unique_urls = list(dict.fromkeys(all_valid_urls))
            
            if unique_urls:
                logger.info(f"Found {len(unique_urls)} product URLs in diff (from added lines): {unique_urls}")
                return unique_urls
            else:
                logger.warning("No product URLs found in diff")
                return []
            
        except Exception as e:
            logger.error(f"Failed to extract product URLs from diff: {e}")
            return []
    
    def _extract_product_from_diff(self, diff_text: str) -> Optional[str]:
        """
        Extract only the new product information from a diff text.
        This handles git-style diffs and extracts only the added lines.
        """
        try:
            logger.info("Extracting new product from diff text")
            
            # Check if this is a git-style diff (starts with +++ or ---)
            if diff_text.startswith('+++') or diff_text.startswith('---') or diff_text.startswith('@@'):
                # Parse git diff format - extract only lines that start with '+' (additions)
                added_lines = []
                in_diff_section = False
                
                for line in diff_text.split('\n'):
                    # Skip diff headers
                    if line.startswith('+++') or line.startswith('---'):
                        continue
                    
                    # Start of a diff section
                    if line.startswith('@@'):
                        in_diff_section = True
                        continue
                    
                    # If in diff section and line starts with '+', it's an addition
                    if in_diff_section and line.startswith('+'):
                        # Remove the '+' prefix
                        added_lines.append(line[1:])
                    # Lines starting with '-' are deletions, skip them
                    elif line.startswith('-'):
                        continue
                    # Lines without prefix are context, skip them in strict diff mode
                    elif in_diff_section and not line.startswith(' '):
                        # This is a new section or end of diff
                        continue
                
                if added_lines:
                    # Join the added lines to form the new product content
                    new_product_content = '\n'.join(added_lines)
                    logger.info(f"Extracted {len(added_lines)} new lines from diff")
                    return new_product_content
            
            # If not a git diff or no additions found, look for product blocks in the diff
            # Try to identify product information blocks (usually start with #)
            product_blocks = []
            current_block = []
            
            for line in diff_text.split('\n'):
                # Check if this is a product heading (starts with # or ##)
                if re.match(r'^#+\s+\w', line):
                    # If we have a current block, save it
                    if current_block:
                        product_blocks.append('\n'.join(current_block))
                        current_block = []
                    # Start a new block
                    current_block.append(line)
                elif current_block:
                    # Add to current block
                    current_block.append(line)
                elif line.strip() and not line.startswith(('+++', '---', '@@', 'diff')):
                    # Potential product content line
                    current_block.append(line)
            
            # Add the last block if any
            if current_block:
                product_blocks.append('\n'.join(current_block))
            
            # Return the first substantial product block
            for block in product_blocks:
                if len(block.strip()) > 50:  # Minimum content length
                    logger.info(f"Extracted product block from diff ({len(block)} characters)")
                    return block
            
            # If no structured product found, return the entire diff as-is
            # (it might already be clean product content)
            logger.info("No structured diff found, using content as-is")
            return diff_text
            
        except Exception as e:
            logger.error(f"Failed to extract product from diff: {e}")
            return None
    
    def _parse_prescraped_to_json(self, url: str, markdown_content: str, is_diff: bool = False) -> Dict[str, Any]:
        """
        Parse pre-scraped markdown content into structured JSON format.
        This ensures webhook content matches the format of directly scraped content.
        
        Args:
            url: The URL of the product
            markdown_content: The markdown content to parse
            is_diff: If True, the content is from a diff and contains only new product info
        """
        try:
            # If this is diff content, extract only the new product
            if is_diff:
                extracted_content = self._extract_product_from_diff(markdown_content)
                if extracted_content:
                    markdown_content = extracted_content
                else:
                    logger.warning("Failed to extract product from diff, using original content")
            
            # Extract title (usually first # heading)
            title_match = re.search(r'^#\s+(.+)$', markdown_content, re.MULTILINE)
            title = title_match.group(1) if title_match else "Product"
            
            # Extract price (look for currency symbols and amounts)
            price_patterns = [
                r'(?:Price|price):\s*([€$£]\s*[\d,]+\.?\d*)',  # Price: €10.00
                r'([€$£]\s*[\d,]+\.?\d*)\s*(?:EUR|USD|GBP)',    # €10.00 EUR
                r'\*\*([€$£][\d,]+\.?\d*)\*\*',                  # **€10.00**
            ]
            price = None
            for pattern in price_patterns:
                price_match = re.search(pattern, markdown_content)
                if price_match:
                    price = price_match.group(1).strip()
                    break
            
            # Extract availability/status
            availability_patterns = [
                r'(?:Status|Availability):\s*\*?\*?([^\n*]+)',
                r'\*\*(?:Status|Availability):\*\*\s*([^\n]+)',
                r'(In Stock|Out of Stock|Sold out|Available|Unavailable)',
            ]
            availability = None
            for pattern in availability_patterns:
                avail_match = re.search(pattern, markdown_content, re.IGNORECASE)
                if avail_match:
                    availability = avail_match.group(1).strip()
                    # Remove any remaining bold markers
                    availability = re.sub(r'\*\*', '', availability)
                    break
            
            # Extract description (text after "Description" heading or first paragraph)
            desc_match = re.search(r'##\s+Description\s*\n+(.+?)(?=\n##|\Z)', markdown_content, re.DOTALL)
            if desc_match:
                description = desc_match.group(1).strip()
                # Clean up markdown formatting
                description = re.sub(r'\*\*(.+?)\*\*', r'\1', description)  # Remove bold
                description = re.sub(r'\n+', ' ', description)  # Single line
                description = description[:500]  # Limit length
            else:
                # Try to get first meaningful paragraph
                paragraphs = [p.strip() for p in markdown_content.split('\n\n') if len(p.strip()) > 50]
                description = paragraphs[0][:500] if paragraphs else "Product information"
            
            # Extract specifications (look for bullet points or structured data)
            specifications = []
            
            # Find specification sections
            spec_patterns = [
                r'##\s+Specifications?\s*\n+((?:[-*]\s+.+?\n)+)',
                r'##\s+(?:Features?|Details?|Product Details?)\s*\n+((?:[-*]\s+.+?\n)+)',
            ]
            
            for pattern in spec_patterns:
                spec_match = re.search(pattern, markdown_content, re.DOTALL)
                if spec_match:
                    spec_text = spec_match.group(1)
                    # Extract bullet points
                    specs = re.findall(r'[-*]\s+(.+)', spec_text)
                    specifications.extend([s.strip() for s in specs if len(s.strip()) > 5])
                    break
            
            # If no structured specs found, look for key-value pairs
            if not specifications:
                kv_patterns = re.findall(r'\*\*([^:]+):\*\*\s*([^\n]+)', markdown_content)
                # Clean up bold markers from keys and values
                for k, v in kv_patterns[:10]:
                    cleaned_key = re.sub(r'\*\*', '', k.strip())
                    cleaned_value = re.sub(r'\*\*', '', v.strip())
                    specifications.append(f"{cleaned_key}: {cleaned_value}")
            
            # Also clean any remaining bold markers from all specifications
            specifications = [re.sub(r'\*\*', '', spec) for spec in specifications]
            
            # Build structured JSON matching the direct scrape format
            # Order matches what Firecrawl returns: price, description, availability, product_name, specifications
            product_data = {
                "price": price or "Price not available",
                "description": description,
                "availability": availability or "Check website",
                "product_name": title,
                "specifications": specifications[:10] if specifications else []
            }
            
            # Create formatted content matching _extract_product_data output
            formatted_content = json.dumps(product_data, indent=2, ensure_ascii=False)
            
            return {
                "url": url,
                "content": formatted_content,
                "title": title,
                "scraped_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to parse pre-scraped content: {e}")
            # Fallback to original markdown if parsing fails
            return {
                "url": url,
                "content": markdown_content,
                "title": "Pre-scraped content",
                "scraped_at": datetime.now().isoformat()
            }
    
    def _scrape_url(self, url: str, pre_scraped_content: Optional[str] = None, is_diff: bool = False) -> Optional[Dict[str, Any]]:
        """Scrape URL content using Firecrawl extract endpoint for clean product data."""
        if pre_scraped_content:
            # Parse pre-scraped content to match structured JSON format
            return self._parse_prescraped_to_json(url, pre_scraped_content, is_diff)

        # Process both individual product URLs and collection/category pages
        product_pattern = self.site_config.get('url_patterns', {}).get('product', '/products/')
        if product_pattern in url.lower():
            # Individual product page - scrape directly
            return self._extract_product_data(url)
        else:
            # Collection/category page - scrape and extract all individual products
            logger.info(f"Processing collection/category page: {url}")
            return self._scrape_category_page(url)
    
    def _scrape_category_page(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape category page and extract all individual product URLs, then scrape each product."""
        try:
            # Rate limiting: wait 1 second before API call
            time.sleep(1)
            
            # Ensure EUR currency for proper pricing
            eur_url = self._ensure_eur_currency(url)
            
            response = requests.post(
                f"{self.firecrawl_base_url}/scrape",
                headers=self.headers,
                json={
                    "url": eur_url,
                    "formats": ["markdown"],
                    "onlyMainContent": True
                },
                timeout=60  # 60 second timeout for scrape operations
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get("success") and data.get("data"):
                # Handle different response formats from Firecrawl API
                response_data = data["data"]
                
                # Try to get content from different possible fields
                content = ""
                if "markdown" in response_data:
                    content = response_data.get("markdown", "")
                elif "html" in response_data:
                    content = response_data.get("html", "")
                elif "text" in response_data:
                    content = response_data.get("text", "")
                else:
                    logger.warning(f"No content found in Firecrawl response for {url}")
                    content = ""
                
                # Try to get title from different possible fields
                title = ""
                if "metadata" in response_data and response_data["metadata"]:
                    title = response_data["metadata"].get("title", "")
                elif "title" in response_data:
                    title = response_data.get("title", "")
                else:
                    title = "Product"
                
                # Extract all product URLs from the collection page
                product_urls = self._extract_product_url_from_diff(content, removed_only=False)
                
                if len(product_urls) == 0:
                    logger.info(f"ℹ️  Category page (no direct product listings): {url}")
                else:
                    logger.info(f"Found {len(product_urls)} product URLs in collection page: {url}")
                
                # Scrape each individual product page
                scraped_products = []
                for product_url in product_urls:
                    try:
                        logger.info(f"Scraping individual product: {product_url}")
                        product_data = self._extract_product_data(product_url)
                        if product_data:
                            scraped_products.append({
                                "url": product_url,
                                "content": product_data.get("content", ""),
                                "title": product_data.get("title", "Product"),
                                "scraped_at": product_data.get("scraped_at", datetime.now().isoformat())
                            })
                        else:
                            logger.warning(f"Failed to scrape product: {product_url}")
                    except Exception as e:
                        logger.error(f"Error scraping product {product_url}: {e}")
                        continue
                
                # Combine all scraped product data into a single content block
                combined_content = ""
                for product in scraped_products:
                    combined_content += f"<|{product['url']}|>\n## {product['title']}\n\n{product['content']}\n\n"
                
                if len(scraped_products) > 0:
                    logger.info(f"✅ Successfully scraped {len(scraped_products)} products from collection page")
                else:
                    logger.debug(f"No products found on category page (this is normal for navigation pages)")
                
                return {
                    "url": eur_url,  # Use EUR URL for indexing
                    "content": combined_content,
                    "title": title,
                    "scraped_at": datetime.now().isoformat(),
                    "product_count": len(scraped_products)
                }
            
        except KeyError as e:
            logger.error(f"Missing expected field in Firecrawl response for category page {url}: {e}")
            logger.debug(f"Response data structure: {data if 'data' in locals() else 'No data available'}")
        except Exception as e:
            logger.error(f"Failed to scrape category page {url}: {e}")
        
        return None
    
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
    
    def _extract_breadcrumbs_from_html(self, html: str) -> List[Dict[str, str]]:
        """
        Extract breadcrumb trail from HTML.
        Returns list of dicts with 'text' and 'url' keys.
        Handles MyDIY.ie breadcrumb format: <div class="breadcrumb">
        """
        import re
        import html as html_module
        
        breadcrumbs = []
        
        try:
            # Find breadcrumb div - MyDIY.ie uses <div class="breadcrumb">
            breadcrumb_match = re.search(
                r'<div class="breadcrumb">(.*?)</div>', 
                html, 
                re.DOTALL | re.IGNORECASE
            )
            
            if not breadcrumb_match:
                return breadcrumbs
            
            breadcrumb_html = breadcrumb_match.group(1)
            
            # Extract all links from breadcrumb
            links = re.findall(
                r'<a href="([^"]+)">([^<]+)</a>', 
                breadcrumb_html
            )
            
            # Build breadcrumb list
            for url, text in links:
                breadcrumbs.append({
                    'text': html_module.unescape(text.strip()),  # Handle &amp; etc.
                    'url': url
                })
            
            logger.debug(f"Extracted {len(breadcrumbs)} breadcrumb items")
            
        except Exception as e:
            logger.warning(f"Failed to extract breadcrumbs: {e}")
        
        return breadcrumbs
    
    def _determine_shard_from_breadcrumbs(self, breadcrumbs: List[Dict[str, str]]) -> str:
        """
        Determine shard name from breadcrumb trail.
        Uses most specific category (last item before product).
        Returns cleaned shard name or "other_products".
        """
        import re
        
        if not breadcrumbs or len(breadcrumbs) <= 1:
            # Only "Home" or empty
            return "other_products"
        
        # Determine which category to use
        if len(breadcrumbs) == 2:
            # Home > Main Category
            category = breadcrumbs[1]['text']
        else:
            # Home > Main > Sub > Leaf
            # Use the most specific (last) category
            category = breadcrumbs[-1]['text']
        
        # Clean category name for shard
        shard_name = category.lower()
        shard_name = shard_name.replace(' ', '_')
        shard_name = shard_name.replace(',', '')
        shard_name = shard_name.replace('&', 'and')
        shard_name = shard_name.replace('-', '_')
        shard_name = shard_name.replace('(', '')
        shard_name = shard_name.replace(')', '')
        # Remove any remaining non-alphanumeric characters except underscore
        shard_name = re.sub(r'[^a-z0-9_]', '', shard_name)
        
        # Remove multiple underscores
        shard_name = re.sub(r'_+', '_', shard_name)
        
        # Remove leading/trailing underscores
        shard_name = shard_name.strip('_')
        
        if not shard_name:
            return "other_products"
        
        logger.debug(f"Determined shard from breadcrumbs: {shard_name} (from '{category}')")
        
        return shard_name
    
    def _extract_product_data(self, url: str) -> Optional[Dict[str, Any]]:
        """Extract structured product data using Firecrawl scrape endpoint with JSON format."""
        try:
            # Rate limiting: wait 1 second before API call
            time.sleep(1)
            
            # Ensure EUR currency for proper pricing
            eur_url = self._ensure_eur_currency(url)
            
            # Check if breadcrumbs are enabled for this site
            use_breadcrumbs = self.site_config.get('shard_extraction', {}).get('use_breadcrumbs', False)
            
            def make_request():
                try:
                    # Request both JSON and HTML formats if breadcrumbs enabled
                    formats = [{
                        "type": "json",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "product_name": {
                                    "type": "string",
                                    "description": "The name/title of the product"
                                },
                                "description": {
                                    "type": "string", 
                                    "description": "The main product description"
                                },
                                "price": {
                                    "type": "string",
                                    "description": "The current price of the product (including currency symbol)"
                                },
                                "availability": {
                                    "type": "string",
                                    "description": "Product availability status (e.g., 'In Stock', 'Out of Stock')"
                                },
                                "specifications": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Key product specifications or features"
                                }
                            },
                            "required": ["product_name", "description", "price"]
                        }
                    }]
                    
                    # Add HTML format if breadcrumbs enabled
                    if use_breadcrumbs:
                        formats.append("html")
                    
                    response = requests.post(
                        f"{self.firecrawl_base_url}/scrape",
                        headers=self.headers,
                        json={
                            "url": eur_url,
                            "formats": formats,
                            "onlyMainContent": False  # Need full page for breadcrumbs
                        },
                        timeout=60  # Increased timeout from 30 to 60 seconds
                    )
                    response.raise_for_status()
                    return response
                except requests.exceptions.Timeout:
                    logger.warning(f"Timeout scraping {eur_url}, will retry...")
                    return None  # Return None to trigger retry
                except requests.exceptions.RequestException as e:
                    logger.warning(f"Request error scraping {eur_url}: {e}")
                    return None  # Return None to trigger retry
            
            # NO automatic retries - fail fast and move to retry queue
            # This prevents any API wastage on problematic URLs
            # Users can manually retry later with --process-retry-queue
            response = make_request()
            
            if response:
                data = response.json()
                if data.get("success") and data.get("data"):
                    response_data = data["data"]
                    extracted_data = response_data.get("json", {})
                    
                    # Extract HTML if available (for breadcrumbs)
                    html_content = response_data.get("html", "")
                    
                    if extracted_data:
                        # Use the extracted data directly as JSON content
                        import json
                        content = json.dumps(extracted_data, indent=2, ensure_ascii=False)
                        
                        result = {
                            "url": eur_url,  # Use EUR URL for indexing
                            "content": content,
                            "title": extracted_data.get("product_name", ""),
                            "scraped_at": datetime.now().isoformat()
                        }
                        
                        # Add HTML if breadcrumbs enabled
                        if use_breadcrumbs and html_content:
                            result["html"] = html_content
                        
                        return result
                    else:
                        # Fallback: try to get content from other fields if JSON extraction failed
                        logger.warning(f"JSON extraction failed for {url}, trying fallback methods")
                        
                        # Try to get content from markdown field
                        content = ""
                        if "markdown" in response_data:
                            content = response_data.get("markdown", "")
                        elif "html" in response_data:
                            content = response_data.get("html", "")
                        elif "text" in response_data:
                            content = response_data.get("text", "")
                        
                        if content:
                            # Try to get title
                            title = ""
                            if "metadata" in response_data and response_data["metadata"]:
                                title = response_data["metadata"].get("title", "")
                            elif "title" in response_data:
                                title = response_data.get("title", "")
                            else:
                                title = "Product"
                            
                            result = {
                                "url": eur_url,
                                "content": content,
                                "title": title,
                                "scraped_at": datetime.now().isoformat()
                            }
                            
                            # Add HTML if breadcrumbs enabled
                            if use_breadcrumbs and html_content:
                                result["html"] = html_content
                            
                            return result
            
        except KeyError as e:
            logger.error(f"Missing expected field in Firecrawl response for {url}: {e}")
            logger.debug(f"Response data structure: {data if 'data' in locals() else 'No data available'}")
        except Exception as e:
            logger.error(f"Failed to extract product data from {url}: {e}")
        
        return None
    
    def _update_url_data(self, url: str, scraped_data: Dict[str, Any]) -> str:
        """Update URL data in index and return shard key with breadcrumb fallback."""
        normalized_url = self._normalize_url(url)
        
        # Try URL path extraction first, with breadcrumb fallback if available
        shard_key = self._get_shard_key_with_breadcrumbs(url, scraped_data)
        
        # Update URL index (use shard_key field, not old shard field)
        self.url_index[normalized_url] = {
            "title": scraped_data.get("title", ""),
            "markdown": scraped_data.get("content", ""),
            "shard_key": shard_key,  # ← Use shard_key not shard!
            "updated_at": scraped_data.get("scraped_at", datetime.now().isoformat())
        }
        
        # Update manifest
        if shard_key not in self.manifest:
            self.manifest[shard_key] = []
        
        if normalized_url not in self.manifest[shard_key]:
            self.manifest[shard_key].append(normalized_url)

        self.existing_urls.add(normalized_url)

        return shard_key
    
    def _get_shard_key_with_breadcrumbs(self, url: str, scraped_data: Dict[str, Any]) -> str:
        """
        Get shard key with proper waterfall:
        1. URL path extraction (works for JG Engineering)
        2. Breadcrumb extraction (NEW - for MyDIY)
        3. Keyword matching (existing fallback)
        4. other_products (ultimate fallback)
        """
        # Check if breadcrumbs are enabled for this site
        use_breadcrumbs = self.site_config.get('shard_extraction', {}).get('use_breadcrumbs', False)
        breadcrumb_fallback = self.site_config.get('shard_extraction', {}).get('breadcrumb_fallback', True)
        
        # Step 1: Try URL path extraction (NO keyword matching yet!)
        shard_key = self._get_shard_key_from_url_only(url)
        
        # Step 2: If URL extraction failed and breadcrumbs enabled, try breadcrumbs
        if use_breadcrumbs and breadcrumb_fallback and shard_key == "other_products":
            if "html" in scraped_data and scraped_data["html"]:
                breadcrumbs = self._extract_breadcrumbs_from_html(scraped_data["html"])
                if breadcrumbs:
                    breadcrumb_shard = self._determine_shard_from_breadcrumbs(breadcrumbs)
                    if breadcrumb_shard != "other_products":
                        logger.info(f"Using breadcrumb-derived shard '{breadcrumb_shard}' for {url}")
                        return breadcrumb_shard
        
        # Step 3: If breadcrumbs also failed, try keyword matching
        if shard_key == "other_products":
            # Extract product name from URL for keyword matching
            from urllib.parse import urlparse
            parsed = urlparse(url)
            path_segments = [seg for seg in parsed.path.split('/') if seg]
            if path_segments:
                product_name = path_segments[-1]
                keyword_shard = self.config_manager._categorize_product(product_name, self.site_config)
                if keyword_shard != "other_products":
                    logger.debug(f"Using keyword-derived shard '{keyword_shard}' for {url}")
                    return keyword_shard
        
        # Step 4: Return whatever we have (might still be other_products)
        return shard_key
    
    def _get_shard_key_from_url_only(self, url: str) -> str:
        """Extract shard key from URL path only, without keyword matching."""
        from urllib.parse import urlparse
        parsed_url = urlparse(url)
        path_segments = [seg for seg in parsed_url.path.split('/') if seg]
        
        shard_config = self.site_config.get("shard_extraction", {})
        segment_index = shard_config.get("segment_index", 1)
        
        # Check for collection-style URLs (JG Engineering)
        if len(path_segments) >= 2:
            if path_segments[0] == "collections" and len(path_segments) > segment_index:
                # /collections/category/products/product-name
                return self.config_manager._sanitize_shard(path_segments[segment_index])
            elif path_segments[0] == "products":
                # Direct product URL like /products/product-name
                # Return other_products (let breadcrumbs handle it)
                return "other_products"
        
        # Try path segment extraction
        if len(path_segments) > segment_index:
            return self.config_manager._sanitize_shard(path_segments[segment_index])
        
        return "other_products"
    
    def _remove_url_data(self, url: str):
        """Remove URL data from index and manifest."""
        normalized_url = self._normalize_url(url)
        
        logger.info(f"🗑️  Attempting to remove URL: {url}")
        logger.info(f"   Normalized to: {normalized_url}")

        if normalized_url in self.url_index:
            shard_key = self.url_index[normalized_url]["shard_key"]
            logger.info(f"   Found in url_index under shard: {shard_key}")
            del self.url_index[normalized_url]
            logger.info(f"   ✅ Removed from url_index")
            self.existing_urls.discard(normalized_url)
            
            # Remove from manifest
            if shard_key in self.manifest:
                logger.info(f"   Shard '{shard_key}' exists in manifest with {len(self.manifest[shard_key])} URLs")
                logger.info(f"   URLs in manifest for this shard: {self.manifest[shard_key]}")
                
                if normalized_url in self.manifest[shard_key]:
                    self.manifest[shard_key].remove(normalized_url)
                    logger.info(f"   ✅ Removed from manifest (now {len(self.manifest[shard_key])} URLs remain)")
                    
                    # Clean up empty shards
                    if not self.manifest[shard_key]:
                        del self.manifest[shard_key]
                        logger.info(f"   🗑️  Removed empty shard from manifest")
                else:
                    logger.warning(f"   ⚠️  URL NOT FOUND in manifest[{shard_key}]!")
                    logger.warning(f"   This is a BUG - url_index and manifest are out of sync!")
            else:
                logger.warning(f"   ⚠️  Shard '{shard_key}' NOT FOUND in manifest!")
        else:
            logger.warning(f"   ⚠️  URL NOT FOUND in url_index!")
    
    def _write_shard_file(self, shard_key: str, urls: List[str]) -> List[str]:
        """Write shard file with content from URLs, automatically splitting if too large."""
        if not urls:
            return []
        
        # Read existing products from all shard files for this key (including splits)
        existing_products = {}
        base_pattern = f"llms-{self.site_name}-{shard_key}"
        
        # Check for main file and any split files
        import glob
        shard_files = glob.glob(os.path.join(self.site_output_dir, f"{base_pattern}*.txt"))
        
        for filepath in shard_files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Parse existing products by URL marker
                current_url = None
                current_content = []
                
                for line in content.split('\n'):
                    if line.startswith('<|') and line.endswith('|>'):
                        # Save previous product if exists
                        if current_url and current_content:
                            existing_products[current_url] = '\n'.join(current_content)
                        
                        # Start new product
                        current_url = line.strip()[2:-2]  # Extract URL from <|URL|>
                        current_content = [line]
                    elif current_url is not None:
                        current_content.append(line)
                
                # Save last product
                if current_url and current_content:
                    existing_products[current_url] = '\n'.join(current_content)
                
            except Exception as e:
                logger.warning(f"Failed to read existing shard file {filepath}: {e}")
        
        if existing_products:
            logger.debug(f"Loaded {len(existing_products)} existing products from {len(shard_files)} file(s)")
        
        # Collect all products for this shard (existing + new from urls list)
        all_products = {}
        
        # First, add all existing products
        for url, content in existing_products.items():
            all_products[url] = content
        
        # Then add/update products from the manifest URLs
        for url in urls:
            if url in self.url_index:
                try:
                    content = self.url_index[url].get("markdown", "")
                    title = self.url_index[url].get("title", "Product")
                    
                    # Build content with header
                    header = f"<|{url}|>\n## {title}\n\n"
                    content_with_header = header + content
                    
                    all_products[url] = content_with_header
                except KeyError as e:
                    logger.warning(f"Missing field in URL index for {url}: {e}")
                    continue
        
        if not all_products:
            return []
        
        # Split products into chunks that fit within max_characters
        chunks = []
        current_chunk = []
        current_chars = 0
        
        for url in sorted(all_products.keys()):  # Sort for consistency
            product_content = all_products[url]
            if not product_content.endswith('\n\n'):
                product_content += '\n\n'
            
            product_size = len(product_content)
            
            # If adding this product would exceed limit, start new chunk
            if current_chars + product_size > self.max_characters and current_chunk:
                chunks.append(current_chunk)
                current_chunk = [product_content]
                current_chars = product_size
            else:
                current_chunk.append(product_content)
                current_chars += product_size
        
        # Add final chunk
        if current_chunk:
            chunks.append(current_chunk)
        
        # Delete old shard files before writing new ones
        for old_file in shard_files:
            try:
                os.remove(old_file)
                logger.debug(f"Removed old shard file: {os.path.basename(old_file)}")
            except Exception as e:
                logger.warning(f"Failed to remove old file {old_file}: {e}")
        
        # Write chunks to files
        written_files = []
        
        if len(chunks) == 1:
            # Single file, no split needed
            filename = f"llms-{self.site_name}-{shard_key}.txt"
            filepath = os.path.join(self.site_output_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(''.join(chunks[0]))
            
            product_count = len(chunks[0])
            char_count = sum(len(p) for p in chunks[0])
            logger.info(f"Wrote shard file: {filename} ({product_count} products, {char_count} characters)")
            written_files.append(filepath)
        else:
            # Multiple files needed
            logger.info(f"Splitting shard '{shard_key}' into {len(chunks)} files ({len(all_products)} total products)")
            
            for i, chunk in enumerate(chunks, 1):
                filename = f"llms-{self.site_name}-{shard_key}_{i}.txt"
                filepath = os.path.join(self.site_output_dir, filename)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(''.join(chunk))
                
                product_count = len(chunk)
                char_count = sum(len(p) for p in chunk)
                logger.info(f"  Wrote {filename} ({product_count} products, {char_count} characters)")
                written_files.append(filepath)
        
        return written_files

    def _should_skip_existing(self, normalized_url: str) -> bool:
        """Return True if URL already scraped and refresh not forced."""
        return not self.force_refresh and normalized_url in self.existing_urls
    
    def _add_to_retry_queue(self, entry: Dict[str, Any]) -> None:
        """Add a failed URL to the retry queue for manual review/retry later."""
        url = entry.get("url")
        normalized_url = entry.get("normalized_url")
        
        # Only add if not already in retry queue
        if normalized_url not in self.retry_queue._index:
            self.retry_queue.enqueue_entry(entry)
            self.retry_queue.save()
            logger.info(f"Added to retry queue: {url}")
        else:
            logger.debug(f"Already in retry queue: {url}")

    def _enqueue_for_batch(
        self,
        url: str,
        category_shard_key: Optional[str] = None,
        source_category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Queue a URL for batched scraping, capturing skip/duplicate status."""
        normalized_url = self._normalize_url(url)
        result = {
            "url": url,
            "normalized_url": normalized_url,
            "queued": False,
            "skipped_existing": False,
            "duplicate": False,
        }

        if self._should_skip_existing(normalized_url):
            result["skipped_existing"] = True
            return result

        metadata: Dict[str, Any] = {"attempts": 0}
        if category_shard_key:
            metadata["category_shard_key"] = category_shard_key
        if source_category:
            metadata["source_category"] = source_category

        queued = self.pending_queue.enqueue(url, normalized_url, metadata)
        if queued:
            result["queued"] = True
        else:
            result["duplicate"] = True
        return result

    def process_queue_batch(self, batch_size: Optional[int] = None) -> Dict[str, Any]:
        """Process a batch (or batches) of queued URLs."""
        effective_batch = batch_size or self.batch_size
        if not effective_batch:
            return {
                "operation": "process_queue_batch",
                "batches_requested": self.max_batches,
                "processed_urls": 0,
                "skipped_existing": 0,
                "queue_size": len(self.pending_queue),
                "reason": "batch_size_not_set",
                "dry_run": self.dry_run,
            }

        total_preview = effective_batch * self.max_batches if self.max_batches else effective_batch
        queue_size = len(self.pending_queue)
        if self.dry_run:
            preview_items = self.pending_queue.peek_batch(total_preview)
            return {
                "operation": "process_queue_batch",
                "dry_run": True,
                "preview_count": len(preview_items),
                "preview_urls": [item["url"] for item in preview_items],
                "queue_size": queue_size,
                "batch_size": effective_batch,
                "max_batches": self.max_batches,
            }

        processed_count = 0
        skipped_existing = 0
        failed_urls: List[str] = []
        touched_shards: Set[str] = set()
        written_files: List[str] = []
        batches_executed = 0
        queue_mutated = False

        while len(self.pending_queue) > 0 and batches_executed < self.max_batches:
            batch = self.pending_queue.dequeue_batch(effective_batch)
            if not batch:
                break

            queue_mutated = True
            batches_executed += 1
            requeue_entries: List[Dict[str, Any]] = []

            logger.info(
                f"Processing batch {batches_executed}/{self.max_batches} with {len(batch)} queued URLs"
            )

            for entry in batch:
                url = entry.get("url")
                normalized_url = entry.get("normalized_url")
                metadata = entry.get("metadata", {})

                if not url or not normalized_url:
                    logger.warning("Encountered malformed queue entry, skipping")
                    continue

                if self._should_skip_existing(normalized_url):
                    skipped_existing += 1
                    logger.info(f"⏭️  Skipping already-scraped URL: {url}")
                    continue

                try:
                    scraped_data = self._scrape_url(url)
                except Exception as exc:  # pragma: no cover - surface error but keep loop going
                    logger.error(f"Error scraping {url}: {exc}")
                    scraped_data = None

                if not scraped_data:
                    # CHANGED: No automatic retry - move to retry queue immediately
                    # This prevents API wastage on consistently failing URLs
                    attempts = metadata.get("attempts", 0) + 1
                    metadata["attempts"] = attempts
                    metadata["last_error"] = f"No data returned at {datetime.now().isoformat()}"
                    entry["metadata"] = metadata
                    
                    # Add to failed_urls list for tracking
                    failed_urls.append(url)
                    
                    # Save to retry queue for manual review/retry later
                    self._add_to_retry_queue(entry)
                    logger.warning(f"Failed to scrape {url}; moved to retry queue (attempt {attempts})")
                    continue

                category_shard_key = metadata.get("category_shard_key")
                if category_shard_key:
                    shard_key = self._update_url_data_with_category(url, scraped_data, category_shard_key)
                else:
                    shard_key = self._update_url_data(url, scraped_data)

                touched_shards.add(shard_key)
                processed_count += 1
                self.existing_urls.add(normalized_url)
                logger.info(f"Scraped {url} into shard '{shard_key}'")

            # NOTE: Removed automatic re-queueing to prevent API wastage
            # Failed URLs are now moved to retry queue for manual review

        # Persist queue changes if anything was dequeued or requeued
        if queue_mutated:
            self.pending_queue.save()

        # Write updated shard files and persist manifests/index
        if processed_count:
            for shard_key in touched_shards:
                if shard_key in self.manifest:
                    written_files.extend(self._write_shard_file(shard_key, self.manifest[shard_key]))
            self._save_url_index()
            self._save_manifest()

        # Log batch processing summary
        total_processed = processed_count + skipped_existing
        if total_processed > 0:
            logger.info(f"📊 Batch Summary:")
            logger.info(f"   ✅ Processed: {processed_count} URLs")
            if skipped_existing > 0:
                logger.info(f"   ⏭️  Skipped: {skipped_existing} already-scraped URLs")
            if failed_urls:
                logger.info(f"   ⚠️  Failed: {len(failed_urls)} URLs (moved to retry queue)")
            logger.info(f"   📦 Queue remaining: {len(self.pending_queue)} URLs")

        return {
            "operation": "process_queue_batch",
            "processed_urls": processed_count,
            "skipped_existing": skipped_existing,
            "failed_urls": failed_urls,
            "queue_size": len(self.pending_queue),
            "batch_size": effective_batch,
            "batches_executed": batches_executed,
            "written_files": written_files,
        }
    
    def full_crawl(self, limit: int = 10000) -> Dict[str, Any]:
        """Perform full crawl of the website."""
        logger.info(f"Starting full crawl for {self.domain}")
        
        # Map website
        urls = self._map_website(limit)
        if not urls:
            return {"error": "No URLs found to crawl"}
        
        # Process URLs
        processed_count = 0
        touched_shards = set()
        
        for i, url in enumerate(urls):
            logger.info(f"Processing {i+1}/{len(urls)}: {url}")
            
            scraped_data = self._scrape_url(url)
            if scraped_data:
                shard_key = self._update_url_data(url, scraped_data)
                touched_shards.add(shard_key)
                processed_count += 1
            
            # Rate limiting
            time.sleep(0.1)
        
        # Write shard files
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
    
    def hierarchical_discovery(self, main_category_url: str, max_products_per_category: int = 50, max_categories: int = 10) -> Dict[str, Any]:
        """Discover and scrape products using the full 4-level hierarchy."""
        logger.info(f"Starting hierarchical discovery from: {main_category_url}")
        
        # Level 1: Discover subcategories from main category page
        logger.info("Level 1: Discovering subcategories...")
        subcategory_urls = self._discover_subcategories(main_category_url)
        
        if not subcategory_urls:
            return {"error": "No subcategories found in main category page"}
        
        logger.info(f"Found {len(subcategory_urls)} subcategories")
        
        # Limit subcategories for testing
        if max_categories and len(subcategory_urls) > max_categories:
            subcategory_urls = subcategory_urls[:max_categories]
            logger.info(f"Limited to first {max_categories} subcategories for testing")
        
        total_processed = 0
        total_products = 0
        all_touched_shards = set()
        all_written_files = []
        
        # Level 2: For each subcategory, discover product categories
        for i, subcategory_url in enumerate(subcategory_urls, 1):
            logger.info(f"Level 2 ({i}/{len(subcategory_urls)}): Processing subcategory: {subcategory_url}")
            
            # Discover product categories from subcategory page
            product_category_urls = self._discover_product_categories(subcategory_url)
            
            if not product_category_urls:
                logger.warning(f"No product categories found in: {subcategory_url}")
                # Try to scrape products directly from this subcategory (it might be a product page itself)
                logger.info(f"Attempting to scrape products directly from: {subcategory_url}")
                result = self.auto_discover_products(subcategory_url, max_products_per_category)
                
                if "error" not in result:
                    total_processed += result.get("processed_urls", 0)
                    total_products += result.get("total_urls", 0)
                    all_touched_shards.update(result.get("touched_shards", []))
                    all_written_files.extend(result.get("written_files", []))
                continue
            
            logger.info(f"Found {len(product_category_urls)} product categories in subcategory")
            
            # Level 3: For each product category, discover and scrape products
            for j, product_category_url in enumerate(product_category_urls, 1):
                logger.info(f"Level 3 ({j}/{len(product_category_urls)}): Processing product category: {product_category_url}")
                
                # Use existing auto_discover_products method for Level 3 → Level 4
                result = self.auto_discover_products(product_category_url, max_products_per_category)
                
                if "error" not in result:
                    total_processed += result.get("processed_urls", 0)
                    total_products += result.get("total_urls", 0)
                    all_touched_shards.update(result.get("touched_shards", []))
                    all_written_files.extend(result.get("written_files", []))
        
        return {
            "operation": "hierarchical_discovery",
            "processed_urls": total_processed,
            "total_urls": total_products,
            "subcategories_processed": len(subcategory_urls),
            "touched_shards": list(all_touched_shards),
            "written_files": all_written_files
        }
    
    def _discover_subcategories(self, main_category_url: str) -> List[str]:
        """Discover subcategory URLs from a main category page (Level 1 → Level 2)."""
        try:
            # Rate limiting: wait 1 second before API call
            time.sleep(1)
            
            response = requests.post(
                f"{self.firecrawl_base_url}/map",
                headers=self.headers,
                json={
                    "url": main_category_url,
                    "limit": 100,  # Get more URLs to filter from
                    "includeSubdomains": False
                },
                timeout=90  # 90 second timeout for map operations
            )
            
            if response.status_code == 200:
                data = response.json()
                all_urls = [link["url"] for link in data.get("links", [])]
                
                # Filter for subcategory URLs (Level 2) and deduplicate
                subcategory_urls = []
                seen_normalized = set()
                for url in all_urls:
                    if self._is_subcategory_url(url, main_category_url):
                        # Normalize URL (remove trailing slash) to avoid duplicates
                        normalized = url.rstrip('/')
                        if normalized not in seen_normalized:
                            seen_normalized.add(normalized)
                            subcategory_urls.append(normalized)
                
                return subcategory_urls
                
        except Exception as e:
            logger.error(f"Failed to discover subcategories from {main_category_url}: {e}")
        
        return []
    
    def _discover_product_categories(self, subcategory_url: str) -> List[str]:
        """Discover product category URLs from a subcategory page (Level 2 → Level 3)."""
        try:
            # Rate limiting: wait 1 second before API call
            time.sleep(1)
            
            # Use SCRAPE with links format to get all links from the page
            # SCRAPE is better than MAP here because it gets all links from rendered page
            response = requests.post(
                f"{self.firecrawl_base_url}/scrape",
                headers=self.headers,
                json={
                    "url": subcategory_url,
                    "formats": ["links"]
                    # NOT using onlyMainContent to ensure we get all category links (nav included)
                },
                timeout=60  # 60 second timeout for scrape operations
            )
            
            if response.status_code == 200:
                data = response.json()
                links_data = data.get("data", {}).get("links", [])
                
                # Extract URLs from response (handle both list of strings and list of objects)
                all_urls = []
                if links_data and len(links_data) > 0:
                    if isinstance(links_data[0], str):
                        all_urls = links_data
                    elif isinstance(links_data[0], dict):
                        all_urls = [link.get("url") or link.get("href") 
                                   for link in links_data 
                                   if link.get("url") or link.get("href")]
                else:
                    logger.warning(f"SCRAPE API returned empty links data for {subcategory_url}")
                    logger.debug(f"Response structure: {data}")
                
                logger.debug(f"SCRAPE API returned {len(all_urls)} total URLs for {subcategory_url}")
                
                # Filter for product category URLs (Level 3) and deduplicate
                product_category_urls = []
                seen_normalized = set()
                filtered_count = 0
                for url in all_urls:
                    if url and self._is_product_category_url(url, subcategory_url):
                        # Normalize URL (remove trailing slash) to avoid duplicates
                        normalized = url.rstrip('/')
                        if normalized not in seen_normalized:
                            seen_normalized.add(normalized)
                            product_category_urls.append(normalized)
                            logger.debug(f"✅ Accepted: {normalized}")
                        else:
                            logger.debug(f"⏭️  Duplicate: {url}")
                    else:
                        filtered_count += 1
                        logger.debug(f"❌ Filtered: {url}")
                
                logger.debug(f"Filtered out {filtered_count} non-category URLs")
                logger.info(f"Found {len(product_category_urls)} product categories using SCRAPE API")
                return product_category_urls
                
        except Exception as e:
            logger.error(f"Failed to discover product categories from {subcategory_url}: {e}")
        
        return []
    
    def _is_subcategory_url(self, url: str, main_category_url: str) -> bool:
        """Check if URL is a subcategory (Level 2) URL."""
        parsed_url = urlparse(url)
        parsed_main = urlparse(main_category_url)
        
        # Must be same domain
        if parsed_url.netloc != parsed_main.netloc:
            return False
        
        # Must be deeper than main category but not a product page
        main_path = parsed_main.path.rstrip('/')
        url_path = parsed_url.path.rstrip('/')
        
        # Should be one level deeper than main category
        if not url_path.startswith(main_path + '/'):
            return False
        
        # Should not be a product page
        if '/products/' in url_path:
            return False
        
        # Should be exactly one level deeper (relative to input URL, not root)
        # Get the path after the main category path
        relative_path = url_path.replace(main_path, '').strip('/')
        # Split and count segments - should have exactly 1 segment
        path_segments = [seg for seg in relative_path.split('/') if seg]
        if len(path_segments) != 1:
            return False
        
        return True
    
    def _is_product_category_url(self, url: str, subcategory_url: str) -> bool:
        """Check if URL is a product category (Level 3) URL."""
        parsed_url = urlparse(url)
        parsed_sub = urlparse(subcategory_url)
        
        # Must be same domain
        if parsed_url.netloc != parsed_sub.netloc:
            return False
        
        # Must be deeper than subcategory but not a product page
        sub_path = parsed_sub.path.rstrip('/')
        url_path = parsed_url.path.rstrip('/')
        
        # Should be one level deeper than subcategory
        if not url_path.startswith(sub_path + '/'):
            return False
        
        # Should not be a product page
        if '/products/' in url_path:
            return False
        
        # Should be exactly one level deeper
        path_parts = url_path.replace(sub_path, '').strip('/').split('/')
        if len(path_parts) != 1:
            return False
        
        return True

    def auto_discover_products(self, category_url: str, max_products: int = 50) -> Dict[str, Any]:
        """Auto-discover and scrape products from a category page using AI-powered link extraction."""
        logger.info(f"Auto-discovering products from: {category_url}")
        category_shard_key = self._get_shard_key_from_category_url(category_url)
        product_urls: List[str] = []
        discovery_errors: List[str] = []

        if self.disable_discovery:
            logger.info("Discovery disabled; will use existing pending queue only")
        else:
            category_data = self._scrape_url(category_url)
            if not category_data:
                discovery_errors.append("failed_to_scrape_category")
            else:
                extracted_urls = self._extract_product_urls_with_ai(
                    category_data["content"], category_url, max_products
                )
                if extracted_urls:
                    product_urls = list(dict.fromkeys(extracted_urls))
                    logger.info(
                        f"Found {len(extracted_urls)} product URLs, {len(product_urls)} unique URLs to process"
                    )
                else:
                    discovery_errors.append("no_product_urls_found")

        discovered_total = len(product_urls)
        result_base: Dict[str, Any] = {
            "operation": "auto_discover_batch" if self.batch_mode else "auto_discover",
            "category_url": category_url,
            "category_shard_key": category_shard_key,
            "discovered_total": discovered_total,
            "discovery_disabled": self.disable_discovery,
        }

        if discovery_errors:
            result_base["discovery_errors"] = discovery_errors

        if self.batch_mode:
            queue_before = len(self.pending_queue)
            queued = 0
            duplicates = 0
            skipped_existing = 0

            for url in product_urls:
                enqueue_result = self._enqueue_for_batch(url, category_shard_key, category_url)
                if enqueue_result["queued"]:
                    queued += 1
                elif enqueue_result["duplicate"]:
                    duplicates += 1
                elif enqueue_result["skipped_existing"]:
                    skipped_existing += 1

            if queued and not self.dry_run:
                self.pending_queue.save()

            # Log discovery summary
            logger.info(f"📊 Discovery Summary: {discovered_total} URLs found")
            if skipped_existing > 0:
                logger.info(f"   ⏭️  Skipped {skipped_existing} already-scraped URLs")
            if duplicates > 0:
                logger.info(f"   🔁 Skipped {duplicates} duplicate URLs (already in queue)")
            if queued > 0:
                logger.info(f"   ✅ Queued {queued} new URLs for scraping")

            # Only process queue if not in discovery-only mode
            if self.discovery_only:
                logger.info(f"🔍 Discovery-only mode: {queued} URLs queued, skipping batch processing")
                result_base.update(
                    {
                        "queued_new": queued,
                        "duplicates": duplicates,
                        "skipped_existing": skipped_existing,
                        "queue_before": queue_before,
                        "queue_after": len(self.pending_queue),
                        "discovery_only": True,
                    }
                )
                return result_base

            batch_summary = self.process_queue_batch(self.batch_size)

            result_base.update(
                {
                    "queued_new": queued,
                    "duplicates": duplicates,
                    "skipped_existing": skipped_existing,
                    "queue_before": queue_before,
                    "queue_after": batch_summary.get("queue_size", len(self.pending_queue)),
                    "batch": batch_summary,
                }
            )

            return result_base

        # Non-batch mode retains direct scraping but respects skip + dry-run controls
        if self.dry_run:
            preview_urls: List[str] = []
            skipped_existing = 0
            for url in product_urls:
                normalized = self._normalize_url(url)
                if self._should_skip_existing(normalized):
                    skipped_existing += 1
                    continue
                preview_urls.append(url)

            result_base.update(
                {
                    "dry_run": True,
                    "preview_urls": preview_urls,
                    "preview_count": len(preview_urls),
                    "skipped_existing": skipped_existing,
                }
            )
            return result_base

        processed_count = 0
        touched_shards = set()
        skipped_existing = 0
        written_files: List[str] = []

        for url in product_urls:
            logger.info(f"Processing product: {url}")
            normalized = self._normalize_url(url)
            if self._should_skip_existing(normalized):
                skipped_existing += 1
                continue

            scraped_data = self._scrape_url(url)
            if scraped_data:
                shard_key = self._update_url_data_with_category(url, scraped_data, category_shard_key)
                touched_shards.add(shard_key)
                processed_count += 1
                self.existing_urls.add(normalized)
            time.sleep(0.1)

        if processed_count:
            for shard_key in touched_shards:
                if shard_key in self.manifest:
                    written_files.extend(self._write_shard_file(shard_key, self.manifest[shard_key]))
            self._save_url_index()
            self._save_manifest()

        result_base.update(
            {
                "processed_urls": processed_count,
                "total_urls": discovered_total,
                "touched_shards": list(touched_shards),
                "written_files": written_files,
                "skipped_existing": skipped_existing,
            }
        )

        return result_base
    
    def _extract_product_urls_with_ai(self, content: str, base_url: str, max_products: int) -> List[str]:
        """Extract product URLs from page content using Scrape API with links format."""
        try:
            # Rate limiting: wait 1 second before API call
            time.sleep(1)
            
            # Use Firecrawl's scrape with links format to get all links from rendered page
            logger.info("Using Firecrawl scrape to discover product URLs...")
            response = requests.post(
                f"{self.firecrawl_base_url}/scrape",
                headers=self.headers,
                json={
                    "url": base_url,
                    "formats": ["links"],
                    "onlyMainContent": True  # Focus on main content, not nav/footer
                },
                timeout=60  # 60 second timeout for scrape operations
            )
            
            if response.status_code == 200:
                data = response.json()
                # Extract links from the response
                links_data = data.get("data", {}).get("links", [])
                
                # Handle both list of strings and list of objects
                all_urls = []
                if links_data:
                    if isinstance(links_data[0], str):
                        all_urls = links_data
                    elif isinstance(links_data[0], dict):
                        all_urls = [link.get("url") or link.get("href") for link in links_data if link.get("url") or link.get("href")]
                
                # Filter for product URLs
                product_urls = []
                for url in all_urls:
                    if url and self._is_valid_product_url(url):
                        product_urls.append(url)
                        if len(product_urls) >= max_products:
                            break
                
                if product_urls:
                    logger.info(f"Found {len(product_urls)} product URLs using scrape with links")
                    return product_urls
            
        except Exception as e:
            logger.warning(f"Scrape with links extraction failed: {e}")
        
        # Fallback to regex-based extraction
        logger.info("Using regex fallback...")
        return self._extract_product_urls_with_regex(content, max_products)
    
    def _extract_product_urls_with_regex(self, content: str, max_products: int) -> List[str]:
        """Fallback method to extract product URLs using regex patterns."""
        product_urls = []
        
        # Look for product links in the content
        url_pattern = r'https?://[^\s\)]+'
        all_urls = re.findall(url_pattern, content)
        
        # Filter for product URLs based on site configuration
        url_patterns = self.site_config.get("url_patterns", {})
        for url in all_urls:
            if any(pattern in url.lower() for pattern in url_patterns.values()):
                # Additional filtering to ensure it's a product page, not category
                if self._is_valid_product_url(url):
                    product_urls.append(url)
                    if len(product_urls) >= max_products:
                        break
        
        return product_urls
    
    def _is_valid_product_url(self, url: str) -> bool:
        """Check if URL is a valid product URL using site configuration."""
        url_lower = url.lower()
        
        # Get product URL validation rules from config
        validation_config = self.site_config.get("product_url_validation", {})
        required_pattern = validation_config.get("required_pattern", "/products/")
        required_suffix = validation_config.get("required_suffix")
        min_length = validation_config.get("min_length", 5)
        excluded_suffixes = validation_config.get("excluded_suffixes", [])
        
        # Default excluded extensions if not configured
        if not excluded_suffixes:
            excluded_suffixes = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.ico', '.css', '.js', '.pdf', '.zip']
        
        # Exclude URLs with excluded suffixes
        if any(url_lower.endswith(ext) for ext in excluded_suffixes):
            return False
        
        # Exclude CDN domains
        if 'cdn' in url_lower and any(ext in url_lower for ext in excluded_suffixes):
            return False
        
        # Exclude common non-product pages from site config
        url_filters = self.site_config.get("url_filters", {})
        excluded_patterns = url_filters.get("exclude_patterns", [])
        
        for pattern in excluded_patterns:
            if pattern in url_lower:
                return False
        
        # Check if URL contains required product pattern
        if required_pattern not in url_lower:
            return False
        
        # Extract the part after the required pattern
        parts = url.split(required_pattern)
        if len(parts) < 2:
            return False
        
        product_part = parts[1]
        
        # Check minimum length
        if len(product_part) < min_length:
            return False
        
        # Check required suffix if specified
        if required_suffix and not product_part.endswith(required_suffix):
            return False
        
        # Exclude obvious category pages
        category_indicators = [
            '/categories/', '/category/', '/collections/', '/collection/',
            '/shop/', '/catalog/', '/browse/', '/search'
        ]
        
        for indicator in category_indicators:
            if indicator in url_lower:
                return False
        
        return True
    
    def _get_shard_key_from_category_url(self, category_url: str) -> str:
        """Extract shard key from category URL using site configuration."""
        try:
            # Parse the URL to get path segments
            from urllib.parse import urlparse
            parsed = urlparse(category_url)
            path_segments = [seg for seg in parsed.path.split('/') if seg]
            
            # Use site configuration to determine shard extraction method
            shard_config = self.site_config.get("shard_extraction", {})
            method = shard_config.get("method", "path_segment")
            segment_index = shard_config.get("segment_index", 1)
            
            if method == "path_segment" and len(path_segments) > segment_index:
                # Extract the category name from the path segment
                category_segment = path_segments[segment_index]
                # Clean up the category name for shard naming
                shard_key = self._clean_shard_name(category_segment)
                return shard_key
            
            # Fallback: use the last meaningful path segment
            if path_segments:
                last_segment = path_segments[-1]
                shard_key = self._clean_shard_name(last_segment)
                return shard_key
                
        except Exception as e:
            logger.warning(f"Failed to extract shard key from category URL: {e}")
        
        # Ultimate fallback
        return "other_products"
    
    def _clean_shard_name(self, name: str) -> str:
        """Clean and format a name for use as a shard key."""
        # Replace hyphens and underscores with underscores
        cleaned = name.replace('-', '_').replace(' ', '_')
        # Remove any non-alphanumeric characters except underscores
        import re
        cleaned = re.sub(r'[^a-zA-Z0-9_]', '', cleaned)
        # Convert to lowercase
        cleaned = cleaned.lower()
        # Ensure it's not empty
        if not cleaned:
            cleaned = "other_products"
        return cleaned
    
    def _update_url_data_with_category(self, url: str, scraped_data: Dict[str, Any], category_shard_key: str) -> str:
        """Update URL data using a specific category-based shard key."""
        normalized_url = self._normalize_url(url)
        
        # Update URL index with the provided category shard key
        self.url_index[normalized_url] = {
            "title": scraped_data.get("title", ""),
            "markdown": scraped_data.get("content", ""),
            "shard": category_shard_key,
            "updated_at": scraped_data.get("scraped_at", datetime.now().isoformat())
        }
        
        # Update manifest with the provided category shard key
        if category_shard_key not in self.manifest:
            self.manifest[category_shard_key] = []
        
        if normalized_url not in self.manifest[category_shard_key]:
            self.manifest[category_shard_key].append(normalized_url)

        self.existing_urls.add(normalized_url)

        return category_shard_key
    
    def incremental_update(self, urls: List[str], operation: str, pre_scraped_content: Optional[str] = None) -> Dict[str, Any]:
        """Perform incremental update (add/change/remove URLs)."""
        logger.info(f"Performing incremental {operation} for {len(urls)} URLs")
        logger.info(f"Diff extraction mode: {self.use_diff_extraction}")
        
        processed_count = 0
        touched_shards = set()
        written_files = []
        
        if operation in ["added", "changed"]:
            # Process URLs to add/update
            for i, url in enumerate(urls):
                logger.info(f"Processing {operation}: {url}")
                
                # Check if this is a category page and we have diff extraction enabled
                # Use site config to determine if it's a product page (agnostic approach)
                product_pattern = self.site_config.get('url_patterns', {}).get('product', '/products/')
                is_category_page = product_pattern not in url.lower()
                content_to_use = pre_scraped_content if i == 0 and pre_scraped_content else None
                
                if is_category_page and self.use_diff_extraction and content_to_use:
                    # This is a category page diff - extract the product URLs from it
                    logger.info(f"Detected category page URL with diff: {url}")
                    product_urls = self._extract_product_url_from_diff(content_to_use)
                    
                    if product_urls:
                        # Process each extracted product URL
                        logger.info(f"Processing {len(product_urls)} extracted product URLs: {product_urls}")
                        for product_url in product_urls:
                            try:
                                logger.info(f"Processing extracted product URL: {product_url}")
                                # Don't use diff extraction for the actual product scraping
                                scraped_data = self._scrape_url(product_url, None, is_diff=False)
                                if scraped_data:
                                    # Use category-based shard key for all products from this category
                                    shard_key = self._get_shard_key_from_category_url(url)
                                    shard_key = self._update_url_data_with_category(product_url, scraped_data, shard_key)
                                    touched_shards.add(shard_key)
                                    processed_count += 1
                                else:
                                    logger.warning(f"Failed to scrape product URL: {product_url}")
                            except Exception as e:
                                logger.error(f"Error processing product URL {product_url}: {e}")
                                # Continue processing other URLs instead of failing completely
                            time.sleep(0.1)
                        # Skip the original category page processing since we processed individual products
                        continue
                    else:
                        # Couldn't extract product URLs, fall back to original behavior
                        logger.warning("Could not extract product URLs from diff, processing category page")
                        try:
                            scraped_data = self._scrape_url(url, content_to_use, is_diff=self.use_diff_extraction)
                            if scraped_data:
                                shard_key = self._update_url_data(url, scraped_data)
                                touched_shards.add(shard_key)
                                processed_count += 1
                            else:
                                logger.warning(f"Failed to scrape category page: {url}")
                        except Exception as e:
                            logger.error(f"Error processing category page {url}: {e}")
                            # Continue processing other URLs instead of failing completely
                else:
                    # Normal product page or no diff extraction
                    try:
                        scraped_data = self._scrape_url(url, content_to_use, is_diff=self.use_diff_extraction)
                        
                        if scraped_data:
                            shard_key = self._update_url_data(url, scraped_data)
                            touched_shards.add(shard_key)
                            processed_count += 1
                        else:
                            logger.warning(f"Failed to scrape URL: {url}")
                    except Exception as e:
                        logger.error(f"Error processing URL {url}: {e}")
                        # Continue processing other URLs instead of failing completely
                
                time.sleep(0.1)
        
        elif operation == "removed":
            # Remove URLs
            for i, url in enumerate(urls):
                logger.info(f"Removing: {url}")
                
                # Check if this is a category page and we have diff extraction enabled
                # Use site config to determine if it's a product page (agnostic approach)
                product_pattern = self.site_config.get('url_patterns', {}).get('product', '/products/')
                is_category_page = product_pattern not in url.lower()
                content_to_use = pre_scraped_content if i == 0 and pre_scraped_content else None
                
                # For removals: if diff content is provided for a category page, treat as diff mode even if flag wasn't set
                if is_category_page and content_to_use:
                    # This is a category page diff - extract the REMOVED product URLs from it
                    logger.info(f"Detected category page removal with diff: {url}")
                    removed_product_urls = self._extract_product_url_from_diff(content_to_use, removed_only=True)
                    
                    if removed_product_urls:
                        logger.info(f"Found {len(removed_product_urls)} product URLs to remove: {removed_product_urls}")
                        # Get shard key from category URL
                        shard_key = self._get_shard_key_from_category_url(url)
                        touched_shards.add(shard_key)
                        
                        # Remove each extracted product URL
                        for product_url in removed_product_urls:
                            logger.info(f"Removing product URL: {product_url}")
                            self._remove_url_data(product_url)
                            processed_count += 1
                        # After removal, ensure shard file for this category is rewritten to trigger hash change
                        if shard_key in self.manifest:
                            filepaths = self._write_shard_file(shard_key, self.manifest[shard_key])
                            written_files.extend(filepaths)
                    else:
                        logger.warning("Could not extract removed product URLs from diff; attempting fallback scrape to diff against manifest")
                        # Fallback: scrape current category page, extract product URLs, and remove those missing
                        cat_data = self._scrape_category_page(url)
                        if cat_data and cat_data.get("content"):
                            current_urls = self._extract_product_url_from_diff(cat_data["content"], removed_only=False)
                            current_set = set(current_urls)
                            shard_key = self._get_shard_key_from_category_url(url)
                            touched_shards.add(shard_key)
                            # Get existing URLs for this shard from manifest
                            existing_urls = list(self.manifest.get(shard_key, []))
                            to_remove = [u for u in existing_urls if u not in current_set]
                            if to_remove:
                                logger.info(f"Fallback removal identified {len(to_remove)} URLs to remove from shard {shard_key}")
                                for product_url in to_remove:
                                    self._remove_url_data(product_url)
                                    processed_count += 1
                                if shard_key in self.manifest:
                                    filepaths = self._write_shard_file(shard_key, self.manifest[shard_key])
                                    written_files.extend(filepaths)
                            else:
                                logger.info("Fallback removal found no URLs to remove")
                else:
                    # Direct product URL removal or no diff extraction
                    normalized_url = self._normalize_url(url)
                    if normalized_url in self.url_index:
                        shard_key = self.url_index[normalized_url]["shard_key"]
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
        description="Agnostic LLMs.txt updater with site configuration support"
    )
    parser.add_argument("domain", help="The domain to process (e.g., jgengineering.ie)")
    
    # Operation modes (mutually exclusive)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--full", action="store_true", help="Perform full crawl")
    group.add_argument("--auto-discover", type=str, help="Auto-discover and scrape all products from a category page URL")
    group.add_argument("--hierarchical", type=str, help="Hierarchical discovery from main category page (Level 1 → Level 4)")
    group.add_argument("--process-retry-queue", action="store_true", help="Process URLs from the retry queue")
    group.add_argument("--added", type=str, help="JSON array of URLs to add")
    group.add_argument("--changed", type=str, help="JSON array of URLs to update")
    group.add_argument("--removed", type=str, help="JSON array of URLs to remove")
    
    # Optional arguments
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
        "--max-categories",
        type=int,
        default=10,
        help="Maximum number of subcategories to process in hierarchical mode (default: 10)"
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
    # Alias to align with workflow passing --diff-file for page_removed
    parser.add_argument(
        "--diff-file",
        help="Alias for --pre-scraped-content when passing diff content file"
    )
    parser.add_argument(
        "--use-diff-extraction",
        action="store_true",
        help="Extract only new product from diff content (for page_added events)"
    )
    parser.add_argument(
        "--max-characters",
        type=int,
        default=300000,
        help="Maximum characters per shard file (default: 300000)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        help="Process discovered URLs in batches of this size (default: domain-specific)"
    )
    parser.add_argument(
        "--max-batches",
        type=int,
        help="Process at most this many batches in a single run (default: 1)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview queue changes and batch contents without scraping or writing files"
    )
    parser.add_argument(
        "--discovery-only",
        action="store_true",
        help="Only discover and queue URLs without scraping them (queue can be processed later)"
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Re-scrape URLs even if they already exist in the index"
    )
    parser.add_argument(
        "--pending-queue",
        type=str,
        help="Custom path for the pending queue file"
    )
    parser.add_argument(
        "--disable-discovery",
        action="store_true",
        help="Skip discovery and only process from the existing pending queue"
    )

    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if not args.firecrawl_api_key:
        logger.error("FIRECRAWL_API_KEY is required")
        sys.exit(1)
    
    # Initialize updater
    updater = AgnosticLLMsUpdater(
        firecrawl_api_key=args.firecrawl_api_key,
        domain=args.domain,
        output_dir=args.output_dir,
        max_characters=args.max_characters,
        use_diff_extraction=args.use_diff_extraction,
        batch_size=args.batch_size,
        max_batches=args.max_batches,
        force_refresh=args.force_refresh,
        dry_run=args.dry_run,
        pending_queue_path=args.pending_queue,
        disable_discovery=args.disable_discovery,
        discovery_only=args.discovery_only
    )
    
    # Load pre-scraped content if provided (support --pre-scraped-content or --diff-file)
    pre_scraped_content = None
    content_path = args.pre_scraped_content or args.diff_file
    if content_path and os.path.exists(content_path):
        with open(content_path, 'r', encoding='utf-8') as f:
            pre_scraped_content = f.read()
    
    # Execute operation
    try:
        if args.full:
            result = updater.full_crawl(args.limit)
        elif args.auto_discover:
            result = updater.auto_discover_products(args.auto_discover, args.max_products)
        elif args.hierarchical:
            result = updater.hierarchical_discovery(args.hierarchical, args.max_products, args.max_categories)
        elif args.process_retry_queue:
            # Move retry queue items back to main queue and process
            retry_count = len(updater.retry_queue)
            logger.info(f"Processing {retry_count} URLs from retry queue")
            
            # Move all items from retry queue to main queue
            while len(updater.retry_queue) > 0:
                entries = updater.retry_queue.dequeue_batch(100)
                for entry in entries:
                    # Reset attempt counter for manual retry
                    entry["metadata"]["attempts"] = 0
                    updater.pending_queue.enqueue_entry(entry)
            
            updater.pending_queue.save()
            updater.retry_queue.save()
            
            # Process the queue
            result = updater.process_queue_batch(updater.batch_size)
            result["retry_queue_processed"] = retry_count
        elif args.added:
            urls = json.loads(args.added)
            result = updater.incremental_update(urls, "added", pre_scraped_content)
        elif args.changed:
            urls = json.loads(args.changed)
            result = updater.incremental_update(urls, "changed", pre_scraped_content)
        elif args.removed:
            urls = json.loads(args.removed)
            result = updater.incremental_update(urls, "removed", pre_scraped_content)
        
        # Print results
        print(json.dumps(result, indent=2))
        
    except KeyError as e:
        logger.error(f"Missing expected field in API response: {e}")
        logger.error("This usually indicates a change in the Firecrawl API response format")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        logger.error(f"Network/API error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.debug(f"Full traceback: {traceback.format_exc()}")
        sys.exit(1)


if __name__ == "__main__":
    main()
