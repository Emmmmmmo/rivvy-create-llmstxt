# ElevenLabs Knowledge Base Management Guide

## Overview
This document outlines best practices and lessons learned for managing ElevenLabs knowledge bases, including document upload, agent assignment, and cleanup procedures.

## Key Lessons Learned

### 1. Document Deletion Process

**❌ Common Mistake:** Attempting to delete documents directly from the knowledge base when they are assigned to agents.

**✅ Correct Process:**
1. **Remove documents from agent's knowledge base first** (via ElevenLabs dashboard or API)
2. **Then delete documents from the knowledge base** using the API

**Error Message:** `"document_has_dependent_agents"` - indicates documents cannot be deleted because they are assigned to agents.

### 2. API Endpoints

**✅ Correct Delete Endpoint:**
```
DELETE https://api.elevenlabs.io/v1/convai/knowledge-base/{documentation_id}
```

**❌ Wrong Endpoint (we initially used):**
```
DELETE https://api.elevenlabs.io/v1/convai/knowledge-base/{document_id}
```

**Key Difference:** Parameter name is `{documentation_id}`, not `{document_id}`.

### 3. Pagination for Large Knowledge Bases

**✅ Correct Pagination Parameters:**
- Use `cursor` and `page_size` parameters
- `page_size` can be up to 100 (maximum allowed)
- Continue fetching until no more documents or cursor is null

**❌ Wrong Approach:**
- Using `page` parameter (not supported)
- Not handling pagination properly

**Example:**
```python
url = f'https://api.elevenlabs.io/v1/convai/knowledge-base?page_size=100'
if cursor:
    url += f'&cursor={cursor}'
```

### 4. File Organization

**✅ Recommended Structure:**
```
out/
├── domain.com/                    # Site-specific subdirectory
│   ├── llms-domain-com-*.txt     # Sharded product files
│   ├── llms-domain-com-index.json
│   └── llms-domain-com-manifest.json
└── domain.com.old/               # Reference files
```

**❌ Avoid:**
- Mixing files from different scraping sessions in root directory
- Not organizing files by domain/website

### 5. Sync State Management

**✅ Best Practices:**
- Use `--force` flag only when necessary (clears sync state)
- Monitor sync state files to avoid re-uploading existing documents
- Clean up duplicate uploads immediately

**❌ Common Issues:**
- Using `--force` unnecessarily causes full re-upload
- Not cleaning up duplicates leads to knowledge base bloat
- Mixing old and new files in same upload session

## Cleanup Procedures

### 1. Identify Files to Delete

**Filter Criteria:**
- Files with specific naming patterns (e.g., `currency=EUR`)
- Files from specific date ranges
- Files with specific content markers

**Example Filter:**
```python
today_files = [doc for doc in all_documents 
               if 'jgengineering.ie' in doc.get('name', '') 
               and 'currency=EUR' in doc.get('name', '')]
```

### 2. Batch Deletion Process

**Recommended Approach:**
1. Delete in batches of 30-50 files
2. Add delays between deletions (0.3-0.5 seconds)
3. Monitor success/failure rates
4. Verify deletions with follow-up queries

**Example Implementation:**
```python
for i, doc in enumerate(files_to_delete):
    delete_url = f'https://api.elevenlabs.io/v1/convai/knowledge-base/{doc_id}'
    delete_response = requests.delete(delete_url, headers=headers)
    
    if delete_response.status_code in [200, 204]:
        deleted_count += 1
    else:
        failed_count += 1
    
    time.sleep(0.5)  # Rate limiting
```

### 3. Verification

**Always verify cleanup:**
- Re-query knowledge base after deletion
- Check remaining file counts
- Confirm only intended files were removed

### 4. Test Document Cleanup

**⚠️ Critical Lesson:** Test documents uploaded during verification testing must be handled specially.

**❌ Common Issue:** Test documents remain in knowledge base after testing because they are assigned to agents.

**✅ Correct Process for Test Documents:**
1. **Remove test documents from agent's knowledge base first** (via ElevenLabs dashboard or API)
2. **Then delete test documents from knowledge base** using the API
3. **Clean up test agent configurations** from `elevenlabs-agents.json`

**Example Test Document Cleanup:**
```python
# Test documents often have different naming patterns
test_files = [doc for doc in all_documents 
              if 'test_' in doc.get('name', '') 
              or 'verification' in doc.get('name', '')]

# Must unassign from agent before deletion
for doc in test_files:
    # Remove from agent first
    remove_from_agent(doc['id'])
    # Then delete from knowledge base
    delete_document(doc['id'])
```

**Note:** Test documents created during script verification (like `test_llms-jgengineering-ie-*.txt`) will remain assigned to agents and cannot be deleted until manually unassigned.

### 5. Agent Assignment Process

**⚠️ Critical Discovery:** ElevenLabs has limits on the number of documents that can be assigned to an agent in a single operation.

**❌ Common Issue:** Attempting to assign large numbers of documents (100+ documents) in a single API call results in silent failures or API errors.

**✅ Correct Process for Large Assignments:**
1. **Use incremental assignment** with small batch sizes (3-5 documents)
2. **Preserve existing knowledge base** documents in each batch
3. **Get current knowledge base** before each batch to avoid overwriting
4. **Add delays between batches** to avoid rate limiting

**Example Incremental Assignment:**
```python
def assign_documents_incremental(agent_id, new_documents, batch_size=5):
    current_kb = get_agent_knowledge_base(agent_id)
    
    for i in range(0, len(new_documents), batch_size):
        batch = new_documents[i:i + batch_size]
        
        # Get current KB (may have grown from previous batches)
        current_kb = get_agent_knowledge_base(agent_id)
        
        # Combine existing + new batch
        combined_kb = current_kb + batch
        
        # Update agent
        update_agent_knowledge_base(agent_id, combined_kb)
        
        # Wait between batches
        time.sleep(2)
```

### 6. File Size and Character Limits

**⚠️ Critical Discovery:** ElevenLabs has a 300,000 character limit for knowledge base documents on non-enterprise accounts.

**❌ Common Issue:** Large files (over 300K characters) cannot be assigned to agents, even if they are successfully uploaded to the knowledge base.

**✅ Correct Process for Large Files:**
1. **Split large files** into smaller chunks under 300K characters
2. **Upload split files** to knowledge base
3. **Assign split files** to agents
4. **Clean up original large files** from knowledge base

**Example File Splitting:**
```python
def split_large_file(file_path, max_chars=300000):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if len(content) <= max_chars:
        return [file_path]
    
    chunks = []
    start = 0
    while start < len(content):
        end = start + max_chars
        chunk_content = content[start:end]
        
        chunk_file = f"{file_path}_part{len(chunks)+1}.txt"
        with open(chunk_file, 'w', encoding='utf-8') as f:
            f.write(chunk_content)
        
        chunks.append(chunk_file)
        start = end
    
    return chunks
```

### 7. RAG Indexing Process

**⚠️ Important Clarification:** RAG indexing happens **AFTER** assignment, not before.

**❌ Common Misconception:** Documents need to be RAG-indexed before they can be assigned to agents.

**✅ Correct Understanding:**
1. **Upload documents** to knowledge base
2. **Assign documents** to agent
3. **RAG indexing happens automatically** in the background after assignment
4. **No manual triggering** of RAG indexing is needed

**Note:** The `rag_index_not_ready` error typically indicates file size limits or other assignment issues, not indexing problems.

## Error Handling

### Common Error Codes

**400 - Bad Request:**
- `document_has_dependent_agents`: Remove from agent first
- Invalid document ID format
- Missing required headers

**401 - Unauthorized:**
- Invalid or expired API key
- Missing `xi-api-key` header

**404 - Not Found:**
- Document ID doesn't exist
- Wrong API endpoint
- `knowledge_base_documentation_not_found`: Document doesn't exist in knowledge base

**422 - Unprocessable Entity:**
- `rag_index_not_ready`: Document cannot be assigned (usually due to file size limits)
- Document still being indexed
- Invalid document format
- Too many documents in single assignment request

**402 - Payment Required:**
- API key has reached usage limits
- Account requires payment for additional usage

### Retry Logic

**Recommended Approach:**
- Implement exponential backoff for rate limits
- Retry failed deletions with different batch sizes
- Log all failures for manual review

## Best Practices Summary

1. **Always remove documents from agents before deletion**
2. **Use correct API endpoints and parameter names**
3. **Implement proper pagination for large datasets**
4. **Organize files by domain/website in subdirectories**
5. **Monitor sync state to avoid unnecessary re-uploads**
6. **Delete in batches with rate limiting**
7. **Verify cleanup operations**
8. **Handle errors gracefully with retry logic**
9. **Document all procedures for future reference**
10. **Test with small batches before full operations**
11. **Use incremental assignment for large document sets (100+ documents)**
12. **Split large files (>300K characters) before assignment**
13. **Preserve existing knowledge base documents during assignment**
14. **Add delays between assignment batches to avoid rate limiting**
15. **Understand that RAG indexing happens after assignment, not before**

## Tools and Scripts

### Available Scripts

1. **`scripts/cleanup_elevenlabs_kb.py`** - Batch deletion tool
2. **`scripts/elevenlabs_rag_sync_corrected.py`** - Legacy sync and assignment tool
3. **`scripts/llms_scraper_sharded.py`** - Main scraping tool
4. **`scripts/upload_to_knowledge_base.py`** - Upload files to knowledge base only
5. **`scripts/assign_to_agent.py`** - Assign uploaded files to agents
6. **`scripts/assign_to_agent_incremental.py`** - Incremental assignment for large document sets
7. **`scripts/sync_domain.py`** - Orchestrates upload + assignment workflow
8. **`scripts/split_large_files.py`** - Split large files for character limit compliance

### Usage Examples

**Clean up specific files:**
```bash
python3 scripts/cleanup_elevenlabs_kb.py
```

**Upload files to knowledge base:**
```bash
python3 scripts/upload_to_knowledge_base.py jgengineering.ie
```

**Assign files to agent (incremental for large sets):**
```bash
python3 scripts/assign_to_agent_incremental.py jgengineering.ie --batch-size=5
```

**Full sync workflow:**
```bash
python3 scripts/sync_domain.py jgengineering.ie
```

**Split large files:**
```bash
python3 scripts/split_large_files.py
```

**Scrape and organize content:**
```bash
python3 scripts/llms_scraper_sharded.py
```

## Future Improvements

1. **Automated cleanup procedures** based on file age/patterns
2. **Better error handling and retry logic**
3. **Monitoring and alerting for knowledge base health**
4. **Automated testing of API endpoints**
5. **Documentation generation from API responses**

## Key Discoveries Summary

### Major Breakthroughs (September 27, 2025)

1. **Assignment Limits Discovered:** ElevenLabs has undocumented limits on the number of documents that can be assigned to an agent in a single operation (approximately 100+ documents cause failures).

2. **Character Limit Identified:** Non-enterprise accounts have a 300,000 character limit per knowledge base document, not a file size limit.

3. **RAG Indexing Clarified:** RAG indexing happens automatically **after** assignment, not before. The `rag_index_not_ready` error typically indicates assignment issues, not indexing problems.

4. **Incremental Assignment Solution:** Created a working solution using incremental assignment with small batch sizes (3-5 documents) while preserving existing knowledge base documents.

5. **File Splitting Success:** Successfully split 15 large files into 104 smaller chunks, all under the character limit, enabling successful assignment.

### Current Status
- ✅ 104 documents uploaded to knowledge base
- ✅ 104 documents successfully split and ready for assignment
- ✅ Incremental assignment script created and tested
- ⏳ Ready for full assignment of all 104 documents to agent

---

*Last Updated: September 27, 2025*
*Based on lessons learned from JG Engineering knowledge base management*
*Major update: Assignment limits, character limits, and incremental assignment solution discovered*
