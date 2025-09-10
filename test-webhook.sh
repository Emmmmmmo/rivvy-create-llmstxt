#!/bin/bash

# Test script to demonstrate dynamic webhook routing
# This script shows how to trigger the GitHub Actions workflow with different sites

# Configuration
GITHUB_TOKEN="${GITHUB_TOKEN:-}"
REPO_OWNER="${REPO_OWNER:-your-username}"
REPO_NAME="${REPO_NAME:-rivvy_create-llmstxt}"

if [ -z "$GITHUB_TOKEN" ]; then
    echo "Error: GITHUB_TOKEN environment variable is required"
    echo "Set it with: export GITHUB_TOKEN=your_github_token"
    exit 1
fi

# Function to trigger webhook
trigger_webhook() {
    local action=$1
    local site=$2
    local urls=$3
    
    echo "Triggering webhook for $action on $site"
    echo "URLs: $urls"
    
    curl -X POST \
        -H "Authorization: token $GITHUB_TOKEN" \
        -H "Accept: application/vnd.github.v3+json" \
        "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/dispatches" \
        -d "{
            \"event_type\": \"$action\",
            \"client_payload\": {
                \"site\": \"$site\",
                \"urls\": $urls
            }
        }"
    
    echo -e "\n---\n"
}

# Test cases
echo "Testing dynamic webhook routing with different sites..."
echo "=================================================="

# Test 1: jgengineering.ie
trigger_webhook "product-added" "https://www.jgengineering.ie" '["https://www.jgengineering.ie/products/product1.html", "https://www.jgengineering.ie/products/product2.html"]'

# Test 2: mydiy.ie
trigger_webhook "product-updated" "https://www.mydiy.ie" '["https://www.mydiy.ie/products/updated-product.html"]'

# Test 3: Different domain format
trigger_webhook "product-removed" "https://example.com" '["https://example.com/products/removed-product.html"]'

# Test 4: Domain with subdomain
trigger_webhook "product-added" "https://shop.example.com" '["https://shop.example.com/products/new-product.html"]'

# Test 5: Domain without www
trigger_webhook "product-updated" "https://example.org" '["https://example.org/products/updated-item.html"]'

echo "All webhook tests triggered!"
echo "Check the GitHub Actions tab to see the workflow runs."
echo ""
echo "Expected behavior:"
echo "- Each webhook should create/update files in out/[domain]/"
echo "- The workflow should automatically detect the domain from the site URL"
echo "- Files should be organized by domain in separate directories"
