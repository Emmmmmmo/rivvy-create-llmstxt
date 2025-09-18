#!/bin/bash

# Test the workflow logic locally
echo "Testing workflow logic locally..."

# Create test payload
cat > /tmp/payload.json << 'EOF'
{
  "website": {
    "url": "https://www.jgengineering.ie"
  },
  "changedPages": [
    {
      "url": "https://www.jgengineering.ie/collections/test-products/products/test-widget",
      "changeType": "page_added",
      "scrapedContent": {
        "markdown": "# Test Widget\n\nThis is a test product."
      }
    }
  ]
}
EOF

echo "Test payload created:"
cat /tmp/payload.json

# Test the jq commands that would run in the workflow
echo -e "\n=== Testing jq commands ==="

website_url=$(jq -r '.website.url // empty' /tmp/payload.json)
echo "Website URL: $website_url"

changed_pages_count=$(jq -r '.changedPages | length // 0' /tmp/payload.json)
echo "Changed pages count: $changed_pages_count"

if [ "$changed_pages_count" -gt 0 ]; then
  echo "New payload format detected with $changed_pages_count changed pages"
  
  for i in $(seq 0 $((changed_pages_count - 1))); do
    page_url=$(jq -r ".changedPages[$i].url // empty" /tmp/payload.json)
    change_type=$(jq -r ".changedPages[$i].changeType // empty" /tmp/payload.json)
    echo "Page $((i+1)): $page_url ($change_type)"
  done
else
  echo "Legacy format or no changed pages"
fi

echo -e "\n=== Test completed ==="
rm /tmp/payload.json
