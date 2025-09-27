#!/usr/bin/env python3
"""
Script to update sync state after successful cleanup of duplicate files.
"""

import json
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def update_sync_state():
    """Remove deleted files from sync state."""
    
    # Load sync state
    sync_state_file = Path("config/elevenlabs_sync_state.json")
    with open(sync_state_file, 'r') as f:
        sync_state = json.load(f)
    
    # Files that were successfully deleted (HTTP 204 responses)
    deleted_files = [
        'jgengineering.ie:llms-jgengineering-ie-taps_dies.txt',
        'jgengineering.ie:llms-jgengineering-ie-metric-helicoil-inserts-ireland.txt',
        'jgengineering.ie:llms-jgengineering-ie-baercoil-metric-helicoil-kits-ireland.txt',
        'jgengineering.ie:llms-jgengineering-ie-baercoil-drill-bits.txt',
        'jgengineering.ie:llms-jgengineering-ie-unc-helicoil-inserts-ireland.txt',
        'jgengineering.ie:llms-jgengineering-ie-other_products.txt',
        'jgengineering.ie:llms-jgengineering-ie-circlips-ireland.txt',
        'jgengineering.ie:llms-jgengineering-ie-clips_rings.txt',
        'jgengineering.ie:llms-jgengineering-ie-unf-helicoil-inserts.txt',
        'jgengineering.ie:llms-jgengineering-ie-baerfix-thread-inserts-cutting-slots-m-case-hardened-steel.txt',
        'jgengineering.ie:llms-jgengineering-ie-baercoil-bottoming-taps-metric-helicoil.txt',
        'jgengineering.ie:llms-jgengineering-ie-drill_bits.txt',
        'jgengineering.ie:llms-jgengineering-ie-unc-helicoil-kits-ireland.txt',
        'jgengineering.ie:llms-jgengineering-ie-thread_repair.txt'
    ]
    
    # Remove deleted files from sync state
    removed_count = 0
    for key in deleted_files:
        if key in sync_state:
            del sync_state[key]
            removed_count += 1
            logger.info(f"🗑️ Removed from sync state: {key}")
    
    # Save updated sync state
    with open(sync_state_file, 'w') as f:
        json.dump(sync_state, f, indent=2)
    
    logger.info(f"✅ Updated sync state: removed {removed_count} deleted files")
    
    # Count remaining files
    remaining_files = len([k for k in sync_state.keys() if k.startswith('jgengineering.ie:')])
    logger.info(f"📊 Remaining files in sync state: {remaining_files}")

if __name__ == "__main__":
    update_sync_state()
