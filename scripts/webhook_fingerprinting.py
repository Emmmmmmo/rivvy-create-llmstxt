#!/usr/bin/env python3
"""
Webhook Fingerprinting Module
Prevents duplicate webhook processing using content-based fingerprints
"""

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class WebhookFingerprinter:
    """Manages webhook fingerprinting to prevent duplicate processing."""
    
    def __init__(self, state_file: str = "config/webhook_fingerprints.json"):
        self.state_file = Path(state_file)
        self.fingerprints = self._load_fingerprints()
    
    def _load_fingerprints(self) -> Dict:
        """Load existing fingerprints from state file."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Could not load fingerprints: {e}")
        return {}
    
    def _save_fingerprints(self):
        """Save fingerprints to state file."""
        try:
            # Ensure directory exists
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.state_file, 'w') as f:
                json.dump(self.fingerprints, f, indent=2)
        except Exception as e:
            print(f"Error saving fingerprints: {e}")
    
    def create_webhook_fingerprint(self, payload: Dict) -> str:
        """Create unique fingerprint for webhook payload."""
        # Sort pages by URL for consistent fingerprinting
        pages = sorted(payload["changedPages"], key=lambda x: x["url"])
        
        fingerprint_data = {
            "website_id": payload["website"]["id"],
            "website_url": payload["website"]["url"],
            "summary": payload.get("summary", ""),
            "pages": []
        }
        
        for page in pages:
            # Create content hash for the page
            content_hash = hashlib.md5(
                page["scrapedContent"]["markdown"].encode('utf-8')
            ).hexdigest()
            
            fingerprint_data["pages"].append({
                "url": page["url"],
                "change_type": page["changeType"],
                "detected_at": page["detectedAt"],
                "content_hash": content_hash[:16],  # Short hash for fingerprint
                "title": page["scrapedContent"].get("title", "")[:100]  # Truncated title
            })
        
        # Create deterministic fingerprint
        fingerprint_str = json.dumps(fingerprint_data, sort_keys=True)
        return hashlib.sha256(fingerprint_str.encode('utf-8')).hexdigest()[:32]
    
    def is_duplicate_webhook(self, payload: Dict) -> Tuple[bool, str, Optional[Dict]]:
        """
        Check if webhook is a duplicate.
        
        Returns:
            (is_duplicate, fingerprint, duplicate_info)
        """
        fingerprint = self.create_webhook_fingerprint(payload)
        
        if fingerprint in self.fingerprints:
            duplicate_info = self.fingerprints[fingerprint]
            return True, fingerprint, duplicate_info
        
        return False, fingerprint, None
    
    def record_webhook_processed(self, payload: Dict, fingerprint: str) -> Dict:
        """Record that a webhook has been processed."""
        webhook_info = {
            "processed_at": datetime.now().isoformat(),
            "summary": payload.get("summary", ""),
            "page_count": len(payload["changedPages"]),
            "website_url": payload["website"]["url"],
            "pages": [
                {
                    "url": page["url"],
                    "change_type": page["changeType"],
                    "detected_at": page["detectedAt"]
                }
                for page in payload["changedPages"]
            ]
        }
        
        self.fingerprints[fingerprint] = webhook_info
        self._save_fingerprints()
        
        return webhook_info
    
    def process_webhook(self, payload: Dict) -> Dict:
        """
        Process webhook with fingerprinting.
        
        Returns processing decision and metadata.
        """
        is_duplicate, fingerprint, duplicate_info = self.is_duplicate_webhook(payload)
        
        result = {
            "fingerprint": fingerprint,
            "is_duplicate": is_duplicate,
            "should_process": not is_duplicate,
            "pages_count": len(payload["changedPages"]),
            "website_url": payload["website"]["url"]
        }
        
        if is_duplicate:
            result["duplicate_info"] = duplicate_info
            result["original_processed_at"] = duplicate_info["processed_at"]
            print(f"🚫 Duplicate webhook detected!")
            print(f"   Fingerprint: {fingerprint}")
            print(f"   Originally processed: {duplicate_info['processed_at']}")
            print(f"   Pages: {duplicate_info['page_count']}")
        else:
            # Record this webhook as processed
            webhook_info = self.record_webhook_processed(payload, fingerprint)
            result["webhook_info"] = webhook_info
            print(f"✅ New webhook detected!")
            print(f"   Fingerprint: {fingerprint}")
            print(f"   Pages to process: {len(payload['changedPages'])}")
        
        return result
    
    def cleanup_old_fingerprints(self, days_old: int = 30):
        """Remove fingerprints older than specified days."""
        cutoff_date = datetime.now().timestamp() - (days_old * 24 * 60 * 60)
        
        old_fingerprints = []
        for fingerprint, info in self.fingerprints.items():
            try:
                processed_date = datetime.fromisoformat(info["processed_at"])
                if processed_date.timestamp() < cutoff_date:
                    old_fingerprints.append(fingerprint)
            except Exception:
                # Remove invalid entries
                old_fingerprints.append(fingerprint)
        
        for fingerprint in old_fingerprints:
            del self.fingerprints[fingerprint]
        
        if old_fingerprints:
            self._save_fingerprints()
            print(f"🧹 Cleaned up {len(old_fingerprints)} old fingerprints")


def main():
    """CLI interface for webhook fingerprinting."""
    if len(sys.argv) < 2:
        print("Usage: python3 webhook_fingerprinting.py <payload_file> [--cleanup]")
        print("       python3 webhook_fingerprinting.py --cleanup [days]")
        sys.exit(1)
    
    fingerprinter = WebhookFingerprinter()
    
    if sys.argv[1] == "--cleanup":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        fingerprinter.cleanup_old_fingerprints(days)
        return
    
    # Process webhook payload file
    payload_file = sys.argv[1]
    
    try:
        with open(payload_file, 'r') as f:
            payload = json.load(f)
    except Exception as e:
        print(f"Error reading payload file: {e}")
        sys.exit(1)
    
    result = fingerprinter.process_webhook(payload)
    
    # Output result as JSON for GitHub Actions
    print("\n" + "="*50)
    print("FINGERPRINT RESULT:")
    print(json.dumps(result, indent=2))
    
    # Exit with appropriate code
    if result["should_process"]:
        print(f"\n✅ Webhook should be processed")
        sys.exit(0)  # Continue processing
    else:
        print(f"\n🚫 Webhook is duplicate - skipping")
        sys.exit(1)  # Skip processing


if __name__ == "__main__":
    main()
