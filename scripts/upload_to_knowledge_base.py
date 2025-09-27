#!/usr/bin/env python3
"""
ElevenLabs Knowledge Base Upload Script

This script uploads files to the ElevenLabs knowledge base without assigning them to agents.
It tracks upload progress in sync state and can resume from where it left off.

Usage:
  python3 scripts/upload_to_knowledge_base.py [domain] [--force]
"""

import os
import json
import logging
import requests
import time
import hashlib
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

class ElevenLabsUploader:
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
            timeout = 120 if file_size_mb > 1 else 60  # 120 seconds for files > 1MB
            
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
    
    def upload_domain(self, domain: str, force_upload: bool = False) -> bool:
        """Upload all LLMs files for a domain to ElevenLabs knowledge base."""
        logger.info(f"Starting upload for domain: {domain}")
        
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
        
        # Handle force upload - clear sync state
        if force_upload:
            logger.info("Force upload requested - clearing sync state")
            self.sync_state = {}
            self._save_sync_state()
        
        # Track what we need to upload
        files_to_upload = []
        files_already_uploaded = []
        
        # Analyze each local file
        for file_path in llms_files:
            filename = f"{file_prefix}_{file_path.name}"
            current_hash = self._get_file_hash(file_path)
            
            if not current_hash:
                logger.warning(f"Could not calculate hash for {file_path.name}, skipping")
                continue
            
            # Check if file needs uploading
            stored_hash = self.sync_state.get(f"{domain}:{file_path.name}", {}).get('hash', '')
            
            if stored_hash == current_hash and not force_upload:
                # File hasn't changed and is already uploaded
                files_already_uploaded.append((file_path, filename))
                logger.debug(f"Already uploaded: {file_path.name}")
            else:
                # File has changed or is new - need to upload
                files_to_upload.append((file_path, filename))
                logger.info(f"File changed/new, will upload: {file_path.name}")
        
        # Report what we found
        logger.info(f"Upload plan for {domain}:")
        logger.info(f"  - Already uploaded: {len(files_already_uploaded)} files")
        logger.info(f"  - Need to upload: {len(files_to_upload)} files")
        
        if not files_to_upload:
            logger.info(f"No files need uploading for {domain}")
            return True
        
        # Upload files
        uploaded_count = 0
        failed_count = 0
        
        for file_path, filename in files_to_upload:
            logger.info(f"📤 Uploading file: {file_path.name}")
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
                logger.info(f"✅ Uploaded {file_path.name} (ID: {document_id})")
            else:
                failed_count += 1
                logger.error(f"❌ Failed to upload {file_path.name}")
            
            # Small delay between uploads
            time.sleep(1)
        
        # Save sync state
        self._save_sync_state()
        
        # Report results
        logger.info(f"🎉 Upload completed for {domain}:")
        logger.info(f"  - Successfully uploaded: {uploaded_count} files")
        logger.info(f"  - Failed uploads: {failed_count} files")
        logger.info(f"  - Already uploaded: {len(files_already_uploaded)} files")
        logger.info(f"  - Total files in sync state: {len([k for k in self.sync_state.keys() if k.startswith(f'{domain}:')])}")
        
        if uploaded_count > 0:
            logger.info("📝 Next step: Run assignment script to assign uploaded files to agent")
        
        return uploaded_count > 0 or len(files_already_uploaded) > 0
    
    def upload_all_domains(self, force_upload: bool = False) -> Dict[str, bool]:
        """Upload all configured domains."""
        results = {}
        out_dir = Path("out")
        
        if not out_dir.exists():
            logger.warning("Output directory 'out' not found")
            return results
        
        # Get all domain directories
        for domain_dir in out_dir.iterdir():
            if domain_dir.is_dir():
                domain = domain_dir.name
                results[domain] = self.upload_domain(domain, force_upload=force_upload)
        
        return results

def main():
    """Main function to run the upload process."""
    try:
        uploader = ElevenLabsUploader()
        
        # Check command line arguments
        force_upload = '--force' in sys.argv
        
        if len(sys.argv) > 1 and sys.argv[1] != '--force':
            domain = sys.argv[1]
            success = uploader.upload_domain(domain, force_upload=force_upload)
            
            if success:
                logger.info(f"🎉 Upload completed successfully for {domain}")
                exit(0)
            else:
                logger.error(f"❌ Upload failed for {domain}")
                exit(1)
        else:
            # Upload all domains
            results = uploader.upload_all_domains(force_upload=force_upload)
            
            if not results:
                logger.warning("No domains found to upload")
                exit(0)
            
            success_count = sum(1 for success in results.values() if success)
            total_count = len(results)
            
            logger.info(f"Upload completed: {success_count}/{total_count} domains successful")
            
            if success_count == total_count:
                exit(0)
            else:
                exit(1)
                
    except Exception as e:
        logger.error(f"Upload process failed: {e}")
        exit(1)

if __name__ == "__main__":
    main()
