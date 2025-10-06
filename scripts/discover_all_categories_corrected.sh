#!/bin/bash

# Discovery-Only Script for All MyDIY.ie Categories (CORRECTED URLS)
# This script runs hierarchical discovery for all actual main categories
# without scraping products (discovery-only mode)

set -e  # Exit on error

# Source environment variables
source env.local

# Color output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Log file
LOG_FILE="out/mydiy-ie/discovery-log-$(date +%Y%m%d-%H%M%S).txt"

echo -e "${BLUE}=== MyDIY.ie Discovery-Only Mode (CORRECTED URLS) ===${NC}"
echo -e "${BLUE}Starting: $(date)${NC}"
echo ""

# Array of all ACTUAL main categories from mydiy.ie homepage
# These URLs were verified by scraping the site on 2025-10-06
declare -a CATEGORIES=(
    "https://www.mydiy.ie/hand-tools/"
    "https://www.mydiy.ie/power-tools/"
    "https://www.mydiy.ie/garden-tools/"
    "https://www.mydiy.ie/adhesives-fixings-and-hardware/"
    "https://www.mydiy.ie/decorating-and-wood-care/"
    "https://www.mydiy.ie/electrical-and-lighting/"
    "https://www.mydiy.ie/abrasives-fillers-sealants-and-lubricants/"
    "https://www.mydiy.ie/consumables/"
    "https://www.mydiy.ie/drill-bits-and-holesaws/"
    "https://www.mydiy.ie/home-leisure-and-automotive-care/"
    "https://www.mydiy.ie/ladders-and-other-access-equipment/"
    "https://www.mydiy.ie/landscape-and-gardening/"
    "https://www.mydiy.ie/padlocks-door-locks-and-security/"
    "https://www.mydiy.ie/power-tool-accessories/"
    "https://www.mydiy.ie/storage-and-access/"
    "https://www.mydiy.ie/workwear-tool-storage-and-safety/"
)

# Track progress
TOTAL=${#CATEGORIES[@]}
CURRENT=0

echo -e "${YELLOW}Total categories to process: $TOTAL${NC}"
echo ""

# Process each category
for CATEGORY in "${CATEGORIES[@]}"; do
    CURRENT=$((CURRENT + 1))
    CATEGORY_NAME=$(echo $CATEGORY | sed 's|https://www.mydiy.ie/||' | sed 's|/$||')
    
    echo -e "${GREEN}[$CURRENT/$TOTAL] Processing: $CATEGORY_NAME${NC}"
    echo "URL: $CATEGORY"
    echo "Started: $(date)"
    
    # Run discovery-only
    python3 scripts/update_llms_agnostic.py mydiy.ie \
        --hierarchical "$CATEGORY" \
        --discovery-only \
        2>&1 | tee -a "$LOG_FILE"
    
    EXIT_CODE=${PIPESTATUS[0]}
    
    if [ $EXIT_CODE -eq 0 ]; then
        echo -e "${GREEN}✓ Completed: $CATEGORY_NAME${NC}"
    else
        echo -e "${YELLOW}⚠ Warning: $CATEGORY_NAME exited with code $EXIT_CODE${NC}"
    fi
    
    echo "Finished: $(date)"
    echo "---"
    echo ""
    
    # Brief pause between categories to be gentle on API
    sleep 2
done

echo ""
echo -e "${BLUE}=== Discovery Complete ===${NC}"
echo -e "${BLUE}Finished: $(date)${NC}"
echo -e "${BLUE}Log saved to: $LOG_FILE${NC}"
echo ""

# Show queue stats
QUEUE_COUNT=$(jq '.pending | length' out/mydiy-ie/pending-queue.json 2>/dev/null || echo "unknown")
echo -e "${GREEN}📊 Total products in queue: $QUEUE_COUNT${NC}"
echo ""
echo -e "${GREEN}Next step: Review queue and run batch scraping${NC}"
echo "Command: source env.local && python3 scripts/update_llms_agnostic.py mydiy.ie --process-queue --batch-size 50 --max-batches 20"

