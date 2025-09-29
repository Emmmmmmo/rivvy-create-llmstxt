#!/bin/bash

# Test webhook processing locally
# Usage: ./test_webhook_locally.sh test_mydiy_new_product.json

set -e

PAYLOAD_FILE="${1:-test_mydiy_new_product.json}"

echo "================================================"
echo "Testing Webhook Processing Locally"
echo "================================================"
echo ""

# Check if payload file exists
if [ ! -f "$PAYLOAD_FILE" ]; then
    echo "Error: Payload file not found: $PAYLOAD_FILE"
    exit 1
fi

echo "📄 Loading payload from: $PAYLOAD_FILE"
echo ""

# Extract data from payload
website_url=$(jq -r '.client_payload.website.url' "$PAYLOAD_FILE")
change_type=$(jq -r '.client_payload.change.changeType' "$PAYLOAD_FILE")
scraped_content=$(jq -r '.client_payload.scrapeResult.markdown // empty' "$PAYLOAD_FILE")

echo "🌐 Website URL: $website_url"
echo "📝 Change Type: $change_type"
echo ""

# Extract domain
domain=$(echo "$website_url" | sed -E 's|^https?://||' | sed -E 's|^www\.||' | sed -E 's|/.*$||' | sed -E 's|:.*$||')

if [ -z "$domain" ]; then
    echo "❌ Error: Could not extract domain from: $website_url"
    exit 1
fi

output_dir="out/$domain"
echo "📁 Domain: $domain"
echo "📂 Output Directory: $output_dir"
echo ""

# Ensure output directory exists
mkdir -p "$output_dir"

# Save scraped content to temp file
temp_file="/tmp/scraped_content_${domain}.md"
if [ -n "$scraped_content" ] && [ "$scraped_content" != "null" ]; then
    printf '%s\n' "$scraped_content" > "$temp_file"
    echo "💾 Saved scraped content to: $temp_file"
    echo ""
fi

# Simulate adding a new product page
# For a real product, we would extract the actual URL from the payload
# For this test, we'll use a realistic mydiy.ie product URL
product_url="https://www.mydiy.ie/products/makita-18v-cordless-hammer-drill-dhp485z.html"

echo "================================================"
echo "Processing Product Addition"
echo "================================================"
echo ""
echo "🔧 Product URL: $product_url"
echo ""

# Check if we're using agnostic system
if [ -f "scripts/update_llms_agnostic.py" ]; then
    echo "✅ Using Agnostic Scraping System"
    echo ""
    
    # Process with agnostic system
    if [ -f "$temp_file" ]; then
        echo "🚀 Running agnostic scraper with pre-scraped content..."
        python3 scripts/update_llms_agnostic.py "$domain" \
            --added "[\"$product_url\"]" \
            --pre-scraped-content "$temp_file"
    else
        echo "🚀 Running agnostic scraper..."
        python3 scripts/update_llms_agnostic.py "$domain" \
            --added "[\"$product_url\"]"
    fi
else
    echo "⚠️  Agnostic system not found, using legacy system"
    echo ""
    
    # Fallback to legacy system
    if [ -f "$temp_file" ]; then
        python3 scripts/update_llms_sharded.py "$website_url" \
            --added "[\"$product_url\"]" \
            --output-dir "$output_dir" \
            --pre-scraped-content "$temp_file"
    else
        python3 scripts/update_llms_sharded.py "$website_url" \
            --added "[\"$product_url\"]" \
            --output-dir "$output_dir"
    fi
fi

echo ""
echo "================================================"
echo "Results"
echo "================================================"
echo ""

# Show files in output directory
echo "📊 Files in output directory:"
ls -lh "$output_dir" | grep -E "\.txt|\.json" || echo "No files found"
echo ""

# Show changes in git
echo "📝 Git changes:"
git status --short
echo ""

# Show file sizes
echo "📏 File sizes:"
du -h "$output_dir"/* 2>/dev/null | tail -5 || echo "No files to display"
echo ""

# Clean up temp file
rm -f "$temp_file"

echo "================================================"
echo "✅ Test Complete!"
echo "================================================"
echo ""
echo "Next steps:"
echo "1. Review the changes in $output_dir"
echo "2. Check git diff to see the actual changes"
echo "3. Commit changes if satisfied: git add . && git commit -m 'Test webhook processing'"
echo ""
