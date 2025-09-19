#!/usr/bin/env python3
"""
Simple test script to debug ElevenLabs API calls
"""

import os
import requests
import json

# Test with a small file
api_key = "sk_afa185e16d193042c92a25186fe3bd13cee53f64ecda8884"
agent_id = "agent_7001k39631sjfz4t73jq484kpzrn"
base_url = "https://api.elevenlabs.io/v1"

# Read a small test file
test_file = "out/jgengineering.ie/llms-jgengineering-ie-ass-products.txt"
with open(test_file, 'r', encoding='utf-8') as f:
    content = f.read()

print(f"File size: {len(content)} characters")
print(f"First 200 chars: {content[:200]}...")

# Test different API endpoints
endpoints_to_test = [
    f"/agents/{agent_id}/knowledge-base",
    f"/agents/{agent_id}/knowledge-base/documents", 
    f"/agents/{agent_id}/documents",
    f"/knowledge-base/documents"
]

headers = {
    "xi-api-key": api_key,
    "Content-Type": "application/json"
}

for endpoint in endpoints_to_test:
    url = base_url + endpoint
    print(f"\nTesting endpoint: {endpoint}")
    
    # Test with a simple payload
    payload = {
        "name": "test_document.txt",
        "content": "This is a test document for ElevenLabs API testing.",
        "type": "text"
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
        
        if response.status_code == 200:
            print("✅ SUCCESS! This endpoint works!")
            break
        elif response.status_code == 404:
            print("❌ 404 - Endpoint not found")
        else:
            print(f"❌ Error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

print("\nTesting agent info endpoint...")
try:
    agent_url = f"{base_url}/agents/{agent_id}"
    response = requests.get(agent_url, headers=headers, timeout=10)
    print(f"Agent info status: {response.status_code}")
    if response.status_code == 200:
        agent_data = response.json()
        print(f"Agent name: {agent_data.get('name', 'Unknown')}")
        print(f"Agent status: {agent_data.get('status', 'Unknown')}")
    else:
        print(f"Agent info response: {response.text[:200]}...")
except Exception as e:
    print(f"Agent info error: {e}")
