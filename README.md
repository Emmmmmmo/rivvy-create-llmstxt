# Rivvy Create LLMs.txt - Production Ready

**Status:** ✅ **FULLY OPERATIONAL** | **Version:** 2.0 | **Last Updated:** January 2025

Automatically generate and maintain LLMs.txt files for unlimited websites with integrated ElevenLabs RAG (Retrieval Augmented Generation) capabilities.

## 🚀 Overview

This production-ready system provides fully automated LLMs.txt file generation and maintenance for unlimited websites using:

- **Dynamic Webhook Routing**: Automatically routes webhooks to correct domain directories
- **Multi-Website Support**: Handle unlimited domains without code changes
- **ElevenLabs RAG Integration**: ⭐ **Enhanced** with automatic old version cleanup
- **Change Detection**: Powered by [rivvy-observer](https://github.com/Emmmmmmo/rivvy-observer) for real-time monitoring
- **Production Ready**: Robust error handling, extended retry logic, and scalable architecture

## 🏗 Architecture

```
Website Changes → rivvy-observer → Webhook → Dynamic Routing → LLMs Generation → ElevenLabs RAG
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
│   └── elevenlabs-agents.json      # ElevenLabs agent mapping (optional)
├── scripts/
│   ├── update_llms_sharded.py      # Core LLMs generation script
│   └── elevenlabs_rag_sync.py      # ElevenLabs integration (optional)
├── out/
│   ├── domain1.com/                # Auto-generated domain directories
│   │   ├── llms-full.products.txt
│   │   ├── llms-full.collections.txt
│   │   ├── llms-index.json
│   │   └── manifest.json
│   └── domain2.com/
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

### 3. Add Website Monitoring

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

### 4. Configure ElevenLabs Agent (Optional)

Create `config/elevenlabs-agents.json`:

```json
{
  "agents": {
    "yoursite.com": {
      "agent_id": "your_agent_id_here",
      "agent_name": "Your Site Expert",
      "enabled": true,
      "sync_enabled": true
    }
  },
  "default_settings": {
    "agent_id": "default_agent_id",
    "enabled": true
  }
}
```

## 🔄 How It Works

### Webhook Processing Flow

1. **Change Detection**: rivvy-observer detects changes on monitored websites
2. **Content Scraping**: Observer scrapes and analyzes the changed content
3. **Webhook Sent**: Observer sends webhook with pre-scraped content to GitHub repository
4. **Dynamic Routing**: Workflow extracts domain and creates appropriate directory
5. **Content Processing**: Uses pre-scraped content (no re-scraping needed) to generate LLMs files
6. **File Organization**: Files saved to `out/{domain}/` with proper structure
7. **ElevenLabs Sync**: Generated files automatically uploaded to RAG system
8. **Git Commit**: Changes committed and pushed to repository

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

## 📊 Generated Files

For each domain, the system generates:

### `llms-full.{category}.txt`
LLMs.txt formatted files containing scraped content organized by category:
- `llms-full.products.txt`: Individual product pages
- `llms-full.collections.txt`: Category/collection pages
- `llms-full.categories.txt`: Category hierarchy

### `llms-index.json`
Metadata and indexing information for all processed URLs:
```json
{
  "https://example.com/product1": {
    "title": "Product Name",
    "shard": "products",
    "updated_at": "2025-09-10T16:00:00Z"
  }
}
```

### `manifest.json`
URL organization and tracking:
```json
{
  "products": [
    "https://example.com/product1",
    "https://example.com/product2"
  ],
  "collections": [
    "https://example.com/category1"
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

## 📈 Scaling

### Multi-Domain Support

The system automatically handles unlimited domains:

```
out/
├── jgengineering.ie/     # Industrial tools
├── mydiy.ie/             # DIY products  
├── toolshop.ie/          # Power tools
├── gardenshop.ie/        # Garden equipment
└── newdomain.com/        # Automatically created
```

### Performance Considerations

- **Parallel Processing**: Each domain processed independently
- **Incremental Updates**: Only changed content is reprocessed
- **Rate Limiting**: Built-in delays prevent API throttling
- **Error Recovery**: Failed operations don't affect other domains

## 🔧 Configuration Options

### Environment Variables

- `FIRECRAWL_API_KEY`: Required for web scraping
- `ELEVENLABS_API_KEY`: Required for RAG integration
- `ONLY_MAIN_CONTENT`: Extract only main content (default: true)

### Script Parameters

The core script supports various options:

```bash
python3 scripts/update_llms_sharded.py [URL] \
  --added "[urls...]" \
  --output-dir "out/domain" \
  --verbose
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

**ElevenLabs sync issues:**
- ✅ **RAG Indexing Delays**: **SOLVED** - Extended retry logic handles timing issues
- ✅ **Document Accumulation**: **SOLVED** - Automatic cleanup prevents accumulation
- Verify API key and agent ID
- Check file size limits
- Review agent configuration
- Check sync state file for tracking issues

### Debug Commands

```bash
# Check workflow status
gh run list --workflow="update-products.yml"

# View detailed logs
gh run view [RUN_ID] --log

# Test local processing
python3 scripts/update_llms_sharded.py https://example.com --added '["https://example.com/test"]' --output-dir out/example.com --verbose
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
**Version:** 2.0 (Enhanced with ElevenLabs RAG Integration)  
**Last Updated:** January 2025

### Key Achievements
- ✅ **Automatic old version cleanup** prevents document accumulation
- ✅ **Extended retry logic** handles RAG indexing delays
- ✅ **Production-ready error handling** with comprehensive logging
- ✅ **Scalable architecture** for unlimited domains and frequent updates

For detailed system status and technical specifications, see [SYSTEM_STATUS.md](./SYSTEM_STATUS.md).

---

**Built with ❤️ for automated content management and AI integration**
