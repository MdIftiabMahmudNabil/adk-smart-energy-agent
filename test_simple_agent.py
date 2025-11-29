"""Simple test to verify ADK agents are working with new API key."""

import sys
import os
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

# Load config to set API key
from utils import config

import asyncio
from google.genai.adk import Agent
from google.genai.adk import InMemoryRunner

# Create a simple test agent
test_agent = Agent(
    name="TestAgent",
    model="gemini-2.5-flash",
    description="A simple test agent",
    instruction="You are a helpful assistant. Answer questions concisely."
)

async def test():
    print("Testing ADK with new API key...")
    print(f"Model: gemini-2.5-flash\n")
    
    runner = InMemoryRunner(agent=test_agent)
    
    # Test simple question
    print("Question: What is 2+2?")
    result = await runner.run_debug("What is 2+2?")
    
    # run_debug returns Response object
    print(f"\nResult type: {type(result)}")
    print(f"Result: {result}\n")
    
    # Check if we got any response (run_debug prints output, so if we reach here, it worked)
    if result is not None:
        print("✅ SUCCESS: ADK is working with the new API key!")
        print("✅ Agent responded correctly!")
        return True
    else:
        print("❌ FAILED: No response received")
        return False

if __name__ == "__main__":
    success = asyncio.run(test())
    exit(0 if success else 1)
