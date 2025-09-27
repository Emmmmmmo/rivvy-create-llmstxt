#!/usr/bin/env python3
"""
Cleanup script to remove all documents uploaded today from ElevenLabs knowledge base.
This includes removing documents from agents first, then deleting from knowledge base.
"""

import os
import json
import requests
import time
import logging
from typing import List, Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ElevenLabsCleanup:
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
    
    def get_agent_knowledge_base(self, agent_id: str) -> List[Dict]:
        """Get current knowledge base from an agent."""
        try:
            url = f"{self.base_url}/agents/{agent_id}"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                kb = data.get("conversation_config", {}).get("agent", {}).get("prompt", {}).get("knowledge_base", [])
                return kb
            else:
                logger.warning(f"Failed to get agent {agent_id}: {response.status_code}")
                return []
        except Exception as e:
            logger.warning(f"Error getting agent knowledge base: {e}")
            return []
    
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
    
    def delete_document(self, document_id: str) -> bool:
        """Delete a document from the knowledge base."""
        try:
            url = f"{self.base_url}/knowledge-base/{document_id}"
            response = requests.delete(url, headers=self.headers)
            
            if response.status_code in [200, 204]:
                return True
            else:
                logger.warning(f"Failed to delete document {document_id}: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.warning(f"Error deleting document {document_id}: {e}")
            return False
    
    def cleanup_jgengineering_documents(self):
        """Clean up all JG Engineering documents."""
        logger.info("🧹 Starting cleanup of JG Engineering documents...")
        
        # Get all documents
        all_documents = self.get_all_documents()
        logger.info(f"📊 Total documents in knowledge base: {len(all_documents)}")
        
        # Filter for JG Engineering documents
        jg_docs = [doc for doc in all_documents if 'jgengineering.ie' in doc.get('name', '')]
        logger.info(f"📊 JG Engineering documents found: {len(jg_docs)}")
        
        if not jg_docs:
            logger.info("✅ No JG Engineering documents found")
            return
        
        # Step 1: Clear agent knowledge base first
        agent_id = "agent_1901k666bcn6evwrwe3hxn41txqe"
        logger.info("🔧 Step 1: Clearing agent knowledge base...")
        self.clear_agent_knowledge_base(agent_id)
        
        # Step 2: Delete documents from knowledge base
        logger.info("🔧 Step 2: Deleting documents from knowledge base...")
        
        deleted_count = 0
        failed_count = 0
        
        for i, doc in enumerate(jg_docs, 1):
            doc_id = doc.get('id')
            doc_name = doc.get('name', 'unknown')
            
            logger.info(f"🗑️  Deleting {i}/{len(jg_docs)}: {doc_name}")
            
            if self.delete_document(doc_id):
                deleted_count += 1
                logger.info(f"✅ Deleted: {doc_name}")
            else:
                failed_count += 1
                logger.error(f"❌ Failed to delete: {doc_name}")
            
            # Rate limiting
            time.sleep(0.5)
        
        logger.info(f"🎉 Cleanup completed:")
        logger.info(f"  - Successfully deleted: {deleted_count} documents")
        logger.info(f"  - Failed to delete: {failed_count} documents")
        
        # Step 3: Verify cleanup
        logger.info("🔧 Step 3: Verifying cleanup...")
        remaining_docs = self.get_all_documents()
        remaining_jg = [doc for doc in remaining_docs if 'jgengineering.ie' in doc.get('name', '')]
        
        if remaining_jg:
            logger.warning(f"⚠️  {len(remaining_jg)} JG Engineering documents still remain")
            for doc in remaining_jg:
                logger.warning(f"  - {doc.get('name', 'unknown')} (ID: {doc.get('id', 'unknown')})")
        else:
            logger.info("✅ All JG Engineering documents successfully removed")

def main():
    """Main cleanup function."""
    try:
        cleanup = ElevenLabsCleanup()
        cleanup.cleanup_jgengineering_documents()
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")

if __name__ == "__main__":
    main()
