#!/usr/bin/env python3
"""
Script to remove original large files from knowledge base since we have split versions.
"""

import os
import json
import logging
import requests
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def cleanup_duplicate_files():
    """Remove original large files from knowledge base."""
    
    # Get API key
    api_key = os.getenv('ELEVENLABS_API_KEY')
    if not api_key:
        logger.error("ELEVENLABS_API_KEY environment variable is required")
        return
    
    # Load sync state
    sync_state_file = Path("config/elevenlabs_sync_state.json")
    with open(sync_state_file, 'r') as f:
        sync_state = json.load(f)
    
    # Identify original large files that have split versions
    original_large_files = [
        'jgengineering.ie:llms-jgengineering-ie-taps_dies.txt',
        'jgengineering.ie:llms-jgengineering-ie-metric-helicoil-inserts-ireland.txt',
        'jgengineering.ie:llms-jgengineering-ie-baercoil-metric-helicoil-kits-ireland.txt',
        'jgengineering.ie:llms-jgengineering-ie-kits_sets.txt',
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
    
    # Find files that have document_ids and need to be removed
    files_to_remove = []
    for key in original_large_files:
        if key in sync_state and 'document_id' in sync_state[key]:
            files_to_remove.append({
                'key': key,
                'document_id': sync_state[key]['document_id'],
                'filename': key.replace('jgengineering.ie:', '')
            })
    
    if not files_to_remove:
        logger.info("No duplicate files found to remove")
        return
    
    logger.info(f"Found {len(files_to_remove)} original large files to remove from knowledge base")
    
    # Remove from knowledge base
    base_url = "https://api.elevenlabs.io/v1/convai"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json"
    }
    
    success_count = 0
    failed_count = 0
    
    for file_info in files_to_remove:
        document_id = file_info['document_id']
        filename = file_info['filename']
        
        logger.info(f"🗑️ Removing {filename} (ID: {document_id})")
        
        try:
            delete_url = f"{base_url}/knowledge-base/{document_id}"
            response = requests.delete(delete_url, headers=headers, timeout=30)
            
            if response.status_code in [200, 204]:
                # Remove from sync state
                del sync_state[file_info['key']]
                logger.info(f"✅ Successfully removed {filename}")
                success_count += 1
            else:
                logger.error(f"❌ Failed to remove {filename}: {response.status_code} - {response.text}")
                failed_count += 1
                
        except Exception as e:
            logger.error(f"❌ Error removing {filename}: {e}")
            failed_count += 1
    
    # Save updated sync state
    with open(sync_state_file, 'w') as f:
        json.dump(sync_state, f, indent=2)
    
    logger.info(f"🎉 Cleanup completed:")
    logger.info(f"  - Successfully removed: {success_count} files")
    logger.info(f"  - Failed removals: {failed_count} files")

if __name__ == "__main__":
    cleanup_duplicate_files()
