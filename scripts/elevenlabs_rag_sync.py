#!/usr/bin/env python3
"""
ElevenLabs RAG Sync Script - Incremental Version

This script syncs generated LLMs.txt files to ElevenLabs conversational AI agents.
It performs incremental updates, preserving existing files and only updating what changed.
"""

import os
import json
import logging
import requests
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
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
                logger.info("No existing sync state found, starting fresh")
                return {}
        except Exception as e:
            logger.warning(f"Error loading sync state: {e}, starting fresh")
            return {}
    
    def _save_sync_state(self):
        """Save sync state to track uploaded files."""
        try:
            self.sync_state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.sync_state_file, 'w') as f:
                json.dump(self.sync_state, f, indent=2)
            logger.debug(f"Saved sync state to {self.sync_state_file}")
        except Exception as e:
            logger.error(f"Error saving sync state: {e}")
    
    def _get_file_hash(self, file_path: Path) -> str:
        """Calculate MD5 hash of file content."""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            return hashlib.md5(content).hexdigest()
        except Exception as e:
            logger.error(f"Error calculating hash for {file_path}: {e}")
            return ""
    
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
    
    def _upload_file_to_knowledge_base(self, file_path: Path, filename: str) -> Optional[str]:
        """Upload a file to ElevenLabs knowledge base and return document ID."""
        # Check file size
        max_size_mb = 8  # Default limit
        if not self._check_file_size(file_path, max_size_mb):
            return None
        
        # Read file content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return None
        
        # Upload to ElevenLabs knowledge base
        upload_url = f"{self.base_url}/knowledge-base/file"
        
        try:
            # Prepare file data for multipart upload
            files = {
                'file': (filename, content, 'text/plain')
            }
            
            headers = {"xi-api-key": self.api_key}
            
            # Use longer timeout for large files
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            timeout = 60 if file_size_mb > 1 else 30  # 60 seconds for files > 1MB
            
            response = requests.post(
                upload_url,
                headers=headers,
                files=files,
                timeout=timeout
            )
            
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    document_id = response_data.get('id')
                    if document_id:
                        logger.info(f"Successfully uploaded {filename} to knowledge base (ID: {document_id})")
                        return document_id
                    else:
                        logger.warning(f"Uploaded {filename} but no document ID in response")
                        return None
                except Exception as e:
                    logger.error(f"Error parsing upload response: {e}")
                    return None
            else:
                logger.error(f"Failed to upload {filename}: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error uploading {filename}: {e}")
            return None
    
    def _update_agent_knowledge_base(self, agent_id: str, knowledge_base: List[Dict], max_retries: int = 3) -> bool:
        """Update the agent's knowledge base with the new list of documents, with retry logic for RAG index issues."""
        for attempt in range(max_retries):
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
                    timeout=30
                )
                
                if update_response.status_code == 200:
                    logger.info(f"Successfully updated agent knowledge base with {len(knowledge_base)} documents")
                    return True
                else:
                    error_text = update_response.text.lower()
                    
                    # Check for RAG index not ready error
                    if "rag_index_not_ready" in error_text:
                        if attempt < max_retries - 1:
                            wait_time = (attempt + 1) * 30  # 30, 60, 90 seconds
                            logger.warning(f"RAG index not ready, waiting {wait_time} seconds before retry {attempt + 2}/{max_retries}")
                            time.sleep(wait_time)
                            continue
                        else:
                            logger.error(f"RAG index still not ready after {max_retries} attempts")
                            return False
                    
                    # Check for size limit errors
                    elif "too large" in error_text or "size" in error_text:
                        logger.warning(f"Knowledge base size limit reached. This shouldn't happen with incremental sync.")
                        return False
                    
                    # Other errors
                    else:
                        logger.error(f"Failed to update agent knowledge base: {update_response.status_code} - {update_response.text}")
                        return False
                        
            except Exception as e:
                logger.error(f"Error updating agent knowledge base (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(10)  # Wait 10 seconds before retry
                    continue
                else:
                    return False
        
        return False
    
    def _clear_knowledge_base(self, agent_id: str) -> bool:
        """Clear all documents from the agent's knowledge base."""
        return self._update_agent_knowledge_base(agent_id, [])
    
    def sync_domain(self, domain: str, force_sync: bool = False) -> bool:
        """Sync all LLMs files for a specific domain with incremental updates."""
        logger.info(f"Starting incremental sync for domain: {domain}")
        
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
        
        # Handle force sync - clear everything and start fresh
        if force_sync:
            logger.info("Force sync requested - clearing knowledge base and starting fresh")
            if not self._clear_knowledge_base(agent_id):
                logger.error("Failed to clear knowledge base for force sync")
                return False
            # Clear sync state
            self.sync_state = {}
            self._save_sync_state()
        
        # Get current knowledge base from ElevenLabs
        current_kb, agent_data = self._get_agent_knowledge_base(agent_id)
        
        # Create a map of current documents by filename (with prefix)
        current_docs_by_name = {}
        for doc in current_kb:
            if isinstance(doc, dict) and 'name' in doc:
                current_docs_by_name[doc['name']] = doc
        
        # Track what we need to do
        files_to_upload = []
        files_to_update = []
        files_to_keep = []
        
        # Analyze each local file
        for file_path in llms_files:
            filename = f"{file_prefix}_{file_path.name}"
            current_hash = self._get_file_hash(file_path)
            
            if not current_hash:
                logger.warning(f"Could not calculate hash for {file_path.name}, skipping")
                continue
            
            # Check if file exists in ElevenLabs
            if filename in current_docs_by_name:
                # File exists - check if it needs updating
                stored_hash = self.sync_state.get(f"{domain}:{file_path.name}", {}).get('hash', '')
                
                if stored_hash == current_hash:
                    # File hasn't changed
                    files_to_keep.append((file_path, filename, current_docs_by_name[filename]))
                    logger.debug(f"Keeping unchanged file: {file_path.name}")
                else:
                    # File has changed - need to update
                    files_to_update.append((file_path, filename, current_docs_by_name[filename]))
                    logger.info(f"File changed, will update: {file_path.name}")
            else:
                # File doesn't exist - need to upload
                files_to_upload.append((file_path, filename))
                logger.info(f"New file, will upload: {file_path.name}")
        
        # Report what we found
        logger.info(f"Sync plan for {domain}:")
        logger.info(f"  - Keep unchanged: {len(files_to_keep)} files")
        logger.info(f"  - Update changed: {len(files_to_update)} files")
        logger.info(f"  - Upload new: {len(files_to_upload)} files")
        
        if not files_to_upload and not files_to_update:
            logger.info(f"No changes needed for {domain}, sync complete")
            return True
        
        # Start building new knowledge base
        new_knowledge_base = []
        
        # Keep unchanged files
        for file_path, filename, existing_doc in files_to_keep:
            new_knowledge_base.append(existing_doc)
        
        # Upload new files
        uploaded_count = 0
        for file_path, filename in files_to_upload:
            logger.info(f"Uploading new file: {file_path.name}")
            document_id = self._upload_file_to_knowledge_base(file_path, filename)
            if document_id:
                new_doc = {
                    "type": "file",
                    "name": filename,
                    "id": document_id,
                    "usage_mode": "auto"
                }
                new_knowledge_base.append(new_doc)
                
                # Update sync state
                file_key = f"{domain}:{file_path.name}"
                self.sync_state[file_key] = {
                    'hash': self._get_file_hash(file_path),
                    'document_id': document_id,
                    'uploaded_at': datetime.now().isoformat()
                }
                uploaded_count += 1
            else:
                logger.error(f"Failed to upload {file_path.name}")
            
            time.sleep(1)  # Rate limiting
        
        # Update changed files
        updated_count = 0
        for file_path, filename, old_doc in files_to_update:
            logger.info(f"Updating changed file: {file_path.name}")
            document_id = self._upload_file_to_knowledge_base(file_path, filename)
            if document_id:
                new_doc = {
                    "type": "file",
                    "name": filename,
                    "id": document_id,
                    "usage_mode": "auto"
                }
                new_knowledge_base.append(new_doc)
                
                # Update sync state
                file_key = f"{domain}:{file_path.name}"
                self.sync_state[file_key] = {
                    'hash': self._get_file_hash(file_path),
                    'document_id': document_id,
                    'uploaded_at': datetime.now().isoformat()
                }
                updated_count += 1
            else:
                logger.error(f"Failed to update {file_path.name}")
                # Keep the old document if update failed
                new_knowledge_base.append(old_doc)
            
            time.sleep(1)  # Rate limiting
        
        # Update the agent's knowledge base with retry logic
        if not self._update_agent_knowledge_base(agent_id, new_knowledge_base):
            logger.error("Failed to update agent knowledge base after retries")
            return False
        
        # Save sync state
        self._save_sync_state()
        
        # Update last sync timestamp
        agent_config['last_sync'] = datetime.now().isoformat()
        self._save_config()
        
        logger.info(f"Sync completed for {domain}:")
        logger.info(f"  - Uploaded: {uploaded_count} new files")
        logger.info(f"  - Updated: {updated_count} changed files")
        logger.info(f"  - Kept: {len(files_to_keep)} unchanged files")
        logger.info(f"  - Total in knowledge base: {len(new_knowledge_base)} files")
        
        return uploaded_count > 0 or updated_count > 0
    
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
            force_sync = '--force' in sys.argv
            success = sync.sync_domain(domain, force_sync=force_sync)
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