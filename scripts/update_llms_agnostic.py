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
    
    def __init__(self, firecrawl_api_key: str, domain: str, output_dir: str = "out", max_characters: int = 300000, use_diff_extraction: bool = False):
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
                }
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
        
        # Only process individual product URLs - skip collection/category pages
        if '/products/' in url.lower():
            return self._extract_product_data(url)
        else:
            # Skip collection/category pages - they contain HTML that pollutes shards
            logger.debug(f"Skipping collection/category page: {url}")
            return None
    
    def _scrape_category_page(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape category page using regular scrape endpoint."""
        try:
            # Ensure EUR currency for proper pricing
            eur_url = self._ensure_eur_currency(url)
            
            response = requests.post(
                f"{self.firecrawl_base_url}/scrape",
                headers=self.headers,
                json={
                    "url": eur_url,
                    "formats": ["markdown"],
                    "onlyMainContent": True
                }
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get("success") and data.get("data"):
                content = data["data"].get("markdown", "")
                title = data["data"].get("metadata", {}).get("title", "")
                
                return {
                    "url": eur_url,  # Use EUR URL for indexing
                    "content": content,
                    "title": title,
                    "scraped_at": datetime.now().isoformat()
                }
            
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
    
    def _extract_product_data(self, url: str) -> Optional[Dict[str, Any]]:
        """Extract structured product data using Firecrawl scrape endpoint with JSON format."""
        try:
            # Ensure EUR currency for proper pricing
            eur_url = self._ensure_eur_currency(url)
            
            def make_request():
                response = requests.post(
                    f"{self.firecrawl_base_url}/scrape",
                    headers=self.headers,
                    json={
                        "url": eur_url,
                        "formats": [{
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
                    },
                    timeout=30
                )
                response.raise_for_status()
                return response
            
            # Use retry logic for 502 errors
            response = retry_with_backoff(make_request, max_retries=3, initial_delay=2)
            
            if response:
                data = response.json()
                if data.get("success") and data.get("data"):
                    extracted_data = data["data"].get("json", {})
                    
                    if extracted_data:
                        # Use the extracted data directly as JSON content
                        import json
                        content = json.dumps(extracted_data, indent=2, ensure_ascii=False)
                        
                        return {
                            "url": eur_url,  # Use EUR URL for indexing
                            "content": content,
                            "title": extracted_data.get("product_name", ""),
                            "scraped_at": datetime.now().isoformat()
                        }
            
        except Exception as e:
            logger.error(f"Failed to extract product data from {url}: {e}")
        
        return None
    
    def _update_url_data(self, url: str, scraped_data: Dict[str, Any]) -> str:
        """Update URL data in index and return shard key."""
        normalized_url = self._normalize_url(url)
        shard_key = self._get_shard_key(url)
        
        # Update URL index
        self.url_index[normalized_url] = {
            "title": scraped_data.get("title", ""),
            "markdown": scraped_data.get("content", ""),
            "shard": shard_key,
            "updated_at": scraped_data.get("scraped_at", datetime.now().isoformat())
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
                
                # Clean up empty shards
                if not self.manifest[shard_key]:
                    del self.manifest[shard_key]
    
    def _write_shard_file(self, shard_key: str, urls: List[str]) -> List[str]:
        """Write shard file with content from URLs."""
        if not urls:
            return []
        
        # Collect content for this shard
        shard_content = []
        total_chars = 0
        
        for url in urls:
            if url in self.url_index:
                content = self.url_index[url]["markdown"]
                title = self.url_index[url]["title"]
                
                # Add content with header
                header = f"<|{url}|>\n## {title}\n\n"
                content_with_header = header + content + "\n\n"
                
                # Check character limit
                if total_chars + len(content_with_header) > self.max_characters:
                    break
                
                shard_content.append(content_with_header)
                total_chars += len(content_with_header)
        
        if not shard_content:
            return []
        
        # Write to file
        filename = f"llms-{self.site_name}-{shard_key}.txt"
        filepath = os.path.join(self.site_output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(''.join(shard_content))
        
        logger.info(f"Wrote shard file: {filename} ({total_chars} characters)")
        return [filepath]
    
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
            response = requests.post(
                f"{self.firecrawl_base_url}/map",
                headers=self.headers,
                json={
                    "url": main_category_url,
                    "limit": 100,  # Get more URLs to filter from
                    "includeSubdomains": False
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                all_urls = [link["url"] for link in data.get("links", [])]
                
                # Filter for subcategory URLs (Level 2)
                subcategory_urls = []
                for url in all_urls:
                    if self._is_subcategory_url(url, main_category_url):
                        subcategory_urls.append(url)
                
                return subcategory_urls
                
        except Exception as e:
            logger.error(f"Failed to discover subcategories from {main_category_url}: {e}")
        
        return []
    
    def _discover_product_categories(self, subcategory_url: str) -> List[str]:
        """Discover product category URLs from a subcategory page (Level 2 → Level 3)."""
        try:
            response = requests.post(
                f"{self.firecrawl_base_url}/map",
                headers=self.headers,
                json={
                    "url": subcategory_url,
                    "limit": 100,  # Get more URLs to filter from
                    "includeSubdomains": False
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                all_urls = [link["url"] for link in data.get("links", [])]
                
                # Filter for product category URLs (Level 3)
                product_category_urls = []
                for url in all_urls:
                    if self._is_product_category_url(url, subcategory_url):
                        product_category_urls.append(url)
                
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
        
        # First, scrape the category page to get product links
        category_data = self._scrape_url(category_url)
        if not category_data:
            return {"error": "Failed to scrape category page"}
        
        # Use AI to extract product URLs from the content
        product_urls = self._extract_product_urls_with_ai(category_data["content"], category_url, max_products)
        
        if not product_urls:
            return {"error": "No product URLs found in category page"}
        
        # Deduplicate URLs to avoid processing the same product multiple times
        unique_urls = list(dict.fromkeys(product_urls))  # Preserves order while removing duplicates
        logger.info(f"Found {len(product_urls)} product URLs, {len(unique_urls)} unique URLs to process")
        
        product_urls = unique_urls
        
        # Extract category-based shard key from the category URL
        category_shard_key = self._get_shard_key_from_category_url(category_url)
        logger.info(f"Using category-based shard key: {category_shard_key}")
        
        # Process product URLs
        processed_count = 0
        touched_shards = set()
        
        for url in product_urls:
            logger.info(f"Processing product: {url}")
            
            scraped_data = self._scrape_url(url)
            if scraped_data:
                # Use category-based shard key instead of product URL-based key
                shard_key = self._update_url_data_with_category(url, scraped_data, category_shard_key)
                touched_shards.add(shard_key)
                processed_count += 1
            
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
            "operation": "auto_discover",
            "processed_urls": processed_count,
            "total_urls": len(product_urls),
            "touched_shards": list(touched_shards),
            "written_files": written_files
        }
    
    def _extract_product_urls_with_ai(self, content: str, base_url: str, max_products: int) -> List[str]:
        """Extract product URLs from page content using Scrape API with links format."""
        try:
            # Use Firecrawl's scrape with links format to get all links from rendered page
            logger.info("Using Firecrawl scrape to discover product URLs...")
            response = requests.post(
                f"{self.firecrawl_base_url}/scrape",
                headers=self.headers,
                json={
                    "url": base_url,
                    "formats": ["links"],
                    "onlyMainContent": True  # Focus on main content, not nav/footer
                }
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
                            logger.info(f"Processing extracted product URL: {product_url}")
                            # Don't use diff extraction for the actual product scraping
                            scraped_data = self._scrape_url(product_url, None, is_diff=False)
                            if scraped_data:
                                # Use category-based shard key for all products from this category
                                shard_key = self._get_shard_key_from_category_url(url)
                                shard_key = self._update_url_data_with_category(product_url, scraped_data, shard_key)
                                touched_shards.add(shard_key)
                                processed_count += 1
                            time.sleep(0.1)
                        # Skip the original category page processing since we processed individual products
                        continue
                    else:
                        # Couldn't extract product URLs, fall back to original behavior
                        logger.warning("Could not extract product URLs from diff, processing category page")
                        scraped_data = self._scrape_url(url, content_to_use, is_diff=self.use_diff_extraction)
                else:
                    # Normal product page or no diff extraction
                    scraped_data = self._scrape_url(url, content_to_use, is_diff=self.use_diff_extraction)
                
                if scraped_data:
                    shard_key = self._update_url_data(url, scraped_data)
                    touched_shards.add(shard_key)
                    processed_count += 1
                
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
                
                if is_category_page and self.use_diff_extraction and content_to_use:
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
                    else:
                        logger.warning("Could not extract removed product URLs from diff")
                else:
                    # Direct product URL removal or no diff extraction
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
        description="Agnostic LLMs.txt updater with site configuration support"
    )
    parser.add_argument("domain", help="The domain to process (e.g., jgengineering.ie)")
    
    # Operation modes (mutually exclusive)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--full", action="store_true", help="Perform full crawl")
    group.add_argument("--auto-discover", type=str, help="Auto-discover and scrape all products from a category page URL")
    group.add_argument("--hierarchical", type=str, help="Hierarchical discovery from main category page (Level 1 → Level 4)")
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
        use_diff_extraction=args.use_diff_extraction
    )
    
    # Load pre-scraped content if provided
    pre_scraped_content = None
    if args.pre_scraped_content and os.path.exists(args.pre_scraped_content):
        with open(args.pre_scraped_content, 'r', encoding='utf-8') as f:
            pre_scraped_content = f.read()
    
    # Execute operation
    try:
        if args.full:
            result = updater.full_crawl(args.limit)
        elif args.auto_discover:
            result = updater.auto_discover_products(args.auto_discover, args.max_products)
        elif args.hierarchical:
            result = updater.hierarchical_discovery(args.hierarchical, args.max_products, args.max_categories)
        elif args.added:
            urls = json.loads(args.added)
            result = updater.incremental_update(urls, "added", pre_scraped_content)
        elif args.changed:
            urls = json.loads(args.changed)
            result = updater.incremental_update(urls, "changed", pre_scraped_content)
        elif args.removed:
            urls = json.loads(args.removed)
            result = updater.incremental_update(urls, "removed")
        
        # Print results
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
