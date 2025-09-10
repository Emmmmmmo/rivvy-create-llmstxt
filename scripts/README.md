# Sharded LLMs.txt Updater

A Python script that generates and maintains sharded LLMs.txt files using the Firecrawl v2 API. This script supports both full crawls and incremental updates, organizing content by product categories (shards) for better organization and performance.

## Features

- 🗂️ **Sharding Support**: Automatically groups pages by product category (first path segment)
- 🔄 **Incremental Updates**: Support for adding, changing, or removing specific URLs
- 📊 **Metadata Tracking**: Maintains per-URL metadata including titles, content, and timestamps
- 🗺️ **Website Mapping**: Uses Firecrawl's map endpoint to discover all URLs
- 📄 **Markdown Extraction**: Scrapes content in markdown format for LLM consumption
- 📁 **Organized Output**: Creates separate LLMs files per shard with manifest tracking
- 🚀 **CI-Friendly**: Outputs JSON summary for continuous integration workflows

## Prerequisites

- Python 3.7+
- Firecrawl API key ([Get one here](https://firecrawl.dev))
- `requests` library (included in requirements.txt)

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up your Firecrawl API key:
```bash
export FIRECRAWL_API_KEY="your-firecrawl-api-key"
```

## Usage

### Full Crawl

Perform a complete crawl of a website:

```bash
python scripts/update_llms_sharded.py https://example.com --full
```

### Incremental Updates

Add new URLs:
```bash
python scripts/update_llms_sharded.py https://example.com --added '["https://example.com/new-page", "https://example.com/another-page"]'
```

Update existing URLs:
```bash
python scripts/update_llms_sharded.py https://example.com --changed '["https://example.com/updated-page"]'
```

Remove URLs:
```bash
python scripts/update_llms_sharded.py https://example.com --removed '["https://example.com/old-page"]'
```

### Advanced Options

Set a base root path for shard key extraction:
```bash
python scripts/update_llms_sharded.py https://example.com --full --base-root "/docs"
```

Use verbose logging:
```bash
python scripts/update_llms_sharded.py https://example.com --full --verbose
```

## Output Structure

The script creates an `out/` directory with the following files:

### Core Files

- **`llms-index.json`**: Per-URL metadata including title, markdown content, shard, and timestamp
- **`manifest.json`**: Mapping of shard keys to lists of URLs
- **`llms-full.<shard>.txt`**: LLMs content files, one per shard

### Example Output

```
out/
├── llms-index.json
├── manifest.json
├── llms-full.products.txt
├── llms-full.docs.txt
└── llms-full.blog.txt
```

### File Formats

#### llms-index.json
```json
{
  "https://example.com/products/widget": {
    "title": "Widget Product Page",
    "markdown": "# Widget\n\nProduct description...",
    "shard": "products",
    "updated_at": "2024-01-15T10:30:00"
  }
}
```

#### manifest.json
```json
{
  "products": ["https://example.com/products/widget", "https://example.com/products/gadget"],
  "docs": ["https://example.com/docs/getting-started"],
  "blog": ["https://example.com/blog/post-1"]
}
```

#### llms-full.products.txt
```
<|URL-lllmstxt|>
## Widget Product Page
# Widget

Product description and details...

<|URL-lllmstxt|>
## Gadget Product Page
# Gadget

Another product description...
```

## Shard Key Logic

The shard key is determined by the first path segment after the domain (or after `BASE_ROOT` if set):

- `https://example.com/products/widget` → shard: `products`
- `https://example.com/docs/api` → shard: `docs`
- `https://example.com/` → shard: `root`

If `BASE_ROOT` is set to `/docs`, then:
- `https://example.com/docs/api/reference` → shard: `api`
- `https://example.com/docs/getting-started` → shard: `getting-started`

## Environment Variables

- **`FIRECRAWL_API_KEY`**: Your Firecrawl API key (required)
- **`BASE_ROOT`**: Base root path for shard key extraction (optional)

## CI Integration

The script outputs a JSON summary at the end, perfect for CI workflows:

```json
{
  "operation": "full_crawl",
  "processed_urls": 150,
  "total_urls": 150,
  "touched_shards": ["products", "docs", "blog"],
  "written_files": [
    "out/llms-full.products.txt",
    "out/llms-full.docs.txt",
    "out/llms-full.blog.txt"
  ]
}
```

## Error Handling

- Failed URL scrapes are logged and skipped
- Invalid JSON input for incremental updates will cause the script to exit
- Missing API keys will cause the script to exit with clear error messages
- Rate limiting is handled with small delays between requests

## Performance Considerations

- Full crawls can take time for large websites
- Incremental updates are much faster for targeted changes
- The script processes URLs sequentially to avoid overwhelming the API
- Consider using incremental updates in CI/CD pipelines for better performance

## Examples

### E-commerce Site
```bash
# Full crawl of an e-commerce site
python scripts/update_llms_sharded.py https://shop.example.com --full

# Add new product pages
python scripts/update_llms_sharded.py https://shop.example.com --added '["https://shop.example.com/products/new-item"]'
```

### Documentation Site
```bash
# Set base root for documentation
export BASE_ROOT="/docs"

# Full crawl
python scripts/update_llms_sharded.py https://docs.example.com --full

# Update changed documentation pages
python scripts/update_llms_sharded.py https://docs.example.com --changed '["https://docs.example.com/docs/api/v2"]'
```

### Blog Site
```bash
# Full crawl
python scripts/update_llms_sharded.py https://blog.example.com --full

# Remove old blog posts
python scripts/update_llms_sharded.py https://blog.example.com --removed '["https://blog.example.com/old-post"]'
```

## Troubleshooting

### Common Issues

1. **API Key Not Found**
   - Ensure `FIRECRAWL_API_KEY` environment variable is set
   - Or pass it via `--firecrawl-api-key` argument

2. **Rate Limiting**
   - The script includes small delays between requests
   - For very large sites, consider processing in smaller batches

3. **Invalid JSON for Incremental Updates**
   - Ensure URLs are properly formatted as a JSON array
   - Use single quotes around the JSON string in shell commands

4. **Empty Shard Files**
   - Check that URLs are being scraped successfully
   - Verify the shard key logic matches your URL structure

### Debug Mode

Use `--verbose` flag to see detailed logging:

```bash
python scripts/update_llms_sharded.py https://example.com --full --verbose
```

## License

MIT License - see LICENSE file for details
