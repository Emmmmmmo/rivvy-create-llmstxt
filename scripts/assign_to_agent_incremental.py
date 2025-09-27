#!/usr/bin/env python3
"""
Incremental ElevenLabs Agent Assignment Script

This script assigns uploaded documents to ElevenLabs agents in small batches,
preserving existing knowledge base documents to avoid hitting API limits.

Usage:
  python3 scripts/assign_to_agent_incremental.py [domain] [--batch-size N]
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

class IncrementalElevenLabsAssigner:
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
    
    def _load_sync_state(self) -> Dict:
        """Load the sync state from the JSON file."""
        try:
            with open(self.sync_state_file, 'r') as f:
                state = json.load(f)
            logger.info(f"Loaded sync state from {self.sync_state_file}")
            return state
        except FileNotFoundError:
            logger.warning(f"Sync state file not found: {self.sync_state_file}")
            return {}
    
    def _save_config(self):
        """Save the configuration back to the file."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"Saved configuration to {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
    
    def _get_agent_for_domain(self, domain: str) -> Optional[Dict]:
        """Get agent configuration for a domain."""
        return self.config.get('agents', {}).get(domain)
    
    def _get_agent_knowledge_base(self, agent_id: str) -> List[Dict]:
        """Get current knowledge base from ElevenLabs agent."""
        try:
            get_url = f"{self.base_url}/agents/{agent_id}"
            headers = {"xi-api-key": self.api_key}
            
            response = requests.get(get_url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                logger.warning(f"Failed to get agent config: {response.status_code}")
                return []
            
            agent_data = response.json()
            prompt_config = agent_data.get("conversation_config", {}).get("agent", {}).get("prompt", {})
            knowledge_base = prompt_config.get("knowledge_base", [])
            
            return knowledge_base
            
        except Exception as e:
            logger.warning(f"Error getting agent knowledge base: {e}")
            return []
    
    def _update_agent_knowledge_base(self, agent_id: str, knowledge_base: List[Dict]) -> bool:
        """Update agent's knowledge base."""
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
                return True
            else:
                logger.error(f"Failed to update agent: {update_response.status_code} - {update_response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating agent: {e}")
            return False
    
    def assign_domain_incremental(self, domain: str, batch_size: int = 5) -> bool:
        """Assign uploaded files for a domain to ElevenLabs agent in incremental batches."""
        logger.info(f"Starting incremental assignment for domain: {domain}")
        
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
        
        # Build list of documents to assign
        documents_to_assign = []
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
                documents_to_assign.append(doc)
        
        if not documents_to_assign:
            logger.warning("No valid documents found to assign")
            return False
        
        logger.info(f"Will assign {len(documents_to_assign)} documents in batches of {batch_size}")
        
        # Get current knowledge base
        current_kb = self._get_agent_knowledge_base(agent_id)
        logger.info(f"Current knowledge base has {len(current_kb)} documents")
        
        # Get existing document IDs to avoid duplicates
        existing_ids = {doc.get('id') for doc in current_kb if doc.get('id')}
        
        # Filter out documents that are already assigned
        new_documents = [doc for doc in documents_to_assign if doc.get('id') not in existing_ids]
        
        if not new_documents:
            logger.info("All documents are already assigned to the agent")
            return True
        
        logger.info(f"Found {len(new_documents)} new documents to assign")
        
        # Assign documents in batches
        total_assigned = 0
        total_batches = (len(new_documents) + batch_size - 1) // batch_size
        
        for i in range(0, len(new_documents), batch_size):
            batch = new_documents[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            
            logger.info(f"📦 Processing batch {batch_num}/{total_batches} ({len(batch)} documents)")
            
            # Get current knowledge base (it may have grown from previous batches)
            current_kb = self._get_agent_knowledge_base(agent_id)
            
            # Combine with new batch
            combined_kb = current_kb + batch
            
            logger.info(f"  - Current KB: {len(current_kb)} documents")
            logger.info(f"  - Adding: {len(batch)} documents")
            logger.info(f"  - Final KB: {len(combined_kb)} documents")
            
            # Update agent
            if self._update_agent_knowledge_base(agent_id, combined_kb):
                total_assigned += len(batch)
                logger.info(f"✅ Batch {batch_num} successful - {len(batch)} documents assigned")
                
                # Wait a moment between batches to avoid rate limiting
                if batch_num < total_batches:
                    logger.info("⏳ Waiting 2 seconds before next batch...")
                    time.sleep(2)
            else:
                logger.error(f"❌ Batch {batch_num} failed")
                return False
        
        # Final verification
        final_kb = self._get_agent_knowledge_base(agent_id)
        logger.info(f"🎉 Assignment completed!")
        logger.info(f"  - Documents assigned: {total_assigned}")
        logger.info(f"  - Total in knowledge base: {len(final_kb)}")
        
        # Update last sync timestamp
        agent_config['last_sync'] = datetime.now().isoformat()
        self._save_config()
        
        return True
    
    def assign_all_domains_incremental(self, batch_size: int = 5) -> Dict[str, bool]:
        """Assign documents for all enabled domains."""
        results = {}
        
        for domain, agent_config in self.config.get('agents', {}).items():
            if agent_config.get('enabled', False) and agent_config.get('sync_enabled', False):
                logger.info(f"Processing domain: {domain}")
                success = self.assign_domain_incremental(domain, batch_size)
                results[domain] = success
            else:
                logger.info(f"Skipping domain {domain} (disabled)")
                results[domain] = False
        
        return results

def main():
    """Main function to run the incremental assignment process."""
    try:
        assigner = IncrementalElevenLabsAssigner()
        
        # Parse command line arguments
        batch_size = 5  # Default batch size
        domain = None
        
        for arg in sys.argv[1:]:
            if arg.startswith('--batch-size='):
                batch_size = int(arg.split('=')[1])
            elif not arg.startswith('--'):
                domain = arg
        
        if domain:
            success = assigner.assign_domain_incremental(domain, batch_size)
            
            if success:
                logger.info(f"🎉 Incremental assignment completed successfully for {domain}")
                exit(0)
            else:
                logger.error(f"❌ Incremental assignment failed for {domain}")
                exit(1)
        else:
            # Assign all domains
            results = assigner.assign_all_domains_incremental(batch_size)
            
            if not results:
                logger.warning("No domains found to assign")
                exit(0)
            
            success_count = sum(1 for success in results.values() if success)
            total_count = len(results)
            
            logger.info(f"Incremental assignment completed: {success_count}/{total_count} domains successful")
            
            if success_count == total_count:
                exit(0)
            else:
                exit(1)
                
    except Exception as e:
        logger.error(f"Incremental assignment process failed: {e}")
        exit(1)

if __name__ == "__main__":
    main()
