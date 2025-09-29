#!/usr/bin/env python3
"""
Add New Site Configuration

This script helps you add new website configurations to the agnostic scraping system.
It provides an interactive interface to configure URL patterns, categorization rules,
and other site-specific settings.

Usage:
  python3 scripts/add_site.py <domain>
  
Example:
  python3 scripts/add_site.py example.com
"""

import os
import sys
import json
import argparse
import logging
from typing import Dict, Any

# Add the scripts directory to the path to import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from site_config_manager import SiteConfigManager

logger = logging.getLogger(__name__)


def get_user_input(prompt: str, default: str = "") -> str:
    """Get user input with optional default value."""
    if default:
        full_prompt = f"{prompt} [{default}]: "
    else:
        full_prompt = f"{prompt}: "
    
    response = input(full_prompt).strip()
    return response if response else default


def get_yes_no(prompt: str, default: bool = True) -> bool:
    """Get yes/no input from user."""
    default_str = "Y/n" if default else "y/N"
    response = input(f"{prompt} [{default_str}]: ").strip().lower()
    
    if not response:
        return default
    
    return response in ['y', 'yes', 'true', '1']


def get_list_input(prompt: str, default: list = None) -> list:
    """Get list input from user (comma-separated)."""
    if default is None:
        default = []
    
    default_str = ", ".join(default) if default else ""
    response = get_user_input(prompt, default_str)
    
    if not response:
        return default
    
    return [item.strip() for item in response.split(",") if item.strip()]


def create_site_config(domain: str) -> Dict[str, Any]:
    """Create site configuration interactively."""
    print(f"\nCreating configuration for {domain}")
    print("=" * 50)
    
    # Basic information
    name = get_user_input("Site name", domain.replace(".", " ").title())
    base_url = get_user_input("Base URL", f"https://{domain}")
    
    # URL patterns
    print("\nURL Patterns:")
    print("Specify the URL patterns used by this site")
    
    product_pattern = get_user_input("Product URL pattern", "/products/")
    category_pattern = get_user_input("Category URL pattern", "/categories/")
    
    url_patterns = {
        "product": product_pattern,
        "category": category_pattern
    }
    
    # Shard extraction
    print("\nShard Extraction:")
    print("How should we extract shard keys from URLs?")
    
    shard_method = get_user_input("Method (path_segment/product_categorization)", "path_segment")
    segment_index = 1
    
    if shard_method == "path_segment":
        try:
            segment_index = int(get_user_input("Path segment index (0-based)", "1"))
        except ValueError:
            segment_index = 1
    
    shard_extraction = {
        "method": shard_method,
        "segment_index": segment_index,
        "fallback_method": "product_categorization"
    }
    
    # URL filters
    print("\nURL Filters:")
    print("Specify patterns to include/exclude from scraping")
    
    include_patterns = get_list_input("Include patterns (comma-separated)", 
                                    ["product", "collection", "shop", "catalog", "item"])
    
    exclude_patterns = get_list_input("Exclude patterns (comma-separated)",
                                    ["sitemap", "robots.txt", "blog", "news", "about", "contact", 
                                     "privacy", "terms", "help", "faq", "search", "cart", "checkout",
                                     "account", "login", "register", "admin", "api", "feed", "rss"])
    
    max_depth = 3
    try:
        max_depth = int(get_user_input("Maximum URL depth", "3"))
    except ValueError:
        max_depth = 3
    
    url_filters = {
        "include_patterns": include_patterns,
        "exclude_patterns": exclude_patterns,
        "max_depth": max_depth
    }
    
    # Product categories
    print("\nProduct Categories:")
    print("Define categories and their keyword patterns for product classification")
    
    categories = {}
    add_categories = get_yes_no("Add custom product categories?", True)
    
    if add_categories:
        while True:
            category_name = get_user_input("Category name (or 'done' to finish)", "")
            if category_name.lower() == 'done' or not category_name:
                break
            
            keywords = get_list_input(f"Keywords for '{category_name}' (comma-separated)", [])
            categories[category_name] = keywords
    
    # Add some default categories if none were added
    if not categories:
        categories = {
            "other_products": []
        }
    
    # ElevenLabs agent
    print("\nElevenLabs Integration:")
    elevenlabs_agent = get_user_input("ElevenLabs agent name", domain)
    
    # Build configuration
    config = {
        "name": name,
        "base_url": base_url,
        "url_patterns": url_patterns,
        "shard_extraction": shard_extraction,
        "url_filters": url_filters,
        "product_categories": categories,
        "elevenlabs_agent": elevenlabs_agent
    }
    
    return config


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Add new site configuration")
    parser.add_argument("domain", help="Domain to configure (e.g., example.com)")
    parser.add_argument("--config-path", default="config/site_configs.json", 
                       help="Path to configuration file")
    parser.add_argument("--interactive", action="store_true", default=True,
                       help="Use interactive mode (default)")
    parser.add_argument("--template", action="store_true",
                       help="Create a template configuration")
    
    args = parser.parse_args()
    
    config_manager = SiteConfigManager(args.config_path)
    
    if args.template:
        # Create a template configuration
        template_config = {
            "name": f"{args.domain.replace('.', ' ').title()}",
            "base_url": f"https://{args.domain}",
            "url_patterns": {
                "product": "/products/",
                "category": "/categories/"
            },
            "shard_extraction": {
                "method": "path_segment",
                "segment_index": 1,
                "fallback_method": "product_categorization"
            },
            "url_filters": {
                "include_patterns": ["product", "collection", "shop", "catalog", "item"],
                "exclude_patterns": [
                    "sitemap", "robots.txt", "blog", "news", "about", "contact", 
                    "privacy", "terms", "help", "faq", "search", "cart", "checkout",
                    "account", "login", "register", "admin", "api", "feed", "rss"
                ],
                "max_depth": 3
            },
            "product_categories": {
                "other_products": []
            },
            "elevenlabs_agent": args.domain
        }
        
        config_manager.add_site_config(args.domain, template_config)
        print(f"Created template configuration for {args.domain}")
        print("You can edit the configuration file to customize it further.")
        
    elif args.interactive:
        # Interactive configuration
        try:
            config = create_site_config(args.domain)
            
            # Show configuration summary
            print("\nConfiguration Summary:")
            print("=" * 30)
            print(json.dumps(config, indent=2))
            
            # Confirm
            if get_yes_no("\nSave this configuration?", True):
                config_manager.add_site_config(args.domain, config)
                print(f"Configuration saved for {args.domain}")
                
                # Validate
                issues = config_manager.validate_config(args.domain)
                if issues:
                    print("\nConfiguration issues found:")
                    for issue in issues:
                        print(f"  - {issue}")
                else:
                    print("Configuration is valid!")
            else:
                print("Configuration not saved.")
                
        except KeyboardInterrupt:
            print("\nConfiguration cancelled.")
        except Exception as e:
            print(f"Error creating configuration: {e}")
    
    else:
        print("Please specify --interactive or --template mode")


if __name__ == "__main__":
    main()
