#!/bin/bash

# Script to scrape all MyDIY.ie main categories
# This will discover products from all 21 main categories and process them in batches

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
BATCH_SIZE=25
MAX_BATCHES=4
MAX_PRODUCTS=500
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Source environment variables
if [ -f "$PROJECT_DIR/env.local" ]; then
    source "$PROJECT_DIR/env.local"
else
    echo -e "${RED}Error: env.local file not found!${NC}"
    exit 1
fi

# All 21 main categories from MyDIY.ie
CATEGORIES=(
    "https://www.mydiy.ie/power-tools/"
    "https://www.mydiy.ie/hand-tools/"
    "https://www.mydiy.ie/garden-tools/"
    "https://www.mydiy.ie/adhesives-fixings-and-hardware/"
    "https://www.mydiy.ie/decorating-and-wood-care/"
    "https://www.mydiy.ie/power-tool-accessories/"
    "https://www.mydiy.ie/padlocks-door-locks-and-security/"
    "https://www.mydiy.ie/drill-bits-and-holesaws/"
    "https://www.mydiy.ie/workwear-tool-storage-and-safety/"
    "https://www.mydiy.ie/home-leisure-and-car-care/"
    "https://www.mydiy.ie/abrasives-fillers-sealants-and-lubricants/"
    "https://www.mydiy.ie/ladders-and-other-access-equipment/"
    "https://www.mydiy.ie/uncategorised-lines/"
    "https://www.mydiy.ie/storage-and-access/"
    "https://www.mydiy.ie/electrical-and-lighting/"
    "https://www.mydiy.ie/power-tool-accessories-1/"
    "https://www.mydiy.ie/security/"
    "https://www.mydiy.ie/consumables/"
    "https://www.mydiy.ie/home-leisure-and-automotive-care/"
    "https://www.mydiy.ie/landscape-and-gardening/"
    "https://www.mydiy.ie/merchandising-1/"
)

# Function to display progress
show_progress() {
    local current=$1
    local total=$2
    local category=$3
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}Progress: Category $current of $total${NC}"
    echo -e "${YELLOW}URL: $category${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Function to show queue status
show_queue_status() {
    local queue_file="$PROJECT_DIR/out/mydiy-ie/pending-queue.json"
    local manifest_file="$PROJECT_DIR/out/mydiy-ie/llms-mydiy-ie-manifest.json"
    
    if [ -f "$queue_file" ]; then
        local queue_size=$(jq 'length' "$queue_file")
        echo -e "${YELLOW}Pending queue: $queue_size URLs${NC}"
    fi
    
    if [ -f "$manifest_file" ]; then
        local total_scraped=$(jq '[.[] | length] | add' "$manifest_file")
        echo -e "${GREEN}Total scraped: $total_scraped products${NC}"
    fi
}

echo -e "${GREEN}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  MyDIY.ie Complete Category Scraping Script       ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Configuration:${NC}"
echo -e "  - Total categories: ${GREEN}${#CATEGORIES[@]}${NC}"
echo -e "  - Batch size: ${GREEN}${BATCH_SIZE}${NC}"
echo -e "  - Max batches per category: ${GREEN}${MAX_BATCHES}${NC}"
echo -e "  - Max products per category: ${GREEN}${MAX_PRODUCTS}${NC}"
echo ""

show_queue_status
echo ""

read -p "$(echo -e ${YELLOW}Start scraping? [y/N]: ${NC})" -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${RED}Aborted.${NC}"
    exit 0
fi

# Track statistics
TOTAL_CATEGORIES=${#CATEGORIES[@]}
SUCCESSFUL=0
FAILED=0
START_TIME=$(date +%s)

# Process each category
for i in "${!CATEGORIES[@]}"; do
    CATEGORY="${CATEGORIES[$i]}"
    CURRENT=$((i + 1))
    
    show_progress $CURRENT $TOTAL_CATEGORIES "$CATEGORY"
    
    # Run hierarchical discovery for this category
    echo -e "${BLUE}Running hierarchical discovery...${NC}"
    python3 "$SCRIPT_DIR/update_llms_agnostic.py" mydiy.ie \
        --hierarchical "$CATEGORY" \
        --max-products $MAX_PRODUCTS \
        --batch-size $BATCH_SIZE \
        --max-batches $MAX_BATCHES
    
    if [ $? -eq 0 ]; then
        SUCCESSFUL=$((SUCCESSFUL + 1))
        echo -e "${GREEN}✓ Category completed successfully${NC}"
    else
        FAILED=$((FAILED + 1))
        echo -e "${RED}✗ Category failed${NC}"
    fi
    
    echo ""
    show_queue_status
    echo ""
    
    # Small delay between categories to avoid rate limiting
    if [ $CURRENT -lt $TOTAL_CATEGORIES ]; then
        echo -e "${YELLOW}Pausing for 2 seconds before next category...${NC}"
        sleep 2
    fi
done

# Process any remaining items in the queue
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}Processing remaining queue...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

QUEUE_FILE="$PROJECT_DIR/out/mydiy-ie/pending-queue.json"
if [ -f "$QUEUE_FILE" ]; then
    QUEUE_SIZE=$(jq 'length' "$QUEUE_FILE")
    
    if [ "$QUEUE_SIZE" -gt 0 ]; then
        echo -e "${YELLOW}Processing $QUEUE_SIZE remaining URLs in queue...${NC}"
        
        # Process in larger batches until queue is empty
        while [ "$QUEUE_SIZE" -gt 0 ]; do
            python3 "$SCRIPT_DIR/update_llms_agnostic.py" mydiy.ie \
                --batch-size 50 \
                --max-batches 10
            
            QUEUE_SIZE=$(jq 'length' "$QUEUE_FILE")
            echo -e "${YELLOW}Remaining in queue: $QUEUE_SIZE${NC}"
            
            if [ "$QUEUE_SIZE" -eq 0 ]; then
                break
            fi
        done
        
        echo -e "${GREEN}✓ Queue processing complete${NC}"
    else
        echo -e "${GREEN}Queue is empty - nothing to process${NC}"
    fi
fi

# Calculate duration
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
MINUTES=$((DURATION / 60))
SECONDS=$((DURATION % 60))

# Final summary
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              Scraping Complete!                    ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Statistics:${NC}"
echo -e "  - Total categories: ${GREEN}${TOTAL_CATEGORIES}${NC}"
echo -e "  - Successful: ${GREEN}${SUCCESSFUL}${NC}"
echo -e "  - Failed: ${RED}${FAILED}${NC}"
echo -e "  - Duration: ${YELLOW}${MINUTES}m ${SECONDS}s${NC}"
echo ""
show_queue_status
echo ""
echo -e "${GREEN}Done!${NC}"

