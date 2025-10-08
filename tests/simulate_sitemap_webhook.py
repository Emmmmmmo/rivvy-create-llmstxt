#!/usr/bin/env python3
"""
Sitemap Webhook Simulator

Generates mock webhook payloads for testing sitemap monitoring integration.
Simulates various scenarios that would be sent by the observer.

Usage:
    python3 tests/simulate_sitemap_webhook.py --scenario new_product
    python3 tests/simulate_sitemap_webhook.py --scenario bulk_changes
"""

import json
import argparse
import sys
from pathlib import Path

# Test scenarios
SCENARIOS = {
    "new_product": {
        "description": "Single new product added to sitemap",
        "payload": {
            "website": {
                "url": "https://www.mydiy.ie",
                "id": "test_mydiy"
            },
            "changedPages": [
                {
                    "url": "https://www.mydiy.ie/products/test-new-cordless-drill.html",
                    "changeType": "page_added",
                    "lastmod": "2025-10-08",
                    "scrapedContent": {
                        "markdown": "Test product content for cordless drill"
                    }
                }
            ]
        }
    },
    
    "product_removed": {
        "description": "Product removed from sitemap (discontinued)",
        "payload": {
            "website": {
                "url": "https://www.mydiy.ie",
                "id": "test_mydiy"
            },
            "changedPages": [
                {
                    "url": "https://www.mydiy.ie/products/discontinued-hammer.html",
                    "changeType": "page_removed"
                }
            ]
        }
    },
    
    "product_modified": {
        "description": "Product content changed (price update)",
        "payload": {
            "website": {
                "url": "https://www.mydiy.ie",
                "id": "test_mydiy"
            },
            "changedPages": [
                {
                    "url": "https://www.mydiy.ie/products/makita-ga4030r-100mm-anti-restart-angle-grinder.html",
                    "changeType": "content_modified",
                    "diff": {
                        "text": "Price changed from €82.75 to €74.82"
                    }
                }
            ]
        }
    },
    
    "bulk_changes": {
        "description": "Multiple products added (10+ products)",
        "payload": {
            "website": {
                "url": "https://www.mydiy.ie",
                "id": "test_mydiy"
            },
            "changedPages": [
                {
                    "url": f"https://www.mydiy.ie/products/test-drill-{i}.html",
                    "changeType": "page_added",
                    "lastmod": "2025-10-08"
                } for i in range(1, 11)
            ]
        }
    },
    
    "mixed_changes": {
        "description": "Mixed operations (add, modify, remove)",
        "payload": {
            "website": {
                "url": "https://www.mydiy.ie",
                "id": "test_mydiy"
            },
            "changedPages": [
                {
                    "url": "https://www.mydiy.ie/products/new-product-1.html",
                    "changeType": "page_added",
                    "lastmod": "2025-10-08"
                },
                {
                    "url": "https://www.mydiy.ie/products/new-product-2.html",
                    "changeType": "page_added",
                    "lastmod": "2025-10-08"
                },
                {
                    "url": "https://www.mydiy.ie/products/updated-product.html",
                    "changeType": "content_modified",
                    "diff": {
                        "text": "Price updated"
                    }
                },
                {
                    "url": "https://www.mydiy.ie/products/old-product.html",
                    "changeType": "page_removed"
                }
            ]
        }
    },
    
    "jg_engineering": {
        "description": "JG Engineering product change (test backward compatibility)",
        "payload": {
            "website": {
                "url": "https://www.jgengineering.ie",
                "id": "test_jg"
            },
            "changedPages": [
                {
                    "url": "https://www.jgengineering.ie/collections/baercoil-drill-bits/products/test-drill-bit.html",
                    "changeType": "page_added",
                    "lastmod": "2025-10-08"
                }
            ]
        }
    }
}

def generate_payload(scenario: str):
    """Generate webhook payload for the specified scenario."""
    if scenario not in SCENARIOS:
        print(f"Error: Unknown scenario '{scenario}'")
        print(f"Available scenarios: {', '.join(SCENARIOS.keys())}")
        return None
    
    return SCENARIOS[scenario]

def save_payload(payload: dict, output_file: str):
    """Save payload to file in JSON format."""
    with open(output_file, 'w') as f:
        json.dump(payload, f, indent=2)
    print(f"Payload saved to: {output_file}")

def simulate_webhook(scenario: str, output_file: str = None, execute: bool = False):
    """
    Simulate a webhook call.
    
    Args:
        scenario: Test scenario to simulate
        output_file: Path to save payload (optional)
        execute: If True, actually call the update script
    """
    print(f"Simulating webhook scenario: {scenario}")
    print("=" * 80)
    
    scenario_data = generate_payload(scenario)
    if not scenario_data:
        return False
    
    print(f"Description: {scenario_data['description']}")
    print(f"Changed pages: {len(scenario_data['payload']['changedPages'])}")
    print()
    
    payload = scenario_data['payload']
    
    # Print payload summary
    print("Payload summary:")
    print(f"  Website: {payload['website']['url']}")
    for i, page in enumerate(payload['changedPages'], 1):
        print(f"  {i}. {page['url']} ({page['changeType']})")
    
    print()
    
    # Save to file if requested
    if output_file:
        save_payload(payload, output_file)
    
    # Execute if requested
    if execute:
        print("Executing webhook simulation...")
        print("=" * 80)
        
        # Extract domain
        domain = payload['website']['url'].replace('https://www.', '').replace('https://', '')
        domain = domain.replace('/', '')
        
        # Separate URLs by operation
        added_urls = []
        removed_urls = []
        
        for page in payload['changedPages']:
            if page['changeType'] in ['page_added', 'content_modified', 'content_changed']:
                added_urls.append(page['url'])
            elif page['changeType'] == 'page_removed':
                removed_urls.append(page['url'])
        
        # Build command
        import subprocess
        
        if added_urls:
            print(f"\nProcessing {len(added_urls)} added/modified URLs...")
            cmd = [
                'python3', 'scripts/update_llms_agnostic.py',
                domain,
                '--added', json.dumps(added_urls)
            ]
            print(f"Command: {' '.join(cmd)}")
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True)
                print(f"Exit code: {result.returncode}")
                if result.stdout:
                    print("Output:")
                    print(result.stdout)
                if result.stderr:
                    print("Errors:")
                    print(result.stderr)
            except Exception as e:
                print(f"Error executing command: {e}")
        
        if removed_urls:
            print(f"\nProcessing {len(removed_urls)} removed URLs...")
            cmd = [
                'python3', 'scripts/update_llms_agnostic.py',
                domain,
                '--removed', json.dumps(removed_urls)
            ]
            print(f"Command: {' '.join(cmd)}")
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True)
                print(f"Exit code: {result.returncode}")
                if result.stdout:
                    print("Output:")
                    print(result.stdout)
                if result.stderr:
                    print("Errors:")
                    print(result.stderr)
            except Exception as e:
                print(f"Error executing command: {e}")
    
    print()
    print("Simulation complete!")
    return True

def main():
    parser = argparse.ArgumentParser(description='Simulate sitemap webhook payloads')
    parser.add_argument(
        '--scenario',
        choices=list(SCENARIOS.keys()),
        required=True,
        help='Test scenario to simulate'
    )
    parser.add_argument(
        '--output',
        help='Save payload to file'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Actually execute the webhook (call update script)'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List available scenarios'
    )
    
    args = parser.parse_args()
    
    if args.list:
        print("Available scenarios:")
        print("=" * 80)
        for name, data in SCENARIOS.items():
            print(f"\n{name}:")
            print(f"  {data['description']}")
        return
    
    success = simulate_webhook(
        args.scenario,
        output_file=args.output,
        execute=args.execute
    )
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()

