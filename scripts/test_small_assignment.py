#!/usr/bin/env python3
"""
Test script to assign just a few documents to see if the assignment works.
"""

import os
import json
import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_small_assignment():
    """Test assigning just 3 documents to see if the assignment works."""
    
    # Set API key
    api_key = os.getenv('ELEVENLABS_API_KEY')
    if not api_key:
        api_key = 'sk_85123b7aa38cae9f16c8d52a2ab5cfd2a8f9a45faeeeb8fe'
        os.environ['ELEVENLABS_API_KEY'] = api_key
    
    agent_id = 'agent_1901k666bcn6evwrwe3hxn41txqe'
    base_url = "https://api.elevenlabs.io/v1/convai"
    
    # Get current knowledge base
    logger.info("🔍 Getting current agent knowledge base...")
    get_url = f"{base_url}/agents/{agent_id}"
    headers = {"xi-api-key": api_key}
    
    response = requests.get(get_url, headers=headers, timeout=10)
    if response.status_code != 200:
        logger.error(f"Failed to get agent: {response.status_code} - {response.text}")
        return False
    
    agent_data = response.json()
    current_kb = agent_data.get("conversation_config", {}).get("agent", {}).get("prompt", {}).get("knowledge_base", [])
    logger.info(f"Current knowledge base has {len(current_kb)} documents")
    
    # Add just 3 real documents
    test_docs = [
        {
            "type": "file",
            "name": "jg_eng_llms-jgengineering-ie-special-kit-sizes-helicoil.txt",
            "id": "uQR0jBcRvBPXRoc3y0i1",
            "usage_mode": "auto"
        },
        {
            "type": "file", 
            "name": "jg_eng_llms-jgengineering-ie-baerfix-thread-inserts-cutting-slots-like-timesert.txt",
            "id": "FWJemEVDmA8rkE3Fwen9",
            "usage_mode": "auto"
        },
        {
            "type": "file",
            "name": "jg_eng_llms-jgengineering-ie-helicoil-inserts-ireland.txt", 
            "id": "eVr4qNWx9PNH61ciWloj",
            "usage_mode": "auto"
        }
    ]
    
    # Combine with existing
    final_kb = current_kb + test_docs
    logger.info(f"Final knowledge base will have {len(final_kb)} documents")
    
    # Update agent
    logger.info("🔄 Updating agent with new knowledge base...")
    update_payload = {
        "conversation_config": {
            "agent": {
                "prompt": {
                    "knowledge_base": final_kb
                }
            }
        }
    }
    
    update_url = f"{base_url}/agents/{agent_id}"
    update_headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json"
    }
    
    update_response = requests.patch(
        update_url,
        headers=update_headers,
        json=update_payload,
        timeout=60
    )
    
    if update_response.status_code == 200:
        logger.info("✅ Successfully updated agent knowledge base")
        
        # Verify
        logger.info("🔍 Verifying update...")
        verify_response = requests.get(get_url, headers=headers, timeout=10)
        if verify_response.status_code == 200:
            verify_data = verify_response.json()
            verify_kb = verify_data.get("conversation_config", {}).get("agent", {}).get("prompt", {}).get("knowledge_base", [])
            logger.info(f"✅ Verification: Agent now has {len(verify_kb)} documents")
            return True
        else:
            logger.error(f"Failed to verify: {verify_response.status_code}")
            return False
    else:
        logger.error(f"Failed to update agent: {update_response.status_code} - {update_response.text}")
        return False

if __name__ == "__main__":
    test_small_assignment()
