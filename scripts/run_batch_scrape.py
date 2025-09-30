#!/usr/bin/env python3
"""
Automated batch scraper for JG Engineering.
Runs 5 batches of 300 products each with automatic delays and error handling.
"""

import subprocess
import time
import json
import os
from datetime import datetime
import sys

def log_message(message):
    """Log message with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def get_current_progress():
    """Get current progress from index file."""
    index_file = "out/jgengineering-ie/llms-jgengineering-ie-index.json"
    if os.path.exists(index_file):
        with open(index_file, 'r') as f:
            data = json.load(f)
            return len(data)
    return 0

def run_batch(batch_num, limit):
    """Run a single batch."""
    log_message(f"Starting Batch {batch_num}: {limit} products")
    
    # Check current progress
    current_count = get_current_progress()
    log_message(f"Current progress: {current_count} products already scraped")
    
    # Set up environment
    env = os.environ.copy()
    env['FIRECRAWL_API_KEY'] = 'fc-7bc152d1afd34567803e4c0d12de3386'
    
    # Run the batch
    cmd = [
        'python3', 'scripts/update_llms_agnostic.py',
        'jgengineering.ie',
        '--full',
        '--limit', str(limit),
        '--verbose'
    ]
    
    try:
        log_message(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=14400)  # 4 hour timeout
        
        if result.returncode == 0:
            log_message(f"✅ Batch {batch_num} completed successfully")
            
            # Check new progress
            new_count = get_current_progress()
            products_added = new_count - current_count
            log_message(f"Products added in this batch: {products_added}")
            log_message(f"Total products scraped: {new_count}")
            
            return True, products_added
        else:
            log_message(f"❌ Batch {batch_num} failed with return code {result.returncode}")
            log_message(f"Error output: {result.stderr}")
            return False, 0
            
    except subprocess.TimeoutExpired:
        log_message(f"⏰ Batch {batch_num} timed out after 4 hours")
        return False, 0
    except Exception as e:
        log_message(f"💥 Batch {batch_num} failed with exception: {e}")
        return False, 0

def main():
    """Main function to run all batches."""
    log_message("🚀 Starting automated batch scrape for JG Engineering")
    log_message("=" * 60)
    
    # Batch configuration
    batches = [
        (1, 300),  # Batch 1: 300 products
        (2, 300),  # Batch 2: 300 products  
        (3, 300),  # Batch 3: 300 products
        (4, 300),  # Batch 4: 300 products
        (5, 300),  # Batch 5: 300 products
    ]
    
    total_products_added = 0
    successful_batches = 0
    
    for batch_num, limit in batches:
        log_message(f"\n🔄 Starting Batch {batch_num}/5")
        log_message("-" * 40)
        
        # Run the batch
        success, products_added = run_batch(batch_num, limit)
        
        if success:
            successful_batches += 1
            total_products_added += products_added
            
            # Check if we've reached the target
            current_total = get_current_progress()
            if current_total >= 1351:  # Target reached (from previous full scrape)
                log_message(f"🎯 Target of 1351 products reached! Current total: {current_total}")
                break
                
            # Delay between batches (except for the last one)
            if batch_num < len(batches):
                log_message("⏳ Waiting 30 seconds before next batch...")
                time.sleep(30)
        else:
            log_message(f"❌ Batch {batch_num} failed. Stopping automated process.")
            log_message("💡 You can manually resume from where it left off.")
            break
    
    # Final summary
    log_message("\n" + "=" * 60)
    log_message("📊 FINAL SUMMARY")
    log_message("=" * 60)
    log_message(f"Successful batches: {successful_batches}/5")
    log_message(f"Total products added: {total_products_added}")
    log_message(f"Final product count: {get_current_progress()}")
    
    if successful_batches == 5:
        log_message("🎉 All batches completed successfully!")
    else:
        log_message(f"⚠️  {5 - successful_batches} batches failed or were skipped")
        log_message("💡 You can manually run remaining batches if needed")

if __name__ == "__main__":
    main()
