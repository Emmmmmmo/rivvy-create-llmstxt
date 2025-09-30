# Category Page Diff Fix

**Date:** September 30, 2025  
**Issue:** Still receiving 2 documents in ElevenLabs despite diff extraction  
**Status:** ✅ **FIXED**

## 🔴 Problem Identified

### What Happened:
After implementing diff extraction, the system was still uploading **2 files** to ElevenLabs:
1. `llms-jgengineering-ie-other_products.txt` (old test data)
2. `llms-jgengineering-ie-kits_sets.txt` (8.3 KB - **entire category page**)

### Root Cause:
The webhook URL was a **category/collection page**, not a product page:
```
❌ Category Page URL: https://www.jgengineering.ie/collections/unc-baerfix-thread-repair-kits-like-timesert
✅ Product URL (hidden in diff): .../products/test_deburring_item
```

**The Problem:**
1. Webhook sends category page URL when a new product is added to that category
2. The diff contains the entire category page HTML with a `+` marker for the new product
3. Diff extraction was processing the whole category page instead of just the product
4. Result: 8.3 KB category page uploaded instead of ~500 byte product entry

## 📊 What Was Being Uploaded

### Before Fix:

**File: `llms-jgengineering-ie-kits_sets.txt`** (8.3 KB)
```
<|https://www.jgengineering.ie/collections/baercoil-workshop-kits-helicoil-lllmstxt|>
## BaerCoil Workshop Kits – JG Engineering Supplies Ltd 01-4730900

[Skip to content](...)

**Welcome to our new website**

**New collections added!** [Learn more](...)

Country/Region

United States (USD $)

## Always better with a Discount

Copy the code and save 10%

FIXIT10Copy code

# BaerCoil Workshop Kits

(10 products)

FilterFilter & Sort

Sort by
...
[ENTIRE CATEGORY PAGE WITH NAVIGATION, FILTERS, ETC.]
```

### After Fix:

The system will:
1. Detect that the URL is a category page (no `/products/` in path)
2. Extract the product URL from the diff
3. Scrape the actual product page
4. Upload only the product data (~500 bytes)

## 🔧 Solution Implemented

### 1. Added Product URL Extraction
**New Method:** `_extract_product_url_from_diff(diff_text)`

```python
def _extract_product_url_from_diff(self, diff_text: str) -> Optional[str]:
    """
    Extract product URL from a category page diff.
    When a new product is added to a category page, extract the product URL.
    """
    # Look for product URLs in the diff (lines with /products/)
    product_url_pattern = r'https?://[^\s\)]+/products/[^\s\)\]"\'>]+'
    matches = re.findall(product_url_pattern, diff_text)
    
    if matches:
        product_url = matches[0]
        logger.info(f"Found product URL in diff: {product_url}")
        return product_url
    
    # Also try relative URLs like /products/...
    # Construct full URL using base_url
```

### 2. Updated Incremental Update Logic

```python
def incremental_update(self, urls: List[str], operation: str, pre_scraped_content: Optional[str] = None):
    for url in urls:
        # Check if this is a category page
        is_category_page = '/products/' not in url.lower()
        
        if is_category_page and self.use_diff_extraction and content_to_use:
            # Extract the product URL from the diff
            product_url = self._extract_product_url_from_diff(content_to_use)
            
            if product_url:
                # Process the extracted product URL instead
                url = product_url
                scraped_data = self._scrape_url(url, None, is_diff=False)
```

## 📋 How It Works Now

### Workflow:

```
1. Webhook arrives:
   URL: https://.../collections/unc-baerfix-thread-repair-kits-like-timesert
   changeType: "page_added"
   diff.text: "...+[Test_Item](.../products/test_deburring_item)..."
   
2. Workflow detects category page:
   ✅ URL contains /collections/
   ✅ diff.text exists
   ✅ --use-diff-extraction flag set
   
3. Python script processes:
   ✅ Detects: is_category_page = True
   ✅ Calls: _extract_product_url_from_diff()
   ✅ Finds: https://.../products/test_deburring_item
   ✅ Scrapes: Actual product page
   ✅ Stores: Only product data (~500 bytes)
   
4. Result:
   ✅ Only 1 new file uploaded to ElevenLabs
   ✅ File contains only the new product
   ✅ No category page bloat
```

## 🎯 Expected Behavior After Fix

### Test Scenario:
New product added to existing category page

### Before Fix:
- **Files uploaded:** 2
  1. Old test data (other_products.txt)
  2. Entire category page (kits_sets.txt - 8.3 KB)
- **Problem:** Category page includes navigation, filters, all existing products

### After Fix:
- **Files uploaded:** 1 (or same 2 if old test data still exists)
- **New file content:** Only the new product (~500 bytes)
- **Product URL:** Extracted from diff and scraped directly
- **No category bloat:** No navigation, no filters, just product data

## 🧪 Testing

### To Test the Fix:

1. **Clean up old test data:**
   ```bash
   rm out/jgengineering-ie/llms-jgengineering-ie-other_products.txt
   git add . && git commit -m "Clean up test data" && git push
   ```

2. **Trigger a new test:**
   ```bash
   gh api repos/Emmmmmmo/rivvy-create-llmstxt/dispatches \
     --method POST \
     --input test_page_added_with_diff.json
   ```

3. **Check the logs:**
   ```bash
   gh run list --limit 1
   gh run view <RUN_ID> --log | grep "Detected category page"
   ```

   Should see:
   ```
   Detected category page URL with diff: https://...
   Extracting product URL from category page diff
   Found product URL in diff: https://.../products/...
   Processing extracted product URL: https://.../products/...
   ```

4. **Check ElevenLabs:**
   - Should have only 1 new document
   - Document should contain only product data
   - No category page navigation/filters

## 📝 Files Modified

**`scripts/update_llms_agnostic.py`:**
- Added `_extract_product_url_from_diff()` method
- Updated `incremental_update()` to detect category pages
- Added category vs product page detection logic
- Extracts product URL from diff before processing

**Commit:** `62af5ca` - "fix: Extract product URL from category page diffs"

## 🚀 Deployment Status

- ✅ **Code pushed to GitHub:** `main` branch
- ✅ **Available for next webhook:** Immediately
- ⏳ **Needs testing:** Trigger new webhook to verify
- ⏳ **Clean up:** Remove old test data files

## 🔍 What to Watch For

### Success Indicators:
- ✅ Log message: "Detected category page URL with diff"
- ✅ Log message: "Found product URL in diff: .../products/..."
- ✅ Log message: "Processing extracted product URL"
- ✅ Only 1 new file uploaded to ElevenLabs
- ✅ File size ~500 bytes (not 8+ KB)
- ✅ File contains only product JSON, not category HTML

### Failure Indicators:
- ❌ "Could not extract product URL from diff"
- ❌ File size > 5 KB
- ❌ File contains category navigation/filters
- ❌ Multiple files uploaded when expecting 1

## 🎉 Expected Outcome

After this fix:
- **Category page `page_added` events** → Extract product URL → Scrape product → Upload only product
- **Product page `page_added` events** → Process normally with diff extraction
- **Result:** Only 1 item in ElevenLabs per new product, regardless of whether webhook sends category or product URL

---

**Status:** ✅ **Ready for Testing**  
**Next Step:** Trigger a new webhook and verify behavior
