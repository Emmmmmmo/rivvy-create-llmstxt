# Rivvy Create LLMs.txt - Restoration Guide

## Overview

This guide provides step-by-step instructions for restoring the system to the working state tagged as `v1.0-working-state-20251004-232548`. This state includes all race condition fixes, automatic cleanup functionality, and proper sync state management.

## Working State Details

**Tag**: `v1.0-working-state-20251004-232548`  
**Date**: October 4, 2025  
**Status**: ✅ Fully functional with all fixes implemented

### Key Features in This State:
- ✅ Automatic old version cleanup working perfectly
- ✅ Race condition fixes implemented in GitHub Actions workflow
- ✅ File locking and atomic operations in sync state management
- ✅ Domain key normalization and reconciliation
- ✅ Hash comparison and incremental sync working
- ✅ All 38 JG Engineering documents properly synced to ElevenLabs
- ✅ Test collections working with Rivvy Observer integration

## Restoration Methods

### Method 1: Git Tag Restoration (Recommended)

```bash
# 1. Checkout the working state tag
git checkout v1.0-working-state-20251004-232548

# 2. Create a new branch from this state (optional but recommended)
git checkout -b restore-working-state-$(date +%Y%m%d)

# 3. Push the restored state
git push origin HEAD
```

### Method 2: Hard Reset to Working State

```bash
# 1. Fetch all tags
git fetch --tags

# 2. Hard reset to the working state
git reset --hard v1.0-working-state-20251004-232548

# 3. Force push (WARNING: This will overwrite remote history)
git push --force-with-lease origin main
```

### Method 3: Cherry-pick Specific Fixes

If you only need specific fixes, you can cherry-pick individual commits:

```bash
# List commits in the working state
git log --oneline v1.0-working-state-20251004-232548

# Cherry-pick specific commits (replace COMMIT_HASH with actual hashes)
git cherry-pick COMMIT_HASH_1
git cherry-pick COMMIT_HASH_2
```

## Post-Restoration Verification

After restoration, verify the system is working correctly:

### 1. Check Key Files Exist and Are Correct

```bash
# Verify workflow file has race condition fixes
grep -n "cancel-in-progress: false" .github/workflows/update-products.yml

# Verify knowledge base manager has automatic cleanup
grep -n "Deleting old version" scripts/knowledge_base_manager_agnostic.py

# Verify sync state is properly formatted
cat config/elevenlabs_sync_state.json | jq .
```

### 2. Test ElevenLabs Integration

```bash
# Test sync functionality
python3 scripts/knowledge_base_manager_agnostic.py list --domain jgengineering-ie

# Verify document count (should be 38)
python3 scripts/knowledge_base_manager_agnostic.py list --domain jgengineering-ie | grep -c "document_id"
```

### 3. Test Observer Integration

```bash
# Check if observer collections are still configured
curl -s -X GET "https://rivvy-observer.vercel.app/api/websites" \
  -H "Authorization: Bearer $OBSERVER_API_KEY" | jq .
```

## Key Fixes Included in This State

### 1. Automatic Old Version Cleanup
- **File**: `scripts/knowledge_base_manager_agnostic.py`
- **Fix**: Moved deletion logic to correct location in upload process
- **Result**: Old documents are now properly deleted before uploading new versions

### 2. Race Condition Fixes
- **File**: `.github/workflows/update-products.yml`
- **Fixes**:
  - Added `cancel-in-progress: false` to concurrency control
  - Implemented atomic git push with retry logic
  - Added `git pull --rebase` before ElevenLabs sync
- **Result**: Concurrent workflow runs no longer cause conflicts

### 3. File Locking and Atomic Operations
- **File**: `scripts/knowledge_base_manager_agnostic.py`
- **Fixes**:
  - Added `fcntl` file locking for sync state operations
  - Implemented atomic file writes using `tempfile` and `shutil.move`
  - Added sync state validation and recovery
- **Result**: Sync state corruption and race conditions eliminated

### 4. Domain Key Normalization
- **File**: `scripts/knowledge_base_manager_agnostic.py`
- **Fix**: Added `_normalize_domain_key` and `_reconcile_sync_state_keys` methods
- **Result**: Consistent domain key handling across all components

### 5. Enhanced Error Handling
- **Files**: Multiple
- **Fixes**:
  - Added comprehensive `KeyError` handling in scraping functions
  - Implemented fallback logic for Firecrawl API responses
  - Added rollback logic for failed uploads
- **Result**: System is more resilient to API changes and failures

## Troubleshooting Restoration

### Issue: Tag Not Found
```bash
# Fetch all tags from remote
git fetch --tags

# List all available tags
git tag -l
```

### Issue: Merge Conflicts During Restoration
```bash
# Abort current merge
git merge --abort

# Use hard reset instead
git reset --hard v1.0-working-state-20251004-232548
```

### Issue: ElevenLabs Out of Sync After Restoration
```bash
# Reset ElevenLabs knowledge base
python3 scripts/knowledge_base_manager_agnostic.py delete --all-domains

# Re-upload all documents
python3 scripts/knowledge_base_manager_agnostic.py sync --domain jgengineering-ie
```

## Environment Variables Required

Ensure these environment variables are set:

```bash
export FIRECRAWL_API_KEY="your_firecrawl_api_key"
export ELEVENLABS_API_KEY="your_elevenlabs_api_key"
export OBSERVER_API_KEY="your_observer_api_key"
```

## File Structure Verification

After restoration, verify this file structure exists:

```
rivvy-create-llmstxt/
├── .github/workflows/update-products.yml (with race condition fixes)
├── scripts/
│   ├── knowledge_base_manager_agnostic.py (with automatic cleanup)
│   ├── update_llms_agnostic.py (with enhanced error handling)
│   └── add_jgengineering_collections_updated.sh (with duplicate prevention)
├── config/
│   ├── elevenlabs_sync_state.json (properly formatted)
│   └── elevenlabs-agents.json (with JG Engineering agent)
├── out/jgengineering-ie/ (38 .txt files + manifest + index)
└── RESTORATION_GUIDE.md (this file)
```

## Success Indicators

The restoration is successful when:

1. ✅ All 38 JG Engineering documents are in ElevenLabs
2. ✅ Sync state shows correct document IDs and hashes
3. ✅ GitHub Actions workflow runs without conflicts
4. ✅ Automatic cleanup deletes old documents before uploading new ones
5. ✅ Only changed files are uploaded (hash comparison working)
6. ✅ Observer integration works for test collections

## Support

If you encounter issues during restoration:

1. Check the troubleshooting section above
2. Review the original issue logs in GitHub Actions
3. Verify environment variables are correctly set
4. Ensure all dependencies are installed (`pip install -r requirements.txt`)

---

**Last Updated**: October 4, 2025  
**Working State Tag**: `v1.0-working-state-20251004-232548`
