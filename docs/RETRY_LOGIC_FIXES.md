# Retry Logic Fixes - API Wastage Prevention

## 🚨 Issues Found and Fixed

### **Before (Excessive Retries):**
```
URL fails consistently:
  Queue Attempt 1: 5 API retries = 5 calls
  Queue Attempt 2: 5 API retries = 5 calls  
  Queue Attempt 3: 5 API retries = 5 calls
  ────────────────────────────────────────
  TOTAL: 15 API calls wasted per bad URL!
```

### **After (Optimized Retries):**
```
URL fails consistently:
  Queue Attempt 1: 2 API retries = 2 calls
  Queue Attempt 2: 2 API retries = 2 calls
  ────────────────────────────────────────
  TOTAL: 4 API calls max per bad URL ✅
  
  Savings: 73% reduction in wasted API calls!
```

---

## 🔧 Changes Made

### **Change 1: Reduced API-Level Retries**
**File:** `scripts/update_llms_agnostic.py` Line 886

**Before:**
```python
response = retry_with_backoff(make_request, max_retries=5, initial_delay=3)
```

**After:**
```python
# Reduced from 5 to 2 retries per attempt
response = retry_with_backoff(make_request, max_retries=2, initial_delay=3)
```

**Impact:** 60% reduction in immediate retries

---

### **Change 2: Reduced Queue-Level Attempts**
**File:** `scripts/update_llms_agnostic.py` Line 1158

**Before:**
```python
if attempts >= 3:  # Give up after 3 attempts
```

**After:**
```python
if attempts >= 2:  # Give up after 2 attempts
```

**Impact:** 33% reduction in queue attempts

---

## 📊 Cost Impact Analysis

### **Scenario: 100 URLs with 5% failure rate (5 bad URLs)**

**Before fixes:**
```
Good URLs: 95 × 1 call = 95 calls
Bad URLs:   5 × 15 calls = 75 calls
────────────────────────────────────
TOTAL: 170 API calls
Cost @ $0.000830/call: $0.141
```

**After fixes:**
```
Good URLs: 95 × 1 call = 95 calls
Bad URLs:   5 × 4 calls = 20 calls
────────────────────────────────────
TOTAL: 115 API calls ✅
Cost @ $0.000830/call: $0.095
Savings: $0.046 (32% reduction)
```

### **For Full Site (6,000 new products, 5% failure):**
```
Before: 5,700 + (300 × 15) = 10,200 calls = $8.47
After:  5,700 + (300 × 4) = 6,900 calls = $5.73 ✅
────────────────────────────────────────────────
Savings: $2.74 (32% reduction in total cost)
```

---

## ✅ Retry Strategy Summary

### **Current Optimized Strategy:**

1. **First Attempt:**
   - Try URL once
   - If fails: retry up to 2 times with exponential backoff
   - Total: Max 2 API calls

2. **Second Attempt (if queued):**
   - Try URL again
   - If fails: retry up to 2 times with exponential backoff
   - Total: Max 2 API calls

3. **After 2 Queue Attempts:**
   - Mark as failed permanently
   - Add to `failed-urls.json`
   - No more retries

**Total Max:** 4 API calls per problematic URL

---

## 🎯 What This Protects Against

1. ✅ **Deleted Products** - Products removed from site won't waste 15 API calls
2. ✅ **Broken Links** - 404 errors fail fast instead of endless retries
3. ✅ **Timeouts** - Slow-loading pages give up after 4 attempts instead of 15
4. ✅ **API Limits** - Rate-limited requests won't hammer the API
5. ✅ **Malformed Pages** - Pages that consistently fail to parse stop quickly

---

## 🧪 Testing Recommendations

### **Test 1: Normal Products (Should Work)**
```bash
# Test with a known good category
source env.local && python3 scripts/update_llms_agnostic.py mydiy.ie \
  --hierarchical https://www.mydiy.ie/garden-tools/ \
  --max-products 50 \
  --batch-size 10 \
  --max-batches 1
```

**Expected:** All products scrape successfully with 1 API call each

### **Test 2: Check Failed URLs**
```bash
# After scraping, check if any URLs failed
jq 'length' out/mydiy-ie/llms-mydiy-ie-failed-urls.json

# View failed URLs to see if they're legitimate failures
jq '.' out/mydiy-ie/llms-mydiy-ie-failed-urls.json
```

**Expected:** Very few failed URLs (< 1% failure rate)

---

## 📝 Monitoring During Scraping

Watch for these log messages:

### **Good Signs:**
```
✅ "Scraped {url} into shard 'category_name'"
✅ "Skipping already-scraped URL: {url}"
```

### **Warning Signs (1-2 times is OK):**
```
⚠️ "No data returned for {url}; re-queued (attempt 1)"
```

### **Concerning Signs (investigate these):**
```
🚨 "No data for {url} after 2 attempts; will not re-queue"
```

If you see many of the concerning messages, check `failed-urls.json` to see if there's a pattern (e.g., all from one category).

---

## 💡 Additional Safety Features

The script also has these built-in protections:

1. **Skip System** - Never scrapes URLs already in index (0 wasted API calls)
2. **Duplicate Detection** - Never queues same URL twice
3. **Exponential Backoff** - Waits longer between retries (3s, 6s, 12s)
4. **502 Error Handling** - Only retries server errors, not client errors
5. **Queue Persistence** - Failed URLs saved for manual review

---

## 🎉 Summary

**Before:** Up to 15 API calls per problematic URL
**After:** Max 4 API calls per problematic URL

**Cost Savings:** 73% reduction in wasted API calls on failures
**Safety:** 100% - Skip system prevents re-scraping existing products

You're now protected against massive API wastage! 🛡️

