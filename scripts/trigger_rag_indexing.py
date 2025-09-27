#!/usr/bin/env python3
"""
Script to trigger RAG indexing for documents before assigning them to the agent.
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

def trigger_rag_indexing():
    """Trigger RAG indexing for all documents in the knowledge base."""
    
    # Get API key
    api_key = os.getenv('ELEVENLABS_API_KEY')
    if not api_key:
        logger.error("ELEVENLABS_API_KEY environment variable is required")
        return
    
    # Load sync state
    sync_state_file = Path("config/elevenlabs_sync_state.json")
    with open(sync_state_file, 'r') as f:
        sync_state = json.load(f)
    
    # Find all documents that have document_ids
    documents_to_index = []
    for key, info in sync_state.items():
        if key.startswith('jgengineering.ie:') and 'document_id' in info:
            documents_to_index.append({
                'document_id': info['document_id'],
                'filename': key.replace('jgengineering.ie:', '')
            })
    
    if not documents_to_index:
        logger.info("No documents found to index")
        return
    
    logger.info(f"Found {len(documents_to_index)} documents to trigger RAG indexing for")
    
    # Trigger RAG indexing for each document
    base_url = "https://api.elevenlabs.io/v1/convai"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json"
    }
    
    success_count = 0
    failed_count = 0
    
    for doc in documents_to_index:
        document_id = doc['document_id']
        filename = doc['filename']
        
        logger.info(f"🔄 Triggering RAG indexing for {filename} (ID: {document_id})")
        
        try:
            # Trigger RAG indexing
            rag_url = f"{base_url}/knowledge-base/{document_id}/rag-index"
            rag_payload = {
                "model": "e5_mistral_7b_instruct"
            }
            
            response = requests.post(
                rag_url,
                headers=headers,
                json=rag_payload,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Successfully triggered RAG indexing for {filename}")
                success_count += 1
            else:
                logger.error(f"❌ Failed to trigger RAG indexing for {filename}: {response.status_code} - {response.text}")
                failed_count += 1
                
        except Exception as e:
            logger.error(f"❌ Error triggering RAG indexing for {filename}: {e}")
            failed_count += 1
    
    logger.info(f"🎉 RAG indexing trigger completed:")
    logger.info(f"  - Successfully triggered: {success_count} documents")
    logger.info(f"  - Failed: {failed_count} documents")
    
    if success_count > 0:
        logger.info("⏳ RAG indexing is now in progress. Wait a few minutes before attempting assignment.")

if __name__ == "__main__":
    trigger_rag_indexing()
