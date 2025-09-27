#!/usr/bin/env python3
"""
Complete cleanup script to remove ALL documents from ElevenLabs knowledge base.
This will clear ALL agents first, then delete ALL documents.
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

class CompleteCleanup:
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
    
    def get_all_agents(self) -> List[Dict]:
        """Get all agents."""
        logger.info("🔍 Fetching all agents...")
        
        try:
            url = f"{self.base_url}/agents"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                agents = data.get('agents', [])
                logger.info(f"📊 Found {len(agents)} agents")
                return agents
            else:
                logger.error(f"❌ Error fetching agents: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            logger.error(f"❌ Error fetching agents: {e}")
            return []
    
    def clear_agent_knowledge_base(self, agent_id: str, agent_name: str = "Unknown") -> bool:
        """Clear all documents from an agent's knowledge base."""
        logger.info(f"🧹 Clearing knowledge base for agent {agent_name} ({agent_id})...")
        
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
                logger.info(f"✅ Successfully cleared agent {agent_name}")
                return True
            else:
                logger.error(f"❌ Failed to clear agent {agent_name}: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Error clearing agent {agent_name}: {e}")
            return False
    
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
    
    def complete_cleanup(self):
        """Complete cleanup of all documents and agents."""
        logger.info("🧹 Starting complete cleanup of ElevenLabs knowledge base...")
        
        # Step 1: Clear all agents
        logger.info("🔧 Step 1: Clearing all agents...")
        agents = self.get_all_agents()
        
        cleared_agents = 0
        for agent in agents:
            agent_id = agent.get('id')
            agent_name = agent.get('name', 'Unknown')
            
            if self.clear_agent_knowledge_base(agent_id, agent_name):
                cleared_agents += 1
            
            time.sleep(0.5)  # Rate limiting
        
        logger.info(f"✅ Cleared {cleared_agents}/{len(agents)} agents")
        
        # Step 2: Delete all documents
        logger.info("🔧 Step 2: Deleting all documents...")
        all_documents = self.get_all_documents()
        
        if not all_documents:
            logger.info("✅ No documents found to delete")
            return
        
        deleted_count = 0
        failed_count = 0
        
        for i, doc in enumerate(all_documents, 1):
            doc_id = doc.get('id')
            doc_name = doc.get('name', 'unknown')
            
            logger.info(f"🗑️  Deleting {i}/{len(all_documents)}: {doc_name}")
            
            if self.delete_document(doc_id, doc_name):
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
        
        if remaining_docs:
            logger.warning(f"⚠️  {len(remaining_docs)} documents still remain")
            for doc in remaining_docs[:10]:  # Show first 10
                logger.warning(f"  - {doc.get('name', 'unknown')} (ID: {doc.get('id', 'unknown')})")
            if len(remaining_docs) > 10:
                logger.warning(f"  ... and {len(remaining_docs) - 10} more")
        else:
            logger.info("✅ All documents successfully removed")

def main():
    """Main cleanup function."""
    try:
        cleanup = CompleteCleanup()
        cleanup.complete_cleanup()
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")

if __name__ == "__main__":
    main()
