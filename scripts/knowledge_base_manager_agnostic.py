#!/usr/bin/env python3
"""
Agnostic ElevenLabs Knowledge Base Manager

This script provides a unified interface for managing the ElevenLabs knowledge base
for any configured website. It automatically adapts to different site configurations
and handles domain-specific agent assignments.

Usage:
  python3 scripts/knowledge_base_manager_agnostic.py [command] [options]
  
Commands:
  upload          Upload files to knowledge base
  list            List documents in knowledge base
  remove          Remove documents from knowledge base
  assign          Assign documents to agents
  sync            Sync operations (upload + assign)
  search          Search documents by criteria
  stats           Show knowledge base statistics
  verify-rag      Verify RAG indexing status for documents
  retry-rag       Retry failed RAG indexing

Examples:
  python3 scripts/knowledge_base_manager_agnostic.py upload --domain jgengineering.ie
  python3 scripts/knowledge_base_manager_agnostic.py upload --domain mydiy.ie
  python3 scripts/knowledge_base_manager_agnostic.py list --sort-by created_at --sort-direction asc
  python3 scripts/knowledge_base_manager_agnostic.py remove --date 2025-09-26
  python3 scripts/knowledge_base_manager_agnostic.py assign --domain jgengineering.ie
  python3 scripts/knowledge_base_manager_agnostic.py sync --domain mydiy.ie
"""

import os
import json
import requests
import time
import logging
import sys
import argparse
import hashlib
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from pathlib import Path

# Add the scripts directory to the path to import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from site_config_manager import SiteConfigManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AgnosticElevenLabsKnowledgeBaseManager:
    def __init__(self, config_path: str = "config/elevenlabs-agents.json"):
        self.config_path = config_path
        self.api_key = self._get_api_key()
        self.base_url = "https://api.elevenlabs.io/v1/convai"
        self.headers = {"xi-api-key": self.api_key}
        self.config = self._load_config()
        self.sync_state_file = Path("config/elevenlabs_sync_state.json")
        self.sync_state = self._load_sync_state()
        
        # Initialize site configuration manager
        self.site_config_manager = SiteConfigManager()
        
        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY environment variable is required")
    
    def _get_api_key(self) -> str:
        """Get API key from environment or env.local file."""
        api_key = os.getenv('ELEVENLABS_API_KEY')
        if not api_key:
            try:
                with open('env.local', 'r') as f:
                    for line in f:
                        if line.startswith('ELEVENLABS_API_KEY:'):
                            api_key = line.split(':', 1)[1].strip()
                            break
            except FileNotFoundError:
                pass
        return api_key
    
    def _load_config(self) -> Dict:
        """Load ElevenLabs configuration."""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Config file {self.config_path} not found")
            return {}
    
    def _load_sync_state(self) -> Dict:
        """Load sync state for tracking uploaded files."""
        try:
            if self.sync_state_file.exists():
                with open(self.sync_state_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Error loading sync state: {e}")
        return {}
    
    def _save_sync_state(self):
        """Save sync state to file."""
        try:
            self.sync_state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.sync_state_file, 'w') as f:
                json.dump(self.sync_state, f, indent=2)
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
        # First try to get from site configuration
        elevenlabs_agent = self.site_config_manager.get_elevenlabs_agent(domain)
        if elevenlabs_agent:
            agents = self.config.get('agents', {})
            return agents.get(elevenlabs_agent)
        
        # Fallback to direct domain lookup
        agents = self.config.get('agents', {})
        return agents.get(domain)
    
    def _get_llms_files(self, domain_dir: Path) -> List[Path]:
        """Get all LLMs.txt files for a domain."""
        llms_files = []
        for file_path in domain_dir.glob("llms-*.txt"):
            if file_path.is_file():
                llms_files.append(file_path)
        return sorted(llms_files)
    
    def upload_files(self, domain: str, force: bool = False) -> Dict[str, Any]:
        """Upload LLMs.txt files to ElevenLabs knowledge base for a domain."""
        logger.info(f"Uploading files for domain: {domain}")
        
        # Get agent configuration
        agent_config = self._get_agent_for_domain(domain)
        if not agent_config:
            return {"error": f"No agent configuration found for domain: {domain}"}
        
        agent_id = agent_config.get('agent_id')
        if not agent_id:
            return {"error": f"No agent_id found in configuration for domain: {domain}"}
        
        # Find domain directory
        site_name = domain.replace('www.', '').replace('.', '-')
        domain_dir = Path("out") / site_name
        
        if not domain_dir.exists():
            return {"error": f"Domain directory not found: {domain_dir}"}
        
        # Get LLMs files
        llms_files = self._get_llms_files(domain_dir)
        if not llms_files:
            return {"error": f"No LLMs.txt files found in {domain_dir}"}
        
        # Initialize sync state for domain if not exists
        if domain not in self.sync_state:
            self.sync_state[domain] = {}
        
        uploaded_count = 0
        skipped_count = 0
        error_count = 0
        uploaded_files = []
        
        for file_path in llms_files:
            try:
                # Calculate file hash
                file_hash = self._get_file_hash(file_path)
                if not file_hash:
                    logger.error(f"Failed to calculate hash for {file_path}")
                    error_count += 1
                    continue
                
                # Check if file was already uploaded and hasn't changed
                if not force and domain in self.sync_state:
                    if file_path.name in self.sync_state[domain]:
                        stored_hash = self.sync_state[domain][file_path.name].get('hash')
                        if stored_hash == file_hash:
                            logger.info(f"Skipping unchanged file: {file_path.name}")
                            skipped_count += 1
                            continue
                
                # Upload file
                logger.info(f"Uploading: {file_path.name}")
                
                with open(file_path, 'rb') as f:
                    files = {'file': (file_path.name, f, 'text/plain')}
                    data = {
                        'agent_id': agent_id,
                        'name': file_path.stem  # Use filename without extension as name
                    }
                    
                    response = requests.post(
                        f"{self.base_url}/knowledge-base/upload",
                        headers=self.headers,
                        files=files,
                        data=data
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        document_id = result.get('document_id')
                        
                        # Update sync state
                        if domain not in self.sync_state:
                            self.sync_state[domain] = {}
                        
                        self.sync_state[domain][file_path.name] = {
                            'hash': file_hash,
                            'document_id': document_id,
                            'uploaded_at': datetime.now().isoformat(),
                            'file_size': file_path.stat().st_size
                        }
                        
                        uploaded_files.append({
                            'filename': file_path.name,
                            'document_id': document_id,
                            'size': file_path.stat().st_size
                        })
                        
                        uploaded_count += 1
                        logger.info(f"Successfully uploaded: {file_path.name} (ID: {document_id})")
                        
                    else:
                        logger.error(f"Failed to upload {file_path.name}: {response.status_code} - {response.text}")
                        error_count += 1
                
                # Rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error uploading {file_path.name}: {e}")
                error_count += 1
        
        # Save sync state
        self._save_sync_state()
        
        return {
            "domain": domain,
            "uploaded_count": uploaded_count,
            "skipped_count": skipped_count,
            "error_count": error_count,
            "total_files": len(llms_files),
            "uploaded_files": uploaded_files
        }
    
    def list_documents(self, domain: Optional[str] = None, sort_by: str = "created_at", sort_direction: str = "desc") -> Dict[str, Any]:
        """List documents in the knowledge base."""
        logger.info("Listing documents in knowledge base")
        
        try:
            params = {
                'sort_by': sort_by,
                'sort_direction': sort_direction
            }
            
            response = requests.get(
                f"{self.base_url}/knowledge-base/documents",
                headers=self.headers,
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                documents = data.get('documents', [])
                
                # Filter by domain if specified
                if domain:
                    agent_config = self._get_agent_for_domain(domain)
                    if agent_config:
                        agent_id = agent_config.get('agent_id')
                        documents = [doc for doc in documents if doc.get('agent_id') == agent_id]
                
                return {
                    "total_documents": len(documents),
                    "documents": documents
                }
            else:
                return {"error": f"Failed to list documents: {response.status_code} - {response.text}"}
                
        except Exception as e:
            return {"error": f"Error listing documents: {e}"}
    
    def remove_documents(self, domain: Optional[str] = None, date: Optional[str] = None, document_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Remove documents from knowledge base."""
        if not any([domain, date, document_ids]):
            return {"error": "Must specify domain, date, or document_ids"}
        
        logger.info(f"Removing documents - domain: {domain}, date: {date}, ids: {document_ids}")
        
        # Get documents to remove
        documents_to_remove = []
        
        if document_ids:
            documents_to_remove = document_ids
        else:
            # List documents first to find what to remove
            list_result = self.list_documents(domain)
            if "error" in list_result:
                return list_result
            
            documents = list_result.get("documents", [])
            
            if date:
                # Filter by date
                target_date = datetime.fromisoformat(date.replace('Z', '+00:00'))
                documents_to_remove = [
                    doc['document_id'] for doc in documents
                    if datetime.fromisoformat(doc['created_at'].replace('Z', '+00:00')).date() == target_date.date()
                ]
            elif domain:
                # Remove all documents for domain
                documents_to_remove = [doc['document_id'] for doc in documents]
        
        if not documents_to_remove:
            return {"message": "No documents found to remove"}
        
        # Remove documents
        removed_count = 0
        error_count = 0
        
        for doc_id in documents_to_remove:
            try:
                response = requests.delete(
                    f"{self.base_url}/knowledge-base/documents/{doc_id}",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    removed_count += 1
                    logger.info(f"Removed document: {doc_id}")
                else:
                    error_count += 1
                    logger.error(f"Failed to remove document {doc_id}: {response.status_code} - {response.text}")
                
                time.sleep(0.1)
                
            except Exception as e:
                error_count += 1
                logger.error(f"Error removing document {doc_id}: {e}")
        
        return {
            "removed_count": removed_count,
            "error_count": error_count,
            "total_requested": len(documents_to_remove)
        }
    
    def assign_documents(self, domain: str) -> Dict[str, Any]:
        """Assign documents to agent for a domain."""
        logger.info(f"Assigning documents to agent for domain: {domain}")
        
        # Get agent configuration
        agent_config = self._get_agent_for_domain(domain)
        if not agent_config:
            return {"error": f"No agent configuration found for domain: {domain}"}
        
        agent_id = agent_config.get('agent_id')
        if not agent_id:
            return {"error": f"No agent_id found in configuration for domain: {domain}"}
        
        # List documents for this agent
        list_result = self.list_documents(domain)
        if "error" in list_result:
            return list_result
        
        documents = list_result.get("documents", [])
        if not documents:
            return {"message": f"No documents found for domain: {domain}"}
        
        # Assign documents to agent
        assigned_count = 0
        error_count = 0
        
        for doc in documents:
            try:
                doc_id = doc['document_id']
                
                response = requests.post(
                    f"{self.base_url}/knowledge-base/documents/{doc_id}/assign",
                    headers=self.headers,
                    json={'agent_id': agent_id}
                )
                
                if response.status_code == 200:
                    assigned_count += 1
                    logger.info(f"Assigned document {doc_id} to agent {agent_id}")
                else:
                    error_count += 1
                    logger.error(f"Failed to assign document {doc_id}: {response.status_code} - {response.text}")
                
                time.sleep(0.1)
                
            except Exception as e:
                error_count += 1
                logger.error(f"Error assigning document {doc['document_id']}: {e}")
        
        return {
            "domain": domain,
            "assigned_count": assigned_count,
            "error_count": error_count,
            "total_documents": len(documents)
        }
    
    def sync_domain(self, domain: str, force: bool = False) -> Dict[str, Any]:
        """Sync domain: upload files and assign to agent."""
        logger.info(f"Syncing domain: {domain}")
        
        # Upload files
        upload_result = self.upload_files(domain, force)
        if "error" in upload_result:
            return upload_result
        
        # Wait a bit for processing
        time.sleep(2)
        
        # Assign documents
        assign_result = self.assign_documents(domain)
        if "error" in assign_result:
            return {
                "upload_result": upload_result,
                "assign_error": assign_result["error"]
            }
        
        return {
            "domain": domain,
            "upload_result": upload_result,
            "assign_result": assign_result
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics."""
        logger.info("Getting knowledge base statistics")
        
        try:
            response = requests.get(
                f"{self.base_url}/knowledge-base/stats",
                headers=self.headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Failed to get stats: {response.status_code} - {response.text}"}
                
        except Exception as e:
            return {"error": f"Error getting stats: {e}"}


def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(
        description="Agnostic ElevenLabs Knowledge Base Manager"
    )
    
    # Commands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Upload command
    upload_parser = subparsers.add_parser('upload', help='Upload files to knowledge base')
    upload_parser.add_argument('--domain', required=True, help='Domain to upload files for')
    upload_parser.add_argument('--force', action='store_true', help='Force upload even if file unchanged')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List documents in knowledge base')
    list_parser.add_argument('--domain', help='Filter by domain')
    list_parser.add_argument('--sort-by', default='created_at', help='Sort field')
    list_parser.add_argument('--sort-direction', default='desc', help='Sort direction')
    
    # Remove command
    remove_parser = subparsers.add_parser('remove', help='Remove documents from knowledge base')
    remove_parser.add_argument('--domain', help='Remove all documents for domain')
    remove_parser.add_argument('--date', help='Remove documents from specific date (YYYY-MM-DD)')
    remove_parser.add_argument('--ids', nargs='+', help='Remove specific document IDs')
    
    # Assign command
    assign_parser = subparsers.add_parser('assign', help='Assign documents to agents')
    assign_parser.add_argument('--domain', required=True, help='Domain to assign documents for')
    
    # Sync command
    sync_parser = subparsers.add_parser('sync', help='Sync domain (upload + assign)')
    sync_parser.add_argument('--domain', required=True, help='Domain to sync')
    sync_parser.add_argument('--force', action='store_true', help='Force upload even if file unchanged')
    
    # Stats command
    subparsers.add_parser('stats', help='Show knowledge base statistics')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        manager = AgnosticElevenLabsKnowledgeBaseManager()
        
        if args.command == 'upload':
            result = manager.upload_files(args.domain, args.force)
        elif args.command == 'list':
            result = manager.list_documents(args.domain, args.sort_by, args.sort_direction)
        elif args.command == 'remove':
            result = manager.remove_documents(args.domain, args.date, args.ids)
        elif args.command == 'assign':
            result = manager.assign_documents(args.domain)
        elif args.command == 'sync':
            result = manager.sync_domain(args.domain, args.force)
        elif args.command == 'stats':
            result = manager.get_stats()
        
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        logger.error(f"Command failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
