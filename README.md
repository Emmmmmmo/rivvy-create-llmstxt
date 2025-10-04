# Rivvy Create LLMs.txt - Agnostic Scraping System

**Status:** ✅ **FULLY OPERATIONAL** | **Version:** 4.0 (Production-Ready with Race Condition Fixes) | **Last Updated:** October 4, 2025

Automatically generate and maintain LLMs.txt files for unlimited websites with **agnostic scraping capabilities** and integrated ElevenLabs RAG (Retrieval Augmented Generation). The system automatically adapts to different website structures, URL patterns, and categorization schemes without requiring code changes.

## 📚 Documentation

**Complete documentation is available in the [`docs/`](./docs/) folder:**

- **[📖 Comprehensive Guide](./docs/COMPREHENSIVE_GUIDE.md)** - Complete system documentation and troubleshooting
- **[🔧 Restoration Guide](./docs/RESTORATION_GUIDE.md)** - System restoration and recovery procedures  
- **[⚙️ Technical Fixes](./docs/TECHNICAL_FIXES_DOCUMENTATION.md)** - Detailed technical implementation
- **[🤖 ElevenLabs Integration](./docs/ELEVENLABS_DOCUMENT_MANAGEMENT.md)** - RAG and knowledge base management
- **[🏗️ Setup Process](./docs/FOUNDATION_SETUP_PROCESS.md)** - Initial system setup guide

**Quick Start**: See [docs/README.md](./docs/README.md) for documentation overview and quick reference.

## 🚀 Overview

This production-ready system provides fully automated LLMs.txt file generation and maintenance for unlimited websites using:

- **⭐ Agnostic Scraping Engine**: Configuration-driven system that adapts to any website structure
- **Multi-Level Hierarchy Support**: Handles complex category structures (Main → Sub → Product Category → Product)
- **Multiple Product Extraction**: ⭐ **NEW** - Processes multiple products from single webhook diff
- **Intelligent Product Discovery**: Uses Firecrawl's AI-powered link extraction and structured data extraction
- **Quality Assurance**: ⭐ **NEW** - Automatic HTML pollution prevention, EUR currency enforcement, and file size compliance
- **Dynamic Webhook Routing**: Automatically routes webhooks to correct domain directories
- **ElevenLabs RAG Integration**: ⭐ **Enhanced** with automatic old version cleanup and RAG verification
- **Change Detection**: Powered by [rivvy-observer](https://github.com/Emmmmmmo/rivvy-observer) for real-time monitoring
- **Production Ready**: Robust error handling, extended retry logic, and scalable architecture
- **Race Condition Fixes**: ⭐ **NEW** - Eliminated all concurrent workflow conflicts and sync state corruption
- **Automatic Cleanup**: ⭐ **NEW** - Clean ElevenLabs knowledge base with no duplicate documents
- **Enhanced Reliability**: ⭐ **NEW** - File locking, atomic operations, and comprehensive error handling

## 🏗 Architecture

```
Website Changes → rivvy-observer → Webhook → Dynamic Routing → Agnostic Scraping → LLMs Generation → ElevenLabs RAG
```

### Components

1. **[rivvy-observer](https://github.com/Emmmmmmo/rivvy-observer)**: Monitors websites for changes
2. **rivvy-create-llmstxt** (this repo): Processes webhooks and generates LLMs files
3. **GitHub Actions**: Orchestrates the entire pipeline
4. **ElevenLabs RAG**: Receives updated knowledge base files

## 📁 Repository Structure

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
│   ├── jgengineering.ie/          # Industrial tools (1,300 products, 37 shards)
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

## ⚡ Quick Start

### 1. Setup Repository

```bash
# Clone the repository
git clone https://github.com/Emmmmmmo/rivvy-create-llmstxt.git
cd rivvy-create-llmstxt

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure GitHub Secrets

Add these secrets to your GitHub repository:

- `FIRECRAWL_API_KEY`: Your Firecrawl API key for web scraping
- `ELEVENLABS_API_KEY`: Your ElevenLabs API key (optional)

### 3. Add a New Site (Agnostic System)

```bash
# Interactive configuration
python3 scripts/add_site.py example.com

# Or create a template
python3 scripts/add_site.py example.com --template
```

### 4. Scrape the Site

```bash
# Full crawl
python3 scripts/update_llms_agnostic.py example.com --full

# Auto-discover products from a category page
python3 scripts/update_llms_agnostic.py example.com --auto-discover https://example.com/category/

# Hierarchical discovery (for complex sites)
python3 scripts/update_llms_agnostic.py example.com --hierarchical https://example.com/main-category/
```

### 5. Upload to ElevenLabs

```bash
# Upload and assign to agent
python3 scripts/knowledge_base_manager_agnostic.py sync --domain example.com
```

### 6. Add Website Monitoring

In your [rivvy-observer](https://github.com/Emmmmmmo/rivvy-observer) configuration:

```json
{
  "websites": {
    "yoursite.com": {
      "url": "https://www.yoursite.com",
      "webhook_target": "https://api.github.com/repos/Emmmmmmo/rivvy-create-llmstxt/dispatches",
      "enabled": true
    }
  }
}
```

## 🔄 How It Works

### Webhook Processing Flow

1. **Change Detection**: rivvy-observer detects changes on monitored websites
2. **Content Scraping**: Observer scrapes and analyzes the changed content
3. **Webhook Sent**: Observer sends webhook with pre-scraped content to GitHub repository
4. **Dynamic Routing**: Workflow extracts domain and creates appropriate directory
5. **Agnostic Processing**: Uses site configuration to determine scraping strategy
6. **Content Processing**: Generates LLMs files with proper categorization and structured data
7. **File Organization**: Files saved to `out/{domain}/` with proper structure
8. **ElevenLabs Sync**: Generated files automatically uploaded to RAG system
9. **Git Commit**: Changes committed and pushed to repository

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

### Supported Change Types

- `content_changed`: Content has been modified
- `content_modified`: Content has been updated  
- `page_added`: New page detected
- `page_removed`: Page has been removed

## 🔧 ElevenLabs Integration Workflow

### ⭐ **NEW: Unified Knowledge Base Manager (Recommended)**

The system now features a comprehensive `knowledge_base_manager_agnostic.py` script that handles all KB operations:

#### **Unified Script: `knowledge_base_manager_agnostic.py`**
- **Purpose**: Complete knowledge base management solution
- **Features**: Upload, assign, verify RAG, retry failed indexing, search, stats
- **Usage**: `python3 scripts/knowledge_base_manager_agnostic.py [command] [options]`

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

### Legacy Scripts (Still Available)

#### **1. Upload Script: `upload_to_knowledge_base.py`**
- **Purpose**: Upload files to ElevenLabs knowledge base
- **Features**: Resume from failures, track progress, handle large files
- **Usage**: `python3 scripts/upload_to_knowledge_base.py [domain] [--force]`

#### **2. Assignment Script: `assign_to_agent_incremental.py`**
- **Purpose**: Assign uploaded files to agents (incremental for large sets)
- **Features**: Batch processing, rate limiting, error recovery
- **Usage**: `python3 scripts/assign_to_agent_incremental.py [domain] [--batch-size=5]`

### Workflow Examples

#### **Complete Sync with RAG Verification (Recommended)**
```bash
# Upload, assign, and verify RAG indexing
python3 scripts/knowledge_base_manager_agnostic.py sync --domain jgengineering.ie
```

#### **Upload Only**
```bash
# Just upload files to knowledge base
python3 scripts/knowledge_base_manager_agnostic.py upload --domain jgengineering.ie
```

#### **Assignment Only**
```bash
# Assign already uploaded files to agent
python3 scripts/knowledge_base_manager_agnostic.py assign --domain jgengineering.ie
```

#### **Verify RAG Indexing**
```bash
# Check RAG indexing status for all documents
python3 scripts/knowledge_base_manager_agnostic.py verify-rag
```

#### **Retry Failed RAG Indexing**
```bash
# Retry failed RAG indexing automatically
python3 scripts/knowledge_base_manager_agnostic.py retry-rag
```

#### **Force Re-upload**
```bash
# Clear sync state and re-upload everything
python3 scripts/knowledge_base_manager_agnostic.py sync --domain jgengineering.ie --force
```

#### **Skip RAG Verification (Faster)**
```bash
# Sync without RAG verification for faster processing
python3 scripts/knowledge_base_manager_agnostic.py sync --domain jgengineering.ie --no-verify-rag
```

#### **Delete Documents (Advanced)**
```bash
# Delete all documents from entire knowledge base (with dry-run)
python3 scripts/knowledge_base_manager_agnostic.py delete --all-domains --dry-run

# Delete N most recent documents for a domain
python3 scripts/knowledge_base_manager_agnostic.py delete --domain jgengineering.ie --count 10

# Delete documents from specific date
python3 scripts/knowledge_base_manager_agnostic.py delete --date 2025-09-26

# Delete specific documents by ID
python3 scripts/knowledge_base_manager_agnostic.py delete --ids doc1 doc2 doc3

# Force delete even if documents are used by agents
python3 scripts/knowledge_base_manager_agnostic.py delete --domain jgengineering.ie --force
```

### Error Recovery

#### **Upload Failed**
```bash
# Retry upload (will skip already uploaded files)
python3 scripts/knowledge_base_manager_agnostic.py upload --domain jgengineering.ie
```

#### **Assignment Failed**
```bash
# Retry assignment (files already uploaded)
python3 scripts/knowledge_base_manager_agnostic.py assign --domain jgengineering.ie
```

#### **RAG Indexing Failed**
```bash
# Check status and retry failed indexing
python3 scripts/knowledge_base_manager_agnostic.py verify-rag
python3 scripts/knowledge_base_manager_agnostic.py retry-rag
```

#### **Large Files Timing Out**
```bash
# Upload with longer timeouts (handled automatically)
python3 scripts/knowledge_base_manager_agnostic.py upload --domain jgengineering.ie
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

## 🤖 ElevenLabs RAG Integration ⭐ **ENHANCED**

### ✅ Production-Ready Features

The system includes **enhanced ElevenLabs RAG integration** with automatic old version cleanup:

- **Automatic Document Upload**: Files uploaded to ElevenLabs knowledge base
- **RAG Agent Assignment**: Documents assigned to RAG-enabled agents
- **Automatic RAG Indexing**: Indexing happens automatically upon assignment
- **⭐ Old Version Cleanup**: Prevents document accumulation with frequent updates
- **Extended Retry Logic**: Handles RAG indexing delays (up to 30 minutes)
- **Production Error Handling**: Robust error recovery and logging

### Agent Configuration

```json
{
  "agents": {
    "toolshop.ie": {
      "agent_id": "agent_toolshop_123",
      "agent_name": "Tool Shop Expert",
      "description": "Specialist in power tools and equipment",
      "enabled": true,
      "sync_enabled": true,
      "categories": ["products", "collections"],
      "max_file_size_mb": 10
    }
  }
}
```

### Enhanced Sync Process

1. **Domain Detection**: System identifies which agent to update
2. **Old Version Cleanup**: ⭐ **NEW** - Removes old versions before adding new ones
3. **File Preparation**: LLMs files prepared with domain prefixes
4. **RAG Upload**: Files uploaded to ElevenLabs knowledge base
5. **Timing Management**: Waits for document processing before assignment
6. **Agent Update**: Conversational AI immediately has latest product info
7. **Automatic Indexing**: RAG indexing happens automatically

### Key Enhancements

- **🧹 Automatic Cleanup**: Prevents document accumulation
- **⏱️ Extended Retry Logic**: Progressive retry intervals (15sec → 30min)
- **📊 Better Error Handling**: Comprehensive logging and recovery
- **🔄 Incremental Updates**: Only processes changed files
- **📈 Scalable**: Handles unlimited files and frequent updates

## 🛠 Manual Operations

### Test Webhook Manually

```bash
# Create test payload
cat > test-webhook.json << EOF
{
  "event_type": "website_changed",
  "client_payload": {
    "website": {
      "name": "Test Site",
      "url": "https://www.example.com"
    },
    "change": {
      "changeType": "content_changed",
      "summary": "Manual test trigger"
    },
    "scrapeResult": {
      "title": "Test Page",
      "description": "Testing webhook trigger",
      "markdown": "# Test Content\n\nThis is a test of the webhook trigger system."
    }
  }
}
EOF

# Send webhook using GitHub CLI
gh api repos/Emmmmmmo/rivvy-create-llmstxt/dispatches --method POST --input test-webhook.json
```

### Monitor Workflows

```bash
# View recent workflow runs
gh run list --limit 10

# View specific run details
gh run view [RUN_ID]

# Check generated files
ls -la out/*/
```

### Add New Domain

1. **Add to rivvy-observer**: Configure monitoring for new website
2. **Add ElevenLabs agent** (optional): Update `config/elevenlabs-agents.json`
3. **Automatic operation**: System handles new domain automatically

## 📈 Currently Supported Sites

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

### Performance Considerations

- **Parallel Processing**: Each domain processed independently
- **Incremental Updates**: Only changed content is reprocessed
- **Rate Limiting**: Built-in delays prevent API throttling
- **Error Recovery**: Failed operations don't affect other domains
- **URL Deduplication**: Prevents redundant scraping

## 🔧 Configuration Options

### Environment Variables

- `FIRECRAWL_API_KEY`: Required for web scraping
- `ELEVENLABS_API_KEY`: Required for RAG integration
- `ONLY_MAIN_CONTENT`: Extract only main content (default: true)

### Agnostic Script Parameters

The agnostic scraping script supports various options:

```bash
# Full crawl
python3 scripts/update_llms_agnostic.py example.com --full

# Auto-discover from category
python3 scripts/update_llms_agnostic.py example.com --auto-discover https://example.com/category/ --max-products 10

# Hierarchical discovery
python3 scripts/update_llms_agnostic.py example.com --hierarchical https://example.com/main-category/ --max-categories 5

# Incremental updates
python3 scripts/update_llms_agnostic.py example.com --added '["https://example.com/product1"]'
```

## 🚨 Troubleshooting

### Common Issues & Solutions

**Webhook not processing:**
- Check GitHub repository dispatch permissions
- Verify webhook payload format matches rivvy-observer format
- Ensure `event_type` is `website_changed`
- Check that required fields (`website.url`, `change.changeType`, `scrapeResult.markdown`) are present
- Check GitHub Actions logs

**Files not generated:**
- Verify Firecrawl API key is set
- Check if URLs are accessible
- Review script error logs
- Check site configuration in `config/site_configs.json`

**ElevenLabs sync issues:**
- ✅ **RAG Indexing Delays**: **SOLVED** - Extended retry logic handles timing issues
- ✅ **Document Accumulation**: **SOLVED** - Automatic cleanup prevents accumulation
- ✅ **RAG Storage Limits**: **SOLVED** - Automatic verification and retry system
- ✅ **Failed Indexing**: **SOLVED** - Built-in retry mechanism for failed documents
- Verify API key and agent ID
- Check file size limits
- Review agent configuration
- Check sync state file for tracking issues
- Use `verify-rag` command to check indexing status

### Debug Commands

```bash
# Check workflow status
gh run list --workflow="update-products.yml"

# View detailed logs
gh run view [RUN_ID] --log

# Test local processing
python3 scripts/update_llms_agnostic.py example.com --auto-discover https://example.com/category/ --max-products 5 --verbose
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with sample webhooks
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🔗 Related Projects

- [rivvy-observer](https://github.com/Emmmmmmo/rivvy-observer): Website monitoring and change detection
- [Firecrawl](https://firecrawl.dev): Web scraping API
- [ElevenLabs](https://elevenlabs.io): Conversational AI platform

## 📞 Support

For issues and questions:
1. Check the troubleshooting section above
2. Review GitHub Actions logs
3. Create an issue in this repository

## 📊 System Status

**Current Status:** ✅ **FULLY OPERATIONAL**  
**Version:** 3.1 (Production-Ready with Quality Fixes)  
**Last Updated:** October 1, 2025

### Key Achievements
- ✅ **Agnostic scraping engine** adapts to any website structure
- ✅ **Multi-level hierarchy support** for complex e-commerce sites
- ✅ **Multiple product extraction** from single webhook diff (NEW)
- ✅ **Production-ready quality system** with HTML pollution prevention and EUR currency enforcement
- ✅ **File size compliance** with automatic splitting for ElevenLabs limits
- ✅ **Structured data extraction** with clean JSON output
- ✅ **Automatic old version cleanup** prevents document accumulation
- ✅ **RAG indexing verification** with automatic retry system
- ✅ **Unified knowledge base management** with comprehensive tooling
- ✅ **Production-ready scalability** for high-volume, frequent updates

For detailed system status and technical specifications, see [COMPREHENSIVE_GUIDE.md](./COMPREHENSIVE_GUIDE.md).

---

**Built with ❤️ for automated content management and AI integration**
