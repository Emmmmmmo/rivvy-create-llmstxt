#!/usr/bin/env python3
"""
Test script to assign individual documents to identify problematic ones.
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

def test_individual_assignment():
    """Test assigning individual documents to identify problematic ones."""
    
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
    
    # Get all jgengineering.ie files
    domain_files = {k: v for k, v in sync_state.items() if k.startswith('jgengineering.ie:')}
    
    # Test documents that failed in batches 2-6
    # From the error log, these document IDs failed:
    failed_doc_ids = [
        'jYOW2qGRbPdHLKBpPwx0',  # metric-helicoil-inserts-ireland.txt
        'aBQJu6xbrJBo3famNX5B',  # baercoil-drill-bits.txt
        'xE0SW1cQ2kZcVakJL00F',  # circlips-ireland.txt
        'dXAPk7hbzTkXmDSs2zoA',  # clips_rings.txt
        'z3jNok5te4NQW4VT6tcm'   # drill_bits.txt
    ]
    
    logger.info(f"Testing {len(failed_doc_ids)} individual documents that failed in batches")
    
    base_url = "https://api.elevenlabs.io/v1/convai"
    
    for doc_id in failed_doc_ids:
        # Find the file info for this document ID
        file_info = None
        file_key = None
        for key, info in domain_files.items():
            if info.get('document_id') == doc_id:
                file_info = info
                file_key = key
                break
        
        if not file_info:
            logger.warning(f"Could not find file info for document ID: {doc_id}")
            continue
        
        filename = file_key.replace('jgengineering.ie:', '')
        prefixed_filename = f"{file_prefix}_{filename}"
        
        logger.info(f"🧪 Testing individual assignment: {prefixed_filename} (ID: {doc_id})")
        
        # Create knowledge base with just this document
        knowledge_base = [{
            "type": "file",
            "name": prefixed_filename,
            "id": doc_id,
            "usage_mode": "auto"
        }]
        
        # Try to assign
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
        
        try:
            response = requests.patch(
                update_url,
                headers=update_headers,
                json=update_payload,
                timeout=60
            )
            
            if response.status_code == 200:
                logger.info(f"✅ SUCCESS: {prefixed_filename}")
            else:
                logger.error(f"❌ FAILED: {prefixed_filename} - {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"❌ ERROR: {prefixed_filename} - {e}")

if __name__ == "__main__":
    test_individual_assignment()
