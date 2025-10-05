# API Timeout Configuration

## ⏱️ Overview

All Firecrawl API calls now have **explicit timeouts** to prevent hanging requests and wasted time.

---

## 🔧 Timeout Settings

### **Operation Types & Timeouts:**

| Operation | API Type | Timeout | Reason |
|-----------|----------|---------|--------|
| **MAP (Website)** | `map` | 90 seconds | Large site structure discovery |
| **MAP (Category)** | `map` | 90 seconds | Subcategory discovery can be slow |
| **SCRAPE (Category)** | `scrape` | 60 seconds | Category page rendering |
| **SCRAPE (Product)** | `scrape` | 60 seconds | Product page with images/data |
| **SCRAPE (Links)** | `scrape` | 60 seconds | Link extraction from pages |

---

## 🚨 Why Timeouts Are Critical

### **Before (No Timeouts):**
```
API call hangs indefinitely
  ↓
Script waits forever
  ↓
User has to manually kill process
  ↓
No automatic recovery
  ↓
Progress lost ❌
```

### **After (With Timeouts):**
```
API call starts
  ↓
Timer: 60 seconds
  ↓
If no response → TimeoutError
  ↓
Move to retry queue
  ↓
Continue with next URL ✅
```

---

## 📊 Impact on Your Scraping

### **Scenario: 100 Products, 2 URLs timeout**

**Without Timeouts:**
```
Product 1-50: ✅ (10 minutes)
Product 51: ⏳ Hangs forever...
[Script stuck - requires manual intervention]
```

**With Timeouts:**
```
Product 1-50: ✅ (10 minutes)
Product 51: ⏱️ Timeout after 60s → retry queue
Product 52-100: ✅ (10 minutes)
────────────────────────────────────────────
Total time: 21 minutes instead of stuck!
Failed URLs: 2 in retry queue for later
```

---

## 🎯 Timeout Behavior

### **What Happens on Timeout:**

1. **API Call Made**
   ```python
   response = requests.post(..., timeout=60)
   ```

2. **If Response > 60 seconds**
   ```python
   requests.exceptions.Timeout raised
   ```

3. **Caught by Retry Logic**
   ```python
   # Try with 2 retries (max 2 API calls)
   response = retry_with_backoff(make_request, max_retries=2)
   ```

4. **If Still Fails**
   ```python
   # Move to retry queue
   self._add_to_retry_queue(entry)
   logger.warning("Failed to scrape {url}; moved to retry queue")
   ```

---

## 📈 Timeout Statistics

### **Expected Timeout Rate:**

| Site Speed | Timeout Rate | What It Means |
|------------|--------------|---------------|
| **Fast** | 0-1% | Excellent infrastructure |
| **Normal** | 1-3% | Typical for most sites |
| **Slow** | 3-5% | May need timeout increase |
| **Very Slow** | >5% | Site performance issues |

### **For MyDIY.ie (6,000 products):**
```
Expected timeouts: 60-180 products (1-3%)
Time saved per timeout: 60 seconds
Total time saved: 60-180 minutes! ⏱️
```

---

## ⚙️ Customizing Timeouts

If you find many timeouts on a slow site, you can adjust:

### **Option 1: Increase Timeout (Quick Fix)**

Edit `scripts/update_llms_agnostic.py`:

```python
# Current
timeout=60  # 60 second timeout

# For slower sites
timeout=120  # 120 second timeout
```

### **Option 2: Add Per-Site Configuration**

Add to `config/site_configs.json`:

```json
{
  "mydiy.ie": {
    "timeouts": {
      "map": 120,
      "scrape": 90,
      "scrape_links": 90
    }
  }
}
```

---

## 🔍 Monitoring Timeouts

### **Check Timeout Errors:**

```bash
# During scraping, watch for:
tail -f logs/scraping.log | grep -i "timeout"
```

**Expected messages:**
```
⚠️ "Timeout scraping {url}, will retry..."
⚠️ "Failed to scrape {url}; moved to retry queue"
```

### **Check Retry Queue:**

```bash
# See if URLs are timing out consistently
jq '.[] | select(.metadata.last_error | contains("Timeout"))' out/mydiy-ie/retry-queue.json
```

---

## 🧪 Testing Timeout Behavior

### **Test with a slow site:**

```bash
# Use verbose logging to see timing
source env.local && python3 scripts/update_llms_agnostic.py mydiy.ie \
  --hierarchical https://www.mydiy.ie/power-tools/ \
  --max-products 100 \
  --batch-size 10 \
  --max-batches 1 \
  --verbose
```

**Watch for:**
- How long each API call takes
- Which URLs timeout
- Whether timeouts are consistent (same URLs) or random

---

## 📊 Timeout vs Failure Types

### **Different Error Types:**

| Error Type | Timeout? | Action | Retry? |
|------------|----------|--------|--------|
| **Timeout** | Yes | Retry queue | Manual |
| **404 Not Found** | No | Retry queue | Usually not worth it |
| **500 Server Error** | No | Retry queue | Yes, might be temporary |
| **502 Bad Gateway** | No | Retry with backoff | Yes, temporary |
| **Connection Error** | Yes | Retry queue | Manual |

---

## 💡 Best Practices

### **1. Don't Set Timeouts Too Low**
```python
timeout=10  # ❌ Too aggressive - many false timeouts
timeout=60  # ✅ Good balance
timeout=120 # ✅ For slower sites
```

### **2. Monitor Timeout Patterns**
```bash
# Check how many URLs timeout per category
jq 'group_by(.metadata.category_shard_key) | 
    map({category: .[0].metadata.category_shard_key, 
         timeouts: [.[] | select(.metadata.last_error | contains("Timeout"))] | length})' \
    out/mydiy-ie/retry-queue.json
```

### **3. Retry Timeouts Later**
```bash
# When site is less busy (e.g., off-peak hours)
source env.local && python3 scripts/update_llms_agnostic.py mydiy.ie \
  --process-retry-queue \
  --batch-size 5 \
  --max-batches 10
```

---

## 🎯 Current Timeout Configuration Summary

```python
# Map Operations (Discovery)
MAP_TIMEOUT = 90 seconds
  - Used for: Website structure discovery
  - Used for: Subcategory discovery
  - Reason: Can involve crawling many pages

# Scrape Operations (Content)
SCRAPE_TIMEOUT = 60 seconds
  - Used for: Category pages
  - Used for: Product pages
  - Used for: Link extraction
  - Reason: Single page render + content extraction

# Retry Logic
MAX_RETRIES = 2
INITIAL_DELAY = 3 seconds
BACKOFF_MULTIPLIER = 2
  - 1st retry: after 3 seconds
  - 2nd retry: after 6 seconds
```

---

## 🚀 Benefits

1. ✅ **No hanging scripts** - Always completes or fails gracefully
2. ✅ **Time saved** - Don't wait forever for slow URLs
3. ✅ **Better diagnostics** - Know which URLs are consistently slow
4. ✅ **Automatic recovery** - Continues scraping other URLs
5. ✅ **Manual control** - Retry timeouts when ready

---

## 📝 Troubleshooting

### **Problem: Many timeouts on all URLs**

**Possible causes:**
- Your internet connection is slow
- Firecrawl API is overloaded
- Timeout setting too aggressive

**Solution:**
```python
# Increase timeout temporarily
timeout=120  # Double the timeout
```

---

### **Problem: Specific category always times out**

**Possible causes:**
- Category has very large pages
- Category has many images/videos
- Category structure is complex

**Solution:**
```bash
# Skip that category for now, try later
# Or manually inspect the category URL
```

---

### **Problem: Random timeouts (1-3%)**

**Status:** ✅ **This is normal!**

**Reason:**
- Network fluctuations
- API load variations
- Site performance variations

**Solution:**
- No action needed
- These will be in retry queue
- Process retry queue later

---

## 🎉 Summary

**All 6 API call types now have timeouts configured!**

- **MAP calls:** 90 seconds
- **SCRAPE calls:** 60 seconds
- **Retry logic:** 2 attempts max
- **Total time saved:** Hours of potentially hanging requests

Your scraping is now bulletproof against hanging API calls! ⏱️✅

