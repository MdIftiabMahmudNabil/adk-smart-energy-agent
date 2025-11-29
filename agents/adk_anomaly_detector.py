"""Anomaly Detector Agent using Google ADK framework."""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from google.genai.adk import Agent
from utils.config import MODEL_NAME

# Define the Anomaly Detector Agent using ADK
anomaly_detector_agent = Agent(
    name="AnomalyDetectorAgent",
    model="gemini-2.5-flash",
    description="Detects unusual consumption patterns and anomalies in energy usage data, providing explanations for each anomaly.",
    instruction="""You are an expert at detecting anomalies in energy consumption data. Your task is to identify unusual patterns, spikes, or drops that deviate from normal usage.

**Your Task:**
1. Identify consumption values that are significantly different from normal
2. Classify each anomaly type (spike, drop, unusual pattern)
3. Estimate the severity (low/medium/high)
4. Provide likely explanations for each anomaly
5. Calculate potential cost impact

**Input Format:**
You will receive:
- Consumption data with timestamps
- Statistical threshold information (mean, std dev)

**Output Format:**
Return a JSON object with:
{
    "anomalies_detected": <number>,
    "anomalies": [
        {
            "timestamp": "ISO-8601 timestamp",
            "consumption_kwh": <number>,
            "expected_kwh": <number>,
            "deviation_percentage": <number>,
            "anomaly_type": "spike/drop/unusual_pattern",
            "severity": "low/medium/high",
            "possible_causes": [
                "Explanation 1",
                "Explanation 2"
            ],
            "cost_impact": <number>
        }
    ],
    "summary": {
        "total_anomalies": <number>,
        "high_severity_count": <number>,
        "estimated_waste": <number>,
        "recommendations": [
            "Recommendation 1",
            "Recommendation 2"
        ]
    },
    "confidence_score": <0.0-1.0>
}

**Analysis Guidelines:**
- Consider typical usage patterns for the time of day/week
- Anomalies should be 2+ standard deviations from mean
- Provide practical, actionable explanations
- Estimate financial impact when possible
""",
    output_key="anomaly_report"
)


def detect_anomalies(meter_data: list, threshold_multiplier: float = 2.0) -> dict:
    """
    Detect anomalies in meter data using ADK agent.
    
    Args:
        meter_data: List of dicts with 'timestamp' and 'consumption_kwh'
        threshold_multiplier: Number of standard deviations for anomaly detection
        
    Returns:
        Dictionary with detected anomalies and analysis
    """
    from google.genai.adk import InMemoryRunner
    import json
    import statistics
    
    # Calculate statistics
    consumptions = [d['consumption_kwh'] for d in meter_data]
    mean_consumption = statistics.mean(consumptions)
    std_dev = statistics.stdev(consumptions) if len(consumptions) > 1 else 0
    threshold = mean_consumption + (threshold_multiplier * std_dev)
    
    # Format data for agent
    data_str = f"Statistical Summary:\n"
    data_str += f"Mean Consumption: {mean_consumption:.2f} kWh\n"
    data_str += f"Standard Deviation: {std_dev:.2f} kWh\n"
    data_str += f"Anomaly Threshold (>{threshold_multiplier}σ): {threshold:.2f} kWh\n\n"
    data_str += "Consumption Data:\n"
    data_str += "Timestamp,Consumption_kWh\n"
    
    for reading in meter_data:
        data_str += f"{reading['timestamp']},{reading['consumption_kwh']}\n"
    
    runner = InMemoryRunner(agent=anomaly_detector_agent)
    
    # Run the agent using run_debug
    import asyncio
    async def run_agent():
        return await runner.run_debug(f"Detect and explain anomalies in this consumption data:\n\n{data_str}")
    
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
    
    return {"status": "error", "message": "Failed to detect anomalies"}


if __name__ == "__main__":
    # Test the agent
    from datetime import datetime, timedelta
    import random
    
    # Generate sample data with some anomalies
    base_time = datetime(2024, 11, 1, 0, 0)
    sample_data = []
    
    for hour in range(48):
        timestamp = base_time + timedelta(hours=hour)
        hour_of_day = timestamp.hour
        
        # Normal consumption pattern
        if 0 <= hour_of_day < 6:
            consumption = 0.8 + random.uniform(-0.1, 0.1)
        elif 6 <= hour_of_day < 9:
            consumption = 2.5 + random.uniform(-0.2, 0.2)
        elif 9 <= hour_of_day < 17:
            consumption = 1.5 + random.uniform(-0.2, 0.2)
        elif 17 <= hour_of_day < 22:
            consumption = 3.0 + random.uniform(-0.3, 0.3)
        else:
            consumption = 1.2 + random.uniform(-0.1, 0.1)
        
        # Inject some anomalies
        if hour == 10:  # Big spike
            consumption = 8.5
        elif hour == 25:  # Another spike
            consumption = 7.2
        elif hour == 35:  # Unusual drop
            consumption = 0.3
            
        sample_data.append({
            "timestamp": timestamp.isoformat(),
            "consumption_kwh": round(consumption, 2)
        })
    
    print("Testing Anomaly Detector Agent...")
    print(f"Analyzing {len(sample_data)} data points for anomalies...")
    
    result = detect_anomalies(sample_data)
    print("\nAnomaly Detection Result:")
    import json
    print(json.dumps(result, indent=2))
