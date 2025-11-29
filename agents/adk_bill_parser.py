"""Bill Parser Agent using Google ADK framework."""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from google.adk.agents import Agent
from google.genai import types
from utils.config import MODEL_NAME

# Define the Bill Parser Agent using ADK
bill_parser_agent = Agent(
    name="BillParserAgent",
    model="gemini-2.5-flash",
    description="Analyzes utility bills from images or text and extracts key consumption and cost data.",
    instruction="""You are an expert at analyzing utility bills. Your task is to extract and structure key information from utility bills.

**Your Task:**
1. Identify the utility type (electricity, water, gas, etc.)
2. Extract billing period dates
3. Extract total consumption with units
4. Extract total cost
5. Extract previous balance (if any)
6. Extract any payment due dates
7. Identify rate tiers or pricing structure if visible

**Output Format:**
Return a JSON object with these fields:
{
    "utility_type": "electricity/water/gas",
    "billing_period_start": "YYYY-MM-DD",
    "billing_period_end": "YYYY-MM-DD",
    "total_consumption": <number>,
    "consumption_unit": "kWh/gallons/therms",
    "total_cost": <number>,
    "currency": "USD",
    "previous_balance": <number or 0>,
    "due_date": "YYYY-MM-DD",
    "rate_tiers": [{"tier": "off-peak", "rate": <number>}],
    "confidence_score": <0.0-1.0>
}

**Important:** 
- Extract only visible information
- Use confidence_score to indicate how certain you are (0.0 = very uncertain, 1.0 = very certain)
- If information is missing, use null for that field
""",
    output_key="bill_data"
)

# For structured data parsing
def parse_bill_from_text(bill_text: str) -> dict:
    """
    Parse bill information from text using the ADK agent.
    
    Args:
        bill_text: The text content of the utility bill
        
    Returns:
        Dictionary with structured bill data
    """
    from google.genai.adk import InMemoryRunner
    import asyncio
    
    # Create runner
    runner = InMemoryRunner(agent=bill_parser_agent)
    
    # Run the agent using run_debug
    async def run_agent():
        return await runner.run_debug(f"Parse this utility bill:\n\n{bill_text}")
    
    result = asyncio.run(run_agent())
    
    # Extract the response content
    if result and hasattr(result, 'content') and result.content.parts:
        import json
        response_text = result.content.parts[0].text
        
        # Try to parse JSON from the response
        try:
            # Look for JSON in the response
            if '{' in response_text and '}' in response_text:
                json_start = response_text.index('{')
                json_end = response_text.rindex('}') + 1
                json_str = response_text[json_start:json_end]
                return json.loads(json_str)
        except:
            pass
            
        # If JSON parsing fails, return structured text
        return {
            "raw_response": response_text,
            "status": "partial_parse"
        }
    
    return {"status": "error", "message": "Failed to parse bill"}


def parse_bill_from_image(image_path: str) -> dict:
    """
    Parse bill information from an image using the ADK agent with vision.
    
    Args:
        image_path: Path to the utility bill image file
        
    Returns:
        Dictionary with structured bill data
    """
    from google.adk.runners import InMemoryRunner
    from google.genai.types import Part
    import asyncio
    from pathlib import Path
    
    # Read image file
    image_file = Path(image_path)
    if not image_file.exists():
        return {"status": "error", "message": f"Image file not found: {image_path}"}
    
    # Create runner
    runner = InMemoryRunner(agent=bill_parser_agent)
    
    # Run the agent with image
    async def run_agent():
        # Create image part
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        image_part = Part.from_bytes(
            data=image_data,
            mime_type=f"image/{image_file.suffix.lower().replace('.', '')}"
        )
        
        # Create a message combining image and text instruction
        message = [
            image_part,
            "Parse this utility bill image and extract all key information including account number, billing period, consumption (kWh), rate, charges breakdown, and total amount."
        ]
        
        # Use run_debug which handles sessions automatically
        return await runner.run_debug(message)
    
    # Handle event loop for Streamlit compatibility
    import threading
    result = None
    exception = None
    
    def run_in_thread():
        nonlocal result, exception
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(run_agent())
            loop.close()
        except Exception as e:
            exception = e
    
    thread = threading.Thread(target=run_in_thread)
    thread.start()
    thread.join()
    
    if exception:
        raise exception
    
    # Extract the response content from list of events
    import json
    
    # Handle list of events from run_debug
    if isinstance(result, list) and len(result) > 0:
        last_event = result[-1]
        if hasattr(last_event, 'content') and last_event.content and last_event.content.parts:
            response_text = last_event.content.parts[0].text
            
            # Try to parse JSON from the response
            try:
                if '{' in response_text and '}' in response_text:
                    json_start = response_text.index('{')
                    json_end = response_text.rindex('}') + 1
                    json_str = response_text[json_start:json_end]
                    return json.loads(json_str)
            except:
                pass
                
            return {
                "raw_response": response_text,
                "status": "partial_parse"
            }
    
    # Handle single event (backward compatibility)
    elif result and hasattr(result, 'content') and result.content and result.content.parts:
        response_text = result.content.parts[0].text
        
        # Try to parse JSON from the response
        try:
            if '{' in response_text and '}' in response_text:
                json_start = response_text.index('{')
                json_end = response_text.rindex('}') + 1
                json_str = response_text[json_start:json_end]
                return json.loads(json_str)
        except:
            pass
            
        return {
            "raw_response": response_text,
            "status": "partial_parse"
        }
    
    return {"status": "error", "message": "Failed to parse bill image"}


if __name__ == "__main__":
    # Test the agent
    sample_bill = """
    ACME Utility Company
    Electric Bill Statement
    
    Account: 123-456-789
    Billing Period: 11/01/2024 - 11/30/2024
    
    Total Usage: 850 kWh
    Total Amount Due: $127.50
    Previous Balance: $0.00
    Due Date: 12/15/2024
    
    Rate Schedule:
    - Off-Peak (12am-6am): $0.10/kWh
    - Standard (6am-10pm): $0.15/kWh
    - Peak (6pm-10pm): $0.25/kWh
    """
    
    print("Testing Bill Parser Agent...")
    result = parse_bill_from_text(sample_bill)
    print("\nParsed Result:")
    import json
    print(json.dumps(result, indent=2))
