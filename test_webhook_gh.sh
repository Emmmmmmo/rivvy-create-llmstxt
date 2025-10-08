#!/bin/bash
#
# Test GitHub Actions Webhook Using GitHub CLI
# 
# This script uses the GitHub CLI (gh) to send a test webhook payload
# to trigger the sitemap monitoring workflow with a new product.
#
# Prerequisites:
#   - GitHub CLI installed: brew install gh
#   - Authenticated: gh auth login
#
# Usage:
#   ./test_webhook_gh.sh
#

set -e

echo "╔═══════════════════════════════════════════════════════════════════════════╗"
echo "║           Test Sitemap Webhook with GitHub CLI                           ║"
echo "╚═══════════════════════════════════════════════════════════════════════════╝"
echo ""

# Check if gh is installed
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh) is not installed"
    echo ""
    echo "To install:"
    echo "  macOS:   brew install gh"
    echo "  Linux:   See https://github.com/cli/cli#installation"
    echo ""
    exit 1
fi

echo "✅ GitHub CLI installed"

# Check authentication
if ! gh auth status &> /dev/null; then
    echo "❌ Not authenticated with GitHub"
    echo ""
    echo "To authenticate, run:"
    echo "  gh auth login"
    echo ""
    exit 1
fi

echo "✅ Authenticated with GitHub"
echo ""

# Repository details
REPO="Emmmmmmo/rivvy-create-llmstxt"

echo "📦 Repository: $REPO"
echo ""

# Test product - using the Makita angle grinder we tested earlier
TEST_URL="https://www.mydiy.ie/products/makita-ga4030r-100mm-anti-restart-angle-grinder.html"

echo "🧪 Test Details:"
echo "─────────────────────────────────────────────────────────────────────────"
echo "Product URL:  $TEST_URL"
echo "Change Type:  page_added"
echo "Expected Shard: angle_grinders_100mm_disc"
echo ""
echo "This will:"
echo "  1. Send webhook to GitHub Actions"
echo "  2. Trigger workflow: 'Update Products from rivvy-observer'"
echo "  3. Scrape product with HTML (for breadcrumbs)"
echo "  4. Extract breadcrumbs: Home > Power Tools > Angle Grinders > 100mm Disc"
echo "  5. Categorize product to correct shard"
echo "  6. Commit and push changes"
echo "  7. Sync to ElevenLabs"
echo "─────────────────────────────────────────────────────────────────────────"
echo ""

read -p "Send test webhook? (y/n): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Cancelled"
    exit 0
fi

echo ""
echo "📤 Sending webhook to GitHub Actions..."
echo ""

# Create payload file
PAYLOAD_FILE="/tmp/webhook_payload_$$.json"
cat > "$PAYLOAD_FILE" <<EOF
{
  "website": {
    "url": "https://www.mydiy.ie",
    "id": "mydiy-test"
  },
  "changedPages": [
    {
      "url": "$TEST_URL",
      "changeType": "page_added",
      "lastmod": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    }
  ]
}
EOF

# Send webhook using gh
if gh api \
  --method POST \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  "/repos/$REPO/dispatches" \
  -f event_type='website_changed' \
  --input "$PAYLOAD_FILE" \
  -F client_payload=@-; then
    
    # Clean up payload file
    rm -f "$PAYLOAD_FILE"
    
    echo ""
    echo "✅ SUCCESS! Webhook sent to GitHub Actions"
    echo ""
    echo "🔍 Watch the workflow run:"
    echo "   https://github.com/$REPO/actions"
    echo ""
    echo "Or use GitHub CLI:"
    echo "   gh run list --repo $REPO --limit 5"
    echo "   gh run view --repo $REPO  # View latest run"
    echo "   gh run watch --repo $REPO # Watch in real-time"
    echo ""
    echo "⏱️  Workflow should start within 10 seconds..."
    echo ""
    echo "📊 What to look for in logs:"
    echo "   ✓ 'rivvy-observer payload validation passed'"
    echo "   ✓ 'Processing 1 changed pages...'"
    echo "   ✓ 'Extracted 4 breadcrumb items'"
    echo "   ✓ \"Using breadcrumb-derived shard 'angle_grinders_100mm_disc'\""
    echo "   ✓ 'Updated shard: angle_grinders_100mm_disc'"
    echo "   ✓ 'Changes committed and pushed'"
    echo ""
    
    # Offer to watch the run
    echo ""
    read -p "Watch workflow execution now? (y/n): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        echo "⏳ Waiting for workflow to start..."
        sleep 5
        
        # Try to watch the latest run
        gh run watch --repo "$REPO" || {
            echo ""
            echo "💡 Workflow may not have started yet. View manually at:"
            echo "   https://github.com/$REPO/actions"
        }
    else
        echo ""
        echo "💡 View workflow later at:"
        echo "   https://github.com/$REPO/actions"
    fi
    
else
    echo ""
    echo "❌ FAILED to send webhook"
    echo ""
    echo "Common issues:"
    echo "  - Repository access: Make sure you have push access"
    echo "  - Authentication: Try 'gh auth refresh'"
    echo "  - Repository name: Check if '$REPO' is correct"
    echo ""
    exit 1
fi

echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
echo "🎉 Test webhook sent successfully!"
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""

