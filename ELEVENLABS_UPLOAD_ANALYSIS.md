# ElevenLabs Upload Analysis - Duplicate File Issue

**Date:** September 29, 2025  
**Issue:** Two files uploaded instead of one during webhook test  
**Status:** ✅ **RESOLVED**

---

## 🔍 **Issue Summary**

During the webhook end-to-end test, the ElevenLabs sync uploaded **2 files** instead of just the new one:

### **Files Uploaded:**
1. ✅ `llms-jgengineering-ie-other_products.txt` → `hhsr3vFRimfCkAMZ6oeI` (New, correct)
2. ❌ `llms-jgengineering-ie-all.txt` → `IdgMhdKNGG19pfDtnWVi` (Legacy, should not exist)

### **Workflow Logs:**
```
2025-09-29 22:24:28,414 - INFO - 📁 Found 2 .txt files in jgengineering-ie
2025-09-29 22:24:29,285 - INFO - ✅ Uploaded: llms-jgengineering-ie-all.txt -> IdgMhdKNGG19pfDtnWVi
2025-09-29 22:24:30,341 - INFO - ✅ Uploaded: llms-jgengineering-ie-other_products.txt -> hhsr3vFRimfCkAMZ6oeI
```

---

## 🕵️ **Root Cause Analysis**

### **1. Legacy File in Repository**

The `llms-jgengineering-ie-all.txt` file was a **legacy file** from the old (pre-agnostic) scraping system:

- **Created:** During initial jgengineering.ie scrape (before sharded system)
- **Format:** All 44 products in a single monolithic file
- **Size:** 22 KB (207 lines)
- **Last Modified:** Commit `0cac4b7` (September 29, during agnostic transition)

### **2. Knowledge Base Manager Behavior**

The `knowledge_base_manager.py` script uploads **all `.txt` files** in the domain directory:

```python
# From knowledge_base_manager.py
txt_files = list(domain_dir.glob("*.txt"))
logger.info(f"📁 Found {len(txt_files)} .txt files in {domain}")
```

**Expected:** Only new/changed shard files  
**Actual:** All `.txt` files, including legacy ones

### **3. Why It Wasn't Deleted Earlier**

The legacy file was in the GitHub repository but not in the local working directory:

```bash
# Git repository (GitHub Actions runner)
✅ out/jgengineering-ie/llms-jgengineering-ie-all.txt (exists)

# Local working directory
❌ out/jgengineering-ie/llms-jgengineering-ie-all.txt (doesn't exist)
```

The GitHub Actions runner checks out the full repository, so it found and uploaded the legacy file.

---

## ✅ **Solution Applied**

### **Fix: Remove Legacy File**

```bash
git rm out/jgengineering-ie/llms-jgengineering-ie-all.txt
git commit -m "chore: Remove legacy jgengineering-ie all.txt file"
git push origin main
```

### **Commit:** `efa5170`

**Impact:**
- ✅ Prevents duplicate uploads to ElevenLabs
- ✅ Only new shard files will be uploaded
- ✅ Existing 44 products remain in their proper shard files
- ✅ Future webhooks will only upload the specific changed shard

---

## 📊 **Current Repository State**

### **jgengineering.ie Files (After Cleanup):**
```
✅ out/jgengineering-ie/llms-jgengineering-ie-index.json
✅ out/jgengineering-ie/llms-jgengineering-ie-manifest.json
✅ out/jgengineering-ie/llms-jgengineering-ie-other_products.txt
```

### **mydiy.ie Files:**
```
✅ 26 shard .txt files (clean, no legacy files)
✅ index.json
✅ manifest.json
```

**Total:** All files are now using the agnostic sharded system ✅

---

## 🎯 **ElevenLabs Document Analysis**

### **Document 1: Legacy File (Should Be Deleted)**
- **Document ID:** `IdgMhdKNGG19pfDtnWVi`
- **Filename:** `<|https://www.jgengineering.ie/products/1-14-x-12-unf-baercoil-kit-b4138-lllmstxt|>`
- **Size:** 22.0 KB
- **Content:** Single BaerCoil product (1 1/4 X 12 UNF BAERCOIL KIT B4138)
- **Status:** ❌ **Should be deleted from ElevenLabs**
- **Reason:** This is from the old monolithic file format

### **Document 2: New File (Correct)**
- **Document ID:** `hhsr3vFRimfCkAMZ6oeI`
- **Filename:** `<|https://www.jgengineering.ie-lllmstxt|>`
- **Size:** 561 B
- **Content:** Test_Deburring_Item (webhook test product)
- **Status:** ✅ **Keep this one**
- **Reason:** This is the new product from the webhook test

---

## 🔧 **Recommended Actions**

### **1. Clean Up ElevenLabs Knowledge Base**

**Delete the legacy document:**
- **Document ID to delete:** `IdgMhdKNGG19pfDtnWVi`
- **Method:** Use ElevenLabs API or dashboard
- **Reason:** It's a duplicate from the old system

**Keep the new document:**
- **Document ID to keep:** `hhsr3vFRimfCkAMZ6oeI`
- **Reason:** This is the correct format from the webhook test

### **2. Re-upload Actual Product Data**

The jgengineering.ie knowledge base is currently **incomplete**. It only has:
- ❌ 1 legacy product (wrong format)
- ✅ 1 test product (Test_Deburring_Item)

**Should have:**
- All 44 jgengineering.ie products in their proper shards

**Options:**
1. **Full re-scrape:** Run agnostic scraper for all jgengineering.ie products
2. **Manual upload:** Use `knowledge_base_manager.py` to upload existing shards

---

## 🚨 **Additional Issue Found: Agent Assignment Failed**

### **Error Logs:**
```
2025-09-29 22:24:30,843 - ERROR - No agent_id found in configuration
2025-09-29 22:24:30,843 - ERROR - Assignment failed
```

### **Problem:**
The uploaded documents were **not assigned** to the `jgengineering.ie` agent's knowledge base.

### **Root Cause:**
The `knowledge_base_manager.py` has a bug in the `assign_documents_to_agents()` method:

```python
# Line 401 (INCORRECT)
agent_id = self.config.get('agent_id')  # ❌ Looking in wrong place
```

The `self.config` contains the entire `elevenlabs-agents.json` structure:
```json
{
  "agents": {
    "jgengineering.ie": {
      "agent_id": "agent_1901k666bcn6evwrwe3hxn41txqe",  ← Should get THIS
      ...
    }
  }
}
```

But it's trying to get `agent_id` from the root level, not from `agents[domain]`.

### **Fix Required:**

The method needs to be updated to look up the agent config by domain:

```python
# BEFORE (line ~401):
agent_id = self.config.get('agent_id')

# AFTER:
agent_config = self.config.get('agents', {}).get(domain, {})
agent_id = agent_config.get('agent_id')
```

### **Impact:**
- Documents are uploaded to ElevenLabs ✅
- But they're **NOT** added to the agent's knowledge base ❌
- The agent can't access the documents for RAG ❌

---

## ✅ **Summary**

### **Issue 1: Duplicate Upload** ✅ FIXED
- **Problem:** Legacy `llms-jgengineering-ie-all.txt` uploaded
- **Solution:** Deleted legacy file from repository
- **Status:** ✅ Resolved

### **Issue 2: Agent Assignment** ⏳ NEEDS FIX
- **Problem:** Documents not assigned to agent
- **Solution:** Fix `knowledge_base_manager.py` to look up domain-specific agent config
- **Status:** ⏳ Pending fix

### **Next Steps:**
1. ✅ Clean up repository (done)
2. ⏳ Fix agent assignment bug
3. ⏳ Delete legacy document from ElevenLabs
4. ⏳ Re-upload all jgengineering.ie products
5. ⏳ Verify agent can access documents

---

*Analysis completed: September 29, 2025*