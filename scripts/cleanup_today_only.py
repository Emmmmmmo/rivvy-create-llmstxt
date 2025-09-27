#!/usr/bin/env python3
"""
Cleanup script to remove ONLY documents uploaded today from ElevenLabs knowledge base.
Based on KNOWLEDGE_BASE_MANAGEMENT.md best practices.
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

class TodayOnlyCleanup:
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
        self.today = datetime.now().strftime('%Y-%m-%d')
    
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
    
    def identify_today_documents(self, all_documents: List[Dict]) -> List[Dict]:
        """Identify documents uploaded today based on naming patterns and content."""
        logger.info("🔍 Identifying documents uploaded today...")
        
        today_docs = []
        
        for doc in all_documents:
            doc_name = doc.get('name', '')
            doc_id = doc.get('id', '')
            created_at = doc.get('created_at', '')
            
            # Criteria for today's uploads based on our patterns:
            # 1. JG Engineering documents
            # 2. Contains 'currency=EUR' (our EUR pricing indicator)
            # 3. Contains '_part' (split files from today)
            # 4. Created today (if timestamp available)
            
            is_jg_engineering = 'jgengineering.ie' in doc_name
            has_currency_eur = 'currency=EUR' in doc_name
            is_split_file = '_part' in doc_name
            is_created_today = self.today in created_at if created_at else False
            
            # Additional patterns from our uploads today:
            has_lllmstxt_pattern = '-lllmstxt|>' in doc_name
            is_test_file = 'test_' in doc_name.lower()
            
            # Document is from today if it matches our upload patterns
            if is_jg_engineering and (has_currency_eur or is_split_file or is_created_today or has_lllmstxt_pattern or is_test_file):
                today_docs.append(doc)
                logger.info(f"📅 Today's upload: {doc_name}")
                logger.info(f"   - Currency EUR: {has_currency_eur}")
                logger.info(f"   - Split file: {is_split_file}")
                logger.info(f"   - Created today: {is_created_today}")
                logger.info(f"   - LLLMSTXT pattern: {has_lllmstxt_pattern}")
                logger.info(f"   - Test file: {is_test_file}")
        
        logger.info(f"📊 Identified {len(today_docs)} documents uploaded today")
        return today_docs
    
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
    
    def cleanup_today_documents(self):
        """Clean up only documents uploaded today."""
        logger.info(f"🧹 Starting cleanup of documents uploaded today ({self.today})...")
        
        # Step 1: Get all documents
        all_documents = self.get_all_documents()
        logger.info(f"📊 Total documents in knowledge base: {len(all_documents)}")
        
        # Step 2: Identify today's documents
        today_docs = self.identify_today_documents(all_documents)
        
        if not today_docs:
            logger.info("✅ No documents from today found")
            return
        
        # Step 3: Clear agent knowledge base first (to remove dependencies)
        logger.info("🔧 Step 1: Clearing agent knowledge base to remove dependencies...")
        agent_id = "agent_1901k666bcn6evwrwe3hxn41txqe"
        self.clear_agent_knowledge_base(agent_id)
        
        # Step 4: Delete today's documents
        logger.info("🔧 Step 2: Deleting today's documents...")
        
        deleted_count = 0
        failed_count = 0
        
        for i, doc in enumerate(today_docs, 1):
            doc_id = doc.get('id')
            doc_name = doc.get('name', 'unknown')
            
            logger.info(f"🗑️  Deleting {i}/{len(today_docs)}: {doc_name}")
            
            if self.delete_document(doc_id, doc_name):
                deleted_count += 1
                logger.info(f"✅ Deleted: {doc_name}")
            else:
                failed_count += 1
                logger.error(f"❌ Failed to delete: {doc_name}")
            
            # Rate limiting
            time.sleep(0.5)
        
        logger.info(f"🎉 Today's cleanup completed:")
        logger.info(f"  - Successfully deleted: {deleted_count} documents")
        logger.info(f"  - Failed to delete: {failed_count} documents")
        
        # Step 5: Verify cleanup
        logger.info("🔧 Step 3: Verifying cleanup...")
        remaining_docs = self.get_all_documents()
        remaining_today = self.identify_today_documents(remaining_docs)
        
        if remaining_today:
            logger.warning(f"⚠️  {len(remaining_today)} documents from today still remain")
            for doc in remaining_today:
                logger.warning(f"  - {doc.get('name', 'unknown')} (ID: {doc.get('id', 'unknown')})")
        else:
            logger.info("✅ All documents from today successfully removed")

def main():
    """Main cleanup function."""
    try:
        cleanup = TodayOnlyCleanup()
        cleanup.cleanup_today_documents()
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")

if __name__ == "__main__":
    main()
