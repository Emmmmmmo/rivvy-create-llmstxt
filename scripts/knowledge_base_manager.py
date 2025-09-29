#!/usr/bin/env python3
"""
Comprehensive ElevenLabs Knowledge Base Manager

This script provides a unified interface for managing the ElevenLabs knowledge base:
- Upload files to knowledge base
- List and search documents
- Remove documents by date, ID, or criteria
- Assign documents to agents
- Manage sync state for incremental operations

Usage:
  python3 scripts/knowledge_base_manager.py [command] [options]
  
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
  python3 scripts/knowledge_base_manager.py upload --domain jgengineering.ie
  python3 scripts/knowledge_base_manager.py list --sort-by created_at --sort-direction asc
  python3 scripts/knowledge_base_manager.py remove --date 2025-09-26
  python3 scripts/knowledge_base_manager.py remove --id ZHGZEEMgWq81Cy8Lx7Un
  python3 scripts/knowledge_base_manager.py assign --domain jgengineering.ie
  python3 scripts/knowledge_base_manager.py sync --domain jgengineering.ie
  python3 scripts/knowledge_base_manager.py search --name "helicoil"
  python3 scripts/knowledge_base_manager.py stats
  python3 scripts/knowledge_base_manager.py verify-rag
  python3 scripts/knowledge_base_manager.py retry-rag --document-ids doc1 doc2
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ElevenLabsKnowledgeBaseManager:
    def __init__(self, config_path: str = "config/elevenlabs-agents.json"):
        self.config_path = config_path
        self.api_key = self._get_api_key()
        self.base_url = "https://api.elevenlabs.io/v1/convai"
        self.headers = {"xi-api-key": self.api_key}
        self.config = self._load_config()
        self.sync_state_file = Path("config/elevenlabs_sync_state.json")
        self.sync_state = self._load_sync_state()
        
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
            logger.warning(f"Could not load sync state: {e}")
        return {}
    
    def _save_sync_state(self):
        """Save sync state to file."""
        try:
            self.sync_state_file.parent.mkdir(exist_ok=True)
            with open(self.sync_state_file, 'w') as f:
                json.dump(self.sync_state, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save sync state: {e}")
    
    def _get_file_hash(self, file_path: Path) -> str:
        """Calculate MD5 hash of file content."""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.error(f"Error calculating hash for {file_path}: {e}")
            return ""
    
    def upload_files(self, domain: str, force_upload: bool = False) -> bool:
        """Upload files from a domain to the knowledge base."""
        logger.info(f"🚀 Starting upload for domain: {domain}")
        
        domain_path = Path(f"out/{domain}")
        if not domain_path.exists():
            logger.error(f"Domain path not found: {domain_path}")
            return False
        
        # Get all .txt files
        txt_files = list(domain_path.glob("*.txt"))
        logger.info(f"📁 Found {len(txt_files)} .txt files in {domain}")
        
        uploaded_count = 0
        skipped_count = 0
        error_count = 0
        
        for file_path in txt_files:
            file_key = f"{domain}:{file_path.name}"
            current_hash = self._get_file_hash(file_path)
            
            # Check if file already uploaded and unchanged
            if not force_upload and file_key in self.sync_state:
                existing_hash = self.sync_state[file_key].get('hash', '')
                if existing_hash == current_hash:
                    logger.info(f"⏭️  Skipping unchanged file: {file_path.name}")
                    skipped_count += 1
                    continue
            
            # Upload file
            document_id = self._upload_file_to_knowledge_base(file_path, file_path.name)
            if document_id:
                # Update sync state with full document info
                self.sync_state[file_key] = {
                    'hash': current_hash,
                    'document_id': document_id,
                    'document_name': file_path.name,
                    'document_type': 'file',  # ElevenLabs expects 'file' or 'url'
                    'uploaded_at': datetime.now().isoformat()
                }
                uploaded_count += 1
                logger.info(f"✅ Uploaded: {file_path.name} -> {document_id}")
            else:
                error_count += 1
                logger.error(f"❌ Failed to upload: {file_path.name}")
            
            # Rate limiting
            time.sleep(0.5)
        
        # Save sync state
        self._save_sync_state()
        
        logger.info(f"🎉 Upload completed:")
        logger.info(f"  - Uploaded: {uploaded_count} files")
        logger.info(f"  - Skipped: {skipped_count} files")
        logger.info(f"  - Errors: {error_count} files")
        
        return uploaded_count > 0
    
    def _upload_file_to_knowledge_base(self, file_path: Path, filename: str) -> Optional[str]:
        """Upload a single file to the knowledge base."""
        try:
            # Check file size (max 10MB)
            file_size = file_path.stat().st_size
            if file_size > 10 * 1024 * 1024:
                logger.error(f"File too large: {filename} ({file_size} bytes)")
                return None
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Prepare upload data
            files = {
                'file': (filename, content, 'text/plain')
            }
            
            upload_url = f"{self.base_url}/knowledge-base/file"
            response = requests.post(upload_url, headers=self.headers, files=files)
            
            if response.status_code in [200, 201]:
                data = response.json()
                return data.get('id')
            else:
                logger.error(f"Upload failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error uploading {filename}: {e}")
            return None
    
    def list_documents(self, sort_by: str = "created_at", sort_direction: str = "desc", 
                      page_size: int = 100, search: Optional[str] = None) -> List[Dict]:
        """List documents in the knowledge base with various options."""
        logger.info(f"📋 Listing documents (sort: {sort_by} {sort_direction})")
        
        try:
            params = {
                'page_size': min(page_size, 100),  # API limit
                'sort_by': sort_by,
                'sort_direction': sort_direction
            }
            
            if search:
                params['search'] = search
            
            url = f"{self.base_url}/knowledge-base"
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                documents = data.get('documents', [])
                logger.info(f"📄 Found {len(documents)} documents")
                return documents
            else:
                logger.error(f"Failed to list documents: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error listing documents: {e}")
            return []
    
    def search_documents(self, name_pattern: Optional[str] = None, 
                        date_from: Optional[str] = None, date_to: Optional[str] = None,
                        document_type: Optional[str] = None) -> List[Dict]:
        """Search documents by various criteria."""
        logger.info("🔍 Searching documents...")
        
        # Get all documents (sorted by oldest first to include all)
        all_documents = self.list_documents(sort_by="created_at", sort_direction="asc", page_size=100)
        
        filtered_docs = []
        
        for doc in all_documents:
            # Filter by name pattern
            if name_pattern:
                doc_name = doc.get('name', '').lower()
                if name_pattern.lower() not in doc_name:
                    continue
            
            # Filter by date range
            if date_from or date_to:
                metadata = doc.get('metadata', {})
                created_at_unix = metadata.get('created_at_unix_secs')
                last_updated_unix = metadata.get('last_updated_at_unix_secs')
                timestamp_to_check = last_updated_unix if last_updated_unix else created_at_unix
                
                if timestamp_to_check:
                    doc_datetime = datetime.fromtimestamp(timestamp_to_check)
                    doc_date_str = doc_datetime.strftime('%Y-%m-%d')
                    
                    if date_from and doc_date_str < date_from:
                        continue
                    if date_to and doc_date_str > date_to:
                        continue
            
            # Filter by document type
            if document_type:
                doc_type = doc.get('type', '')
                if doc_type != document_type:
                    continue
            
            filtered_docs.append(doc)
        
        logger.info(f"🔍 Found {len(filtered_docs)} matching documents")
        return filtered_docs
    
    def remove_documents_by_date(self, target_date: str) -> bool:
        """Remove all documents created on a specific date."""
        logger.info(f"🗑️  Removing documents from {target_date}...")
        
        # Get documents sorted by oldest first to include all dates
        all_documents = self.list_documents(sort_by="created_at", sort_direction="asc", page_size=100)
        
        # Filter documents by date
        docs_to_remove = self._filter_documents_by_date(all_documents, target_date)
        logger.info(f"📋 Found {len(docs_to_remove)} documents from {target_date}")
        
        if not docs_to_remove:
            logger.info(f"✅ No documents found from {target_date}")
            return True
        
        return self._delete_documents(docs_to_remove)
    
    def remove_document_by_id(self, document_id: str) -> bool:
        """Remove a specific document by ID."""
        logger.info(f"🗑️  Removing document: {document_id}")
        
        try:
            url = f"{self.base_url}/knowledge-base/{document_id}"
            response = requests.delete(url, headers=self.headers)
            
            if response.status_code in [200, 204]:
                logger.info(f"✅ Successfully deleted document: {document_id}")
                return True
            else:
                logger.error(f"❌ Failed to delete document: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Error deleting document: {e}")
            return False
    
    def _filter_documents_by_date(self, documents: List[Dict], target_date: str) -> List[Dict]:
        """Filter documents by creation date."""
        try:
            target_datetime = datetime.strptime(target_date, "%Y-%m-%d")
            target_date_str = target_datetime.strftime("%Y-%m-%d")
            
            filtered_docs = []
            
            for doc in documents:
                metadata = doc.get('metadata', {})
                created_at_unix = metadata.get('created_at_unix_secs')
                last_updated_unix = metadata.get('last_updated_at_unix_secs')
                
                # Use last_updated if available, otherwise use created_at
                timestamp_to_check = last_updated_unix if last_updated_unix else created_at_unix
                
                if timestamp_to_check:
                    try:
                        doc_datetime = datetime.fromtimestamp(timestamp_to_check)
                        doc_date_str = doc_datetime.strftime("%Y-%m-%d")
                        
                        if doc_date_str == target_date_str:
                            filtered_docs.append(doc)
                            logger.info(f"📅 Found document from {target_date}: {doc.get('name', 'Unknown')}")
                    except (ValueError, OSError) as e:
                        logger.warning(f"Could not parse timestamp for document {doc.get('name', 'Unknown')}: {e}")
                        continue
            
            return filtered_docs
            
        except ValueError as e:
            logger.error(f"Invalid date format '{target_date}'. Use YYYY-MM-DD format.")
            return []
    
    def _delete_documents(self, documents: List[Dict]) -> bool:
        """Delete a list of documents."""
        deleted_count = 0
        failed_count = 0
        
        for i, doc in enumerate(documents, 1):
            doc_id = doc.get('id')
            doc_name = doc.get('name', 'unknown')
            
            logger.info(f"🗑️  Deleting {i}/{len(documents)}: {doc_name}")
            
            if self.remove_document_by_id(doc_id):
                deleted_count += 1
            else:
                failed_count += 1
            
            # Rate limiting
            time.sleep(0.5)
        
        logger.info(f"🎉 Deletion completed:")
        logger.info(f"  - Successfully deleted: {deleted_count} documents")
        logger.info(f"  - Failed to delete: {failed_count} documents")
        
        return failed_count == 0
    
    def assign_documents_to_agents(self, domain: str, batch_size: int = 5) -> bool:
        """Assign uploaded documents to agents in batches."""
        logger.info(f"🔗 Assigning documents to agents for domain: {domain}")
        
        # Get domain-specific documents from sync state
        domain_docs = []
        for file_key, doc_info in self.sync_state.items():
            if file_key.startswith(f"{domain}:"):
                domain_docs.append(doc_info)
        
        if not domain_docs:
            logger.warning(f"No uploaded documents found for domain: {domain}")
            return False
        
        logger.info(f"📋 Found {len(domain_docs)} documents to assign")
        
        # Get agent configuration for this domain
        agent_config = self.config.get('agents', {}).get(domain, {})
        agent_id = agent_config.get('agent_id')
        if not agent_id:
            logger.error(f"No agent_id found in configuration for domain: {domain}")
            logger.error(f"Available domains in config: {list(self.config.get('agents', {}).keys())}")
            return False
        
        logger.info(f"✅ Found agent_id for {domain}: {agent_id}")
        
        # Get current agent knowledge base
        current_kb = self._get_agent_knowledge_base(agent_id)
        if current_kb is None:
            logger.error("Failed to get current agent knowledge base")
            return False
        
        # Filter out already assigned documents
        current_doc_ids = {doc.get('id') for doc in current_kb}
        new_docs = [doc for doc in domain_docs if doc['document_id'] not in current_doc_ids]
        
        if not new_docs:
            logger.info("✅ All documents already assigned to agent")
            return True
        
        logger.info(f"📋 {len(new_docs)} new documents to assign")
        
        # Assign in batches
        success_count = 0
        for i in range(0, len(new_docs), batch_size):
            batch = new_docs[i:i + batch_size]
            # Format documents with required fields for ElevenLabs API
            batch_kb = [{
                'id': doc['document_id'],
                'type': doc.get('document_type', 'file'),
                'name': doc.get('document_name', 'unknown')
            } for doc in batch]
            
            # Combine with existing knowledge base
            combined_kb = current_kb + batch_kb
            
            if self._update_agent_knowledge_base(agent_id, combined_kb):
                current_kb = combined_kb  # Update for next batch
                success_count += len(batch)
                logger.info(f"✅ Assigned batch {i//batch_size + 1}: {len(batch)} documents")
            else:
                logger.error(f"❌ Failed to assign batch {i//batch_size + 1}")
            
            # Rate limiting
            time.sleep(1)
        
        logger.info(f"🎉 Assignment completed: {success_count}/{len(new_docs)} documents assigned")
        return success_count == len(new_docs)
    
    def _get_agent_knowledge_base(self, agent_id: str) -> Optional[List[Dict]]:
        """Get current agent knowledge base."""
        try:
            url = f"{self.base_url}/agents/{agent_id}"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                kb = data.get('conversation_config', {}).get('agent', {}).get('prompt', {}).get('knowledge_base', [])
                return kb
            else:
                logger.error(f"Failed to get agent: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error getting agent: {e}")
            return None
    
    def _update_agent_knowledge_base(self, agent_id: str, knowledge_base: List[Dict]) -> bool:
        """Update agent knowledge base."""
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
            
            url = f"{self.base_url}/agents/{agent_id}"
            response = requests.patch(url, headers=self.headers, json=update_payload)
            
            if response.status_code == 200:
                return True
            else:
                logger.error(f"Failed to update agent: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error updating agent: {e}")
            return False
    
    def sync_domain(self, domain: str, force_upload: bool = False, verify_rag: bool = True) -> bool:
        """Complete sync operation: upload + assign + verify RAG."""
        logger.info(f"🔄 Starting sync for domain: {domain}")
        
        # Step 1: Upload files
        upload_success = self.upload_files(domain, force_upload)
        if not upload_success:
            logger.error("Upload failed, aborting sync")
            return False
        
        # Step 2: Assign to agents
        assign_success = self.assign_documents_to_agents(domain)
        if not assign_success:
            logger.error("Assignment failed")
            return False
        
        # Step 3: Verify RAG indexing (optional)
        if verify_rag:
            logger.info("🔍 Verifying RAG indexing...")
            rag_results = self.verify_rag_indexing()
            
            if rag_results["failed"] > 0:
                logger.warning(f"⚠️  {rag_results['failed']} documents failed RAG indexing")
                logger.info("🔄 Retrying failed RAG indexing...")
                retry_results = self.retry_failed_rag_indexing()
                
                if retry_results["still_failed"] > 0:
                    logger.error(f"❌ {retry_results['still_failed']} documents still failed after retry")
                    return False
                else:
                    logger.info("✅ All RAG indexing issues resolved")
            else:
                logger.info("✅ All documents successfully indexed for RAG")
        
        logger.info(f"✅ Sync completed successfully for domain: {domain}")
        return True
    
    def get_statistics(self) -> Dict:
        """Get knowledge base statistics."""
        logger.info("📊 Getting knowledge base statistics...")
        
        # Get all documents
        all_documents = self.list_documents(sort_by="created_at", sort_direction="asc", page_size=100)
        
        stats = {
            'total_documents': len(all_documents),
            'by_type': {},
            'by_date': {},
            'total_size_bytes': 0,
            'sync_state_entries': len(self.sync_state)
        }
        
        for doc in all_documents:
            # Count by type
            doc_type = doc.get('type', 'unknown')
            stats['by_type'][doc_type] = stats['by_type'].get(doc_type, 0) + 1
            
            # Count by date
            metadata = doc.get('metadata', {})
            created_at_unix = metadata.get('created_at_unix_secs')
            last_updated_unix = metadata.get('last_updated_at_unix_secs')
            timestamp_to_check = last_updated_unix if last_updated_unix else created_at_unix
            
            if timestamp_to_check:
                doc_datetime = datetime.fromtimestamp(timestamp_to_check)
                date_str = doc_datetime.strftime('%Y-%m-%d')
                stats['by_date'][date_str] = stats['by_date'].get(date_str, 0) + 1
            
            # Sum size
            size_bytes = metadata.get('size_bytes', 0)
            stats['total_size_bytes'] += size_bytes
        
        return stats
    
    def check_rag_index_status(self, document_id: str, model: str = "e5_mistral_7b_instruct") -> Dict[str, any]:
        """Check RAG indexing status for a specific document."""
        try:
            response = requests.post(
                f"{self.base_url}/knowledge-base/{document_id}/rag-index",
                headers=self.headers,
                json={"model": model}
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to check RAG status for {document_id}: {e}")
            return {"error": str(e)}
    
    def verify_rag_indexing(self, document_ids: List[str] = None, model: str = "e5_mistral_7b_instruct") -> Dict[str, any]:
        """Verify RAG indexing status for documents."""
        logger.info("🔍 Verifying RAG indexing status...")
        
        if document_ids is None:
            # Get all documents from sync state
            document_ids = [doc_data["document_id"] for doc_data in self.sync_state.values()]
        
        results = {
            "total_checked": len(document_ids),
            "succeeded": 0,
            "failed": 0,
            "processing": 0,
            "not_found": 0,
            "errors": 0,
            "details": []
        }
        
        for doc_id in document_ids:
            try:
                status_response = self.check_rag_index_status(doc_id, model)
                
                if "error" in status_response:
                    results["errors"] += 1
                    results["details"].append({
                        "document_id": doc_id,
                        "status": "error",
                        "error": status_response["error"]
                    })
                else:
                    status = status_response.get("status", "unknown")
                    results["details"].append({
                        "document_id": doc_id,
                        "status": status,
                        "progress": status_response.get("progress_percentage", 0),
                        "usage_bytes": status_response.get("document_model_index_usage", {}).get("used_bytes", 0)
                    })
                    
                    if status == "succeeded":
                        results["succeeded"] += 1
                    elif status == "failed":
                        results["failed"] += 1
                    elif status in ["processing", "created"]:
                        results["processing"] += 1
                    else:
                        results["not_found"] += 1
                
                # Small delay to avoid rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error checking RAG status for {doc_id}: {e}")
                results["errors"] += 1
                results["details"].append({
                    "document_id": doc_id,
                    "status": "error",
                    "error": str(e)
                })
        
        return results
    
    def retry_failed_rag_indexing(self, document_ids: List[str] = None, model: str = "e5_mistral_7b_instruct") -> Dict[str, any]:
        """Retry RAG indexing for failed documents."""
        logger.info("🔄 Retrying failed RAG indexing...")
        
        if document_ids is None:
            # First verify to find failed documents
            verification_results = self.verify_rag_indexing()
            failed_docs = [
                detail["document_id"] 
                for detail in verification_results["details"] 
                if detail["status"] == "failed"
            ]
            document_ids = failed_docs
        
        if not document_ids:
            logger.info("✅ No failed documents found to retry")
            return {"retried": 0, "successful": 0, "still_failed": 0}
        
        results = {
            "retried": len(document_ids),
            "successful": 0,
            "still_failed": 0,
            "details": []
        }
        
        for doc_id in document_ids:
            try:
                logger.info(f"🔄 Retrying RAG indexing for {doc_id}")
                status_response = self.check_rag_index_status(doc_id, model)
                
                if "error" not in status_response:
                    status = status_response.get("status", "unknown")
                    results["details"].append({
                        "document_id": doc_id,
                        "status": status,
                        "progress": status_response.get("progress_percentage", 0)
                    })
                    
                    if status in ["succeeded", "created"]:
                        results["successful"] += 1
                    else:
                        results["still_failed"] += 1
                else:
                    results["still_failed"] += 1
                    results["details"].append({
                        "document_id": doc_id,
                        "status": "error",
                        "error": status_response["error"]
                    })
                
                # Small delay to avoid rate limiting
                time.sleep(0.2)
                
            except Exception as e:
                logger.error(f"Error retrying RAG indexing for {doc_id}: {e}")
                results["still_failed"] += 1
                results["details"].append({
                    "document_id": doc_id,
                    "status": "error",
                    "error": str(e)
                })
        
        return results

def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(description='ElevenLabs Knowledge Base Manager')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Upload command
    upload_parser = subparsers.add_parser('upload', help='Upload files to knowledge base')
    upload_parser.add_argument('--domain', required=True, help='Domain to upload')
    upload_parser.add_argument('--force', action='store_true', help='Force upload even if unchanged')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List documents in knowledge base')
    list_parser.add_argument('--sort-by', default='created_at', choices=['name', 'created_at', 'updated_at', 'size'], help='Sort field')
    list_parser.add_argument('--sort-direction', default='desc', choices=['asc', 'desc'], help='Sort direction')
    list_parser.add_argument('--page-size', type=int, default=100, help='Number of documents to return')
    list_parser.add_argument('--search', help='Search by name pattern')
    
    # Remove command
    remove_parser = subparsers.add_parser('remove', help='Remove documents from knowledge base')
    remove_group = remove_parser.add_mutually_exclusive_group(required=True)
    remove_group.add_argument('--date', help='Remove documents from specific date (YYYY-MM-DD)')
    remove_group.add_argument('--id', help='Remove specific document by ID')
    
    # Assign command
    assign_parser = subparsers.add_parser('assign', help='Assign documents to agents')
    assign_parser.add_argument('--domain', required=True, help='Domain to assign')
    assign_parser.add_argument('--batch-size', type=int, default=5, help='Batch size for assignment')
    
    # Sync command
    sync_parser = subparsers.add_parser('sync', help='Complete sync operation (upload + assign + verify RAG)')
    sync_parser.add_argument('--domain', required=True, help='Domain to sync')
    sync_parser.add_argument('--force', action='store_true', help='Force upload even if unchanged')
    sync_parser.add_argument('--no-verify-rag', action='store_true', help='Skip RAG verification step')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search documents by criteria')
    search_parser.add_argument('--name', help='Search by name pattern')
    search_parser.add_argument('--date-from', help='Filter from date (YYYY-MM-DD)')
    search_parser.add_argument('--date-to', help='Filter to date (YYYY-MM-DD)')
    search_parser.add_argument('--type', help='Filter by document type')
    
    # Stats command
    subparsers.add_parser('stats', help='Show knowledge base statistics')
    
    # Verify RAG command
    verify_rag_parser = subparsers.add_parser('verify-rag', help='Verify RAG indexing status for documents')
    verify_rag_parser.add_argument('--document-ids', nargs='+', help='Specific document IDs to check (default: all from sync state)')
    verify_rag_parser.add_argument('--model', default='e5_mistral_7b_instruct', help='RAG model to check')
    
    # Retry RAG command
    retry_rag_parser = subparsers.add_parser('retry-rag', help='Retry failed RAG indexing')
    retry_rag_parser.add_argument('--document-ids', nargs='+', help='Specific document IDs to retry (default: all failed documents)')
    retry_rag_parser.add_argument('--model', default='e5_mistral_7b_instruct', help='RAG model to use')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        manager = ElevenLabsKnowledgeBaseManager()
        
        if args.command == 'upload':
            manager.upload_files(args.domain, args.force)
        elif args.command == 'list':
            documents = manager.list_documents(args.sort_by, args.sort_direction, args.page_size, args.search)
            for doc in documents:
                print(f"{doc.get('id', 'Unknown')} - {doc.get('name', 'Unknown')}")
        elif args.command == 'remove':
            if args.date:
                manager.remove_documents_by_date(args.date)
            elif args.id:
                manager.remove_document_by_id(args.id)
        elif args.command == 'assign':
            manager.assign_documents_to_agents(args.domain, args.batch_size)
        elif args.command == 'sync':
            manager.sync_domain(args.domain, args.force, verify_rag=not args.no_verify_rag)
        elif args.command == 'search':
            documents = manager.search_documents(args.name, args.date_from, args.date_to, args.type)
            for doc in documents:
                print(f"{doc.get('id', 'Unknown')} - {doc.get('name', 'Unknown')}")
        elif args.command == 'stats':
            stats = manager.get_statistics()
            print(f"Total documents: {stats['total_documents']}")
            print(f"Total size: {stats['total_size_bytes']:,} bytes")
            print(f"Sync state entries: {stats['sync_state_entries']}")
            print("\nBy type:")
            for doc_type, count in stats['by_type'].items():
                print(f"  {doc_type}: {count}")
            print("\nBy date (last 10):")
            for date, count in sorted(stats['by_date'].items(), reverse=True)[:10]:
                print(f"  {date}: {count}")
        
        elif args.command == 'verify-rag':
            results = manager.verify_rag_indexing(args.document_ids, args.model)
            print(f"\n🔍 RAG Indexing Verification Results:")
            print(f"Total checked: {results['total_checked']}")
            print(f"✅ Succeeded: {results['succeeded']}")
            print(f"❌ Failed: {results['failed']}")
            print(f"⏳ Processing: {results['processing']}")
            print(f"❓ Not found: {results['not_found']}")
            print(f"⚠️  Errors: {results['errors']}")
            
            if results['failed'] > 0 or results['errors'] > 0:
                print(f"\n❌ Failed/Error Details:")
                for detail in results['details']:
                    if detail['status'] in ['failed', 'error']:
                        print(f"  {detail['document_id']}: {detail['status']} - {detail.get('error', 'N/A')}")
        
        elif args.command == 'retry-rag':
            results = manager.retry_failed_rag_indexing(args.document_ids, args.model)
            print(f"\n🔄 RAG Indexing Retry Results:")
            print(f"Retried: {results['retried']}")
            print(f"✅ Successful: {results['successful']}")
            print(f"❌ Still failed: {results['still_failed']}")
            
            if results['still_failed'] > 0:
                print(f"\n❌ Still Failed Details:")
                for detail in results['details']:
                    if detail['status'] not in ['succeeded', 'created']:
                        print(f"  {detail['document_id']}: {detail['status']} - {detail.get('error', 'N/A')}")
        
    except Exception as e:
        logger.error(f"Command failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
