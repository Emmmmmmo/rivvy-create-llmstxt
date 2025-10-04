# Rivvy Create LLMs.txt - Comprehensive Guide

**Status:** ✅ **FULLY OPERATIONAL** | **Version:** 4.0 (Production-Ready with Race Condition Fixes) | **Last Updated:** October 4, 2025

## 🎯 System Overview

This production-ready system provides **fully automated, agnostic web scraping** and LLMs.txt file generation for unlimited websites with integrated ElevenLabs RAG (Retrieval Augmented Generation) capabilities. The system automatically adapts to different website structures, URL patterns, and categorization schemes without requiring code changes.

### Core Architecture
```
Website Changes → rivvy-observer → Webhook → Dynamic Routing → Agnostic Scraping → LLMs Generation → ElevenLabs RAG
```

## 🚀 Key Features

### ✅ **Agnostic Scraping Engine**
- **Configuration-Driven**: Adapts to any website structure via JSON configuration
- **Multi-Level Hierarchy Support**: Handles complex category structures (Main → Sub → Product Category → Product)
- **Intelligent Product Discovery**: Uses Firecrawl's AI-powered link extraction
- **Multiple Product Support**: ⭐ **NEW** - Extracts and processes multiple products from single webhook diff
- **Structured Data Extraction**: Clean JSON output with product name, description, price, availability
- **URL Validation**: Site-specific product URL validation rules
- **Shard Organization**: Category-based file organization matching site structure
- **Quality Assurance**: ⭐ **NEW** - Automatic HTML pollution prevention, EUR currency enforcement, and file size compliance

### ✅ **ElevenLabs RAG Integration**
- **Automatic Document Upload**: Files uploaded to ElevenLabs knowledge base
- **RAG Agent Assignment**: Documents assigned to RAG-enabled agents
- **RAG Indexing Verification**: Automatic verification and retry system
- **Old Version Cleanup**: Prevents document accumulation
- **Unified Management**: Single script for all KB operations

### ✅ **Production-Ready Features**
- **Unlimited Domain Support**: Dynamic domain detection and routing
- **Incremental Updates**: Only processes changed content
- **Error Recovery**: Robust error handling with retry logic
- **Rate Limiting**: Prevents API throttling
- **Concurrent Processing**: GitHub Actions handles multiple domains

## 📁 System Architecture

```
rivvy-create-llmstxt/
├── .github/workflows/
│   └── update-products.yml         # Main workflow with dynamic routing
├── config/
│   ├── site_configs.json          # ⭐ NEW - Agnostic site configurations
│   ├── elevenlabs-agents.json     # ElevenLabs agent mapping
│   └── elevenlabs_sync_state.json # Sync state tracking
├── scripts/
│   ├── update_llms_agnostic.py    # ⭐ NEW - Agnostic scraping engine
│   ├── site_config_manager.py     # ⭐ NEW - Configuration management
│   ├── add_site.py               # ⭐ NEW - Site configuration tool
│   ├── knowledge_base_manager_agnostic.py  # Unified KB management
│   └── [legacy scripts...]        # Backward compatibility
├── out/
│   ├── jgengineering-ie/          # Industrial tools (1,300 products, 37 shards)
│   │   ├── llms-jgengineering-ie-*.txt
│   │   ├── llms-jgengineering-ie-index.json
│   │   └── llms-jgengineering-ie-manifest.json
│   ├── mydiy.ie/                  # DIY products (1,335 products)
│   │   ├── llms-mydiy-ie-*.txt
│   │   ├── llms-mydiy-ie-index.json
│   │   └── llms-mydiy-ie-manifest.json
│   └── [new-domain.com]/          # Auto-generated for new sites
├── requirements.txt
└── README.md
```

## ⚙️ Agnostic Configuration System

### Site Configuration Structure

Each website has a configuration in `config/site_configs.json`:

```json
{
  "sites": {
    "mydiy.ie": {
      "name": "My DIY Ireland",
      "base_url": "https://www.mydiy.ie",
      "url_patterns": {
        "product": "/products/",
        "category": "/power-tools/",
        "subcategory": "/power-tools/angle-grinders-wall-chasers-and-metalworking-tools/"
      },
      "product_url_validation": {
        "required_pattern": "/products/",
        "required_suffix": ".html",
        "min_length": 10,
        "excluded_suffixes": [".jpg", ".png", ".gif", ".webp", ".jpeg"]
      },
      "shard_extraction": {
        "method": "path_segment",
        "segment_index": 1,
        "fallback_method": "product_categorization"
      },
      "url_filters": {
        "include_patterns": ["product", "power-tools", "hand-tools"],
        "exclude_patterns": ["admin", "api", "cart", "checkout"],
        "max_depth": 4
      },
      "product_categories": {
        "power_tools": ["drill", "saw", "grinder", "sander"],
        "hand_tools": ["hammer", "screwdriver", "wrench"],
        "garden_tools": ["shovel", "rake", "pruner"],
        "other_products": []
      },
      "elevenlabs_agent": "mydiy.ie"
    }
  }
}
```

### Configuration Fields

| Field | Description | Example |
|-------|-------------|---------|
| `name` | Human-readable site name | "My DIY Store" |
| `base_url` | Site's base URL | "https://mydiy.ie" |
| `url_patterns` | URL structure patterns | `{"product": "/products/"}` |
| `product_url_validation` | Rules for identifying product URLs | `{"required_pattern": "/products/"}` |
| `shard_extraction` | How to extract category from URLs | `{"method": "path_segment", "segment_index": 1}` |
| `url_filters` | What URLs to include/exclude | `{"include_patterns": ["product"]}` |
| `product_categories` | Category keywords for classification | `{"tools": ["drill", "saw"]}` |
| `elevenlabs_agent` | ElevenLabs agent name | "mydiy.ie" |

## 🔧 Shard Extraction Methods

### 1. Path Segment Method
Extracts category from URL path segments:
- URL: `https://example.com/categories/electronics/phones`
- Segment index 1: `electronics`
- Segment index 2: `phones`

### 2. Product Categorization Method
Uses product name keywords to determine category:
- Product: "Bosch Professional Drill"
- Keywords: `["drill", "saw", "grinder"]` → `power_tools`

## 🚀 Quick Start

### 1. Add a New Site

```bash
# Interactive configuration
python3 scripts/add_site.py example.com

# Or create a template
python3 scripts/add_site.py example.com --template
```

### 2. Scrape the Site

```bash
# Full crawl
python3 scripts/update_llms_agnostic.py example.com --full

# Auto-discover products from a category page
python3 scripts/update_llms_agnostic.py example.com --auto-discover https://example.com/category/

# Hierarchical discovery (for complex sites)
python3 scripts/update_llms_agnostic.py example.com --hierarchical https://example.com/main-category/

# Incremental updates
python3 scripts/update_llms_agnostic.py example.com --added '["https://example.com/product1"]'
```

### 3. Upload to ElevenLabs

```bash
# Upload and assign to agent
python3 scripts/knowledge_base_manager_agnostic.py sync --domain example.com

# Or just upload
python3 scripts/knowledge_base_manager_agnostic.py upload --domain example.com
```

## 📊 Currently Supported Sites

### Active Sites

| Site | Domain | Products | Categories | Status |
|------|--------|----------|------------|--------|
| JG Engineering | jgengineering.ie | 1,300 | Thread repair, tools, fasteners | ✅ Active |
| My DIY | mydiy.ie | 1,335 | Power tools, hand tools, garden | ✅ Active |

### Site-Specific Features

#### **mydiy.ie** - Complex Multi-Level Hierarchy
- **4-Level Structure**: Main Category → Subcategory → Product Category → Product
- **Hierarchical Discovery**: Automatically navigates complex category structures
- **Fallback Logic**: Direct product scraping when subcategories contain products
- **Clean JSON Output**: Structured product data with Euro symbol support

#### **jgengineering.ie** - Production-Ready Quality
- **1,300 Products**: Complete product catalog with clean data
- **37 Shard Files**: Properly organized by collection categories
- **Quality Assured**: No HTML pollution, EUR pricing, working URLs
- **ElevenLabs Ready**: All files under 300k character limit
- **Thread Repair Focus**: Specialized in industrial tools and fasteners

## 🔧 Quality Assurance & Production Fixes

### ⭐ **NEW: Production-Ready Quality System**

The system now includes comprehensive quality assurance features that ensure clean, production-ready data:

#### **Automatic HTML Pollution Prevention**
- **Product-Only Processing**: Only URLs containing `/products/` are processed
- **Collection Page Filtering**: Collection/category pages are automatically skipped
- **Clean JSON Output**: No HTML artifacts in generated shard files

#### **Currency Standardization**
- **EUR Enforcement**: All Firecrawl requests use `?currency=EUR` parameter
- **Consistent Pricing**: All prices displayed in Euro (€) format
- **URL Parameter Preservation**: Currency parameter maintained during URL normalization

#### **File Size Compliance**
- **ElevenLabs Limit**: Automatic splitting of files over 300k characters
- **Smart Sharding**: Large collections split into multiple compliant files
- **Manifest Updates**: Automatic manifest updates for split shards

#### **URL Quality**
- **Suffix Removal**: No more `-lllmstxt` suffixes in URLs
- **Working Links**: All URLs point to actual product pages
- **Proper Formatting**: Clean, normalized URLs in all files

### Quality Verification Tools

#### **Comprehensive Verification Script**
```bash
# Verify all shards for quality issues
python3 scripts/verify_all_shards.py jgengineering-ie
```

#### **Shard Splitting for Large Files**
```bash
# Split files over 300k characters
python3 scripts/split_large_shard.py jgengineering-ie 300000
```

#### **Data Recovery from Index**
```bash
# Recover shard files from index data
python3 scripts/recover_shards_from_index.py jgengineering-ie
```

### Quality Metrics

**Current jgengineering.ie Quality Score: 100/100**
- ✅ **1,300 products** with clean JSON data
- ✅ **37 shard files** all under 300k limit
- ✅ **0 HTML pollution** detected
- ✅ **1,299 EUR prices** (99.9% coverage)
- ✅ **0 USD prices** found
- ✅ **0 collection pages** in shards

## 🛠 Advanced Usage

### Hierarchical Discovery

For complex sites with multi-level category structures:

```bash
# Discover all subcategories and products
python3 scripts/update_llms_agnostic.py mydiy.ie --hierarchical https://www.mydiy.ie/power-tools/ --max-categories 10

# Limit processing for testing
python3 scripts/update_llms_agnostic.py mydiy.ie --hierarchical https://www.mydiy.ie/garden-tools/ --max-products 5 --max-categories 3
```

### Custom URL Filtering

```json
{
  "url_filters": {
    "include_patterns": ["product", "item", "shop"],
    "exclude_patterns": ["admin", "api", "cart", "checkout"],
    "max_depth": 4
  }
}
```

### Product URL Validation

```json
{
  "product_url_validation": {
    "required_pattern": "/products/",
    "required_suffix": ".html",
    "min_length": 10,
    "excluded_suffixes": [".jpg", ".png", ".gif", ".webp", ".jpeg"]
  }
}
```

### Incremental Updates

```bash
# Add new products
python3 scripts/update_llms_agnostic.py example.com --added '["https://example.com/new-product"]'

# Update changed products
python3 scripts/update_llms_agnostic.py example.com --changed '["https://example.com/updated-product"]'

# Remove products
python3 scripts/update_llms_agnostic.py example.com --removed '["https://example.com/old-product"]'
```

## 🤖 ElevenLabs RAG Integration

### Unified Knowledge Base Manager

The system features a comprehensive `knowledge_base_manager_agnostic.py` script:

#### **Available Commands:**
- `upload` - Upload files to knowledge base
- `assign` - Assign documents to agents  
- `sync` - Complete sync (upload + assign + verify RAG)
- `verify-rag` - Check RAG indexing status
- `retry-rag` - Retry failed RAG indexing
- `list` - List documents in knowledge base
- `search` - Search documents by criteria
- `remove` - Remove documents by date/ID (basic)
- `delete` - Delete documents with advanced options
- `stats` - Show knowledge base statistics

#### **Workflow Examples:**

```bash
# Complete sync with RAG verification (Recommended)
python3 scripts/knowledge_base_manager_agnostic.py sync --domain mydiy.ie

# Upload only
python3 scripts/knowledge_base_manager_agnostic.py upload --domain mydiy.ie

# Verify RAG indexing status
python3 scripts/knowledge_base_manager_agnostic.py verify-rag

# Retry failed RAG indexing
python3 scripts/knowledge_base_manager_agnostic.py retry-rag

# Delete documents (advanced options)
python3 scripts/knowledge_base_manager_agnostic.py delete --all-domains --dry-run
python3 scripts/knowledge_base_manager_agnostic.py delete --domain mydiy.ie --count 10
python3 scripts/knowledge_base_manager_agnostic.py delete --date 2025-09-26
```

### Key Features

1. **RAG Indexing Verification** ⭐ **NEW**
   - Automatic verification of RAG indexing status
   - Identifies failed documents and retries automatically
   - Comprehensive reporting of indexing results
   - Handles RAG storage limit issues

2. **Automatic Cleanup**
   - Removes old versions when files are updated
   - Prevents knowledge base from growing indefinitely
   - Essential for high-volume, frequent updates

3. **Extended Retry Logic**
   - Progressive retry intervals: 15sec → 30min
   - Handles RAG indexing delays gracefully
   - Production-ready for timing issues

4. **Incremental Sync**
   - Only processes changed files
   - Hash-based change detection
   - Efficient for webhook-driven updates

## 🔄 Webhook Integration

### Webhook Processing Flow

1. **Change Detection**: rivvy-observer detects changes on monitored websites
2. **Content Scraping**: Observer scrapes and analyzes the changed content
3. **Webhook Sent**: Observer sends webhook with pre-scraped content to GitHub repository
4. **Dynamic Routing**: Workflow extracts domain and creates appropriate directory
5. **Diff Extraction**: ⭐ **NEW** - For `page_added` events, extracts all new product URLs from category page diff
6. **Multiple Product Processing**: ⭐ **NEW** - Each extracted product URL processed individually
7. **Agnostic Processing**: Uses site configuration to determine scraping strategy
8. **Content Processing**: Generates LLMs files with proper categorization
9. **Shard Assignment**: All products from same category assigned to same shard
10. **File Organization**: Files saved to `out/{domain}/` with proper structure
11. **ElevenLabs Sync**: Generated files automatically uploaded to RAG system
12. **Git Commit**: Changes committed and pushed to repository

### Multiple Product Support ⭐ **NEW**

When a category page is updated with multiple new products, the system:

1. **Detects Category Page Update**: Identifies webhook with `changeType: "page_added"` or `"content_modified"`
2. **Extracts All Product URLs**: Parses diff to find all newly added product links
3. **Processes Each Product**: Scrapes each product page individually
4. **Assigns to Shard**: All products from same category go to same shard
5. **Updates Files**: Shard file rewritten with existing + new products
6. **Syncs to ElevenLabs**: Updated shard sent as single document

**Key Benefits:**
- ✅ Handles 1, 2, 3, or more products in single webhook
- ✅ Efficient processing - each product scraped individually
- ✅ Proper categorization - maintains shard structure
- ✅ No duplicates - intelligent deduplication
- ✅ Backward compatible - works for single product additions

### Webhook Format

```json
{
  "event_type": "website_changed",
  "client_payload": {
    "website": {
      "name": "Website Name",
      "url": "https://www.yoursite.com"
    },
    "change": {
      "changeType": "content_changed|content_modified|page_added|page_removed",
      "summary": "Brief description of changes",
      "diff": {
        "added": ["New content added"],
        "removed": ["Old content removed"]
      }
    },
    "scrapeResult": {
      "title": "Page title",
      "description": "Page description",
      "markdown": "Pre-scraped content (used instead of re-scraping)"
    }
  }
}
```

## 📊 Generated Files

### File Structure Per Domain

```
out/domain.com/
├── llms-domain-com-{category}.txt    # Sharded product files
├── llms-domain-com-index.json        # URL metadata
└── llms-domain-com-manifest.json     # Shard mappings
```

### Content Format

#### **Product Files** (`llms-domain-com-{category}.txt`)
Clean JSON format with structured product data:

```json
{
  "url": "https://www.mydiy.ie/products/bosch-professional-drill.html",
  "product_name": "Bosch Professional Drill GSB 18V-21",
  "description": "Professional cordless drill with 18V battery...",
  "price": "€154.99",
  "availability": "In Stock",
  "specifications": {
    "voltage": "18V",
    "battery_type": "Lithium-ion",
    "weight": "1.2kg"
  }
}
```

#### **Index File** (`llms-domain-com-index.json`)
URL metadata and tracking:

```json
{
  "https://example.com/product1": {
    "title": "Product Name",
    "shard": "power_tools",
    "updated_at": "2025-09-29T22:00:00Z"
  }
}
```

#### **Manifest File** (`llms-domain-com-manifest.json`)
Shard organization:

```json
{
  "power_tools": [
    "https://example.com/product1",
    "https://example.com/product2"
  ],
  "hand_tools": [
    "https://example.com/product3"
  ]
}
```

## 🚨 Troubleshooting

### Common Issues & Solutions

1. **No URLs found during mapping**
   - Check `url_filters.include_patterns`
   - Verify `base_url` is correct
   - Check if site requires authentication

2. **Products not categorized correctly**
   - Update `product_categories` keywords
   - Check `shard_extraction.segment_index`
   - Verify URL structure

3. **Hierarchical discovery not finding subcategories**
   - Check `_is_subcategory_url` logic
   - Verify URL depth patterns
   - Test with `--max-categories` limit

4. **ElevenLabs upload fails**
   - Check `elevenlabs_agent` configuration
   - Verify agent exists in `config/elevenlabs-agents.json`
   - Check API key permissions

5. **RAG indexing issues**
   - Use `verify-rag` command to check status
   - Retry failed indexing with `retry-rag`
   - Check RAG storage limits per agent

### Debug Mode

```bash
# Enable verbose logging
python3 scripts/update_llms_agnostic.py example.com --full --verbose

# Check configuration
python3 scripts/site_config_manager.py --validate example.com

# Test with small subset
python3 scripts/update_llms_agnostic.py example.com --auto-discover https://example.com/category/ --max-products 5
```

## 📈 Performance Metrics

### Current Performance
- **Processing Time**: ~3-5 minutes per domain (including RAG sync and verification)
- **File Generation**: ~1-2 minutes for typical e-commerce sites
- **ElevenLabs Sync**: ~2-3 minutes (including cleanup, retry logic, and RAG verification)
- **RAG Verification**: ~30-60 seconds for 100+ documents
- **Concurrent Domains**: Unlimited (GitHub Actions handles concurrency)

### Optimization Features
- **Incremental Processing**: Only changed content processed
- **Hash-based Detection**: Efficient change detection
- **Batch Processing**: Multiple pages processed together
- **Rate Limiting**: Prevents API throttling
- **URL Deduplication**: Prevents redundant scraping

## 🔒 Security Considerations

- Store API keys in `env.local` file
- Use HTTPS URLs only
- Respect robots.txt (implement if needed)
- Add rate limiting for large crawls
- Validate all input URLs and configurations

## 🔧 Recent Improvements & Fixes (October 2025)

### ✅ **Race Condition Resolution**
**Problem**: Concurrent GitHub Actions runs were causing merge conflicts and sync state corruption.

**Solutions Implemented**:
- **Concurrency Control**: Added `cancel-in-progress: false` to prevent premature workflow cancellation
- **Atomic Git Operations**: Implemented retry logic with `git pull --rebase` before critical operations
- **File Locking**: Added `fcntl` file locking for sync state read/write operations
- **Atomic File Writes**: Used `tempfile` and `shutil.move` for atomic sync state updates

**Result**: ✅ Eliminated all race conditions and merge conflicts in concurrent runs

### ✅ **Automatic Old Version Cleanup**
**Problem**: Old document versions were accumulating in ElevenLabs, causing confusion and storage bloat.

**Solution Implemented**:
- **Pre-Upload Deletion**: System now deletes old document versions before uploading new ones
- **Rollback Logic**: Failed uploads restore previous document IDs to prevent data loss
- **Hash-Based Detection**: Only processes files that have actually changed
- **Sync State Tracking**: Maintains accurate document ID mapping

**Result**: ✅ Clean ElevenLabs knowledge base with no duplicate documents

### ✅ **Domain Key Normalization**
**Problem**: Inconsistent domain key handling (dotted vs hyphenated) caused sync mismatches.

**Solution Implemented**:
- **Standardized Format**: All domain keys now use hyphenated format (e.g., `jgengineering-ie`)
- **Automatic Reconciliation**: System merges entries from dotted keys into hyphenated equivalents
- **Validation**: Sync state validation ensures consistent key formatting

**Result**: ✅ Consistent domain handling across all components

### ✅ **Enhanced Error Handling**
**Problem**: API response format changes and missing fields caused system failures.

**Solutions Implemented**:
- **Fallback Logic**: Multiple fallback options for Firecrawl API response fields
- **KeyError Prevention**: Safe dictionary access with `.get()` methods and defaults
- **Comprehensive Logging**: Detailed error messages with context for debugging
- **Graceful Degradation**: System continues processing even if individual URLs fail

**Result**: ✅ Resilient system that handles API changes and edge cases

### ✅ **Sync State Validation & Recovery**
**Problem**: Corrupted sync state files caused incorrect behavior and data loss.

**Solutions Implemented**:
- **Integrity Checks**: Validates sync state structure and required fields
- **Automatic Recovery**: Fixes common sync state issues automatically
- **Backup Creation**: Creates backup files before major operations
- **Validation Logging**: Detailed logging of sync state operations

**Result**: ✅ Robust sync state management with automatic recovery

### ✅ **Observer Integration Improvements**
**Problem**: Duplicate monitoring entries and inefficient collection management.

**Solutions Implemented**:
- **Duplicate Prevention**: Checks existing URLs before adding to observer
- **Batch Processing**: Efficient handling of multiple collection additions
- **Summary Reporting**: Clear feedback on added vs skipped collections
- **Error Handling**: Graceful handling of observer API failures

**Result**: ✅ Clean observer integration with no duplicates

### ✅ **Workflow Reliability Enhancements**
**Problem**: Workflow failures due to Git conflicts and timing issues.

**Solutions Implemented**:
- **Retry Logic**: Automatic retry with exponential backoff for failed operations
- **Conflict Resolution**: Automatic resolution of common Git conflicts
- **State Synchronization**: Ensures latest state before critical operations
- **Comprehensive Logging**: Detailed workflow execution logs

**Result**: ✅ Reliable workflow execution with minimal manual intervention

## 🎯 Future Enhancements

### Planned Features
- [ ] Multi-language support
- [ ] Advanced content filtering
- [ ] Performance analytics dashboard
- [ ] Custom RAG model selection
- [ ] Automated site configuration detection

### Potential Improvements
- [ ] Parallel domain processing
- [ ] Advanced caching mechanisms
- [ ] Real-time monitoring
- [ ] Custom webhook formats
- [ ] Machine learning for product categorization

## 🛠️ Troubleshooting Guide

### Common Issues & Solutions

#### **Issue: All Files Being Re-uploaded Instead of Just Changed Ones**
**Symptoms**: GitHub Actions logs show "uploaded_count: 38" instead of "uploaded_count: 1"
**Causes**: 
- Sync state corruption or missing entries
- Domain key mismatch (dotted vs hyphenated)
- Hash comparison failures

**Solutions**:
```bash
# 1. Check sync state integrity
cat config/elevenlabs_sync_state.json | jq .

# 2. Verify domain key format (should be hyphenated)
grep -o '"jgengineering-ie"' config/elevenlabs_sync_state.json

# 3. Reset sync state if corrupted
python3 scripts/knowledge_base_manager_agnostic.py delete --all-domains
python3 scripts/knowledge_base_manager_agnostic.py sync --domain jgengineering-ie
```

#### **Issue: Old Documents Not Being Deleted from ElevenLabs**
**Symptoms**: Multiple versions of same document in ElevenLabs knowledge base
**Causes**: 
- Automatic cleanup logic not working
- Sync state missing previous document IDs

**Solutions**:
```bash
# 1. Check if automatic cleanup is enabled
grep -n "Deleting old version" scripts/knowledge_base_manager_agnostic.py

# 2. Manually clean up duplicates
python3 scripts/knowledge_base_manager_agnostic.py list --domain jgengineering-ie
python3 scripts/knowledge_base_manager_agnostic.py delete --ids OLD_DOCUMENT_ID --force
```

#### **Issue: GitHub Actions Workflow Failures with Merge Conflicts**
**Symptoms**: Workflow fails with "merge conflict" errors
**Causes**: 
- Concurrent workflow runs
- Race conditions in Git operations

**Solutions**:
```bash
# 1. Check workflow concurrency settings
grep -A 3 "concurrency:" .github/workflows/update-products.yml

# 2. Verify retry logic is in place
grep -n "git pull --rebase" .github/workflows/update-products.yml

# 3. Manual conflict resolution if needed
git pull --rebase origin main
git push origin main
```

#### **Issue: Firecrawl API KeyError: 'markdown'**
**Symptoms**: Workflow fails with missing 'markdown' field errors
**Causes**: 
- Firecrawl API response format changes
- Missing fallback logic

**Solutions**:
```bash
# 1. Check fallback logic is implemented
grep -n "\.get.*markdown" scripts/update_llms_agnostic.py

# 2. Verify error handling
grep -A 5 "KeyError" scripts/update_llms_agnostic.py
```

#### **Issue: Observer Adding Duplicate Collections**
**Symptoms**: Same collection appears multiple times in observer
**Causes**: 
- Script not checking for existing URLs
- Observer API not preventing duplicates

**Solutions**:
```bash
# 1. Check duplicate prevention logic
grep -n "check_url_exists" scripts/add_jgengineering_collections_updated.sh

# 2. Manually remove duplicates from observer
curl -X DELETE "https://rivvy-observer.vercel.app/api/websites/DUPLICATE_ID" \
  -H "Authorization: Bearer $OBSERVER_API_KEY"
```

### Diagnostic Commands

#### **System Health Check**
```bash
# Check all components are working
echo "=== System Health Check ==="
echo "1. Sync State Integrity:"
cat config/elevenlabs_sync_state.json | jq 'keys' | wc -l

echo "2. ElevenLabs Connection:"
python3 scripts/knowledge_base_manager_agnostic.py list --domain jgengineering-ie | head -5

echo "3. Observer Integration:"
curl -s -X GET "https://rivvy-observer.vercel.app/api/websites" \
  -H "Authorization: Bearer $OBSERVER_API_KEY" | jq '.data | length'

echo "4. Workflow Configuration:"
grep -c "cancel-in-progress: false" .github/workflows/update-products.yml
```

#### **Sync State Analysis**
```bash
# Analyze sync state for issues
echo "=== Sync State Analysis ==="
echo "Total domains: $(cat config/elevenlabs_sync_state.json | jq 'keys | length')"
echo "Total files tracked: $(cat config/elevenlabs_sync_state.json | jq '[.[] | keys] | flatten | length')"
echo "Domain keys: $(cat config/elevenlabs_sync_state.json | jq 'keys')"
```

### Recovery Procedures

#### **Complete System Reset**
```bash
# 1. Backup current state
git tag -a "backup-$(date +%Y%m%d-%H%M%S)" -m "Backup before reset"

# 2. Clean ElevenLabs
python3 scripts/knowledge_base_manager_agnostic.py delete --all-domains

# 3. Reset sync state
echo '{"jgengineering-ie": {}}' > config/elevenlabs_sync_state.json

# 4. Re-upload all documents
python3 scripts/knowledge_base_manager_agnostic.py sync --domain jgengineering-ie

# 5. Commit changes
git add . && git commit -m "System reset completed"
```

#### **Restore from Working State**
```bash
# Restore to last known working state
git checkout v1.0-working-state-20251004-232548
git checkout -b restore-$(date +%Y%m%d)
git push origin HEAD
```

## 📞 Support & Maintenance

### Monitoring
- **GitHub Actions**: Monitor workflow runs
- **ElevenLabs Dashboard**: Check agent status
- **Logs**: Review processing logs for issues
- **Sync State**: Monitor `config/elevenlabs_sync_state.json` for corruption

### Maintenance Tasks
- **Regular**: Monitor sync state file size and integrity
- **Periodic**: Review agent configurations and document counts
- **As Needed**: Update API keys and secrets
- **Configuration**: Update site configs for new patterns
- **Weekly**: Run system health check diagnostic commands

## 🎉 System Status: FULLY OPERATIONAL

**The agnostic scraping system is production-ready with comprehensive ElevenLabs RAG integration, automatic cleanup functionality, and robust error handling. The system can handle unlimited domains with complex category structures and frequent updates.**

### Key Achievements
- ✅ **Agnostic scraping engine** adapts to any website structure
- ✅ **Multi-level hierarchy support** for complex e-commerce sites
- ✅ **Multiple product extraction** from single webhook diff (NEW)
- ✅ **Structured data extraction** with clean JSON output
- ✅ **Automatic old version cleanup** prevents document accumulation
- ✅ **RAG indexing verification** with automatic retry system
- ✅ **Unified knowledge base management** with comprehensive tooling
- ✅ **Production-ready scalability** for high-volume, frequent updates

---

*This document serves as the comprehensive guide for the agnostic scraping system and ElevenLabs RAG integration.*
