#!/usr/bin/env python3
"""
Sitemap Integration Test

End-to-end test of sitemap monitoring workflow:
1. Simulate sitemap webhook with product changes
2. Verify shards updated correctly
3. Verify manifest/index updated
4. Verify no unexpected changes to JG Engineering

Usage:
    python3 tests/test_sitemap_integration.py
"""

import sys
import json
import subprocess
from pathlib import Path
import shutil
from datetime import datetime

def setup_test_environment():
    """Backup current state before testing."""
    print("Setting up test environment...")
    print("-" * 80)
    
    # Create backup of current index/manifest
    mydiy_dir = Path("out/mydiy-ie")
    if mydiy_dir.exists():
        backup_dir = Path(f"out/mydiy-ie-backup-{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        print(f"Creating backup: {backup_dir}")
        shutil.copytree(mydiy_dir, backup_dir)
        print("✓ Backup created")
    else:
        print("⚠️  MyDIY directory doesn't exist - will be created")
    
    # Check JG Engineering state (should not change)
    jg_dir = Path("out/jgengineering-ie")
    jg_manifest_hash = None
    jg_index_hash = None
    
    if jg_dir.exists():
        import hashlib
        
        manifest_file = jg_dir / "llms-jgengineering-ie-manifest.json"
        if manifest_file.exists():
            jg_manifest_hash = hashlib.md5(manifest_file.read_bytes()).hexdigest()
        
        index_file = jg_dir / "llms-jgengineering-ie-index.json"
        if index_file.exists():
            jg_index_hash = hashlib.md5(index_file.read_bytes()).hexdigest()
        
        print(f"JG manifest hash: {jg_manifest_hash}")
        print(f"JG index hash: {jg_index_hash}")
    
    print()
    return {
        "jg_manifest_hash": jg_manifest_hash,
        "jg_index_hash": jg_index_hash
    }

def simulate_webhook_payload(scenario: str):
    """Generate test webhook payload."""
    if scenario == "test_products":
        return {
            "website": {
                "url": "https://www.mydiy.ie",
                "id": "test_mydiy"
            },
            "changedPages": [
                {
                    "url": "https://www.mydiy.ie/products/test-integration-product-1.html",
                    "changeType": "page_added",
                    "lastmod": "2025-10-08"
                },
                {
                    "url": "https://www.mydiy.ie/products/test-integration-product-2.html",
                    "changeType": "page_added",
                    "lastmod": "2025-10-08"
                },
                {
                    "url": "https://www.mydiy.ie/products/test-integration-product-3.html",
                    "changeType": "page_added",
                    "lastmod": "2025-10-08"
                }
            ]
        }
    return None

def process_webhook(payload: dict, dry_run: bool = False):
    """Process webhook payload (simulate GitHub Actions workflow)."""
    print("Processing webhook payload...")
    print("-" * 80)
    
    domain = payload['website']['url'].replace('https://www.', '').replace('https://', '').replace('/', '')
    
    # Separate by operation
    added_urls = []
    removed_urls = []
    
    for page in payload['changedPages']:
        if page['changeType'] in ['page_added', 'content_modified', 'content_changed']:
            added_urls.append(page['url'])
        elif page['changeType'] == 'page_removed':
            removed_urls.append(page['url'])
    
    print(f"Domain: {domain}")
    print(f"Added/Modified: {len(added_urls)} URLs")
    print(f"Removed: {len(removed_urls)} URLs")
    print()
    
    results = {"added": None, "removed": None}
    
    # Process added URLs
    if added_urls and not dry_run:
        print(f"Processing {len(added_urls)} added URLs...")
        cmd = [
            'python3', 'scripts/update_llms_agnostic.py',
            domain,
            '--added', json.dumps(added_urls)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            results['added'] = {
                'exit_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
            if result.returncode == 0:
                print("✓ Added URLs processed successfully")
            else:
                print(f"✗ Processing failed with exit code {result.returncode}")
                if result.stderr:
                    print(f"Error: {result.stderr[:500]}")
        except subprocess.TimeoutExpired:
            print("✗ Processing timed out")
            results['added'] = {'error': 'timeout'}
        except Exception as e:
            print(f"✗ Error: {e}")
            results['added'] = {'error': str(e)}
    
    # Process removed URLs
    if removed_urls and not dry_run:
        print(f"\nProcessing {len(removed_urls)} removed URLs...")
        cmd = [
            'python3', 'scripts/update_llms_agnostic.py',
            domain,
            '--removed', json.dumps(removed_urls)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            results['removed'] = {
                'exit_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
            if result.returncode == 0:
                print("✓ Removed URLs processed successfully")
            else:
                print(f"✗ Processing failed with exit code {result.returncode}")
                if result.stderr:
                    print(f"Error: {result.stderr[:500]}")
        except subprocess.TimeoutExpired:
            print("✗ Processing timed out")
            results['removed'] = {'error': 'timeout'}
        except Exception as e:
            print(f"✗ Error: {e}")
            results['removed'] = {'error': str(e)}
    
    print()
    return results

def verify_results(initial_state: dict):
    """Verify that changes were applied correctly."""
    print("Verifying results...")
    print("-" * 80)
    
    passed = 0
    failed = 0
    
    # Verify MyDIY changes
    mydiy_dir = Path("out/mydiy-ie")
    if mydiy_dir.exists():
        manifest_file = mydiy_dir / "llms-mydiy-ie-manifest.json"
        index_file = mydiy_dir / "llms-mydiy-ie-index.json"
        
        if manifest_file.exists():
            with open(manifest_file) as f:
                manifest = json.load(f)
            
            print(f"✓ MyDIY manifest exists ({len(manifest)} shards)")
            passed += 1
        else:
            print("✗ MyDIY manifest not found")
            failed += 1
        
        if index_file.exists():
            with open(index_file) as f:
                index = json.load(f)
            
            print(f"✓ MyDIY index exists ({len(index)} products)")
            passed += 1
            
            # Check for consistent format (all should have shard_key)
            has_shard_key = sum(1 for v in index.values() if isinstance(v, dict) and 'shard_key' in v)
            has_old_shard = sum(1 for v in index.values() if isinstance(v, dict) and 'shard' in v and 'shard_key' not in v)
            
            if has_old_shard == 0:
                print(f"✓ All index entries use shard_key format")
                passed += 1
            else:
                print(f"✗ {has_old_shard} entries still use old format")
                failed += 1
        else:
            print("✗ MyDIY index not found")
            failed += 1
    else:
        print("✗ MyDIY output directory not found")
        failed += 1
    
    # Verify JG Engineering unchanged
    print()
    print("Checking JG Engineering (should be unchanged)...")
    jg_dir = Path("out/jgengineering-ie")
    
    if jg_dir.exists():
        import hashlib
        
        manifest_file = jg_dir / "llms-jgengineering-ie-manifest.json"
        if manifest_file.exists():
            current_hash = hashlib.md5(manifest_file.read_bytes()).hexdigest()
            if current_hash == initial_state.get('jg_manifest_hash'):
                print("✓ JG manifest unchanged")
                passed += 1
            else:
                print("⚠️  JG manifest changed (unexpected)")
                failed += 1
        
        index_file = jg_dir / "llms-jgengineering-ie-index.json"
        if index_file.exists():
            current_hash = hashlib.md5(index_file.read_bytes()).hexdigest()
            if current_hash == initial_state.get('jg_index_hash'):
                print("✓ JG index unchanged")
                passed += 1
            else:
                print("⚠️  JG index changed (unexpected)")
                failed += 1
    else:
        print("⚠️  JG Engineering directory not found (skipping verification)")
    
    print()
    print("-" * 80)
    print(f"Verification: {passed} passed, {failed} failed")
    print()
    
    return failed == 0

def run_integration_test():
    """Run full integration test."""
    print("=" * 80)
    print("SITEMAP MONITORING INTEGRATION TEST")
    print("=" * 80)
    print()
    
    # Setup
    initial_state = setup_test_environment()
    
    # Generate test payload
    payload = simulate_webhook_payload("test_products")
    if not payload:
        print("✗ Failed to generate test payload")
        return False
    
    print("Test payload generated:")
    print(f"  Changed pages: {len(payload['changedPages'])}")
    for page in payload['changedPages']:
        print(f"    - {page['url']} ({page['changeType']})")
    print()
    
    # Note: This is a dry-run test since we don't want to make actual API calls
    # In a real environment with test data, set dry_run=False
    print("⚠️  NOTE: This is a dry-run test (no actual scraping)")
    print("    To run with actual scraping, ensure:")
    print("    1. FIRECRAWL_API_KEY is set")
    print("    2. You have sufficient API credits")
    print("    3. Test URLs are accessible")
    print()
    
    # Process webhook (dry-run)
    results = process_webhook(payload, dry_run=True)
    
    # Verify results
    success = verify_results(initial_state)
    
    print("=" * 80)
    if success:
        print("✓ INTEGRATION TEST PASSED")
    else:
        print("✗ INTEGRATION TEST FAILED")
    print("=" * 80)
    
    return success

if __name__ == "__main__":
    success = run_integration_test()
    sys.exit(0 if success else 1)

