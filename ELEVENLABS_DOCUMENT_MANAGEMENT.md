# ElevenLabs Document Management Strategy

**Status:** 📋 **SOLUTION PROPOSAL** | **Version:** 1.0 | **Date:** September 30, 2025

## 🎯 Problem Statement

### Current Issue: Document Accumulation

When the system updates product data and syncs to ElevenLabs:

1. **Local System:** ✅ **WORKS CORRECTLY**
   - Appends new products to existing shard files
   - Updates `index.json` and `manifest.json`
   - Rewrites shard file with existing + new products
   - Single file contains all cumulative data

2. **ElevenLabs System:** ❌ **CREATES DUPLICATES**
   - Each upload creates a NEW document with unique `document_id`
   - Same filename = NEW document (not updated)
   - Old documents remain in knowledge base
   - Multiple versions of same logical file accumulate

### Example Scenario

**Initial State:**
```
ElevenLabs KB:
- llms-jgengineering-ie-products.txt (doc_id: ABC123) → 1 product
```

**After Adding New Product:**
```
Local System:
- llms-jgengineering-ie-products.txt → 2 products (appended)

ElevenLabs KB:
- llms-jgengineering-ie-products.txt (doc_id: ABC123) → 1 product (OLD)
- llms-jgengineering-ie-products.txt (doc_id: XYZ789) → 2 products (NEW)
```

**Problem:** Both documents exist, agent may reference outdated data

## 🔍 Current System Behavior

### Upload Process

```python
def _upload_file_to_knowledge_base(self, file_path: Path, filename: str) -> Optional[str]:
    """Upload a single file to the knowledge base."""
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
        return data.get('id')  # NEW document ID returned
```

### Sync State Tracking

```json
{
  "jgengineering.ie:llms-jgengineering-ie-products.txt": {
    "hash": "new_hash_here",
    "document_id": "XYZ789",  // ← NEW ID (old doc ABC123 still exists)
    "uploaded_at": "2025-09-30T11:04:09.057Z"
  }
}
```

### Impact Assessment

| Aspect | Impact | Severity |
|--------|--------|----------|
| **Storage** | Multiple versions consume storage | ⚠️ Medium |
| **Data Accuracy** | Agent may reference old data | 🔴 High |
| **RAG Performance** | Multiple similar documents affect retrieval | ⚠️ Medium |
| **Agent Confusion** | Conflicting information possible | 🔴 High |
| **Cost** | Storage costs increase over time | ⚠️ Medium |

## 💡 Proposed Solutions

### Solution 1: Automatic Old Version Cleanup (RECOMMENDED)

**Description:** Before uploading a new version, delete the old document.

**Implementation:**

```python
def upload_files(self, domain: str, force_upload: bool = False) -> bool:
    """Upload files from a domain to the knowledge base."""
    logger.info(f"🚀 Starting upload for domain: {domain}")
    
    domain_path = Path(f"out/{domain}")
    if not domain_path.exists():
        logger.error(f"Domain path not found: {domain_path}")
        return False
    
    txt_files = list(domain_path.glob("*.txt"))
    logger.info(f"📁 Found {len(txt_files)} .txt files in {domain}")
    
    uploaded_count = 0
    
    for file_path in txt_files:
        file_key = f"{domain}:{file_path.name}"
        current_hash = self._get_file_hash(file_path)
        
        # Check if file already uploaded and unchanged
        if not force_upload and file_key in self.sync_state:
            existing_hash = self.sync_state[file_key].get('hash', '')
            if existing_hash == current_hash:
                logger.info(f"⏭️  Skipping unchanged file: {file_path.name}")
                continue
            
            # File has changed - DELETE OLD VERSION FIRST
            old_document_id = self.sync_state[file_key].get('document_id')
            if old_document_id:
                logger.info(f"🗑️  Deleting old version: {old_document_id}")
                self._delete_document(old_document_id)
        
        # Upload NEW version
        document_id = self._upload_file_to_knowledge_base(file_path, file_path.name)
        if document_id:
            # Update sync state with new document info
            self.sync_state[file_key] = {
                'hash': current_hash,
                'document_id': document_id,
                'document_name': file_path.name,
                'document_type': 'file',
                'uploaded_at': datetime.now().isoformat()
            }
            uploaded_count += 1
            logger.info(f"✅ Uploaded: {file_path.name} -> {document_id}")
        
        time.sleep(0.5)
    
    self._save_sync_state()
    return uploaded_count > 0

def _delete_document(self, document_id: str) -> bool:
    """Delete a document from the knowledge base."""
    try:
        delete_url = f"{self.base_url}/knowledge-base/{document_id}"
        response = requests.delete(delete_url, headers=self.headers)
        
        if response.status_code in [200, 204]:
            logger.info(f"✅ Deleted old document: {document_id}")
            return True
        else:
            logger.warning(f"Failed to delete document {document_id}: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {e}")
        return False
```

**Pros:**
- ✅ Prevents accumulation
- ✅ Agent always has latest data
- ✅ No storage waste
- ✅ Clean knowledge base
- ✅ Minimal code changes

**Cons:**
- ⚠️ Brief moment where no document exists (during delete → upload)
- ⚠️ Requires API permission to delete documents
- ⚠️ If upload fails after delete, data is lost

**Risk Mitigation:**
- Use transactions: Delete → Upload → Update sync state (rollback on failure)
- Keep backup of deleted document IDs for recovery
- Add retry logic for failed uploads

### Solution 2: Update Existing Document (IF API SUPPORTS)

**Description:** Update document content instead of creating new one.

**Implementation:**

```python
def upload_files(self, domain: str, force_upload: bool = False) -> bool:
    """Upload files from a domain to the knowledge base."""
    
    for file_path in txt_files:
        file_key = f"{domain}:{file_path.name}"
        current_hash = self._get_file_hash(file_path)
        
        # Check if file exists
        if file_key in self.sync_state:
            existing_document_id = self.sync_state[file_key].get('document_id')
            existing_hash = self.sync_state[file_key].get('hash', '')
            
            if existing_hash != current_hash:
                # File changed - UPDATE existing document
                logger.info(f"🔄 Updating existing document: {existing_document_id}")
                success = self._update_document(existing_document_id, file_path)
                if success:
                    self.sync_state[file_key]['hash'] = current_hash
                    self.sync_state[file_key]['uploaded_at'] = datetime.now().isoformat()
                    continue
        
        # File doesn't exist - create new
        document_id = self._upload_file_to_knowledge_base(file_path, file_path.name)
        # ... handle new document

def _update_document(self, document_id: str, file_path: Path) -> bool:
    """Update an existing document's content."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        update_url = f"{self.base_url}/knowledge-base/{document_id}"
        response = requests.put(
            update_url,
            headers=self.headers,
            json={'content': content}  # API-dependent format
        )
        
        if response.status_code in [200, 201]:
            logger.info(f"✅ Updated document: {document_id}")
            return True
        else:
            logger.warning(f"Failed to update document: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"Error updating document: {e}")
        return False
```

**Pros:**
- ✅ No document duplication
- ✅ Document ID remains constant
- ✅ No data loss risk
- ✅ Agent assignments persist

**Cons:**
- ❌ Requires ElevenLabs API to support document updates (MAY NOT BE AVAILABLE)
- ⚠️ Need to verify RAG re-indexing happens automatically
- ⚠️ API endpoint/format unknown

**Status:** 🔍 **NEEDS INVESTIGATION** - Check if ElevenLabs API supports PATCH/PUT operations

### Solution 3: Versioned Naming Convention

**Description:** Include version or timestamp in filename to make duplicates obvious.

**Implementation:**

```python
def _generate_versioned_filename(self, base_filename: str) -> str:
    """Generate a versioned filename."""
    name, ext = os.path.splitext(base_filename)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{name}_v{timestamp}{ext}"

def upload_files(self, domain: str, force_upload: bool = False) -> bool:
    """Upload files with versioned names."""
    
    for file_path in txt_files:
        # Generate versioned filename
        versioned_name = self._generate_versioned_filename(file_path.name)
        
        # Upload with versioned name
        document_id = self._upload_file_to_knowledge_base(file_path, versioned_name)
```

**Example:**
```
llms-jgengineering-ie-products_v20250930_110400.txt
llms-jgengineering-ie-products_v20250930_143000.txt
```

**Pros:**
- ✅ No API changes needed
- ✅ Easy to identify versions
- ✅ Audit trail of changes
- ✅ Can manually clean up old versions

**Cons:**
- ❌ Still accumulates documents
- ❌ Agent may reference old versions
- ❌ Manual cleanup required
- ❌ Doesn't solve core problem

**Status:** 🚫 **NOT RECOMMENDED** - Doesn't address root cause

### Solution 4: Periodic Cleanup Job

**Description:** Separate job that periodically removes old document versions.

**Implementation:**

```python
def cleanup_old_versions(self, domain: str, keep_latest: int = 1) -> Dict[str, int]:
    """Remove old versions of documents, keeping only the latest N versions."""
    logger.info(f"🧹 Starting cleanup for domain: {domain}")
    
    # Get all documents from ElevenLabs
    all_documents = self._list_all_documents()
    
    # Group documents by base filename
    document_groups = {}
    for doc in all_documents:
        base_name = self._extract_base_filename(doc['name'])
        if base_name not in document_groups:
            document_groups[base_name] = []
        document_groups[base_name].append(doc)
    
    deleted_count = 0
    
    # For each group, keep only latest N versions
    for base_name, docs in document_groups.items():
        if len(docs) <= keep_latest:
            continue
        
        # Sort by creation date (newest first)
        docs_sorted = sorted(docs, key=lambda x: x['created_at'], reverse=True)
        
        # Delete old versions
        for old_doc in docs_sorted[keep_latest:]:
            logger.info(f"🗑️  Deleting old version: {old_doc['id']}")
            if self._delete_document(old_doc['id']):
                deleted_count += 1
    
    logger.info(f"✅ Cleanup complete: Deleted {deleted_count} old versions")
    return {
        'total_groups': len(document_groups),
        'deleted_count': deleted_count
    }
```

**Pros:**
- ✅ Doesn't interfere with upload process
- ✅ Can run during low-traffic periods
- ✅ Configurable retention policy
- ✅ Safe - can test thoroughly first

**Cons:**
- ⚠️ Old versions exist temporarily
- ⚠️ Additional complexity
- ⚠️ Need to schedule/trigger cleanup
- ⚠️ Requires robust document listing

**Status:** 🟡 **FALLBACK OPTION** - Use if Solution 1 has issues

## 🎯 Recommended Implementation

### Phase 1: Immediate Implementation (Solution 1)

**Priority:** 🔴 **HIGH** - Implement automatic old version cleanup

**Steps:**

1. **Add Document Deletion Method**
   ```python
   def _delete_document(self, document_id: str) -> bool
   ```

2. **Modify Upload Process**
   - Check if file changed (hash comparison)
   - If changed: Delete old document → Upload new → Update sync state
   - If unchanged: Skip

3. **Add Rollback Logic**
   - If upload fails after delete: Log error, keep old document_id in sync state
   - Next run will retry

4. **Update Sync State Structure**
   ```json
   {
     "file_key": {
       "hash": "current_hash",
       "document_id": "current_doc_id",
       "previous_document_id": "backup_doc_id",  // For rollback
       "uploaded_at": "timestamp"
     }
   }
   ```

5. **Testing**
   - Test with small dataset first
   - Verify old documents deleted
   - Verify new documents uploaded
   - Verify agent has correct data

### Phase 2: Add Safety Features

**Priority:** 🟡 **MEDIUM** - Add after Phase 1 works

1. **Pre-Delete Verification**
   - Verify document exists before deleting
   - Check document not assigned to multiple agents

2. **Backup Mechanism**
   - Keep record of deleted document IDs for 24 hours
   - Add recovery command if needed

3. **Monitoring & Alerts**
   - Log all deletions
   - Alert if delete rate too high
   - Track storage savings

### Phase 3: Periodic Cleanup (Optional)

**Priority:** 🟢 **LOW** - Add if needed for additional safety

1. **Cleanup Command**
   ```bash
   python3 scripts/knowledge_base_manager_agnostic.py remove --domain example.com
   ```

2. **Scheduled Job**
   - Run weekly/monthly
   - Catch any documents that slipped through
   - Generate cleanup report

## 📊 Expected Results

### After Implementation

**Storage:**
- ✅ No document accumulation
- ✅ Only latest version exists
- ✅ Storage usage stable

**Data Quality:**
- ✅ Agent always has latest data
- ✅ No conflicting information
- ✅ RAG retrieval more accurate

**Operations:**
- ✅ Automatic cleanup
- ✅ No manual intervention needed
- ✅ Clean knowledge base

### Metrics to Track

1. **Document Count**: Should remain stable per domain
2. **Storage Usage**: Should not grow linearly with updates
3. **Agent Accuracy**: Verify agent references latest data
4. **Deletion Success Rate**: Track failed deletions
5. **Upload Success Rate**: Monitor impact of delete → upload flow

## 🚨 Risks & Mitigation

### Risk 1: Data Loss

**Scenario:** Delete succeeds, upload fails

**Mitigation:**
- Keep `previous_document_id` in sync state for rollback
- Add retry logic with exponential backoff
- Log all deletion operations for recovery

### Risk 2: Agent Downtime

**Scenario:** Brief period where no document exists

**Mitigation:**
- Minimize time between delete and upload (< 1 second)
- Consider uploading first, then deleting (if API allows duplicate names)
- Monitor agent response times during updates

### Risk 3: API Rate Limits

**Scenario:** Too many delete + upload operations

**Mitigation:**
- Add rate limiting between operations
- Batch updates when possible
- Use sync state to skip unchanged files

## 🔧 Code Changes Required

### Files to Modify

1. **`scripts/knowledge_base_manager_agnostic.py`**
   - Add `_delete_document()` method
   - Modify `upload_files()` to delete old versions
   - Update sync state structure

2. **`config/elevenlabs_sync_state.json`**
   - Add `previous_document_id` field
   - Track deletion timestamp

3. **`.github/workflows/update-products.yml`**
   - No changes needed (uses existing sync command)

### Estimated Implementation Time

- **Phase 1 (Core Feature):** 2-3 hours
- **Phase 2 (Safety Features):** 2-4 hours
- **Phase 3 (Cleanup Job):** 3-5 hours
- **Testing & Validation:** 4-6 hours

**Total:** ~11-18 hours

## 📝 Testing Plan

### Unit Tests

1. Test `_delete_document()` with valid document ID
2. Test `_delete_document()` with invalid document ID
3. Test upload flow with existing document
4. Test upload flow with new document
5. Test rollback on failed upload

### Integration Tests

1. Add new product → Verify old doc deleted, new doc uploaded
2. Update existing product → Verify seamless update
3. Multiple updates in sequence → Verify no accumulation
4. Failed upload after delete → Verify rollback

### Production Validation

1. Deploy to test domain first
2. Monitor for 1 week
3. Verify document count stable
4. Check agent responses accurate
5. Roll out to all domains

## 🎯 Success Criteria

✅ **Implementation Successful When:**

1. Document count per domain remains stable over time
2. No duplicate documents in knowledge base
3. Agent always references latest product data
4. Zero data loss incidents
5. Storage usage doesn't grow with updates
6. All tests pass successfully

---

**Recommendation:** **Implement Solution 1 (Automatic Old Version Cleanup)** as it provides the best balance of effectiveness, safety, and implementation simplicity. Start with Phase 1, validate thoroughly, then add Phase 2 safety features.

**Next Steps:**
1. Review ElevenLabs API documentation for delete endpoint
2. Implement `_delete_document()` method
3. Test with small dataset on jgengineering.ie
4. Validate results
5. Deploy to all domains

---

*This document serves as the implementation guide for ElevenLabs document management improvements.*
