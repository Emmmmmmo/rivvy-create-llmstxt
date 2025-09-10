#!/bin/bash

# Local test script to verify webhook processing logic
# This simulates the domain extraction and validation logic from the workflow

echo "Testing domain extraction logic locally..."
echo "========================================"

# Test function to extract domain (same logic as in workflow)
extract_domain() {
    local site_url="$1"
    echo "Testing URL: $site_url"
    
    # Extract domain with improved regex and validation (same as workflow)
    domain=$(echo "$site_url" | sed -E 's|^https?://||' | sed -E 's|^www\.||' | sed -E 's|/.*$||' | sed -E 's|:.*$||')
    
    echo "  Extracted domain: $domain"
    
    # Validate domain format
    if [ -z "$domain" ] || [ "$domain" = "null" ]; then
        echo "  ❌ Error: Could not extract valid domain"
        return 1
    fi
    
    # Additional validation for common domain patterns
    if ! echo "$domain" | grep -E '^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$' > /dev/null; then
        echo "  ⚠️  Warning: Domain format may be invalid"
    else
        echo "  ✅ Domain format is valid"
    fi
    
    output_dir="out/$domain"
    echo "  Output directory: $output_dir"
    echo ""
}

# Test various URL formats
echo "Testing various URL formats:"
echo ""

extract_domain "https://www.jgengineering.ie"
extract_domain "https://www.mydiy.ie"
extract_domain "https://shop.example.com"
extract_domain "https://example.org"
extract_domain "http://www.test-site.co.uk"
extract_domain "https://subdomain.example.com/path/to/page"
extract_domain "https://example.com:8080/path"

echo "Domain extraction tests completed!"
echo ""
echo "Expected output directories:"
echo "- out/jgengineering.ie/"
echo "- out/mydiy.ie/"
echo "- out/shop.example.com/"
echo "- out/example.org/"
echo "- out/test-site.co.uk/"
echo "- out/subdomain.example.com/"
echo "- out/example.com/"
