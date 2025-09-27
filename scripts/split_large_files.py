#!/usr/bin/env python3
"""
Script to split large files into smaller chunks for ElevenLabs assignment.
This preserves all content while staying within file size limits.
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FileSplitter:
    def __init__(self, max_characters: int = 300000):  # ElevenLabs 300K character limit
        self.max_characters = max_characters
        self.split_files_dir = Path("out/jgengineering.ie/split")
        self.split_files_dir.mkdir(exist_ok=True)
    
    def split_large_file(self, file_path: Path) -> List[Path]:
        """Split a large file into smaller chunks."""
        file_size = file_path.stat().st_size
        
        # Read the file content first to check character count
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        char_count = len(content)
        
        if char_count <= self.max_characters:
            logger.info(f"✅ File {file_path.name} is already small enough ({char_count:,} characters)")
            return [file_path]
        
        logger.info(f"📦 Splitting {file_path.name} ({char_count:,} characters) into smaller chunks...")
        
        # Split into chunks
        chunks = []
        chunk_size = self.max_characters
        start = 0
        
        while start < len(content):
            end = start + chunk_size
            
            # Try to find a good break point (end of a product section)
            if end < len(content):
                # Look for the last occurrence of a product separator
                chunk_content = content[start:end]
                
                # Find the last complete product section
                last_product_end = chunk_content.rfind('\n\n## ')
                if last_product_end > chunk_size * 0.7:  # If we found a good break point
                    end = start + last_product_end
                else:
                    # Look for other good break points
                    last_section_end = chunk_content.rfind('\n\n---\n')
                    if last_section_end > chunk_size * 0.7:
                        end = start + last_section_end
                    else:
                        # Look for double newlines
                        last_break = chunk_content.rfind('\n\n')
                        if last_break > chunk_size * 0.8:
                            end = start + last_break
            
            chunk_content = content[start:end]
            
            # Create chunk file
            chunk_num = len(chunks) + 1
            chunk_filename = f"{file_path.stem}_part{chunk_num}.txt"
            chunk_path = self.split_files_dir / chunk_filename
            
            with open(chunk_path, 'w', encoding='utf-8') as f:
                f.write(chunk_content)
            
            chunks.append(chunk_path)
            logger.info(f"  📄 Created chunk {chunk_num}: {chunk_filename} ({len(chunk_content):,} chars)")
            
            start = end
        
        logger.info(f"✅ Split {file_path.name} into {len(chunks)} chunks")
        return chunks
    
    def split_all_large_files(self, domain_dir: Path) -> Dict[str, List[Path]]:
        """Split all large files in a domain directory."""
        results = {}
        
        for file_path in domain_dir.glob("*.txt"):
            if file_path.name.startswith("llms-"):
                file_size = file_path.stat().st_size
                
                # Check character count instead of file size
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                char_count = len(content)
                
                if char_count > self.max_characters:
                    logger.info(f"🔍 Processing large file: {file_path.name} ({char_count:,} characters)")
                    chunks = self.split_large_file(file_path)
                    results[file_path.name] = chunks
                else:
                    logger.info(f"✅ File is small enough: {file_path.name} ({char_count:,} characters)")
                    results[file_path.name] = [file_path]
        
        return results
    
    def update_sync_state_for_split_files(self, domain: str, split_results: Dict[str, List[Path]]):
        """Update the sync state to include split files."""
        sync_state_file = Path("config/elevenlabs_sync_state.json")
        
        with open(sync_state_file, 'r') as f:
            sync_state = json.load(f)
        
        # Remove original large files from sync state
        for original_filename, chunks in split_results.items():
            if len(chunks) > 1:  # File was split
                original_key = f"{domain}:{original_filename}"
                if original_key in sync_state:
                    del sync_state[original_key]
                    logger.info(f"🗑️ Removed original file from sync state: {original_filename}")
                
                # Add split files to sync state
                for chunk_path in chunks:
                    chunk_key = f"{domain}:{chunk_path.name}"
                    sync_state[chunk_key] = {
                        "file_path": str(chunk_path),
                        "file_size": chunk_path.stat().st_size,
                        "split_from": original_filename,
                        "needs_upload": True
                    }
                    logger.info(f"➕ Added split file to sync state: {chunk_path.name}")
        
        # Save updated sync state
        with open(sync_state_file, 'w') as f:
            json.dump(sync_state, f, indent=2)
        
        logger.info("💾 Updated sync state with split files")

def main():
    """Main function to split large files."""
    domain_dir = Path("out/jgengineering.ie")
    
    if not domain_dir.exists():
        logger.error(f"Domain directory not found: {domain_dir}")
        return
    
    splitter = FileSplitter()
    
    # Split all large files
    split_results = splitter.split_all_large_files(domain_dir)
    
    # Update sync state
    splitter.update_sync_state_for_split_files("jgengineering.ie", split_results)
    
    # Summary
    total_original = len(split_results)
    total_chunks = sum(len(chunks) for chunks in split_results.values())
    
    logger.info(f"📊 Summary:")
    logger.info(f"  • Original files: {total_original}")
    logger.info(f"  • Total chunks: {total_chunks}")
    logger.info(f"  • Files split: {sum(1 for chunks in split_results.values() if len(chunks) > 1)}")
    
    logger.info("✅ File splitting completed!")

if __name__ == "__main__":
    main()
