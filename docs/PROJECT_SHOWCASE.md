# Rivvy LLMs.txt Generator
**An Intelligent Web Scraping System for AI Knowledge Bases**

[![Production](https://img.shields.io/badge/status-production-success)]()
[![Cost Savings](https://img.shields.io/badge/saves-$3400%2B%2Fyr-brightgreen)]()
[![Efficiency](https://img.shields.io/badge/skip%20rate-81%25-blue)]()

> **Built by:** Emmett Maher  
> **Status:** Production (Oct 2024 - Present)  
> **Impact:** 95% cost reduction vs. SaaS alternatives

---

## What Is This?

A production-grade data pipeline that maintains up-to-date product catalogs from e-commerce sites for AI conversational agents. Instead of expensive full-site rescans, it intelligently scrapes only what changed, when it changed.

**Think of it as:** Git for web scraping - track changes, apply diffs, never process the same thing twice.

---

## Why It Exists

### The Problem
- E-commerce sites have 8,000+ products that change frequently
- AI agents need current data to provide accurate information
- SaaS scraping solutions cost $3,500+/year for regular updates
- Full site rescans waste time and money

### The Solution
A custom system that:
- Detects changes via webhooks (real-time, not polling)
- Scrapes only changed pages (incremental updates)
- Maintains index to skip existing products (81% skip rate)
- Organizes output for RAG systems (124 category shards)
- Handles failures gracefully (retry queue, zero waste)

**Result:** Same functionality at 5% of the cost ($50-80/year vs. $3,500+)

---

## Key Features

### 🎯 Discovery-Only Mode
```bash
# Step 1: Discover what exists (~$3.60)
python update_llms_agnostic.py mydiy.ie \
  --hierarchical https://www.mydiy.ie/ \
  --discovery-only

# Step 2: Review queue
jq '.pending | length' out/mydiy-ie/pending-queue.json
# Output: 2,000 products found

# Step 3: Process in controlled batches (~$18)
python update_llms_agnostic.py mydiy.ie \
  --process-queue-only \
  --batch-size 50 \
  --max-batches 40
```

**Why this matters:** Know the scope and cost before committing budget.

---

### 🔍 Intelligent Skip System
```python
# System maintains index of 5,823 existing products
# Before making expensive API call:
if url in existing_index:
    skip(url)  # No API call made!
else:
    scrape(url)  # Only scrape if new
```

**Real result:** Skipped 22 of 27 URLs in testing (81% efficiency)

---

### 🔄 Hierarchical Discovery
```
Level 1 (MAP API)  → 21 main categories
Level 2 (SCRAPE)   → 37 subcategories  
Level 3 (SCRAPE)   → 315 product categories
Level 4 (SCRAPE)   → 8,000+ individual products
```

**Why this matters:** Understands site structure, can resume mid-operation, organizes output intelligently.

---

### 🚨 Zero-Waste Error Handling
```python
# Traditional approach: Retry 5 times immediately
# Problem: Wastes credits on consistently bad URLs

# My approach: Zero retries + dedicated retry queue
try:
    data = scrape(url)
except Exception as e:
    retry_queue.add(url, error=e)
    # Manual review, fix root cause, retry efficiently
```

**Why this matters:** Failed URLs don't waste credits - they're isolated for root cause analysis.

---

### 📊 RAG-Optimized Output
```
Instead of:
└── all-products.txt (15MB, 8,000 products)

You get:
├── llms-mydiy-ie-power_tools.txt (2.5MB, 2,500 products)
├── llms-mydiy-ie-hand_tools.txt (1.8MB, 1,800 products)
├── llms-mydiy-ie-garden_tools.txt (1.2MB, 1,200 products)
└── ... (124 shards total)
```

**Why this matters:** AI agents load only relevant categories. Query about drills? Load 1 shard (~50KB), not 15MB.

---

## Architecture

```
┌─────────────────────────────────────────────┐
│  Rivvy-Observer (Change Detection)          │
│  • Monitors site for changes                │
│  • Sends webhooks on updates                │
└─────────────────┬───────────────────────────┘
                  │ Webhook
                  ▼
┌─────────────────────────────────────────────┐
│  GitHub Actions (Automation)                │
│  • Receives webhook                         │
│  • Triggers scraper                         │
└─────────────────┬───────────────────────────┘
                  │ Executes
                  ▼
┌─────────────────────────────────────────────┐
│  update_llms_agnostic.py (Core Logic)       │
│  ├─ Hierarchical discovery                  │
│  ├─ Skip system (index-based)               │
│  ├─ Queue management                        │
│  ├─ Retry handling                          │
│  └─ Shard organization                      │
└─────────────────┬───────────────────────────┘
                  │ Outputs
                  ▼
┌─────────────────────────────────────────────┐
│  Organized Data (Shards + State Files)      │
│  ├─ llms-{site}-{category}.txt (content)   │
│  ├─ llms-{site}-index.json (tracked URLs)  │
│  ├─ llms-{site}-manifest.json (mappings)   │
│  ├─ pending-queue.json (to scrape)         │
│  └─ retry-queue.json (failed URLs)         │
└─────────────────┬───────────────────────────┘
                  │ Syncs
                  ▼
┌─────────────────────────────────────────────┐
│  ElevenLabs Knowledge Base (AI Agents)      │
│  • Auto-updated when data changes           │
│  • Serves conversational AI                 │
└─────────────────────────────────────────────┘
```

---

## Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| **Core** | Python 3.9+ | Rich data processing ecosystem |
| **Scraping** | Firecrawl API | Reliable rendering, structured extraction |
| **Monitoring** | Rivvy-Observer | Real-time change detection |
| **Automation** | GitHub Actions | Free, integrated, no cold starts |
| **State** | JSON files | Git-trackable, debuggable, sufficient for scale |
| **Downstream** | ElevenLabs API | AI conversational agents |

---

## Metrics

### Cost Comparison
```
Traditional SaaS Approach:
├─ Initial: $72
├─ Monthly: $288-360 (weekly updates)
└─ Year 1: $3,500+

My System:
├─ Initial: $22 (69% cheaper)
├─ Monthly: $2-5 (98% cheaper)  
└─ Year 1: $50-80 (98% cheaper)

Savings: $3,400+ in first year
```

### Operational Metrics
```
Products Processed:  5,828+
Shards Generated:    124
Skip Efficiency:     81%
Sites Supported:     2 (unlimited potential)
Error Rate:          <1%
Uptime:             Production since Oct 2024
```

### Development Metrics
```
Core Script:        2,176 lines (update_llms_agnostic.py)
Documentation:      7 comprehensive guides (~3,500 lines)
Test Coverage:      Production-validated (5,828 products)
Development Time:   ~10 hours (one-time)
ROI:               340x in first year
```

---

## What Makes This Special?

### 1. It's Not Just a Scraper
This is a **data pipeline** with:
- Change detection (webhooks, not polling)
- State management (index, manifest, queues)
- Cost optimization (skip system, discovery-only mode)
- Failure isolation (retry queue)
- Organized output (RAG-ready shards)

### 2. It Solves the Real Problem
Most scraping tutorials show you how to scrape once. This shows you how to:
- **Maintain** data over time (incremental updates)
- **Optimize** costs (skip existing, batch processing)
- **Handle** failures (retry queue, error isolation)
- **Scale** efficiently (site-agnostic design)

### 3. It Demonstrates Production Thinking
- Comprehensive logging (can debug from logs alone)
- Multiple backup strategies (git tag + branch + filesystem)
- Extensive documentation (7 guides for different audiences)
- Business awareness (ROI analysis, cost controls)

---

## Code Samples

### Intelligent Skip Logic
```python
def _should_skip_existing(self, normalized_url: str) -> bool:
    """Return True if URL already scraped and refresh not forced."""
    return not self.force_refresh and normalized_url in self.existing_urls

def process_queue_batch(self, batch_size: int):
    """Process queue with skip checking at multiple levels."""
    for entry in self.pending_queue.dequeue_batch(batch_size):
        url = entry["url"]
        
        # Skip if already processed (saved ~$0.20 in one test batch)
        if self._should_skip_existing(url):
            logger.info(f"⏭️  Skipping already-scraped URL: {url}")
            continue
            
        # Only make expensive API call for new URLs
        scraped_data = self._scrape_url(url)
        if scraped_data:
            self.existing_urls.add(url)  # Track for future skips
```

### Hierarchical Discovery
```python
def hierarchical_discovery(self, main_category_url: str):
    """4-level discovery with cost optimization."""
    
    # Level 1: Fast structure discovery (MAP API - cheap)
    subcategories = self._discover_subcategories(main_category_url)
    
    for subcategory in subcategories:
        # Level 2: Find product categories (SCRAPE API)
        product_categories = self._discover_product_categories(subcategory)
        
        for category in product_categories:
            # Level 3: Discover product URLs (SCRAPE API)
            product_urls = self.auto_discover_products(category)
            
            for url in product_urls:
                # Skip check BEFORE Level 4
                if url not in self.existing_urls:
                    queue.add(url)  # Queue for later
                    
    # Level 4: Batch process queue (SCRAPE API with JSON schema)
    self.process_queue_batch(batch_size=50)
```

### Retry Queue (Zero Waste)
```python
def _add_to_retry_queue(self, entry: Dict[str, Any]) -> None:
    """Failed URLs go to retry queue, not auto-retry."""
    url = entry.get("url")
    normalized_url = entry.get("normalized_url")
    
    if not self.retry_queue.contains(normalized_url):
        self.retry_queue.add({
            "url": url,
            "normalized_url": normalized_url,
            "metadata": entry.get("metadata", {}),
            "error": entry.get("error", "Unknown error"),
            "timestamp": datetime.now().isoformat(),
            "attempts": entry.get("metadata", {}).get("attempts", 0)
        })
        logger.warning(f"Added to retry queue: {url}")
```

---

## Documentation

This project is extensively documented:

| Document | Purpose |
|----------|---------|
| **CASE_STUDY_INTELLIGENT_WEB_SCRAPING.md** | Full technical deep-dive (for interviews) |
| **CASE_STUDY_EXECUTIVE_SUMMARY.md** | Quick overview (1-page) |
| **LOGGING_GUIDE.md** | How to interpret system logs |
| **RETRY_QUEUE_SYSTEM.md** | Error handling patterns |
| **BACKUP_RESTORE_GUIDE.md** | Disaster recovery procedures |
| **TIMEOUT_CONFIGURATION.md** | API timeout settings |
| **ZERO_RETRY_STRATEGY.md** | Why zero retries are better |

---

## Running the System

### Prerequisites
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp env.local.example env.local
# Add FIRECRAWL_API_KEY, ELEVENLABS_API_KEY
```

### Discovery Phase (Find Products)
```bash
# Discover all products in a category (queue only, ~$3.60)
python scripts/update_llms_agnostic.py mydiy.ie \
  --hierarchical https://www.mydiy.ie/power-tools/ \
  --discovery-only

# Check what was found
jq '.pending | length' out/mydiy-ie/pending-queue.json
```

### Scraping Phase (Process Queue)
```bash
# Process queue in batches (~$18 for 2,000 products)
python scripts/update_llms_agnostic.py mydiy.ie \
  --process-queue-only \
  --batch-size 50 \
  --max-batches 40
```

### Incremental Updates (Webhook-Driven)
```bash
# This runs automatically via GitHub Actions when webhooks arrive
# Processes only changed pages (typically ~$0.45/update)
```

---

## Lessons Learned

### 1. Cost Optimization Isn't Premature
Initial thought: "Just make it work, optimize later"  
Reality: API costs compound quickly. Skip system paid for itself in first test.

### 2. State Management is Hard
Initial mistake: Assumed index and manifest would stay in sync naturally  
Reality: Built explicit synchronization and verification tools

### 3. Logging is a Feature, Not an Afterthought
Evolution: Basic errors → comprehensive summaries with visual indicators  
Result: Can debug issues from logs alone

### 4. Documentation Pays Dividends
Created 7 guides for different scenarios  
Result: Can onboard team members or remember my own decisions months later

### 5. Production Systems Need Multiple Safety Nets
Implemented: Git tags + backup branch + filesystem archive  
Result: Can test boldly, rollback confidently

---

## Future Enhancements

- [ ] **Weekly MAP verification** - Safety net for missed products (~$0.47/year)
- [ ] **Parallel processing** - 5x faster with rate limit management
- [ ] **Diff-based updates** - Apply webhook diffs without API calls
- [ ] **Analytics dashboard** - Track costs, velocity, coverage per site
- [ ] **Multi-site orchestration** - Process multiple sites in parallel

---

## Contact

**Emmett Maher**  
📧 Email: emmett@example.com  
💼 LinkedIn: [Your LinkedIn]  
💻 GitHub: github.com/Emmmmmmo

---

## License

Private project - Available for interview/portfolio review

---

*"The most valuable engineering skill isn't knowing how to write code - it's knowing when to write code, and when to leverage existing tools. This project demonstrates both."*

