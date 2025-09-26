#!/usr/bin/env python3
"""
ElevenLabs RAG Sync Script - Single Phase Approach

This script uploads files directly to the ElevenLabs agent, which triggers
automatic indexing. Uses extended retry logic to handle RAG indexing delays.

Usage:
  python3 scripts/elevenlabs_rag_sync.py [domain] [--force]
"""

import os
import json
import logging
import requests
import time
import hashlib
import sys
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
    
    def _trigger_rag_indexing(self, document_id: str) -> bool:
        """Manually trigger RAG indexing for a document."""
        try:
            index_url = f"{self.base_url}/knowledge-base/documents/{document_id}/compute-rag-index"
            headers = {
                "xi-api-key": self.api_key,
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "e5_mistral_7b_instruct"  # Default embedding model
            }
            
            response = requests.post(index_url, headers=headers, json=payload, timeout=30)
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"Successfully triggered RAG indexing for document {document_id}")
                return True
            else:
                logger.warning(f"Failed to trigger RAG indexing: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.warning(f"Error triggering RAG indexing: {e}")
            return False

    def _check_rag_indexing_status(self, document_id: str, max_wait_time: int = 600) -> bool:
        """Check RAG indexing status for a document with proper polling."""
        start_time = time.time()
        
        # First, try to trigger indexing
        logger.info(f"Triggering RAG indexing for document {document_id}")
        self._trigger_rag_indexing(document_id)
        
        # Then poll for completion
        status_url = f"{self.base_url}/knowledge-base/documents/{document_id}/compute-rag-index"
        headers = {"xi-api-key": self.api_key}
        
        while time.time() - start_time < max_wait_time:
            try:
                response = requests.get(status_url, headers=headers, timeout=10)
                if response.status_code == 200:
                    status_data = response.json()
                    status = status_data.get('status', 'unknown')
                    logger.info(f"RAG indexing status for {document_id}: {status}")
                    
                    if status == "SUCCEEDED":
                        logger.info(f"✅ RAG indexing completed for document {document_id}")
                        return True
                    elif status == "FAILED":
                        logger.error(f"❌ RAG indexing failed for document {document_id}")
                        return False
                    else:
                        # Still processing, wait and check again
                        logger.info(f"🔄 RAG indexing in progress for {document_id}, waiting 30s...")
                        time.sleep(30)
                else:
                    # If status endpoint doesn't work, fall back to time-based waiting
                    logger.info(f"Cannot check RAG status (HTTP {response.status_code}), using time-based waiting")
                    break
            except Exception as e:
                logger.warning(f"Error checking RAG status: {e}, falling back to time-based waiting")
                break
        
        # Fallback: wait a reasonable amount of time and assume it's ready
        elapsed = time.time() - start_time
        if elapsed < 180:  # If we haven't waited at least 3 minutes, wait more
            wait_more = 180 - elapsed
            logger.info(f"Waiting additional {wait_more:.0f} seconds for RAG indexing to complete")
            time.sleep(wait_more)
        
        logger.info(f"Proceeding with assignment after {elapsed + (180 - elapsed if elapsed < 180 else 0):.0f} seconds")
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
    
    def _update_agent_knowledge_base(self, agent_id: str, knowledge_base: List[Dict], max_retries: int = 8) -> bool:
        """Update the agent's knowledge base with extended retry logic for RAG indexing delays."""
        # Progressive retry intervals: 15sec, 45sec, 2min, 5min, 10min, 15min, 20min, 30min (more patient for RAG indexing)
        retry_intervals = [15, 45, 120, 300, 600, 900, 1200, 1800]  # seconds
        
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
                    timeout=60  # Increased timeout for agent updates
                )
                
                if update_response.status_code == 200:
                    logger.info(f"✅ Successfully updated agent knowledge base with {len(knowledge_base)} documents")
                    return True
                else:
                    error_text = update_response.text.lower()
                    logger.warning(f"Agent update failed (attempt {attempt + 1}/{max_retries}): {update_response.status_code}")
                    logger.debug(f"Error response: {update_response.text[:500]}")
                    
                    # Check for RAG index not ready error
                    if "rag_index_not_ready" in error_text or "rag" in error_text:
                        if attempt < max_retries - 1:
                            wait_time = retry_intervals[attempt]
                            if wait_time >= 60:
                                logger.warning(f"🔄 RAG index not ready, waiting {wait_time//60} minutes before retry {attempt + 2}/{max_retries}")
                            else:
                                logger.warning(f"🔄 RAG index not ready, waiting {wait_time} seconds before retry {attempt + 2}/{max_retries}")
                            time.sleep(wait_time)
                            continue
                        else:
                            logger.error(f"❌ RAG index still not ready after {max_retries} attempts ({max_retries * retry_intervals[-1] // 60} total minutes waited)")
                            return False
                    
                    # Check for document not found error
                    elif "knowledge_base_documentation_not_found" in error_text:
                        logger.warning(f"Some documents not found in knowledge base - they may still be indexing")
                        if attempt < max_retries - 1:
                            wait_time = retry_intervals[attempt]
                            if wait_time >= 60:
                                logger.warning(f"Waiting {wait_time//60} minutes for document indexing before retry {attempt + 2}/{max_retries}")
                            else:
                                logger.warning(f"Waiting {wait_time} seconds for document indexing before retry {attempt + 2}/{max_retries}")
                            time.sleep(wait_time)
                            continue
                        else:
                            logger.error(f"Documents still not found after {max_retries} attempts")
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
                    wait_time = retry_intervals[attempt]
                    if wait_time >= 60:
                        logger.warning(f"Waiting {wait_time//60} minutes before retry {attempt + 2}/{max_retries}")
                    else:
                        logger.warning(f"Waiting {wait_time} seconds before retry {attempt + 2}/{max_retries}")
                    time.sleep(wait_time)
                    continue
                else:
                    return False
        
        return False
    
    def _clear_knowledge_base(self, agent_id: str) -> bool:
        """Clear all documents from the agent's knowledge base."""
        return self._update_agent_knowledge_base(agent_id, [])
    
    def _remove_old_document_versions(self, agent_id: str, current_kb: List[Dict], files_to_upload: List[Tuple[Path, str]], file_prefix: str) -> List[Dict]:
        """Remove old versions of files that are being updated to prevent accumulation."""
        logger.info("🧹 Cleaning up old document versions...")
        
        # Create a set of filenames that are being updated
        updated_filenames = set()
        for _, filename in files_to_upload:
            updated_filenames.add(filename)
        
        # Filter out old versions of files being updated
        cleaned_kb = []
        removed_count = 0
        
        for doc in current_kb:
            if isinstance(doc, dict) and 'name' in doc:
                doc_name = doc['name']
                
                # Check if this is an old version of a file being updated
                if doc_name in updated_filenames:
                    logger.info(f"🗑️  Removing old version: {doc_name} (ID: {doc.get('id', 'unknown')})")
                    removed_count += 1
                else:
                    # Keep this document (not being updated)
                    cleaned_kb.append(doc)
        
        if removed_count > 0:
            logger.info(f"✅ Removed {removed_count} old document versions")
        else:
            logger.info("ℹ️  No old versions to remove")
        
        return cleaned_kb
    
    def sync_domain(self, domain: str, force_sync: bool = False) -> bool:
        """Sync all LLMs files for a domain to ElevenLabs agent (single-phase approach)."""
        logger.info(f"Starting single-phase sync for domain: {domain}")
        
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
        
        # Handle force sync - clear sync state and knowledge base
        if force_sync:
            logger.info("Force sync requested - clearing sync state and knowledge base")
            self.sync_state = {}
            self._save_sync_state()
            if not self._clear_knowledge_base(agent_id):
                logger.warning("Failed to clear knowledge base, continuing anyway")
        
        # Get current knowledge base from ElevenLabs
        current_kb, agent_data = self._get_agent_knowledge_base(agent_id)
        
        # Create a map of current documents by filename (with prefix)
        current_docs_by_name = {}
        for doc in current_kb:
            if isinstance(doc, dict) and 'name' in doc:
                current_docs_by_name[doc['name']] = doc
        
        # Track what we need to upload
        files_to_upload = []
        files_to_keep = []
        
        # Analyze each local file
        for file_path in llms_files:
            filename = f"{file_prefix}_{file_path.name}"
            current_hash = self._get_file_hash(file_path)
            
            if not current_hash:
                logger.warning(f"Could not calculate hash for {file_path.name}, skipping")
                continue
            
            # Check if file needs uploading
            stored_hash = self.sync_state.get(f"{domain}:{file_path.name}", {}).get('hash', '')
            
            if stored_hash == current_hash and filename in current_docs_by_name:
                # File hasn't changed and is already assigned
                files_to_keep.append((file_path, filename, current_docs_by_name[filename]))
                logger.debug(f"Keeping unchanged file: {file_path.name}")
            else:
                # File has changed or is new - need to upload
                files_to_upload.append((file_path, filename))
                logger.info(f"File changed/new, will upload: {file_path.name}")
        
        # Report what we found
        logger.info(f"Sync plan for {domain}:")
        logger.info(f"  - Keep unchanged: {len(files_to_keep)} files")
        logger.info(f"  - Upload new/changed: {len(files_to_upload)} files")
        
        if not files_to_upload:
            logger.info(f"No changes needed for {domain}, sync complete")
            return True
        
        # Clean up old versions of files being updated
        cleaned_kb = self._remove_old_document_versions(agent_id, current_kb, files_to_upload, file_prefix)
        
        # Upload and assign files one by one to trigger immediate indexing
        uploaded_count = 0
        assigned_count = 0
        
        for file_path, filename in files_to_upload:
            logger.info(f"Uploading file: {file_path.name}")
            document_id = self._upload_file_to_knowledge_base(file_path, filename)
            if document_id:
                # Update sync state
                file_key = f"{domain}:{file_path.name}"
                self.sync_state[file_key] = {
                    'hash': self._get_file_hash(file_path),
                    'document_id': document_id,
                    'uploaded_at': datetime.now().isoformat()
                }
                uploaded_count += 1
                
                # According to ElevenLabs docs: "indexing happens automatically when document is added to agent with RAG enabled"
                # But we need to wait for the document to be processed before assignment
                logger.info(f"Waiting for document to be processed before assignment: {file_path.name}")
                
                # Wait longer for new documents to be processed by ElevenLabs
                logger.info(f"Waiting 3 minutes for ElevenLabs to process document for RAG indexing...")
                time.sleep(180)  # Wait 3 minutes for document processing
                
                new_doc = {
                    "type": "file",
                    "name": filename,
                    "id": document_id,
                    "usage_mode": "auto"
                }
                
                # Build knowledge base with cleaned files + this new file
                temp_knowledge_base = []
                for _, _, existing_doc in files_to_keep:
                    temp_knowledge_base.append(existing_doc)
                temp_knowledge_base.append(new_doc)
                
                # Try to assign this file to the RAG-enabled agent with extended retry logic
                # The "rag_index_not_ready" error should be resolved after the wait period
                if self._update_agent_knowledge_base(agent_id, temp_knowledge_base, max_retries=6):
                    assigned_count += 1
                    logger.info(f"✅ Successfully assigned {file_path.name} to RAG-enabled agent - indexing will happen automatically")
                else:
                    logger.warning(f"⚠️  Failed to assign {file_path.name} to agent, will retry in final batch")
                
                # Wait a bit between assignments to avoid overwhelming the API
                time.sleep(2)
            else:
                logger.error(f"Failed to upload {file_path.name}")
            
            time.sleep(1)  # Rate limiting between uploads
        
        # Save sync state
        self._save_sync_state()
        
        # Final assignment attempt with all files (including those not ready initially)
        if assigned_count < uploaded_count:
            remaining_files = uploaded_count - assigned_count
            logger.info(f"Performing final assignment attempt for {remaining_files} remaining files")
            logger.info("Waiting additional time for ElevenLabs to process documents for RAG indexing...")
            
            # Give ElevenLabs more time to process the documents internally
            time.sleep(120)  # Wait 2 minutes for background processing
            
            # Build complete knowledge base
            final_knowledge_base = []
            
            # Add kept files
            for file_path, filename, existing_doc in files_to_keep:
                final_knowledge_base.append(existing_doc)
            
            # Add all uploaded documents to final knowledge base
            for file_path, filename in files_to_upload:
                file_key = f"{domain}:{file_path.name}"
                if file_key in self.sync_state:
                    document_id = self.sync_state[file_key].get('document_id')
                    if document_id:
                        new_doc = {
                            "type": "file",
                            "name": filename,
                            "id": document_id,
                            "usage_mode": "auto"
                        }
                        final_knowledge_base.append(new_doc)
            
            # Final assignment attempt with extended retry logic
            logger.info(f"Attempting final assignment of {len(final_knowledge_base)} total documents")
            if self._update_agent_knowledge_base(agent_id, final_knowledge_base):
                assigned_count = uploaded_count
                logger.info("Final assignment attempt successful - all documents now assigned to agent")
            else:
                logger.warning(f"Final assignment attempt failed, {remaining_files} files may not be assigned to agent")
                logger.warning("Documents are uploaded to knowledge base but may need manual assignment in ElevenLabs dashboard")
        
        # Update last sync timestamp
        agent_config['last_sync'] = datetime.now().isoformat()
        self._save_config()
        
        logger.info(f"Sync completed for {domain}:")
        logger.info(f"  - Uploaded: {uploaded_count} files")
        logger.info(f"  - Assigned to agent: {assigned_count} files")
        logger.info(f"  - Total in knowledge base: {len(files_to_keep) + uploaded_count} files")
        
        return uploaded_count > 0
    
    def _save_config(self):
        """Save updated configuration."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
    
    def sync_all_domains(self, force_sync: bool = False) -> Dict[str, bool]:
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
                results[domain] = self.sync_domain(domain, force_sync=force_sync)
        
        return results

def main():
    """Main function to run the sync process."""
    try:
        sync = ElevenLabsRAGSync()
        
        # Check command line arguments
        force_sync = '--force' in sys.argv
        
        if len(sys.argv) > 1 and sys.argv[1] != '--force':
            domain = sys.argv[1]
            success = sync.sync_domain(domain, force_sync=force_sync)
            
            if success:
                logger.info(f"Sync completed successfully for {domain}")
                exit(0)
            else:
                logger.error(f"Sync failed for {domain}")
                exit(1)
        else:
            # Sync all domains
            results = sync.sync_all_domains(force_sync=force_sync)
            
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