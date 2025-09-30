#!/usr/bin/env python3
"""
Site Configuration Manager for Agnostic Web Scraping

This module provides a unified interface for managing different website configurations,
allowing the scraping workflow to work with any e-commerce site by simply adding
a configuration entry.
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse
from pathlib import Path

logger = logging.getLogger(__name__)


class SiteConfigManager:
    """Manages site-specific configurations for agnostic web scraping."""
    
    def __init__(self, config_path: str = "config/site_configs.json"):
        """Initialize the configuration manager."""
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load site configurations from file."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {self.config_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in configuration file: {e}")
            raise
    
    def get_site_config(self, domain: str) -> Dict[str, Any]:
        """Get configuration for a specific site domain."""
        # Normalize domain (remove www, protocol, etc.)
        normalized_domain = self._normalize_domain(domain)
        
        if normalized_domain in self.config.get("sites", {}):
            site_config = self.config["sites"][normalized_domain].copy()
            # Merge with defaults
            defaults = self.config.get("defaults", {})
            for key, default_value in defaults.items():
                if key not in site_config:
                    site_config[key] = default_value
            return site_config
        else:
            logger.warning(f"No configuration found for domain: {domain}")
            return self._get_default_config(domain)
    
    def _normalize_domain(self, domain: str) -> str:
        """Normalize domain name for consistent lookup."""
        # Remove protocol if present
        if "://" in domain:
            domain = urlparse(domain).netloc
        
        # Remove www prefix
        if domain.startswith("www."):
            domain = domain[4:]
        
        return domain
    
    def _get_default_config(self, domain: str) -> Dict[str, Any]:
        """Get default configuration for unknown sites."""
        defaults = self.config.get("defaults", {})
        return {
            "name": domain.replace(".", " ").title(),
            "base_url": f"https://{domain}",
            "url_patterns": {
                "product": "/products/",
                "category": "/categories/"
            },
            **defaults
        }
    
    def get_shard_key(self, url: str, site_config: Dict[str, Any]) -> str:
        """Extract shard key from URL using site-specific configuration."""
        parsed_url = urlparse(url)
        path_segments = [seg for seg in parsed_url.path.split('/') if seg]
        
        shard_config = site_config.get("shard_extraction", {})
        method = shard_config.get("method", "path_segment")
        segment_index = shard_config.get("segment_index", 1)
        
        # Handle different URL patterns
        if len(path_segments) >= 2:
            if path_segments[0] == "collections" and len(path_segments) > segment_index:
                # Collection URL: /collections/collection-name/products/product-name
                # Use the collection name (segment_index 1)
                return self._sanitize_shard(path_segments[segment_index])
            elif path_segments[0] == "products":
                # Direct product URL: /products/product-name
                # Categorize by product name
                product_name = path_segments[-1] if path_segments else ""
                return self._categorize_product(product_name, site_config)
        
        # Fallback to original logic
        if method == "path_segment" and len(path_segments) > segment_index:
            return self._sanitize_shard(path_segments[segment_index])
        
        # Final fallback
        return "other_products"
    
    def _sanitize_shard(self, shard_name: str) -> str:
        """Sanitize shard name for file system compatibility."""
        # Replace problematic characters
        sanitized = shard_name.lower()
        sanitized = sanitized.replace(" ", "_")
        sanitized = sanitized.replace("-", "_")
        sanitized = sanitized.replace("&", "and")
        sanitized = "".join(c for c in sanitized if c.isalnum() or c == "_")
        
        # Ensure it's not empty
        if not sanitized:
            sanitized = "other_products"
        
        return sanitized
    
    def _categorize_product(self, product_name: str, site_config: Dict[str, Any]) -> str:
        """Categorize product based on name patterns in site configuration."""
        if not product_name:
            return "other_products"
        
        name_lower = product_name.lower()
        categories = site_config.get("product_categories", {})
        
        for category, keywords in categories.items():
            if any(keyword in name_lower for keyword in keywords):
                return category
        
        return "other_products"
    
    def filter_urls(self, urls: List[str], site_config: Dict[str, Any]) -> List[str]:
        """Filter URLs based on site-specific configuration."""
        filtered = []
        url_filters = site_config.get("url_filters", {})
        
        include_patterns = url_filters.get("include_patterns", [])
        exclude_patterns = url_filters.get("exclude_patterns", [])
        max_depth = url_filters.get("max_depth", 3)
        
        for url in urls:
            url_lower = url.lower()
            
            # Skip if URL contains excluded patterns
            if any(pattern in url_lower for pattern in exclude_patterns):
                continue
            
            # Check depth
            if url.count('/') > max_depth:
                continue
            
            # Keep if URL contains included patterns
            if any(pattern in url_lower for pattern in include_patterns):
                filtered.append(url)
            # Keep shallow URLs (likely categories)
            elif url.count('/') <= 2:
                filtered.append(url)
        
        return filtered
    
    def get_elevenlabs_agent(self, domain: str) -> Optional[str]:
        """Get ElevenLabs agent name for a domain."""
        site_config = self.get_site_config(domain)
        return site_config.get("elevenlabs_agent")
    
    def add_site_config(self, domain: str, config: Dict[str, Any]) -> None:
        """Add or update site configuration."""
        normalized_domain = self._normalize_domain(domain)
        
        if "sites" not in self.config:
            self.config["sites"] = {}
        
        self.config["sites"][normalized_domain] = config
        self._save_config()
    
    def _save_config(self) -> None:
        """Save configuration to file."""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            raise
    
    def list_sites(self) -> List[str]:
        """List all configured sites."""
        return list(self.config.get("sites", {}).keys())
    
    def validate_config(self, domain: str) -> List[str]:
        """Validate site configuration and return any issues."""
        issues = []
        site_config = self.get_site_config(domain)
        
        # Check required fields
        required_fields = ["name", "base_url", "url_patterns"]
        for field in required_fields:
            if field not in site_config:
                issues.append(f"Missing required field: {field}")
        
        # Check URL patterns
        url_patterns = site_config.get("url_patterns", {})
        if not url_patterns:
            issues.append("No URL patterns defined")
        
        # Check shard extraction
        shard_config = site_config.get("shard_extraction", {})
        if not shard_config:
            issues.append("No shard extraction configuration")
        
        return issues


def main():
    """CLI interface for site configuration management."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Manage site configurations")
    parser.add_argument("--list", action="store_true", help="List all configured sites")
    parser.add_argument("--validate", type=str, help="Validate configuration for a domain")
    parser.add_argument("--config-path", default="config/site_configs.json", help="Path to configuration file")
    
    args = parser.parse_args()
    
    config_manager = SiteConfigManager(args.config_path)
    
    if args.list:
        sites = config_manager.list_sites()
        print("Configured sites:")
        for site in sites:
            print(f"  - {site}")
    
    if args.validate:
        issues = config_manager.validate_config(args.validate)
        if issues:
            print(f"Issues with {args.validate}:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print(f"Configuration for {args.validate} is valid")


if __name__ == "__main__":
    main()
