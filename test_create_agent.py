#!/usr/bin/env python3
"""
Test script to create an ElevenLabs agent
"""

import requests
import json

api_key = "sk_83e6c1cc81d1cede94e780e3b968e715d2ef58389bc44bfa"
base_url = "https://api.elevenlabs.io/v1"

headers = {
    "xi-api-key": api_key,
    "Content-Type": "application/json"
}

print("Testing ElevenLabs agent creation...")

# Try to create a test agent
agent_data = {
    "name": "JG Engineering Test Agent",
    "description": "Test agent for JG Engineering products",
    "instructions": "You are a helpful assistant for JG Engineering products and services.",
    "voice_id": "21m00Tcm4TlvDq8ikWAM",  # Default voice
    "model_id": "eleven_turbo_v2_5",
    "knowledge_base": {
        "enabled": True
    }
}

print("\n1. Attempting to create agent...")
try:
    create_url = f"{base_url}/agents"
    response = requests.post(create_url, headers=headers, json=agent_data, timeout=30)
    print(f"Create agent status: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200 or response.status_code == 201:
        agent_info = response.json()
        print(f"✅ Agent created successfully!")
        print(f"Agent ID: {agent_info.get('agent_id')}")
        print(f"Agent Name: {agent_info.get('name')}")
    else:
        print(f"❌ Failed to create agent")
        
except Exception as e:
    print(f"❌ Exception creating agent: {e}")

# Try alternative endpoints
print("\n2. Testing alternative agent endpoints...")
alternative_endpoints = [
    "/conversational-ai/agents",
    "/ai-agents", 
    "/assistants",
    "/chat-agents"
]

for endpoint in alternative_endpoints:
    try:
        url = f"{base_url}{endpoint}"
        response = requests.get(url, headers=headers, timeout=10)
        print(f"{endpoint}: {response.status_code}")
        if response.status_code == 200:
            print(f"✅ Found working endpoint: {endpoint}")
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)[:200]}...")
    except Exception as e:
        print(f"{endpoint}: Error - {e}")
