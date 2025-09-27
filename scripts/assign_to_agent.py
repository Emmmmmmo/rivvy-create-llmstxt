#!/usr/bin/env python3
"""
ElevenLabs Agent Assignment Script

This script assigns uploaded documents from the knowledge base to ElevenLabs agents.
It reads the sync state to find successfully uploaded files and assigns them to agents.

Usage:
  python3 scripts/assign_to_agent.py [domain] [--wait-for-indexing]
"""

import os
import json
import logging
import requests
import time
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ElevenLabsAssigner:
    def __init__(self, config_path: str = "config/elevenlabs-agents.json"):
        self.config_path = config_path
        self.api_key = os.getenv('ELEVENLABS_API_KEY')
        self.base_url = "https://api.elevenlabs.io/v1/convai"
        self.config = self._load_config()
        self.sync_state_file = Path("config/elevenlabs_sync_state.json")
        self.sync_state = self._load_sync_state()
        
        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY environment variable is required")
    
    def _load_config(self) -> Dict:
        """Load the ElevenLabs agents configuration."""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            logger.info(f"Loaded configuration from {self.config_path}")
            return config
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {self.config_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in configuration file: {e}")
            raise
    
    def _load_sync_state(self) -> Dict:
        """Load sync state to track uploaded files and their hashes."""
        try:
            if self.sync_state_file.exists():
                with open(self.sync_state_file, 'r') as f:
                    state = json.load(f)
                logger.info(f"Loaded sync state from {self.sync_state_file}")
                return state
            else:
                logger.error("No sync state file found. Run upload script first.")
                return {}
        except Exception as e:
            logger.error(f"Error loading sync state: {e}")
            return {}
    
    def _save_config(self):
        """Save updated configuration."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
    
    def _get_agent_for_domain(self, domain: str) -> Optional[Dict]:
        """Get agent configuration for a specific domain."""
        agents = self.config.get('agents', {})
        return agents.get(domain)
    
    def _get_agent_knowledge_base(self, agent_id: str) -> Tuple[List[Dict], Dict]:
        """Get current knowledge base from ElevenLabs agent and return both docs and full config."""
        try:
            get_url = f"{self.base_url}/agents/{agent_id}"
            headers = {"xi-api-key": self.api_key}
            
            response = requests.get(get_url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                logger.warning(f"Failed to get agent config: {response.status_code}")
                return [], {}
            
            agent_data = response.json()
            prompt_config = agent_data.get("conversation_config", {}).get("agent", {}).get("prompt", {})
            knowledge_base = prompt_config.get("knowledge_base", [])
            
            logger.info(f"Found {len(knowledge_base)} existing documents in agent knowledge base")
            return knowledge_base, agent_data
            
        except Exception as e:
            logger.warning(f"Error getting agent knowledge base: {e}")
            return [], {}
    
    def _check_rag_indexing_status(self, document_id: str, max_wait_time: int = 300) -> bool:
        """Check RAG indexing status for a document."""
        try:
            status_url = f"{self.base_url}/knowledge-base/documents/{document_id}/compute-rag-index"
            headers = {"xi-api-key": self.api_key}
            
            start_time = time.time()
            while time.time() - start_time < max_wait_time:
                response = requests.get(status_url, headers=headers, timeout=10)
                if response.status_code == 200:
                    status_data = response.json()
                    status = status_data.get('status', 'unknown')
                    
                    if status == "SUCCEEDED":
                        logger.debug(f"✅ RAG indexing completed for document {document_id}")
                        return True
                    elif status == "FAILED":
                        logger.warning(f"❌ RAG indexing failed for document {document_id}")
                        return False
                    else:
                        logger.debug(f"🔄 RAG indexing in progress for {document_id}: {status}")
                        time.sleep(10)
                else:
                    logger.debug(f"Cannot check RAG status for {document_id} (HTTP {response.status_code})")
                    time.sleep(10)
            
            logger.warning(f"⏰ RAG indexing check timeout for document {document_id}")
            return False
            
        except Exception as e:
            logger.warning(f"Error checking RAG indexing status for {document_id}: {e}")
            return False
    
    def _verify_agent_assignment(self, agent_id: str, expected_docs: List[Dict]) -> bool:
        """Verify that documents are properly assigned to the agent."""
        logger.info("🔍 Verifying agent assignment...")
        
        try:
            # Get current agent knowledge base
            current_kb, _ = self._get_agent_knowledge_base(agent_id)
            
            # Create sets of expected and actual document IDs
            expected_ids = {doc.get('id') for doc in expected_docs if doc.get('id')}
            actual_ids = {doc.get('id') for doc in current_kb if doc.get('id')}
            
            # Check for missing documents
            missing_ids = expected_ids - actual_ids
            if missing_ids:
                logger.error(f"❌ Missing documents in agent assignment: {missing_ids}")
                return False
            
            # Check for extra documents (not necessarily an error, but worth noting)
            extra_ids = actual_ids - expected_ids
            if extra_ids:
                logger.info(f"ℹ️  Extra documents in agent (not from this sync): {len(extra_ids)} documents")
            
            # Verify all expected documents are present
            assigned_count = len(expected_ids & actual_ids)
            logger.info(f"✅ Verification successful: {assigned_count}/{len(expected_ids)} expected documents assigned")
            
            return True
            
        except Exception as e:
            logger.error(f"Error verifying agent assignment: {e}")
            return False
    
    def _assign_files_to_agent(self, agent_id: str, knowledge_base: List[Dict]) -> bool:
        """Assign files to agent - handles large batches by splitting them."""
        try:
            # If we have more than 15 documents, split into batches
            if len(knowledge_base) > 15:
                logger.info(f"📦 Large batch detected ({len(knowledge_base)} docs). Splitting into smaller batches...")
                return self._assign_files_to_agent_batched(agent_id, knowledge_base)
            
            # For small batches, use the original method
            return self._assign_files_to_agent_single(agent_id, knowledge_base)
                
        except Exception as e:
            logger.error(f"Error assigning documents: {e}")
            return False
    
    def _assign_files_to_agent_batched(self, agent_id: str, knowledge_base: List[Dict]) -> bool:
        """Assign files to agent in batches of 10-15 documents."""
        batch_size = 10
        total_batches = (len(knowledge_base) + batch_size - 1) // batch_size
        
        logger.info(f"🔄 Processing {len(knowledge_base)} documents in {total_batches} batches of {batch_size}")
        
        all_successful = True
        
        for i in range(0, len(knowledge_base), batch_size):
            batch = knowledge_base[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            
            logger.info(f"📦 Processing batch {batch_num}/{total_batches} ({len(batch)} documents)")
            
            if not self._assign_files_to_agent_single(agent_id, batch):
                logger.error(f"❌ Batch {batch_num} failed")
                all_successful = False
            else:
                logger.info(f"✅ Batch {batch_num} successful")
        
        if all_successful:
            logger.info("🎉 All batches processed successfully!")
            return True
        else:
            logger.error("❌ Some batches failed")
            return False
    
    def _assign_files_to_agent_single(self, agent_id: str, knowledge_base: List[Dict]) -> bool:
        """Assign files to agent with a single batch."""
        try:
            update_payload = {
                "conversation_config": {
                    "agent": {
                        "prompt": {
                            "knowledge_base": knowledge_base
                        }
                    }
                }
            }
            
            update_url = f"{self.base_url}/agents/{agent_id}"
            update_headers = {
                "xi-api-key": self.api_key,
                "Content-Type": "application/json"
            }
            
            update_response = requests.patch(
                update_url,
                headers=update_headers,
                json=update_payload,
                timeout=60
            )
            
            if update_response.status_code == 200:
                logger.info(f"✅ Successfully assigned {len(knowledge_base)} documents to agent")
                return True
            else:
                logger.error(f"Failed to assign documents: {update_response.status_code} - {update_response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error assigning documents: {e}")
            return False
    
    def assign_domain(self, domain: str, wait_for_indexing: bool = False) -> bool:
        """Assign uploaded files for a domain to ElevenLabs agent."""
        logger.info(f"Starting assignment for domain: {domain}")
        
        # Get agent configuration
        agent_config = self._get_agent_for_domain(domain)
        if not agent_config:
            logger.warning(f"No agent configuration found for domain: {domain}")
            return False
        
        if not agent_config.get('enabled', False):
            logger.info(f"Agent for domain {domain} is disabled")
            return False
        
        if not agent_config.get('sync_enabled', False):
            logger.info(f"Sync for domain {domain} is disabled")
            return False
        
        # Check if agent ID is configured
        if agent_config.get('agent_id') == 'YOUR_AGENT_ID_HERE':
            logger.error(f"Agent ID not configured for domain {domain}. Please update config/elevenlabs-agents.json")
            return False
        
        agent_id = agent_config['agent_id']
        file_prefix = agent_config.get('file_prefix', domain.replace('.', '_'))
        
        # Filter sync state for this domain
        domain_files = {k: v for k, v in self.sync_state.items() if k.startswith(f'{domain}:')}
        
        if not domain_files:
            logger.warning(f"No uploaded files found for domain {domain} in sync state")
            logger.info("Run upload script first to upload files to knowledge base")
            return False
        
        logger.info(f"Found {len(domain_files)} uploaded files for {domain}")
        
        # Build knowledge base with uploaded files
        knowledge_base = []
        for file_key, file_info in domain_files.items():
            if 'document_id' in file_info:
                # Extract filename from key (remove domain prefix)
                filename = file_key.replace(f'{domain}:', '')
                prefixed_filename = f"{file_prefix}_{filename}"
                
                doc = {
                    "type": "file",
                    "name": prefixed_filename,
                    "id": file_info['document_id'],
                    "usage_mode": "auto"
                }
                knowledge_base.append(doc)
                logger.info(f"📄 Will assign: {prefixed_filename} (ID: {file_info['document_id']})")
        
        if not knowledge_base:
            logger.warning("No valid documents found to assign")
            return False
        
        # Check RAG indexing status if requested
        if wait_for_indexing:
            logger.info("🔍 Checking RAG indexing status for all documents...")
            ready_docs = []
            not_ready_docs = []
            
            for doc in knowledge_base:
                doc_id = doc['id']
                if self._check_rag_indexing_status(doc_id):
                    ready_docs.append(doc)
                else:
                    not_ready_docs.append(doc)
            
            if not_ready_docs:
                logger.warning(f"⚠️  {len(not_ready_docs)} documents are not ready for assignment yet")
                logger.info("You can retry assignment later, or assign without waiting")
                
                if ready_docs:
                    logger.info(f"Assigning {len(ready_docs)} ready documents now...")
                    knowledge_base = ready_docs
                else:
                    logger.error("No documents are ready for assignment")
                    return False
        
        # Get current agent knowledge base
        current_kb, _ = self._get_agent_knowledge_base(agent_id)
        
        # Combine with existing documents (if any)
        final_knowledge_base = current_kb + knowledge_base
        
        logger.info(f"📊 Final knowledge base will have {len(final_knowledge_base)} documents")
        
        # Assign to agent
        logger.info("🎯 Assigning documents to agent...")
        if self._assign_files_to_agent(agent_id, final_knowledge_base):
            logger.info("✅ Documents assigned to agent successfully")
            
            # Verify assignment
            if self._verify_agent_assignment(agent_id, final_knowledge_base):
                logger.info("✅ Assignment verification successful")
                
                # Update last sync timestamp
                agent_config['last_sync'] = datetime.now().isoformat()
                self._save_config()
                
                logger.info(f"🎉 Assignment completed for {domain}:")
                logger.info(f"  - Assigned: {len(knowledge_base)} new documents")
                logger.info(f"  - Total in knowledge base: {len(final_knowledge_base)} documents")
                logger.info(f"  - RAG indexing will happen automatically in the background")
                
                return True
            else:
                logger.error("❌ Assignment verification failed")
                return False
        else:
            logger.error("❌ Failed to assign documents to agent")
            return False
    
    def assign_all_domains(self, wait_for_indexing: bool = False) -> Dict[str, bool]:
        """Assign all configured domains."""
        results = {}
        
        # Get all domains from sync state
        domains = set()
        for key in self.sync_state.keys():
            if ':' in key:
                domain = key.split(':')[0]
                domains.add(domain)
        
        for domain in domains:
            results[domain] = self.assign_domain(domain, wait_for_indexing=wait_for_indexing)
        
        return results

def main():
    """Main function to run the assignment process."""
    try:
        assigner = ElevenLabsAssigner()
        
        # Check command line arguments
        wait_for_indexing = '--wait-for-indexing' in sys.argv
        
        if len(sys.argv) > 1 and sys.argv[1] not in ['--wait-for-indexing']:
            domain = sys.argv[1]
            success = assigner.assign_domain(domain, wait_for_indexing=wait_for_indexing)
            
            if success:
                logger.info(f"🎉 Assignment completed successfully for {domain}")
                exit(0)
            else:
                logger.error(f"❌ Assignment failed for {domain}")
                exit(1)
        else:
            # Assign all domains
            results = assigner.assign_all_domains(wait_for_indexing=wait_for_indexing)
            
            if not results:
                logger.warning("No domains found to assign")
                exit(0)
            
            success_count = sum(1 for success in results.values() if success)
            total_count = len(results)
            
            logger.info(f"Assignment completed: {success_count}/{total_count} domains successful")
            
            if success_count == total_count:
                exit(0)
            else:
                exit(1)
                
    except Exception as e:
        logger.error(f"Assignment process failed: {e}")
        exit(1)

if __name__ == "__main__":
    main()
