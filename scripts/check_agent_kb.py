#!/usr/bin/env python3
"""
Simple script to check the agent's knowledge base directly.
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

def check_agent_knowledge_base():
    """Check the agent's knowledge base directly."""
    
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
    
    # Get agent knowledge base
    base_url = "https://api.elevenlabs.io/v1/convai"
    url = f"{base_url}/agents/{agent_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            agent_data = response.json()
            knowledge_base = agent_data.get('agent', {}).get('prompt', {}).get('knowledge_base', [])
            
            logger.info(f"📊 Agent knowledge base contains {len(knowledge_base)} documents:")
            
            for i, doc in enumerate(knowledge_base, 1):
                doc_name = doc.get('name', 'Unknown')
                doc_id = doc.get('id', 'Unknown')
                doc_type = doc.get('type', 'Unknown')
                usage_mode = doc.get('usage_mode', 'Unknown')
                logger.info(f"  {i:2d}. {doc_name} (ID: {doc_id}, Type: {doc_type}, Mode: {usage_mode})")
            
            return True
        else:
            logger.error(f"Failed to get agent: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error checking agent knowledge base: {e}")
        return False

if __name__ == "__main__":
    check_agent_knowledge_base()
