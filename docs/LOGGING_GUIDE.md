# Logging Guide - Understanding Your Scraping Output

## 📋 Overview

The script now provides **clear, visible logging** for all operations, especially when skipping URLs.

---

## 🎨 Log Message Types

### **✅ Success Messages (INFO)**
```
✅ "Scraped {url} into shard 'category_name'"
✅ "Queued {count} new URLs for scraping"
✅ "Processed: {count} URLs"
```

### **⏭️ Skip Messages (INFO)**
```
⏭️ "Skipping already-scraped URL: {url}"
⏭️ "Skipped {count} already-scraped URLs"
⏭️ "Skipped {count} duplicate URLs (already in queue)"
```

### **⚠️ Warning Messages**
```
⚠️ "Failed to scrape {url}; moved to retry queue"
⚠️ "Failed: {count} URLs (moved to retry queue)"
⚠️ "Timeout scraping {url}, will retry..."
```

### **❌ Error Messages**
```
❌ "Error scraping {url}: {error}"
❌ "No data for {url} after 1 attempts; will not re-queue"
```

---

## 📊 Example Output

### **During Discovery Phase:**

```bash
$ python3 scripts/update_llms_agnostic.py mydiy.ie \
  --hierarchical https://www.mydiy.ie/power-tools/ \
  --max-products 500 \
  --batch-size 25 \
  --max-batches 4
```

**Output:**
```
2025-10-05 21:00:00 - INFO - Initialized for My DIY Ireland (mydiy.ie)
2025-10-05 21:00:00 - INFO - Retry queue initialized with 0 URLs
2025-10-05 21:00:00 - INFO - Starting hierarchical discovery from: https://www.mydiy.ie/power-tools/
2025-10-05 21:00:00 - INFO - Level 1: Discovering subcategories...
2025-10-05 21:00:05 - INFO - Found 37 subcategories

2025-10-05 21:00:05 - INFO - Level 2 (1/37): Processing subcategory: https://www.mydiy.ie/power-tools/drills-cordless-drills
2025-10-05 21:00:08 - INFO - Found 12 product categories using SCRAPE API
2025-10-05 21:00:08 - INFO - Found 12 product categories in subcategory

2025-10-05 21:00:08 - INFO - Level 3 (1/12): Processing product category: https://www.mydiy.ie/power-tools/drills-cordless-drills/18v-drills/
2025-10-05 21:00:08 - INFO - Auto-discovering products from: https://www.mydiy.ie/power-tools/drills-cordless-drills/18v-drills/
2025-10-05 21:00:10 - INFO - Using Firecrawl scrape to discover product URLs...
2025-10-05 21:00:12 - INFO - Found 50 product URLs using scrape with links
2025-10-05 21:00:12 - INFO - Found 50 product URLs, 50 unique URLs to process

📊 Discovery Summary: 50 URLs found
   ⏭️  Skipped 9 already-scraped URLs
   🔁 Skipped 41 duplicate URLs (already in queue)
   ✅ Queued 0 new URLs for scraping

2025-10-05 21:00:15 - INFO - Processing batch 1/4 with 25 queued URLs
2025-10-05 21:00:15 - INFO - ⏭️  Skipping already-scraped URL: https://www.mydiy.ie/products/dewalt-drill-123.html
2025-10-05 21:00:15 - INFO - ⏭️  Skipping already-scraped URL: https://www.mydiy.ie/products/makita-drill-456.html
2025-10-05 21:00:16 - INFO - Scraped https://www.mydiy.ie/products/bosch-drill-789.html into shard 'drills_cordless_drills'
2025-10-05 21:00:17 - INFO - Scraped https://www.mydiy.ie/products/milwaukee-drill-012.html into shard 'drills_cordless_drills'
...

📊 Batch Summary:
   ✅ Processed: 21 URLs
   ⏭️  Skipped: 4 already-scraped URLs
   ⚠️  Failed: 0 URLs (moved to retry queue)
   📦 Queue remaining: 16 URLs
```

---

## 🔍 What Each Section Means

### **1. Initialization**
```
INFO - Initialized for My DIY Ireland (mydiy.ie)
INFO - Retry queue initialized with 0 URLs
```
**Meaning:** Script started, queues loaded

---

### **2. Discovery Phase**
```
INFO - Level 1: Discovering subcategories...
INFO - Found 37 subcategories
```
**Meaning:** Finding all subcategories under main category

---

### **3. URL Discovery**
```
INFO - Found 50 product URLs using scrape with links
INFO - Found 50 product URLs, 50 unique URLs to process
```
**Meaning:** Discovered product URLs from category page

---

### **4. Discovery Summary** ⭐
```
📊 Discovery Summary: 50 URLs found
   ⏭️  Skipped 9 already-scraped URLs
   🔁 Skipped 41 duplicate URLs (already in queue)
   ✅ Queued 0 new URLs for scraping
```

**Meaning:**
- **50 URLs found:** Total discovered
- **9 skipped (already-scraped):** These are in your shards already ✅
- **41 skipped (duplicates):** These are in pending queue already ✅
- **0 queued:** No new URLs to scrape (all are handled!)

---

### **5. Individual Skip Messages**
```
INFO - ⏭️  Skipping already-scraped URL: https://www.mydiy.ie/products/dewalt-drill-123.html
```

**Meaning:** This specific URL was already scraped and is in your shards

---

### **6. Batch Summary** ⭐
```
📊 Batch Summary:
   ✅ Processed: 21 URLs
   ⏭️  Skipped: 4 already-scraped URLs
   ⚠️  Failed: 0 URLs (moved to retry queue)
   📦 Queue remaining: 16 URLs
```

**Meaning:**
- **Processed 21:** Successfully scraped 21 new products
- **Skipped 4:** Found 4 URLs already in shards (safety check)
- **Failed 0:** No failures (great!)
- **Remaining 16:** 16 URLs still in queue for next batch

---

## 🎯 Interpreting Skip Statistics

### **High Skip Rate is GOOD!** ✅

```
📊 Discovery Summary: 100 URLs found
   ⏭️  Skipped 95 already-scraped URLs  ← GOOD! Skip system working!
   ✅ Queued 5 new URLs for scraping
```

**This means:**
- Your skip system is working perfectly
- Only 5 new products found (most already scraped)
- No API calls wasted on the 95 existing products

---

### **Low Skip Rate on First Run** ✅

```
📊 Discovery Summary: 100 URLs found
   ⏭️  Skipped 0 already-scraped URLs  ← Expected on first run
   ✅ Queued 100 new URLs for scraping
```

**This means:**
- First time scraping this category
- All 100 are new products
- This is expected and correct

---

### **Mixed Results** ✅

```
📊 Discovery Summary: 100 URLs found
   ⏭️  Skipped 60 already-scraped URLs
   🔁 Skipped 20 duplicate URLs (already in queue)
   ✅ Queued 20 new URLs for scraping
```

**This means:**
- 60 products already in shards (from previous scrape)
- 20 products already queued (might be processing now)
- 20 new products discovered (will scrape these)

---

## 📈 Monitoring During Scraping

### **What to Watch For:**

#### **✅ Good Signs:**
```
✅ "Scraped {url} into shard"  ← Products being saved
⏭️  "Skipped X already-scraped URLs"  ← Skip system working
📦 "Queue remaining: 0 URLs"  ← Queue emptying
```

#### **⚠️ Warning Signs (OK in small numbers):**
```
⚠️  "Failed: 2 URLs (moved to retry queue)"  ← Some failures (< 5% is normal)
⚠️  "Timeout scraping {url}"  ← Slow page (occasional is OK)
```

#### **🚨 Concerning Signs:**
```
❌ "Error scraping {url}"  ← Repeated on many URLs
⚠️  "Failed: 25 URLs"  ← High failure rate (> 10%)
```

If you see concerning signs:
1. Check your internet connection
2. Check if MyDIY.ie is accessible
3. Check Firecrawl API status
4. Review retry queue for patterns

---

## 🔍 Verbose Mode

For even more detail, add `--verbose`:

```bash
python3 scripts/update_llms_agnostic.py mydiy.ie \
  --hierarchical https://www.mydiy.ie/power-tools/ \
  --max-products 100 \
  --batch-size 10 \
  --max-batches 1 \
  --verbose
```

**Additional output:**
```
DEBUG - EUR currency URL: {url} -> {eur_url}
DEBUG - Extracted 0 added lines from diff
DEBUG - Using product pattern '/products/' from site config
DEBUG - Found X product categories using SCRAPE API
```

---

## 📊 End-of-Run Summary (JSON)

At the very end, you get a JSON summary:

```json
{
  "operation": "hierarchical_discovery",
  "processed_urls": 85,
  "total_urls": 150,
  "subcategories_processed": 37,
  "touched_shards": ["drills_cordless_drills", "sanders", "grinders"],
  "written_files": [
    "out/mydiy-ie/llms-mydiy-ie-drills_cordless_drills.txt",
    "out/mydiy-ie/llms-mydiy-ie-sanders.txt",
    "out/mydiy-ie/llms-mydiy-ie-grinders.txt"
  ],
  "batch": {
    "operation": "process_queue_batch",
    "processed_urls": 85,
    "skipped_existing": 12,
    "failed_urls": [],
    "queue_size": 0,
    "batches_executed": 4
  }
}
```

**Key metrics:**
- `processed_urls: 85` - Successfully scraped
- `skipped_existing: 12` - Skipped (already in shards)
- `failed_urls: []` - No failures (empty array is good!)
- `queue_size: 0` - Queue is empty

---

## 🎯 Quick Reference

| Log Message | Meaning | Action |
|-------------|---------|--------|
| ⏭️ Skipping already-scraped | URL in shards | ✅ No action (working as designed) |
| 🔁 Skipped duplicate | URL in queue | ✅ No action (working as designed) |
| ✅ Scraped into shard | Success! | ✅ No action (great!) |
| ⚠️ Moved to retry queue | Failed once | ⚠️ Review retry queue later |
| ❌ Error scraping | Exception occurred | 🔍 Check logs for details |
| 📦 Queue remaining: 0 | Done! | 🎉 Move to next category |

---

## 💡 Tips

### **1. Redirect Logs to File**
```bash
python3 scripts/update_llms_agnostic.py mydiy.ie \
  --hierarchical https://www.mydiy.ie/power-tools/ \
  --max-products 500 \
  --batch-size 25 \
  --max-batches 4 \
  2>&1 | tee scraping.log
```

Now you can review later:
```bash
# See all skips
grep "Skipping" scraping.log

# Count skips
grep "Skipping" scraping.log | wc -l

# See failures
grep "Failed" scraping.log
```

---

### **2. Monitor in Real-Time**
```bash
# In another terminal
tail -f scraping.log | grep -E "Skipping|Scraped|Failed"
```

---

### **3. Count Operations**
```bash
# After scraping, analyze log
echo "Scraped: $(grep 'Scraped.*into shard' scraping.log | wc -l)"
echo "Skipped: $(grep 'Skipping already-scraped' scraping.log | wc -l)"
echo "Failed: $(grep 'moved to retry queue' scraping.log | wc -l)"
```

---

## 🎉 Summary

**You now have:**
- ✅ Visible skip messages (INFO level, no --verbose needed)
- ✅ Discovery summaries (see stats immediately)
- ✅ Batch summaries (know what happened each batch)
- ✅ Clear emoji indicators (⏭️ ✅ ⚠️ ❌)
- ✅ JSON output (machine-readable at end)

**Your logs will clearly show:**
- What's being skipped (and why)
- What's being scraped
- What's failing
- What's remaining

**No more guessing!** 📊✨

