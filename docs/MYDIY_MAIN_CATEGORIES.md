# MyDIY.ie Main Categories - Manual Scraping Guide

## 21 Main Categories to Scrape

Run each category individually using the command pattern below.

### Command Pattern:
```bash
source env.local && python3 scripts/update_llms_agnostic.py mydiy.ie \
  --hierarchical [CATEGORY_URL] \
  --max-products 500 \
  --batch-size 25 \
  --max-batches 4
```

---

## Categories List:

### 1. Power Tools
```bash
source env.local && python3 scripts/update_llms_agnostic.py mydiy.ie \
  --hierarchical https://www.mydiy.ie/power-tools/ \
  --max-products 500 \
  --batch-size 25 \
  --max-batches 4
```

### 2. Hand Tools
```bash
source env.local && python3 scripts/update_llms_agnostic.py mydiy.ie \
  --hierarchical https://www.mydiy.ie/hand-tools/ \
  --max-products 500 \
  --batch-size 25 \
  --max-batches 4
```

### 3. Garden Tools
```bash
source env.local && python3 scripts/update_llms_agnostic.py mydiy.ie \
  --hierarchical https://www.mydiy.ie/garden-tools/ \
  --max-products 500 \
  --batch-size 25 \
  --max-batches 4
```

### 4. Adhesives, Fixings and Hardware
```bash
source env.local && python3 scripts/update_llms_agnostic.py mydiy.ie \
  --hierarchical https://www.mydiy.ie/adhesives-fixings-and-hardware/ \
  --max-products 500 \
  --batch-size 25 \
  --max-batches 4
```

### 5. Decorating and Wood Care
```bash
source env.local && python3 scripts/update_llms_agnostic.py mydiy.ie \
  --hierarchical https://www.mydiy.ie/decorating-and-wood-care/ \
  --max-products 500 \
  --batch-size 25 \
  --max-batches 4
```

### 6. Power Tool Accessories
```bash
source env.local && python3 scripts/update_llms_agnostic.py mydiy.ie \
  --hierarchical https://www.mydiy.ie/power-tool-accessories/ \
  --max-products 500 \
  --batch-size 25 \
  --max-batches 4
```

### 7. Padlocks, Door Locks and Security
```bash
source env.local && python3 scripts/update_llms_agnostic.py mydiy.ie \
  --hierarchical https://www.mydiy.ie/padlocks-door-locks-and-security/ \
  --max-products 500 \
  --batch-size 25 \
  --max-batches 4
```

### 8. Drill Bits and Holesaws
```bash
source env.local && python3 scripts/update_llms_agnostic.py mydiy.ie \
  --hierarchical https://www.mydiy.ie/drill-bits-and-holesaws/ \
  --max-products 500 \
  --batch-size 25 \
  --max-batches 4
```

### 9. Workwear, Tool Storage and Safety
```bash
source env.local && python3 scripts/update_llms_agnostic.py mydiy.ie \
  --hierarchical https://www.mydiy.ie/workwear-tool-storage-and-safety/ \
  --max-products 500 \
  --batch-size 25 \
  --max-batches 4
```

### 10. Home, Leisure and Car Care
```bash
source env.local && python3 scripts/update_llms_agnostic.py mydiy.ie \
  --hierarchical https://www.mydiy.ie/home-leisure-and-car-care/ \
  --max-products 500 \
  --batch-size 25 \
  --max-batches 4
```

### 11. Abrasives, Fillers, Sealants and Lubricants
```bash
source env.local && python3 scripts/update_llms_agnostic.py mydiy.ie \
  --hierarchical https://www.mydiy.ie/abrasives-fillers-sealants-and-lubricants/ \
  --max-products 500 \
  --batch-size 25 \
  --max-batches 4
```

### 12. Ladders and Other Access Equipment
```bash
source env.local && python3 scripts/update_llms_agnostic.py mydiy.ie \
  --hierarchical https://www.mydiy.ie/ladders-and-other-access-equipment/ \
  --max-products 500 \
  --batch-size 25 \
  --max-batches 4
```

### 13. Uncategorised Lines
```bash
source env.local && python3 scripts/update_llms_agnostic.py mydiy.ie \
  --hierarchical https://www.mydiy.ie/uncategorised-lines/ \
  --max-products 500 \
  --batch-size 25 \
  --max-batches 4
```

### 14. Storage and Access
```bash
source env.local && python3 scripts/update_llms_agnostic.py mydiy.ie \
  --hierarchical https://www.mydiy.ie/storage-and-access/ \
  --max-products 500 \
  --batch-size 25 \
  --max-batches 4
```

### 15. Electrical and Lighting
```bash
source env.local && python3 scripts/update_llms_agnostic.py mydiy.ie \
  --hierarchical https://www.mydiy.ie/electrical-and-lighting/ \
  --max-products 500 \
  --batch-size 25 \
  --max-batches 4
```

### 16. Power Tool Accessories (Alternative)
```bash
source env.local && python3 scripts/update_llms_agnostic.py mydiy.ie \
  --hierarchical https://www.mydiy.ie/power-tool-accessories-1/ \
  --max-products 500 \
  --batch-size 25 \
  --max-batches 4
```

### 17. Security
```bash
source env.local && python3 scripts/update_llms_agnostic.py mydiy.ie \
  --hierarchical https://www.mydiy.ie/security/ \
  --max-products 500 \
  --batch-size 25 \
  --max-batches 4
```

### 18. Consumables
```bash
source env.local && python3 scripts/update_llms_agnostic.py mydiy.ie \
  --hierarchical https://www.mydiy.ie/consumables/ \
  --max-products 500 \
  --batch-size 25 \
  --max-batches 4
```

### 19. Home, Leisure and Automotive Care
```bash
source env.local && python3 scripts/update_llms_agnostic.py mydiy.ie \
  --hierarchical https://www.mydiy.ie/home-leisure-and-automotive-care/ \
  --max-products 500 \
  --batch-size 25 \
  --max-batches 4
```

### 20. Landscape and Gardening
```bash
source env.local && python3 scripts/update_llms_agnostic.py mydiy.ie \
  --hierarchical https://www.mydiy.ie/landscape-and-gardening/ \
  --max-products 500 \
  --batch-size 25 \
  --max-batches 4
```

### 21. Merchandising
```bash
source env.local && python3 scripts/update_llms_agnostic.py mydiy.ie \
  --hierarchical https://www.mydiy.ie/merchandising-1/ \
  --max-products 500 \
  --batch-size 25 \
  --max-batches 4
```

---

## Monitoring Progress

### Check Queue Status:
```bash
jq 'length' out/mydiy-ie/pending-queue.json
```

### Check Total Scraped:
```bash
jq '[.[] | length] | add' out/mydiy-ie/llms-mydiy-ie-manifest.json
```

### Check Failed URLs:
```bash
jq 'length' out/mydiy-ie/llms-mydiy-ie-failed-urls.json
```

---

## Notes:

- Each category will discover subcategories and product categories automatically
- The skip system will prevent re-scraping existing products
- Process 100 products per category (4 batches × 25 products)
- You can interrupt anytime with Ctrl+C - progress is saved
- After all categories are done, run without --hierarchical to process remaining queue

