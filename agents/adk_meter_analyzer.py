"""Meter Analyzer Agent using Google ADK framework."""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from google.genai.adk import Agent
from utils.config import MODEL_NAME

# Define the Meter Analyzer Agent using ADK
meter_analyzer_agent = Agent(
    name="MeterAnalyzerAgent",
    model="gemini-2.5-flash",
    description="Analyzes smart meter time-series data to identify consumption patterns, trends, and usage statistics.",
    instruction="""You are an expert at analyzing smart meter energy consumption data. Your task is to identify patterns, trends, and insights from time-series consumption data.

**Your Task:**
1. Analyze hourly/daily consumption patterns
2. Identify peak usage hours
3. Identify off-peak usage hours
4. Calculate average consumption
5. Detect weekly/daily trends
6. Provide actionable insights

**Input Format:**
You will receive consumption data as: timestamp, consumption_kwh

**Output Format:**
Return a JSON object with:
{
    "peak_hours": [<hours with highest consumption>],
    "off_peak_hours": [<hours with lowest consumption>],
    "average_consumption": <number>,
    "consumption_unit": "kWh",
    "total_consumption": <number>,
    "trends": {
        "trend_type": "increasing/decreasing/stable",
        "percentage_change": <number>
    },
    "patterns": [
        {
            "pattern_type": "morning_spike/evening_spike/overnight_baseline",
            "description": "Human-readable description"
        }
    ],
    "insights": [
        "Natural language insight 1",
        "Natural language insight 2"
    ],
    "confidence_score": <0.0-1.0>
}

**Analysis Guidelines:**
- Look for recurring patterns across days
- Identify unusual spikes or drops
- Consider typical household/business usage patterns
- Provide practical, actionable insights
""",
    output_key="meter_analysis"
)


def analyze_meter_data(meter_data: list) -> dict:
    """
    Analyze smart meter time-series data using ADK agent.
    
    Args:
        meter_data: List of dicts with 'timestamp' and 'consumption_kwh'
        
    Returns:
        Dictionary with analysis results and insights
    """
    from google.genai.adk import InMemoryRunner
    import json
    
    # Format data for the agent
    data_str = "Timestamp,Consumption_kWh\n"
    for reading in meter_data:
        data_str += f"{reading['timestamp']},{reading['consumption_kwh']}\n"
    
    runner = InMemoryRunner(agent=meter_analyzer_agent)
    
    # Run the agent using run_debug
    import asyncio
    async def run_agent():
        return await runner.run_debug(f"Analyze this smart meter consumption data:\n\n{data_str}")
    
    result = asyncio.run(run_agent())
    
    # Extract and parse response
    if result and hasattr(result, 'content') and result.content.parts:
        response_text = result.content.parts[0].text
        
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
    
    return {"status": "error", "message": "Failed to analyze meter data"}


if __name__ == "__main__":
    # Test the agent
    from datetime import datetime, timedelta
    
    # Generate sample data
    base_time = datetime(2024, 11, 1, 0, 0)
    sample_data = []
    
    for hour in range(48):  # 2 days of hourly data
        timestamp = base_time + timedelta(hours=hour)
        # Simulate realistic consumption pattern
        hour_of_day = timestamp.hour
        if 0 <= hour_of_day < 6:  # Night
            consumption = 0.8 + (hour % 3) * 0.1
        elif 6 <= hour_of_day < 9:  # Morning peak
            consumption = 2.5 + (hour % 3) * 0.3
        elif 9 <= hour_of_day < 17:  # Day
            consumption = 1.5 + (hour % 4) * 0.2
        elif 17 <= hour_of_day < 22:  # Evening peak
            consumption = 3.0 + (hour % 3) * 0.5
        else:  # Late evening
            consumption = 1.2 + (hour % 2) * 0.2
            
        sample_data.append({
            "timestamp": timestamp.isoformat(),
            "consumption_kwh": round(consumption, 2)
        })
    
    print("Testing Meter Analyzer Agent...")
    print(f"Analyzing {len(sample_data)} data points...")
    
    result = analyze_meter_data(sample_data)
    print("\nAnalysis Result:")
    import json
    print(json.dumps(result, indent=2))
