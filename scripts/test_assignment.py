#!/usr/bin/env python3
"""
Test script to assign files in small batches to identify issues.
"""

import os
import json
import logging
import requests
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_small_assignment():
    """Test assigning just a few files to see if the issue is with specific files or the API."""
    
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
    
    agent_id = config['agents']['jgengineering.ie']['agent_id']
    file_prefix = config['agents']['jgengineering.ie']['file_prefix']
    
    # Get first 5 files for testing
    domain_files = {k: v for k, v in sync_state.items() if k.startswith('jgengineering.ie:')}
    test_files = list(domain_files.items())[:5]  # First 5 files
    
    logger.info(f"Testing assignment with {len(test_files)} files")
    
    # Build knowledge base with just test files
    knowledge_base = []
    for file_key, file_info in test_files:
        if 'document_id' in file_info:
            filename = file_key.replace('jgengineering.ie:', '')
            prefixed_filename = f"{file_prefix}_{filename}"
            
            doc = {
                "type": "file",
                "name": prefixed_filename,
                "id": file_info['document_id'],
                "usage_mode": "auto"
            }
            knowledge_base.append(doc)
            logger.info(f"📄 Testing: {prefixed_filename} (ID: {file_info['document_id']})")
    
    # Try to assign
    base_url = "https://api.elevenlabs.io/v1/convai"
    update_payload = {
        "conversation_config": {
            "agent": {
                "prompt": {
                    "knowledge_base": knowledge_base
                }
            }
        }
    }
    
    update_url = f"{base_url}/agents/{agent_id}"
    update_headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json"
    }
    
    logger.info("🎯 Attempting assignment...")
    try:
        response = requests.patch(
            update_url,
            headers=update_headers,
            json=update_payload,
            timeout=60
        )
        
        if response.status_code == 200:
            logger.info("✅ SUCCESS! Small batch assignment worked")
            return True
        else:
            logger.error(f"❌ Failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_small_assignment()
