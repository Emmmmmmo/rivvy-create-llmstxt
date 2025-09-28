#!/usr/bin/env python3
"""
Force refresh script to re-scrape the UNC BaerFix collection page
and update the knowledge base with current content.
"""

import os
import sys
import json
import subprocess
from pathlib import Path

def main():
    # The URL that needs to be refreshed
    url = "https://www.jgengineering.ie/collections/unc-baerfix-thread-repair-kits-like-timesert"
    base_url = "https://www.jgengineering.ie"
    output_dir = "out/jgengineering.ie"
    
    print(f"🔄 Force refreshing: {url}")
    print(f"📁 Output directory: {output_dir}")
    
    # Check if the script exists
    script_path = "scripts/update_llms_sharded.py"
    if not os.path.exists(script_path):
        print(f"❌ Script not found: {script_path}")
        sys.exit(1)
    
    # Prepare the command
    cmd = [
        "python3", script_path,
        base_url,
        "--added", json.dumps([url]),
        "--output-dir", output_dir,
        "--verbose"
    ]
    
    print(f"🚀 Running command: {' '.join(cmd)}")
    
    # Run the script
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("✅ Script completed successfully!")
        print("📄 Output:")
        print(result.stdout)
        
        # Check if the file was updated
        expected_file = f"{output_dir}/llms-jgengineering-ie-unc-baerfix-thread-repair-kits-like-timesert.txt"
        if os.path.exists(expected_file):
            print(f"✅ File updated: {expected_file}")
            
            # Check if it contains the new product
            with open(expected_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if "Test_Deburring_Item" in content and "6 products" in content:
                    print("✅ File contains the new product and shows 6 products!")
                else:
                    print("❌ File still contains old content")
                    print("Content preview:")
                    print(content[:500] + "..." if len(content) > 500 else content)
        else:
            print(f"❌ Expected file not found: {expected_file}")
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Script failed with exit code {e.returncode}")
        print("📄 Error output:")
        print(e.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
