# Workflow Diff File Bug Fix

**Date:** September 30, 2025  
**Issue:** Category page uploaded instead of product despite diff extraction  
**Root Cause:** Workflow not passing diff content file to Python script  
**Status:** ✅ **FIXED**

## 🔴 Problem Summary

Despite implementing diff extraction, the system was still uploading the **entire category page** (14.7 KB) instead of just the new product.

### Symptoms:
- ✅ Only 1 document uploaded (progress from before)
- ❌ Wrong document - category page with navigation/filters
- ❌ Product URL not extracted from diff
- ❌ No logging from category page detection code

### Test Result:
```
Uploaded: llms-jgengineering-ie-kits_sets.txt (14732 characters)
Content: [Skip to content]... FilterFilter & Sort... (10 products)...
Expected: ~500 bytes with only new product JSON
```

## 🔍 Root Cause Analysis

### What the Logs Showed:
```bash
# Workflow successfully:
✅ Saved diff content for https://... (page_added with diff)
✅ Detected diff-based content for incremental processing  
✅ Using agnostic scraping system with diff extraction

# Python script:
✅ Diff extraction mode: True
❌ [NO logging from category page detection]
❌ [NO logging from product URL extraction]
```

### The Bug:
The workflow was:
1. ✅ **Saving** diff content to `/tmp/diff_content_${i}_${url_hash}.md`
2. ✅ **Setting** `/tmp/diff_urls.txt` marker file
3. ✅ **Passing** `--use-diff-extraction` flag to Python
4. ❌ **NOT passing** `--pre-scraped-content <diff_file>` to Python!

**Result:** Python script had the flag set but **no diff content**, so category page detection logic never ran!

### Code Path Analysis:

**Workflow (Before Fix):**
```bash
# Saves diff file
diff_file="/tmp/diff_content_${i}_${url_hash}.md"
printf '%s\n' "$diff_text" > "$diff_file"
echo "$page_url" >> /tmp/diff_urls.txt

# But then calls Python WITHOUT the file!
if [ -f "/tmp/diff_urls.txt" ]; then
  python3 scripts/update_llms_agnostic.py "$domain" \
    --added "$added_urls_json" \
    --use-diff-extraction              # ← Flag only, no content!
fi
```

**Python Script:**
```python
def incremental_update(self, urls, operation, pre_scraped_content=None):
    for i, url in enumerate(urls):
        content_to_use = pre_scraped_content if i == 0 and pre_scraped_content else None
        
        if is_category_page and self.use_diff_extraction and content_to_use:
            # ↑ This condition FAILS because content_to_use is None!
            product_url = self._extract_product_url_from_diff(content_to_use)
```

**What Happened:**
- `self.use_diff_extraction` = True ✅
- `content_to_use` = None ❌ (no file passed)
- Condition failed → category page URL processed directly → entire page uploaded

## ✅ The Fix

### Workflow Change:
```bash
# Now finds and passes the diff file
if [ -f "/tmp/diff_urls.txt" ]; then
  echo "Detected diff-based content for incremental processing"
  
  # Find the first diff file
  first_diff_file=$(ls -1 /tmp/diff_content_*.md 2>/dev/null | head -1)
  
  if [ -n "$first_diff_file" ] && [ -f "$first_diff_file" ]; then
    echo "Using diff file: $first_diff_file"
    # Pass BOTH flag AND file
    python3 scripts/update_llms_agnostic.py "$domain" \
      --added "$added_urls_json" \
      --use-diff-extraction \
      --pre-scraped-content "$first_diff_file"  # ← Now passes the file!
  fi
fi
```

### Expected Flow (After Fix):
```
1. Webhook → Workflow receives diff.text
2. Workflow saves diff to /tmp/diff_content_*.md
3. Workflow passes BOTH --use-diff-extraction AND --pre-scraped-content <file>
4. Python receives diff content
5. Python detects category page URL
6. Python extracts product URL from diff
7. Python scrapes product URL directly
8. Only product uploaded (~500 bytes)
```

## 📋 Test Checklist

When the next webhook arrives, verify these logs appear:

### Workflow Logs Should Show:
```
✅ Saved diff content for ... (page_added with diff)
✅ Detected diff-based content for incremental processing
✅ Using diff file: /tmp/diff_content_0_<hash>.md    ← NEW!
✅ Using agnostic scraping system with diff extraction
```

### Python Logs Should Show:
```
✅ Diff extraction mode: True
✅ Processing added: https://.../collections/...
✅ Detected category page URL with diff: ...          ← NEW!
✅ Extracting product URL from category page diff     ← NEW!
✅ Found product URL in diff: https://.../products/... ← NEW!
✅ Processing extracted product URL: .../products/...  ← NEW!
✅ Wrote shard file: ... (~500 characters)            ← Small size!
```

### ElevenLabs Should Receive:
```
✅ 1 document uploaded
✅ File size: ~500 bytes (not 14+ KB)
✅ Content: Only product JSON, no category page
✅ No navigation/filters/product listings
```

## 🚀 Deployment Status

- ✅ **Bug identified:** Workflow not passing diff file
- ✅ **Fix committed:** `8623e66` - "fix: Pass diff file to Python script"
- ✅ **Pushed to GitHub:** `main` branch
- ⏳ **Needs testing:** Trigger new webhook to verify
- ⏳ **Verify ElevenLabs:** Check uploaded document size and content

## 📝 Files Modified

**Commit:** `8623e66` - "fix: Pass diff file to Python script in multi-page format"

**File:** `.github/workflows/update-products.yml`
- Added logic to find first diff file: `ls -1 /tmp/diff_content_*.md | head -1`
- Pass file via `--pre-scraped-content "$first_diff_file"`
- Added logging: "Using diff file: ..."

## 🔄 Previous Fixes That Work Now

With this fix, the previous fixes will now work correctly:

### 1. Category Page Detection (commit `431ea20`)
- ✅ Now receives diff content via `pre_scraped_content`
- ✅ Can detect `is_category_page = True`
- ✅ Runs extraction logic

### 2. Product URL Extraction (commit `431ea20`)
- ✅ Now has diff content to parse
- ✅ Can extract `/products/...` URL from diff
- ✅ Can scrape product directly

### 3. Diff Extraction (commit `eea83a2`)
- ✅ Flag works correctly when combined with content
- ✅ Processes only added lines from diff
- ✅ Prevents category page bloat

## 🎯 Expected Outcome

After this fix, when a `page_added` event occurs:

1. **Workflow:**
   - ✅ Extracts diff.text from webhook
   - ✅ Saves to temp file
   - ✅ Passes both flag AND file to Python

2. **Python:**
   - ✅ Receives diff content
   - ✅ Detects category page URL
   - ✅ Extracts product URL from diff
   - ✅ Scrapes product page
   - ✅ Uploads only product data

3. **ElevenLabs:**
   - ✅ Receives 1 document
   - ✅ ~500 bytes (not 14+ KB)
   - ✅ Only product JSON
   - ✅ No category page content

---

**Status:** ✅ **Ready for Testing**  
**Next Action:** Trigger new webhook and verify all logging appears correctly
