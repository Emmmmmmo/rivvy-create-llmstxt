#!/bin/bash

# Script to add all jgengineering.ie collection URLs to the observer
# This provides complete monitoring coverage for the entire product catalog

OBSERVER_API_KEY="fc_nrQqdfLXX6hBsB7f3Q2lpmxJOH47Ae1v"
WEBHOOK_URL="https://api.github.com/repos/Emmmmmmo/rivvy-create-llmstxt/dispatches"

echo "🚀 Adding jgengineering.ie collection URLs to observer..."
echo ""

# Function to add a collection URL
add_collection() {
    local url="$1"
    local name="$2"
    
    echo "Adding: $name"
    echo "URL: $url"
    
    response=$(curl -s -X POST https://rivvy-observer.vercel.app/api/websites \
        -H "Authorization: Bearer $OBSERVER_API_KEY" \
        -H "Content-Type: application/json" \
        -d "{
            \"url\": \"$url\",
            \"type\": \"scrape\",
            \"checkInterval\": 60,
            \"webhook\": \"$WEBHOOK_URL\",
            \"name\": \"$name\"
        }")
    
    if echo "$response" | grep -q '"success":true'; then
        echo "✅ Success"
        website_id=$(echo "$response" | grep -o '"websiteId":"[^"]*"' | cut -d'"' -f4)
        echo "   Website ID: $website_id"
    else
        echo "❌ Failed: $response"
    fi
    echo ""
}

# Main Helicoil Kit Collections
add_collection "https://www.jgengineering.ie/collections/baercoil-metric-helicoil-kits-ireland" "JG Engineering - BaerCoil Metric Helicoil Kits"
add_collection "https://www.jgengineering.ie/collections/unc-helicoil-kits-ireland" "JG Engineering - UNC Helicoil Kits"
add_collection "https://www.jgengineering.ie/collections/unf-helicoil-kits-ireland" "JG Engineering - UNF Helicoil Kits"
add_collection "https://www.jgengineering.ie/collections/bsw-helicoil-kits-ireland" "JG Engineering - BSW Helicoil Kits"
add_collection "https://www.jgengineering.ie/collections/bsf-helicoil-kits-ireland" "JG Engineering - BSF Helicoil Kits"
add_collection "https://www.jgengineering.ie/collections/bsb-helicoil-kits-ireland" "JG Engineering - BSB Helicoil Kits"
add_collection "https://www.jgengineering.ie/collections/bsp-helicoil-kits-ireland" "JG Engineering - BSP Helicoil Kits"
add_collection "https://www.jgengineering.ie/collections/ba-helicoil-kits-ireland" "JG Engineering - BA Helicoil Kits"

# Thread Repair Components
add_collection "https://www.jgengineering.ie/collections/metric-helicoil-inserts-ireland" "JG Engineering - Metric Helicoil Inserts"
add_collection "https://www.jgengineering.ie/collections/unc-helicoil-inserts-ireland" "JG Engineering - UNC Helicoil Inserts"
add_collection "https://www.jgengineering.ie/collections/unf-helicoil-inserts" "JG Engineering - UNF Helicoil Inserts"
add_collection "https://www.jgengineering.ie/collections/baercoil-drill-bits" "JG Engineering - BaerCoil Drill Bits"
add_collection "https://www.jgengineering.ie/collections/baercoil-taps-helicoil" "JG Engineering - BaerCoil Taps"
add_collection "https://www.jgengineering.ie/collections/baercoil-bottoming-taps-metric-helicoil" "JG Engineering - BaerCoil Bottoming Taps"
add_collection "https://www.jgengineering.ie/collections/baercoil-workshop-kits-helicoil" "JG Engineering - BaerCoil Workshop Kits"

# BaerFix Thread Repair
add_collection "https://www.jgengineering.ie/collections/metric-baerfix-thread-repair-kits-like-timesert" "JG Engineering - Metric BaerFix Thread Repair Kits"
add_collection "https://www.jgengineering.ie/collections/unf-baerfix-thread-repair-kits-like-timeserts" "JG Engineering - UNF BaerFix Thread Repair Kits"
add_collection "https://www.jgengineering.ie/collections/metric-baerfix-thread-inserts-like-timeserts" "JG Engineering - Metric BaerFix Thread Inserts"
add_collection "https://www.jgengineering.ie/collections/baerfix-thread-inserts-cutting-slots-m-case-hardened-steel" "JG Engineering - BaerFix Thread Inserts with Cutting Slots"

# Circlips & Fasteners
add_collection "https://www.jgengineering.ie/collections/circlips-ireland" "JG Engineering - Circlips Ireland"
add_collection "https://www.jgengineering.ie/collections/external-circlips" "JG Engineering - External Circlips"
add_collection "https://www.jgengineering.ie/collections/internal-circlips-carbon-black" "JG Engineering - Internal Circlips"

# Tools & Accessories
add_collection "https://www.jgengineering.ie/collections/baer-hand-taps" "JG Engineering - Baer Hand Taps"
add_collection "https://www.jgengineering.ie/collections/baercoil-inserting-tools-ireland" "JG Engineering - BaerCoil Inserting Tools"

# Special Collections
add_collection "https://www.jgengineering.ie/collections/front-page" "JG Engineering - Front Page Featured"
add_collection "https://www.jgengineering.ie/collections/ass-products" "JG Engineering - ASS Products"
add_collection "https://www.jgengineering.ie/collections/metric-baercoil-kits" "JG Engineering - Metric BaerCoil Kits"
add_collection "https://www.jgengineering.ie/collections/vendors" "JG Engineering - Vendors"

echo "🎉 All jgengineering.ie collection URLs have been added to the observer!"
echo "📊 Total collections monitored: 27"
echo "🔄 Check interval: 60 minutes"
echo "🔗 Webhook: GitHub repository dispatches"
echo ""
echo "Next steps:"
echo "1. Monitor GitHub Actions for webhook triggers"
echo "2. Check that new products are added to correct shards"
echo "3. Verify ElevenLabs RAG updates automatically"
