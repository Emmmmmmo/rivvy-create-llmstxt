#!/usr/bin/env python3
"""
Verify agent assignment for specific document
"""

import os
import json
import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def verify_agent_assignment(agent_id: str, target_filename: str):
    """Verify that a specific document is assigned to the agent."""
    
    api_key = os.getenv('ELEVENLABS_API_KEY')
    if not api_key:
        logger.error("ELEVENLABS_API_KEY environment variable is required")
        return False
    
    base_url = "https://api.elevenlabs.io/v1/convai"
    
    try:
        # Get agent knowledge base
        get_url = f"{base_url}/agents/{agent_id}"
        headers = {"xi-api-key": api_key}
        
        response = requests.get(get_url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            logger.error(f"Failed to get agent config: {response.status_code}")
            return False
        
        agent_data = response.json()
        prompt_config = agent_data.get("conversation_config", {}).get("agent", {}).get("prompt", {})
        knowledge_base = prompt_config.get("knowledge_base", [])
        
        logger.info(f"Found {len(knowledge_base)} documents in agent knowledge base")
        
        # Look for the target file
        target_found = False
        for doc in knowledge_base:
            if isinstance(doc, dict) and 'name' in doc:
                doc_name = doc['name']
                if target_filename in doc_name:
                    logger.info(f"✅ Found target document: {doc_name} (ID: {doc.get('id', 'unknown')})")
                    target_found = True
                    break
        
        if target_found:
            logger.info(f"🎉 SUCCESS: {target_filename} is assigned to agent {agent_id}")
            return True
        else:
            logger.warning(f"⚠️  {target_filename} not found in agent knowledge base")
            return False
            
    except Exception as e:
        logger.error(f"Error verifying agent assignment: {e}")
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 3:
        print("Usage: python3 verify_agent_assignment.py <agent_id> <target_filename>")
        sys.exit(1)
    
    agent_id = sys.argv[1]
    target_filename = sys.argv[2]
    
    success = verify_agent_assignment(agent_id, target_filename)
    sys.exit(0 if success else 1)
