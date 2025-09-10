# Dynamic Webhook Routing Documentation

This document explains how the GitHub Actions workflow handles dynamic webhook routing for different websites.

## Overview

The workflow automatically detects the target website from the webhook payload and routes the processing to the correct output directory. This eliminates the need to hardcode specific domains in the workflow file.

## Webhook Format

### Repository Dispatch Event

The workflow listens for `repository_dispatch` events with the following structure:

```json
{
  "event_type": "product-added|product-updated|product-removed",
  "client_payload": {
    "site": "https://example.com",
    "urls": ["https://example.com/product1.html", "https://example.com/product2.html"]
  }
}
```

### Required Fields

- **`event_type`**: The action type (`product-added`, `product-updated`, or `product-removed`)
- **`client_payload.site`**: The base URL of the website (e.g., `https://www.example.com`)
- **`client_payload.urls`**: JSON array of URLs to process

## Domain Detection

The workflow automatically extracts the domain from the `site` URL using the following logic:

1. **Primary extraction**: Removes protocol (`https://` or `http://`), `www.` prefix, and path/query parameters
2. **Fallback extraction**: If primary extraction fails, uses regex to find any valid domain pattern
3. **Validation**: Ensures the extracted domain matches standard domain format patterns

### Supported URL Formats

- `https://www.example.com`
- `https://example.com`
- `http://www.example.com`
- `https://shop.example.com`
- `https://example.com/path/to/page`

## Output Directory Structure

Files are automatically organized by domain:

```
out/
├── example.com/
│   ├── llms-full.products.txt
│   ├── llms-index.json
│   └── manifest.json
├── jgengineering.ie/
│   ├── llms-full.collections.txt
│   ├── llms-full.products.txt
│   ├── llms-index.json
│   └── manifest.json
└── mydiy.ie/
    ├── llms-full.products.txt
    ├── llms-index.json
    └── manifest.json
```

## Error Handling

The workflow includes comprehensive error handling:

1. **Payload validation**: Checks for required fields before processing
2. **Domain validation**: Validates extracted domain format
3. **Fallback mechanisms**: Attempts alternative domain extraction if primary method fails
4. **Script error handling**: Captures and reports errors from the update script
5. **Detailed logging**: Provides extensive logging for debugging

## Testing

Use the provided test script to verify webhook functionality:

```bash
# Set your GitHub token
export GITHUB_TOKEN=your_github_token
export REPO_OWNER=your-username
export REPO_NAME=rivvy_create-llmstxt

# Run the test script
./test-webhook.sh
```

## Manual Webhook Triggering

You can manually trigger webhooks using the GitHub API:

```bash
curl -X POST \
  -H "Authorization: token YOUR_GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  "https://api.github.com/repos/OWNER/REPO/dispatches" \
  -d '{
    "event_type": "product-added",
    "client_payload": {
      "site": "https://www.example.com",
      "urls": ["https://www.example.com/products/new-product.html"]
    }
  }'
```

## Push Event Handling

For push events (when manifest files are updated), the workflow:

1. **Auto-discovers sites**: Scans the `out/` directory for existing sites
2. **Reads manifests**: Extracts URLs from each site's manifest.json file
3. **Processes all sites**: Updates all discovered sites automatically
4. **Dynamic base URL detection**: Uses manifest data or constructs URLs from domain names

## Benefits

1. **Scalability**: Add new sites without modifying the workflow
2. **Maintainability**: Single workflow handles all sites
3. **Flexibility**: Supports various URL formats and domain structures
4. **Reliability**: Comprehensive error handling and validation
5. **Automation**: Automatic site discovery for push events

## Troubleshooting

### Common Issues

1. **Invalid domain format**: Ensure the site URL is properly formatted
2. **Missing payload fields**: Verify both `site` and `urls` are provided
3. **Permission errors**: Ensure the GitHub token has repository dispatch permissions
4. **Script failures**: Check the Firecrawl API key and network connectivity

### Debug Information

The workflow provides detailed logging including:
- Webhook payload validation
- Domain extraction process
- Output directory creation
- Script execution results
- File system changes

Check the GitHub Actions logs for detailed debugging information.
