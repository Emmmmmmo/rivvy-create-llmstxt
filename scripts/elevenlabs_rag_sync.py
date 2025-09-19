#!/usr/bin/env python3
"""
ElevenLabs RAG Sync Script

This script syncs generated LLMs.txt files to ElevenLabs conversational AI agents.
It reads the configuration from config/elevenlabs-agents.json and uploads files
to the appropriate agents based on domain mapping.
"""

import os
import json
import logging
import requests
import time
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ElevenLabsRAGSync:
    def __init__(self, config_path: str = "config/elevenlabs-agents.json"):
        self.config_path = config_path
        self.api_key = os.getenv('ELEVENLABS_API_KEY')
        self.base_url = "https://api.elevenlabs.io/v1/convai"
        self.config = self._load_config()
        
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
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for ElevenLabs API requests."""
        return {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }
    
    def _get_agent_for_domain(self, domain: str) -> Optional[Dict]:
        """Get agent configuration for a specific domain."""
        agents = self.config.get('agents', {})
        return agents.get(domain)
    
    def _get_llms_files(self, domain_dir: Path) -> List[Path]:
        """Get all LLMs.txt files for a domain."""
        llms_files = []
        for file_path in domain_dir.glob("llms-*.txt"):
            if file_path.is_file():
                llms_files.append(file_path)
        return llms_files
    
    def _check_file_size(self, file_path: Path, max_size_mb: int) -> bool:
        """Check if file size is within limits."""
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        if file_size_mb > max_size_mb:
            logger.warning(f"File {file_path.name} is {file_size_mb:.2f}MB, exceeds limit of {max_size_mb}MB")
            return False
        return True
    
    def _upload_file_to_agent(self, agent_config: Dict, file_path: Path, domain: str) -> bool:
        """Upload a single file to an ElevenLabs agent."""
        agent_id = agent_config['agent_id']
        file_prefix = agent_config.get('file_prefix', domain.replace('.', '_'))
        
        # Create filename with prefix
        filename = f"{file_prefix}_{file_path.name}"
        
        # Check file size
        max_size_mb = agent_config.get('max_file_size_mb', 8)
        if not self._check_file_size(file_path, max_size_mb):
            return False
        
        # Read file content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return False
        
        # Upload to ElevenLabs knowledge base
        upload_url = f"{self.base_url}/knowledge-base/file"
        
        try:
            # Prepare file data for multipart upload
            files = {
                'file': (filename, content, 'text/plain')
            }
            
            # Remove Content-Type from headers for multipart upload
            headers = {"xi-api-key": self.api_key}
            
            response = requests.post(
                upload_url,
                headers=headers,
                files=files,
                timeout=30
            )
            
            if response.status_code == 200:
                # Parse the response to get the document ID
                try:
                    response_data = response.json()
                    document_id = response_data.get('id')
                    if document_id:
                        logger.info(f"Successfully uploaded {filename} to knowledge base (ID: {document_id})")
                        # Link the document to the agent
                        if self._link_document_to_agent(agent_id, document_id):
                            logger.info(f"Successfully linked document {document_id} to agent {agent_id}")
                            return True
                        else:
                            logger.warning(f"Uploaded {filename} but failed to link to agent")
                            return False
                    else:
                        logger.warning(f"Uploaded {filename} but no document ID in response")
                        return False
                except Exception as e:
                    logger.error(f"Error parsing upload response: {e}")
                    return False
            else:
                logger.error(f"Failed to upload {filename}: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error uploading {filename}: {e}")
            return False
    
    def _link_document_to_agent(self, agent_id: str, document_id: str) -> bool:
        """Link a knowledge base document to an agent"""
        try:
            # Get current agent configuration
            get_url = f"{self.base_url}/agents/{agent_id}"
            headers = {"xi-api-key": self.api_key}
            
            response = requests.get(get_url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                logger.error(f"Failed to get agent config: {response.status_code}")
                return False
            
            agent_data = response.json()
            
            # Add document to knowledge base list
            # The knowledge_base field is under conversation_config.agent.prompt
            prompt_config = agent_data.get("conversation_config", {}).get("agent", {}).get("prompt", {})
            knowledge_base = prompt_config.get("knowledge_base", [])
            
            # Check if document is already linked
            document_already_linked = any(
                doc.get("id") == document_id for doc in knowledge_base
            )
            
            if not document_already_linked:
                # Add new document to knowledge base
                new_document = {
                    "type": "file",
                    "name": f"Document {document_id}",
                    "id": document_id,
                    "usage_mode": "prompt"
                }
                knowledge_base.append(new_document)
                
                # Create a minimal update payload to avoid conflicts
                update_payload = {
                    "conversation_config": {
                        "agent": {
                            "prompt": {
                                "knowledge_base": knowledge_base
                            }
                        }
                    }
                }
                
                # Update agent configuration
                update_url = f"{self.base_url}/agents/{agent_id}"
                update_headers = {
                    "xi-api-key": self.api_key,
                    "Content-Type": "application/json"
                }
                
                update_response = requests.patch(
                    update_url,
                    headers=update_headers,
                    json=update_payload,
                    timeout=30
                )
                
                if update_response.status_code == 200:
                    logger.info(f"Successfully linked document {document_id} to agent {agent_id}")
                    return True
                else:
                    logger.error(f"Failed to update agent: {update_response.status_code} - {update_response.text}")
                    return False
            else:
                logger.info(f"Document {document_id} already linked to agent {agent_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error linking document to agent: {e}")
            return False
    
    def sync_domain(self, domain: str) -> bool:
        """Sync all LLMs files for a specific domain."""
        logger.info(f"Starting sync for domain: {domain}")
        
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
        
        # Get domain directory
        domain_dir = Path("out") / domain
        if not domain_dir.exists():
            logger.warning(f"Domain directory not found: {domain_dir}")
            return False
        
        # Get LLMs files
        llms_files = self._get_llms_files(domain_dir)
        if not llms_files:
            logger.warning(f"No LLMs files found for domain: {domain}")
            return False
        
        logger.info(f"Found {len(llms_files)} LLMs files for {domain}")
        
        # Upload files
        success_count = 0
        for file_path in llms_files:
            if self._upload_file_to_agent(agent_config, file_path, domain):
                success_count += 1
            time.sleep(1)  # Rate limiting
        
        logger.info(f"Successfully uploaded {success_count}/{len(llms_files)} files for {domain}")
        
        # Update last sync timestamp
        agent_config['last_sync'] = datetime.now().isoformat()
        self._save_config()
        
        return success_count > 0
    
    def _save_config(self):
        """Save updated configuration."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
    
    def sync_all_domains(self) -> Dict[str, bool]:
        """Sync all configured domains."""
        results = {}
        out_dir = Path("out")
        
        if not out_dir.exists():
            logger.warning("Output directory 'out' not found")
            return results
        
        # Get all domain directories
        for domain_dir in out_dir.iterdir():
            if domain_dir.is_dir():
                domain = domain_dir.name
                results[domain] = self.sync_domain(domain)
        
        return results

def main():
    """Main function to run the sync process."""
    try:
        sync = ElevenLabsRAGSync()
        
        # Check if specific domain provided as argument
        import sys
        if len(sys.argv) > 1:
            domain = sys.argv[1]
            success = sync.sync_domain(domain)
            if success:
                logger.info(f"Sync completed successfully for {domain}")
                exit(0)
            else:
                logger.error(f"Sync failed for {domain}")
                exit(1)
        else:
            # Sync all domains
            results = sync.sync_all_domains()
            
            if not results:
                logger.warning("No domains found to sync")
                exit(0)
            
            success_count = sum(1 for success in results.values() if success)
            total_count = len(results)
            
            logger.info(f"Sync completed: {success_count}/{total_count} domains successful")
            
            if success_count == total_count:
                exit(0)
            else:
                exit(1)
                
    except Exception as e:
        logger.error(f"Sync process failed: {e}")
        exit(1)

if __name__ == "__main__":
    main()
