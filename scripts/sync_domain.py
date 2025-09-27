#!/usr/bin/env python3
"""
ElevenLabs Domain Sync Orchestrator

This script orchestrates the upload and assignment process for a domain.
It runs the upload script first, then the assignment script.

Usage:
  python3 scripts/sync_domain.py [domain] [--force] [--wait-for-indexing]
"""

import os
import sys
import subprocess
import logging
import time
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_script(script_path: str, args: list) -> bool:
    """Run a script and return success status."""
    try:
        cmd = [sys.executable, script_path] + args
        logger.info(f"Running: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("✅ Script completed successfully")
            if result.stdout:
                logger.info(f"Output: {result.stdout}")
            return True
        else:
            logger.error(f"❌ Script failed with return code {result.returncode}")
            if result.stderr:
                logger.error(f"Error: {result.stderr}")
            if result.stdout:
                logger.info(f"Output: {result.stdout}")
            return False
            
    except Exception as e:
        logger.error(f"Error running script {script_path}: {e}")
        return False

def main():
    """Main function to orchestrate upload and assignment."""
    try:
        # Check command line arguments
        args = sys.argv[1:] if len(sys.argv) > 1 else []
        
        # Determine domain
        domain = None
        force_upload = False
        wait_for_indexing = False
        
        for arg in args:
            if arg == '--force':
                force_upload = True
            elif arg == '--wait-for-indexing':
                wait_for_indexing = True
            elif not arg.startswith('--'):
                domain = arg
                break
        
        if not domain:
            logger.error("Domain is required. Usage: python3 scripts/sync_domain.py [domain] [--force] [--wait-for-indexing]")
            exit(1)
        
        logger.info(f"🚀 Starting sync process for domain: {domain}")
        
        # Step 1: Upload files
        logger.info("📤 Step 1: Uploading files to knowledge base...")
        upload_args = [domain]
        if force_upload:
            upload_args.append('--force')
        
        upload_success = run_script("scripts/upload_to_knowledge_base.py", upload_args)
        
        if not upload_success:
            logger.error("❌ Upload failed. Stopping sync process.")
            exit(1)
        
        # Step 2: Wait a bit for files to be processed
        logger.info("⏱️  Waiting 30 seconds for files to be processed...")
        time.sleep(30)
        
        # Step 3: Assign files to agent
        logger.info("🎯 Step 2: Assigning files to agent...")
        assign_args = [domain]
        if wait_for_indexing:
            assign_args.append('--wait-for-indexing')
        
        assign_success = run_script("scripts/assign_to_agent.py", assign_args)
        
        if not assign_success:
            logger.error("❌ Assignment failed. Files are uploaded but not assigned.")
            logger.info("💡 You can retry assignment later with: python3 scripts/assign_to_agent.py {domain}")
            exit(1)
        
        logger.info(f"🎉 Sync completed successfully for {domain}!")
        logger.info("🤖 RAG indexing will happen automatically in the background")
        
    except Exception as e:
        logger.error(f"Sync process failed: {e}")
        exit(1)

if __name__ == "__main__":
    main()
