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

**422 - Unprocessable Entity:**
- Document still being indexed
- Invalid document format

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

## Tools and Scripts

### Available Scripts

1. **`scripts/cleanup_elevenlabs_kb.py`** - Batch deletion tool
2. **`scripts/elevenlabs_rag_sync_corrected.py`** - Sync and assignment tool
3. **`scripts/llms_scraper_sharded.py`** - Main scraping tool

### Usage Examples

**Clean up specific files:**
```bash
python3 scripts/cleanup_elevenlabs_kb.py
```

**Sync new files to agent:**
```bash
python3 scripts/elevenlabs_rag_sync_corrected.py
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

---

*Last Updated: September 27, 2025*
*Based on lessons learned from JG Engineering knowledge base management*
