#!/usr/bin/env python3
"""
Test script to assign a single document to the agent and debug the issue.
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

def test_single_assignment():
    """Test assigning a single document to the agent."""
    
    # Get API key
    api_key = os.getenv('ELEVENLABS_API_KEY')
    if not api_key:
        logger.error("ELEVENLABS_API_KEY environment variable is required")
        return
    
    # Get agent config
    config_file = Path("config/elevenlabs-agents.json")
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    agent_id = config['agents']['jgengineering.ie']['agent_id']
    file_prefix = config['agents']['jgengineering.ie']['file_prefix']
    
    # Load sync state
    sync_state_file = Path("config/elevenlabs_sync_state.json")
    with open(sync_state_file, 'r') as f:
        sync_state = json.load(f)
    
    # Find a small file to test with
    test_file = None
    for key, info in sync_state.items():
        if key.startswith('jgengineering.ie:') and 'document_id' in info:
            # Pick a small file (not a split file)
            if 'part' not in info.get('file_path', ''):
                test_file = info
                break
    
    if not test_file:
        logger.error("No suitable test file found")
        return
    
    file_path = test_file.get('file_path', 'unknown')
    document_id = test_file['document_id']
    
    logger.info(f"Testing with file: {file_path}")
    logger.info(f"Document ID: {document_id}")
    
    # Create knowledge base payload
    knowledge_base = [{
        "id": document_id,
        "type": "file",
        "name": f"{file_prefix}_{Path(file_path).name}",
        "usage_mode": "auto"
    }]
    
    logger.info(f"Knowledge base payload: {json.dumps(knowledge_base, indent=2)}")
    
    # Update agent
    base_url = "https://api.elevenlabs.io/v1/convai"
    update_url = f"{base_url}/agents/{agent_id}"
    
    update_payload = {
        "conversation_config": {
            "agent": {
                "prompt": {
                    "knowledge_base": knowledge_base
                }
            }
        }
    }
    
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json"
    }
    
    logger.info(f"Updating agent with payload: {json.dumps(update_payload, indent=2)}")
    
    try:
        response = requests.patch(
            update_url,
            headers=headers,
            json=update_payload,
            timeout=60
        )
        
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response body: {response.text}")
        
        if response.status_code == 200:
            logger.info("✅ Agent updated successfully")
            
            # Wait a moment and check the agent's knowledge base
            import time
            time.sleep(2)
            
            # Get agent to verify
            get_url = f"{base_url}/agents/{agent_id}"
            get_response = requests.get(get_url, headers=headers, timeout=30)
            
            if get_response.status_code == 200:
                agent_data = get_response.json()
                kb = agent_data.get('agent', {}).get('prompt', {}).get('knowledge_base', [])
                logger.info(f"Agent knowledge base now contains {len(kb)} documents:")
                for doc in kb:
                    logger.info(f"  - {doc.get('name', 'Unknown')} (ID: {doc.get('id', 'Unknown')})")
            else:
                logger.error(f"Failed to get agent: {get_response.status_code} - {get_response.text}")
        else:
            logger.error(f"Failed to update agent: {response.status_code} - {response.text}")
            
    except Exception as e:
        logger.error(f"Error updating agent: {e}")

if __name__ == "__main__":
    test_single_assignment()
