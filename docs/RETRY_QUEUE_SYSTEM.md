# Retry Queue System - Zero API Wastage Strategy

## 🎯 Overview

The retry queue system completely eliminates API wastage by **immediately moving failed URLs to a separate queue** instead of retrying them automatically.

---

## 🔄 How It Works

### **Old System (Wasteful):**
```
URL fails
  ↓
Retry 5 times immediately (5 API calls)
  ↓
Re-queue for later
  ↓
Retry 5 times again (5 API calls)
  ↓
Re-queue one more time
  ↓
Retry 5 times again (5 API calls)
  ↓
Finally give up
───────────────────────────────────
TOTAL: 15 API calls wasted! ❌
```

### **New System (Smart):**
```
URL fails
  ↓
Try once with 2 retries (max 2 API calls)
  ↓
Move to retry-queue.json immediately
  ↓
Continue scraping other URLs
  ↓
Manually review/retry later when ready
───────────────────────────────────
TOTAL: 2 API calls max! ✅
Savings: 87% reduction
```

---

## 📁 Queue Files

Your site will now have TWO queue files:

### **1. `pending-queue.json`** (Active Queue)
- URLs discovered but not yet scraped
- Processed automatically during scraping
- High success rate expected

### **2. `retry-queue.json`** (Failed Queue)  
- URLs that failed to scrape
- Requires manual review
- Process when ready with `--process-retry-queue`

---

## 💰 Cost Impact

### **Example: 100 URLs with 5 failing URLs**

**Old System:**
```
Good URLs: 95 × 2 calls = 190 calls
Bad URLs:   5 × 15 calls = 75 calls
──────────────────────────────────
TOTAL: 265 API calls
Cost: $0.22
```

**New System:**
```
Good URLs: 95 × 2 calls = 190 calls
Bad URLs:   5 × 2 calls = 10 calls  
──────────────────────────────────
TOTAL: 200 API calls ✅
Cost: $0.17
Savings: $0.05 (24%)
```

### **Full Site (6,000 products, 1% failure):**
```
Old System: 6,000 × 2 + 60 × 15 = 12,900 calls = $10.71
New System: 6,000 × 2 + 60 × 2 = 12,120 calls = $10.06 ✅
────────────────────────────────────────────────────────
Savings: $0.65 per full scrape + you can review failures!
```

---

## 🚀 Usage

### **1. Normal Scraping (Automatic)**

Just run your scraping commands as usual:

```bash
source env.local && python3 scripts/update_llms_agnostic.py mydiy.ie \
  --hierarchical https://www.mydiy.ie/power-tools/ \
  --max-products 500 \
  --batch-size 25 \
  --max-batches 4
```

**What happens:**
- ✅ Successful URLs → scraped and saved to shards
- ⚠️ Failed URLs → moved to `retry-queue.json` immediately
- 📊 You see log: `"Failed to scrape {url}; moved to retry queue"`

---

### **2. Check Retry Queue**

See how many URLs failed:

```bash
# Count failed URLs
jq 'length' out/mydiy-ie/retry-queue.json

# View first 5 failed URLs
jq '.[0:5] | .[] | {url: .url, error: .metadata.last_error}' out/mydiy-ie/retry-queue.json
```

**Example output:**
```json
{
  "url": "https://www.mydiy.ie/products/some-product.html",
  "error": "No data returned at 2025-10-05T20:30:15.123Z"
}
```

---

### **3. Review Failed URLs**

Manually check why URLs failed:

```bash
# Get all failed URLs
jq '.[] | .url' out/mydiy-ie/retry-queue.json

# Check if they exist (open in browser)
# Are they 404s? Deleted products? Malformed pages?
```

---

### **4. Process Retry Queue**

When you're ready to retry the failed URLs:

```bash
source env.local && python3 scripts/update_llms_agnostic.py mydiy.ie \
  --process-retry-queue \
  --batch-size 10 \
  --max-batches 5
```

**What happens:**
- Moves all URLs from `retry-queue.json` back to `pending-queue.json`
- Resets attempt counter to 0
- Processes them with fresh retries
- Any that fail again go back to retry queue

---

### **5. Clear Retry Queue (Manual)**

If you've confirmed URLs are permanently broken:

```bash
# Backup first
cp out/mydiy-ie/retry-queue.json out/mydiy-ie/retry-queue-backup.json

# Clear it
echo "[]" > out/mydiy-ie/retry-queue.json
```

---

## 📊 Monitoring

### **During Scraping:**

Watch for these messages:

```bash
✅ "Scraped {url} into shard 'category_name'"  # Success
⚠️ "Failed to scrape {url}; moved to retry queue"  # Failed (saved for later)
📝 "Added to retry queue: {url}"  # Confirmed added
```

### **After Scraping:**

Check status:

```bash
# Summary
echo "Pending queue: $(jq 'length' out/mydiy-ie/pending-queue.json)"
echo "Retry queue: $(jq 'length' out/mydiy-ie/retry-queue.json)"
echo "Total scraped: $(jq '[.[] | length] | add' out/mydiy-ie/llms-mydiy-ie-manifest.json)"
```

**Example output:**
```
Pending queue: 0
Retry queue: 12
Total scraped: 5838
```

**Interpretation:** 5,838 products scraped successfully, 12 failed and waiting for review.

---

## 🎯 Best Practices

### **1. Don't Worry About Failures During Scraping**
- Failed URLs are safely stored
- You can review them later
- Focus on getting the bulk of products first

### **2. Review Retry Queue Periodically**
- After scraping a few categories
- Look for patterns (same category? specific product type?)
- Decide if URLs are worth retrying

### **3. Common Failure Reasons**
| Reason | What to Do |
|--------|------------|
| **404 - Product Deleted** | Remove from retry queue |
| **Timeout** | Retry with `--process-retry-queue` |
| **Malformed Page** | Manually inspect, may need site config fix |
| **Rate Limiting** | Wait a bit, then retry |
| **API Error** | Retry later when API is stable |

### **4. Batch Processing**
```bash
# Process retry queue in small batches
python3 scripts/update_llms_agnostic.py mydiy.ie \
  --process-retry-queue \
  --batch-size 5 \  # Small batches
  --max-batches 2   # Test with just 10 URLs first
```

---

## 🔍 Debugging Failed URLs

### **Get Detailed Error Info:**
```bash
# Show all failures with metadata
jq '.[] | {url: .url, attempts: .metadata.attempts, error: .metadata.last_error, category: .metadata.category_shard_key}' out/mydiy-ie/retry-queue.json
```

### **Group by Category:**
```bash
# See which categories have most failures
jq 'group_by(.metadata.category_shard_key) | map({category: .[0].metadata.category_shard_key, count: length})' out/mydiy-ie/retry-queue.json
```

**Example output:**
```json
[
  {"category": "power_tools", "count": 8},
  {"category": "hand_tools", "count": 4}
]
```

---

## ✅ Benefits Summary

| Feature | Benefit |
|---------|---------|
| **No Automatic Retries** | 87% reduction in wasted API calls |
| **Separate Queue** | Easy to review and manage failures |
| **Manual Control** | Decide when to retry |
| **Pattern Detection** | Identify systemic issues |
| **Cost Savings** | $0.50-$5.00 saved per full site scrape |
| **Peace of Mind** | Nothing is lost, everything tracked |

---

## 🎉 Example Workflow

### **Day 1: Initial Scrape**
```bash
# Scrape all 21 categories
for category in power-tools hand-tools garden-tools ...; do
  python3 scripts/update_llms_agnostic.py mydiy.ie \
    --hierarchical https://www.mydiy.ie/$category/ \
    --max-products 500 \
    --batch-size 25 \
    --max-batches 4
done

# Check results
echo "Scraped: $(jq '[.[] | length] | add' out/mydiy-ie/llms-mydiy-ie-manifest.json)"
echo "Failed: $(jq 'length' out/mydiy-ie/retry-queue.json)"
```

**Result:** 5,800 scraped, 50 in retry queue

---

### **Day 2: Review Failures**
```bash
# View failed URLs
jq '.[] | .url' out/mydiy-ie/retry-queue.json > failed-urls.txt

# Manually check first 10 in browser
# Confirm they're real products, not 404s
```

---

### **Day 3: Retry**
```bash
# Retry all failed URLs
python3 scripts/update_llms_agnostic.py mydiy.ie \
  --process-retry-queue \
  --batch-size 10 \
  --max-batches 10

# Check results again
echo "Still failed: $(jq 'length' out/mydiy-ie/retry-queue.json)"
```

**Result:** 45 succeeded, 5 still failing (probably deleted products)

---

## 🛡️ Safety Features

1. ✅ **Failed URLs never lost** - Always saved to retry-queue.json
2. ✅ **Attempt counter tracks history** - Know how many times it failed
3. ✅ **Error messages preserved** - See exact failure reason
4. ✅ **Category metadata kept** - Know which category it came from
5. ✅ **Manual control** - You decide when to retry
6. ✅ **Batch processing** - Test with small batches first

---

## 🎯 Summary

**Old Way:** Waste 15 API calls per failed URL ❌
**New Way:** Use 2 API calls, save for manual review ✅

**You now have complete control over retries while minimizing API waste!** 🎉

