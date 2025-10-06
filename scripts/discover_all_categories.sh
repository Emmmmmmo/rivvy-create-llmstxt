#!/bin/bash

# Discovery-Only Script for All MyDIY.ie Categories
# This script runs hierarchical discovery for all 21 main categories
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

echo -e "${BLUE}=== MyDIY.ie Discovery-Only Mode ===${NC}"
echo -e "${BLUE}Starting: $(date)${NC}"
echo ""

# Array of all 21 main categories
declare -a CATEGORIES=(
    "https://www.mydiy.ie/power-tools/"
    "https://www.mydiy.ie/garden-tools/"
    "https://www.mydiy.ie/adhesives-fixings-and-hardware/"
    "https://www.mydiy.ie/automotive/"
    "https://www.mydiy.ie/ladders-and-other-access-equipment/"
    "https://www.mydiy.ie/protective-workwear/"
    "https://www.mydiy.ie/electrical-lighting/"
    "https://www.mydiy.ie/storage-and-shelving/"
    "https://www.mydiy.ie/building/"
    "https://www.mydiy.ie/plumbing/"
    "https://www.mydiy.ie/painting-and-decorating/"
    "https://www.mydiy.ie/safety-and-security/"
    "https://www.mydiy.ie/cleaning/"
    "https://www.mydiy.ie/ironmongery/"
    "https://www.mydiy.ie/outdoor/"
    "https://www.mydiy.ie/welding-and-gas-equipment/"
    "https://www.mydiy.ie/abrasives-and-cutting/"
    "https://www.mydiy.ie/workplace-and-facilities/"
    "https://www.mydiy.ie/materials-handling/"
    "https://www.mydiy.ie/timber/"
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
echo -e "${GREEN}Next step: Review queue and run batch scraping${NC}"
echo "Command: source env.local && python3 scripts/update_llms_agnostic.py mydiy.ie --process-queue --batch-size 50 --max-batches 20"

