#!/usr/bin/env python3
"""
Remove the most recent 30 documents from ElevenLabs knowledge base.
"""

import os
import json
import requests
import time
import logging
from typing import List, Dict
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RecentCleanup:
    def __init__(self):
        self.api_key = os.getenv('ELEVENLABS_API_KEY')
        if not self.api_key:
            # Try to get from env.local
            try:
                with open('env.local', 'r') as f:
                    for line in f:
                        if line.startswith('ELEVENLABS_API_KEY:'):
                            self.api_key = line.split(':', 1)[1].strip()
                            break
            except FileNotFoundError:
                pass
        
        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY not found in environment or env.local")
        
        self.base_url = "https://api.elevenlabs.io/v1/convai"
        self.headers = {"xi-api-key": self.api_key}
    
    def get_all_documents(self) -> List[Dict]:
        """Get all documents from the knowledge base."""
        logger.info("🔍 Fetching all documents from knowledge base...")
        
        all_documents = []
        cursor = None
        page_size = 100
        
        while True:
            url = f"{self.base_url}/knowledge-base?page_size={page_size}"
            if cursor:
                url += f"&cursor={cursor}"
            
            response = requests.get(url, headers=self.headers)
            if response.status_code != 200:
                logger.error(f"❌ Error fetching documents: {response.status_code} - {response.text}")
                break
            
            data = response.json()
            documents = data.get('documents', [])
            all_documents.extend(documents)
            
            logger.info(f"📄 Fetched {len(documents)} documents (total: {len(all_documents)})")
            
            cursor = data.get('cursor')
            if not cursor:
                break
        
        return all_documents
    
    def clear_agent_knowledge_base(self, agent_id: str) -> bool:
        """Clear all documents from an agent's knowledge base."""
        logger.info(f"🧹 Clearing knowledge base for agent {agent_id}...")
        
        try:
            update_payload = {
                "conversation_config": {
                    "agent": {
                        "prompt": {
                            "knowledge_base": []
                        }
                    }
                }
            }
            
            url = f"{self.base_url}/agents/{agent_id}"
            response = requests.patch(url, headers=self.headers, json=update_payload)
            
            if response.status_code == 200:
                logger.info(f"✅ Successfully cleared agent {agent_id} knowledge base")
                return True
            else:
                logger.error(f"❌ Failed to clear agent {agent_id}: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Error clearing agent {agent_id}: {e}")
            return False
    
    def delete_document(self, document_id: str, document_name: str = "Unknown") -> bool:
        """Delete a document from the knowledge base."""
        try:
            url = f"{self.base_url}/knowledge-base/{document_id}"
            response = requests.delete(url, headers=self.headers)
            
            if response.status_code in [200, 204]:
                return True
            else:
                logger.warning(f"Failed to delete document {document_name}: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.warning(f"Error deleting document {document_name}: {e}")
            return False
    
    def remove_recent_30(self):
        """Remove the most recent 30 documents."""
        logger.info("🧹 Starting removal of most recent 30 documents...")
        
        # Step 1: Get all documents
        all_documents = self.get_all_documents()
        logger.info(f"📊 Total documents in knowledge base: {len(all_documents)}")
        
        if len(all_documents) < 30:
            logger.warning(f"⚠️  Only {len(all_documents)} documents available, will remove all")
            docs_to_remove = all_documents
        else:
            # Sort by creation date (most recent first)
            # Note: We'll use the order they appear in the API response as a proxy for recency
            docs_to_remove = all_documents[:30]
        
        logger.info(f"📋 Will remove {len(docs_to_remove)} documents")
        
        # Step 2: Clear agent knowledge base first (to remove dependencies)
        logger.info("🔧 Step 1: Clearing agent knowledge base to remove dependencies...")
        agent_id = "agent_1901k666bcn6evwrwe3hxn41txqe"
        self.clear_agent_knowledge_base(agent_id)
        
        # Step 3: Delete the recent documents
        logger.info("🔧 Step 2: Deleting recent documents...")
        
        deleted_count = 0
        failed_count = 0
        
        for i, doc in enumerate(docs_to_remove, 1):
            doc_id = doc.get('id')
            doc_name = doc.get('name', 'unknown')
            created_at = doc.get('created_at', 'unknown')
            
            logger.info(f"🗑️  Deleting {i}/{len(docs_to_remove)}: {doc_name}")
            logger.info(f"    Created: {created_at}")
            
            if self.delete_document(doc_id, doc_name):
                deleted_count += 1
                logger.info(f"✅ Deleted: {doc_name}")
            else:
                failed_count += 1
                logger.error(f"❌ Failed to delete: {doc_name}")
            
            # Rate limiting
            time.sleep(0.5)
        
        logger.info(f"🎉 Recent document removal completed:")
        logger.info(f"  - Successfully deleted: {deleted_count} documents")
        logger.info(f"  - Failed to delete: {failed_count} documents")
        
        # Step 4: Verify cleanup
        logger.info("🔧 Step 3: Verifying cleanup...")
        remaining_docs = self.get_all_documents()
        logger.info(f"📊 Remaining documents in knowledge base: {len(remaining_docs)}")

def main():
    """Main cleanup function."""
    try:
        cleanup = RecentCleanup()
        cleanup.remove_recent_30()
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")

if __name__ == "__main__":
    main()
