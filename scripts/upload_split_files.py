#!/usr/bin/env python3
"""
Script to upload split files to ElevenLabs knowledge base.
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

def upload_split_files():
    """Upload split files to ElevenLabs knowledge base."""
    
    # Get API key
    api_key = os.getenv('ELEVENLABS_API_KEY')
    if not api_key:
        logger.error("ELEVENLABS_API_KEY environment variable is required")
        return
    
    # Load sync state
    sync_state_file = Path("config/elevenlabs_sync_state.json")
    with open(sync_state_file, 'r') as f:
        sync_state = json.load(f)
    
    # Get agent config
    config_file = Path("config/elevenlabs-agents.json")
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    file_prefix = config['agents']['jgengineering.ie']['file_prefix']
    
    # Find split files that need upload
    split_files = {}
    for key, info in sync_state.items():
        if key.startswith('jgengineering.ie:') and info.get('needs_upload', False):
            if 'split_from' in info:  # This is a split file
                split_files[key] = info
    
    if not split_files:
        logger.info("No split files need uploading")
        return
    
    logger.info(f"Found {len(split_files)} split files to upload")
    
    # Upload each split file
    base_url = "https://api.elevenlabs.io/v1/convai"
    upload_url = f"{base_url}/knowledge-base/file"
    
    headers = {
        "xi-api-key": api_key
    }
    
    success_count = 0
    failed_count = 0
    
    for key, info in split_files.items():
        file_path = Path(info['file_path'])
        filename = file_path.name
        
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            failed_count += 1
            continue
        
        logger.info(f"📤 Uploading split file: {filename}")
        
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (filename, f, 'text/plain')}
                
                response = requests.post(
                    upload_url,
                    headers=headers,
                    files=files,
                    timeout=120
                )
            
            if response.status_code == 200:
                result = response.json()
                document_id = result.get('id')
                
                if document_id:
                    # Update sync state
                    sync_state[key]['document_id'] = document_id
                    sync_state[key]['needs_upload'] = False
                    sync_state[key]['uploaded_at'] = info.get('uploaded_at', '2025-09-27T22:00:00Z')
                    
                    logger.info(f"✅ Successfully uploaded {filename} (ID: {document_id})")
                    success_count += 1
                else:
                    logger.error(f"❌ No document ID in response for {filename}")
                    failed_count += 1
            else:
                logger.error(f"❌ Failed to upload {filename}: {response.status_code} - {response.text}")
                failed_count += 1
                
        except Exception as e:
            logger.error(f"❌ Error uploading {filename}: {e}")
            failed_count += 1
    
    # Save updated sync state
    with open(sync_state_file, 'w') as f:
        json.dump(sync_state, f, indent=2)
    
    logger.info(f"🎉 Upload completed:")
    logger.info(f"  - Successfully uploaded: {success_count} files")
    logger.info(f"  - Failed uploads: {failed_count} files")

if __name__ == "__main__":
    upload_split_files()
