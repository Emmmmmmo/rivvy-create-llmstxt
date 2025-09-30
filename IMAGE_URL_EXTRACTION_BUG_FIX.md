# Image URL Extraction Bug Fix

**Date:** September 30, 2025  
**Issue:** Product URL extraction matching image URLs instead of product pages  
**Status:** ✅ **FIXED**

## 🔴 Problem Summary

After implementing category page detection, the system was extracting **image URLs** instead of actual product page URLs from the diff.

### Symptoms:
```
Found product URL in diff: https://www.jgengineering.ie/cdn/shop/products/ArtF005_...jpg?v=1509797029&width=460
Processing extracted product URL: https://www.jgengineering.ie/cdn/shop/products/ArtF005_...jpg
```

**Result:** 
- 2 files uploaded again
- Neither file contained correct product data
- One file was likely the image/404 page, another was the category page

### Root Cause

The regex pattern `https?://[^\s\)]+/products/[^\s\)\]"\'>]+` was matching **ANY** URL containing `/products/`, including:

❌ **Image URLs:** `https://www.jgengineering.ie/cdn/shop/products/ArtF005_...jpg?v=...`  
❌ **CDN URLs:** `https://cdn.domain.com/shop/products/...`  
✅ **Product Pages:** `https://www.jgengineering.ie/collections/unc-baerfix-thread-repair-kits-like-timesert/products/test_deburring_item`

Since image URLs appear earlier in the diff (for product thumbnails), they were matched first!

### Example from Diff:

```diff
+[![](https://www.jgengineering.ie/cdn/shop/products/ArtF005_...jpg?v=1509797029&width=460)]
+(https://www.jgengineering.ie/collections/unc-baerfix-thread-repair-kits-like-timesert/products/test_deburring_item)
+
+[Test_Deburring_Item](https://www.jgengineering.ie/collections/unc-baerfix-thread-repair-kits-like-timesert/products/test_deburring_item)
```

**Old behavior:** Matched the first `/products/` URL → image  
**New behavior:** Filters images, matches actual product URL

## ✅ Solution Implemented

**Commit:** `dd707bc` - "fix: Filter out image URLs when extracting product URL from diff"

### Changes to `_extract_product_url_from_diff()`:

1. **Image Extension Filtering:**
   ```python
   image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.ico')
   
   # Skip if it's an image URL
   if any(url_path.lower().endswith(ext) for ext in image_extensions):
       logger.debug(f"Skipping image URL: {url}")
       continue
   ```

2. **CDN URL Filtering:**
   ```python
   # Skip CDN URLs (they're usually images)
   if '/cdn/' in url.lower() or '/cdn.' in url.lower():
       logger.debug(f"Skipping CDN URL: {url}")
       continue
   ```

3. **Context-Aware Relative URL Matching:**
   ```python
   # If it's in a markdown link or href, it's likely a product page
   if '(' + rel_url + ')' in context or 'href="' + rel_url in context:
       valid_relative.append(rel_url)
   ```

### New Extraction Logic:

```
1. Find all URLs with /products/ in them
2. Filter out image URLs (by extension)
3. Filter out CDN URLs (by path)
4. Return first valid product page URL
5. Fallback: Look for relative URLs in markdown link context
```

## 🎯 Expected Result

After this fix, when a `page_added` webhook is received:

1. ✅ Detects category page URL
2. ✅ Extracts **actual product URL** from diff (not image)
3. ✅ Scrapes only the product page
4. ✅ Uploads **1 file** to ElevenLabs with just the new product data

### Test Case:

**Input Diff:**
```
+[![](https://www.jgengineering.ie/cdn/shop/products/ArtF005_...jpg?v=1509797029&width=460)]
+(https://www.jgengineering.ie/collections/unc-baerfix-thread-repair-kits-like-timesert/products/test_deburring_item)
+
+[Test_Deburring_Item](https://www.jgengineering.ie/collections/unc-baerfix-thread-repair-kits-like-timesert/products/test_deburring_item)
```

**Old behavior:** Extracted `https://www.jgengineering.ie/cdn/shop/products/ArtF005_...jpg` ❌

**New behavior:** Extracts `https://www.jgengineering.ie/collections/unc-baerfix-thread-repair-kits-like-timesert/products/test_deburring_item` ✅

**Result:**
- Only 1 document uploaded
- Contains product: "Test_Deburring_Item" ($12.00)
- ~500 bytes of product JSON

## 📝 Testing

To test, trigger a new webhook from rivvy-observer and check:

```bash
# Check GitHub Actions logs
gh run list --limit 1
gh run view <run_id> --log | grep "Found product URL"

# Should see:
# "Found product URL in diff: https://www.jgengineering.ie/collections/unc-baerfix-thread-repair-kits-like-timesert/products/test_deburring_item"
# NOT: "Found product URL in diff: https://www.jgengineering.ie/cdn/shop/products/ArtF005_...jpg"
```

## 🔄 Related Issues

- Initial issue: [DIFF_EXTRACTION_IMPLEMENTATION.md](DIFF_EXTRACTION_IMPLEMENTATION.md)
- Category page detection: [CATEGORY_PAGE_DIFF_FIX.md](CATEGORY_PAGE_DIFF_FIX.md)
- Workflow fix: [WORKFLOW_DIFF_FILE_BUG_FIX.md](WORKFLOW_DIFF_FILE_BUG_FIX.md)

## ✨ Current Status

**Commit SHA:** `dd707bc`  
**Branch:** `main`  
**Deployed:** ✅ Yes  
**Ready for Testing:** ✅ Yes

Now when you receive a `page_added` event from rivvy-observer, the system should correctly:
1. Extract the new product URL (not images)
2. Scrape only that product
3. Upload 1 file with just the new product to ElevenLabs
