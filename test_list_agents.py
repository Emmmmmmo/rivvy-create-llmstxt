#!/usr/bin/env python3
"""
Test script to list available ElevenLabs agents
"""

import requests
import json

api_key = "sk_83e6c1cc81d1cede94e780e3b968e715d2ef58389bc44bfa"
base_url = "https://api.elevenlabs.io/v1"

headers = {
    "xi-api-key": api_key,
    "Content-Type": "application/json"
}

print("Testing ElevenLabs API access...")

# Test user info
print("\n1. Testing user info...")
try:
    user_url = f"{base_url}/user"
    response = requests.get(user_url, headers=headers, timeout=10)
    print(f"User info status: {response.status_code}")
    if response.status_code == 200:
        user_data = response.json()
        print(f"User: {user_data}")
    else:
        print(f"User info response: {response.text}")
except Exception as e:
    print(f"User info error: {e}")

# Test agents list
print("\n2. Testing agents list...")
try:
    agents_url = f"{base_url}/agents"
    response = requests.get(agents_url, headers=headers, timeout=10)
    print(f"Agents list status: {response.status_code}")
    if response.status_code == 200:
        agents_data = response.json()
        print(f"Found {len(agents_data.get('agents', []))} agents:")
        for agent in agents_data.get('agents', []):
            print(f"  - ID: {agent.get('agent_id')}")
            print(f"    Name: {agent.get('name')}")
            print(f"    Status: {agent.get('status')}")
            print()
    else:
        print(f"Agents list response: {response.text}")
except Exception as e:
    print(f"Agents list error: {e}")

# Test voices list (to verify API key works)
print("\n3. Testing voices list...")
try:
    voices_url = f"{base_url}/voices"
    response = requests.get(voices_url, headers=headers, timeout=10)
    print(f"Voices list status: {response.status_code}")
    if response.status_code == 200:
        voices_data = response.json()
        print(f"Found {len(voices_data.get('voices', []))} voices")
    else:
        print(f"Voices list response: {response.text}")
except Exception as e:
    print(f"Voices list error: {e}")
