#!/usr/bin/env python3
"""
Migrate MyDIY.ie Index Format

This script migrates the old index format (with "shard" field) to the new format
(with "shard_key" field) for consistency across all products.

Usage:
    python3 scripts/migrate_index_format.py [--dry-run] [--domain mydiy-ie]
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime
import shutil

def migrate_index(domain: str, dry_run: bool = False):
    """Migrate index format from old to new structure."""
    
    base_path = Path(f"out/{domain}")
    index_file = base_path / f"llms-{domain}-index.json"
    
    if not index_file.exists():
        print(f"❌ Index file not found: {index_file}")
        return False
    
    print(f"🔍 Migrating index for {domain}")
    print(f"   File: {index_file}")
    print("=" * 80)
    
    # Load index
    with open(index_file, 'r') as f:
        index = json.load(f)
    
    print(f"\n📊 Current state:")
    print(f"   Total entries: {len(index)}")
    
    # Analyze current structure
    stats = {
        'has_shard_key': 0,
        'has_old_shard': 0,
        'has_both': 0,
        'has_neither': 0,
        'migrated': 0
    }
    
    for url, data in index.items():
        if isinstance(data, dict):
            has_shard_key = 'shard_key' in data
            has_shard = 'shard' in data
            
            if has_shard_key and has_shard:
                stats['has_both'] += 1
            elif has_shard_key:
                stats['has_shard_key'] += 1
            elif has_shard:
                stats['has_old_shard'] += 1
            else:
                stats['has_neither'] += 1
    
    print(f"\n   Entries with 'shard_key': {stats['has_shard_key']}")
    print(f"   Entries with old 'shard': {stats['has_old_shard']}")
    print(f"   Entries with both: {stats['has_both']}")
    print(f"   Entries with neither: {stats['has_neither']}")
    
    # Check if migration needed
    if stats['has_old_shard'] == 0 and stats['has_both'] == 0:
        print(f"\n✅ No migration needed - all entries already use 'shard_key'")
        return True
    
    print(f"\n🔄 Migration plan:")
    print(f"   Will migrate: {stats['has_old_shard']} entries")
    print(f"   Will clean up: {stats['has_both']} entries (remove duplicate 'shard' field)")
    
    if dry_run:
        print(f"\n⚠️  DRY RUN MODE - No changes will be made")
        return True
    
    # Confirm migration
    print(f"\n⚠️  This will modify {index_file}")
    response = input("Continue with migration? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Migration cancelled")
        return False
    
    # Create backup
    backup_file = index_file.with_suffix('.json.backup')
    print(f"\n💾 Creating backup: {backup_file.name}")
    shutil.copy2(index_file, backup_file)
    
    # Perform migration
    print(f"\n🔄 Migrating entries...")
    migrated_index = {}
    
    for url, data in index.items():
        if isinstance(data, dict):
            new_data = data.copy()
            
            # If has old 'shard' field but no 'shard_key'
            if 'shard' in new_data and 'shard_key' not in new_data:
                new_data['shard_key'] = new_data['shard']
                stats['migrated'] += 1
            
            # Remove old 'shard' field if both exist
            if 'shard' in new_data and 'shard_key' in new_data:
                del new_data['shard']
            
            # Ensure scraped_at exists
            if 'scraped_at' not in new_data:
                # Use updated_at if available, otherwise use current time
                if 'updated_at' in new_data:
                    new_data['scraped_at'] = new_data['updated_at']
                else:
                    new_data['scraped_at'] = datetime.now().isoformat()
            
            # Ensure source exists
            if 'source' not in new_data:
                new_data['source'] = 'migrated_from_old_format'
            
            migrated_index[url] = new_data
        else:
            # Keep non-dict entries as-is (shouldn't happen)
            migrated_index[url] = data
    
    # Save migrated index
    print(f"💾 Saving migrated index...")
    with open(index_file, 'w') as f:
        json.dump(migrated_index, f, indent=2)
    
    # Validate migration
    print(f"\n✅ Migration complete!")
    print(f"   Migrated: {stats['migrated']} entries")
    
    # Re-analyze
    print(f"\n📊 Post-migration state:")
    stats_after = {'has_shard_key': 0, 'has_old_shard': 0, 'has_neither': 0}
    
    for url, data in migrated_index.items():
        if isinstance(data, dict):
            if 'shard_key' in data:
                stats_after['has_shard_key'] += 1
            elif 'shard' in data:
                stats_after['has_old_shard'] += 1
            else:
                stats_after['has_neither'] += 1
    
    print(f"   Entries with 'shard_key': {stats_after['has_shard_key']}")
    print(f"   Entries with old 'shard': {stats_after['has_old_shard']}")
    print(f"   Entries with neither: {stats_after['has_neither']}")
    
    if stats_after['has_old_shard'] == 0:
        print(f"\n✅ SUCCESS - All entries now use 'shard_key' format")
    else:
        print(f"\n⚠️  WARNING - {stats_after['has_old_shard']} entries still have old format")
    
    print(f"\n💾 Backup saved to: {backup_file}")
    print(f"   To restore: cp {backup_file} {index_file}")
    
    return True

def main():
    parser = argparse.ArgumentParser(description='Migrate index format from old to new structure')
    parser.add_argument('--domain', type=str, default='mydiy-ie',
                       help='Domain to migrate (default: mydiy-ie)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be migrated without making changes')
    
    args = parser.parse_args()
    
    success = migrate_index(args.domain, dry_run=args.dry_run)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()

