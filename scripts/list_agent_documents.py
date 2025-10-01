#!/usr/bin/env python3
"""
List all documents assigned to an agent
"""

import os
import json
import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def list_agent_documents(agent_id: str):
    """List all documents assigned to the agent."""
    
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
        
        logger.info(f"📊 Found {len(knowledge_base)} documents in agent knowledge base")
        logger.info("=" * 80)
        
        # List all documents
        for i, doc in enumerate(knowledge_base, 1):
            if isinstance(doc, dict) and 'name' in doc:
                doc_name = doc['name']
                doc_id = doc.get('id', 'unknown')
                doc_type = doc.get('type', 'unknown')
                usage_mode = doc.get('usage_mode', 'unknown')
                
                logger.info(f"{i:2d}. {doc_name}")
                logger.info(f"    ID: {doc_id}")
                logger.info(f"    Type: {doc_type}, Usage: {usage_mode}")
                logger.info("")
        
        logger.info("=" * 80)
        logger.info(f"✅ Total documents assigned: {len(knowledge_base)}")
        
        return True
            
    except Exception as e:
        logger.error(f"Error listing agent documents: {e}")
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python3 list_agent_documents.py <agent_id>")
        sys.exit(1)
    
    agent_id = sys.argv[1]
    
    success = list_agent_documents(agent_id)
    sys.exit(0 if success else 1)
