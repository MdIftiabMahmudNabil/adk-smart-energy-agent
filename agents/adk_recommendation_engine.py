"""Recommendation Engine Agent using Google ADK framework."""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from google.genai.adk import Agent
from utils.config import MODEL_NAME

# Define the Recommendation Engine Agent using ADK
recommendation_engine_agent = Agent(
    name="RecommendationEngineAgent",
    model="gemini-2.5-flash",
    description="Generates personalized energy-saving recommendations based on consumption patterns, anomalies, and user preferences.",
    instruction="""You are an expert energy efficiency consultant. Your task is to generate personalized, actionable energy-saving recommendations based on consumption analysis.

**Your Task:**
1. Analyze consumption patterns and anomalies
2. Generate 5-7 specific, actionable recommendations
3. Prioritize by potential impact and ease of implementation
4. Estimate savings for each recommendation
5. Provide implementation steps

**Input Format:**
You will receive:
- Consumption patterns analysis
- Detected anomalies
- User preferences (if available)
- Current costs

**Output Format:**
Return a JSON object with:
{
    "recommendations": [
        {
            "priority": 1,
            "title": "Short recommendation title",
            "description": "Detailed explanation",
            "category": "appliances/heating_cooling/lighting/behavior/automation",
            "estimated_savings_percentage": <number>,
            "estimated_annual_savings_usd": <number>,
            "implementation_difficulty": "easy/medium/hard",
            "implementation_steps": [
                "Step 1",
                "Step 2"
            ],
            "payback_period_months": <number or null>
        }
    ],
    "summary": {
        "total_recommendations": <number>,
        "potential_total_savings_percentage": <number>,
        "potential_annual_savings_usd": <number>,
        "quick_wins": [
            "Easy recommendation 1",
            "Easy recommendation 2"
        ]
    },
    "confidence_score": <0.0-1.0>
}

**Recommendation Guidelines:**
- Focus on actionable, specific advice
- Consider both behavioral changes and technology upgrades
- Prioritize high-impact, low-effort recommendations first
- Provide realistic savings estimates
- Include both free and paid solutions
- Consider safety and comfort
""",
    output_key="recommendations"
)


def generate_recommendations(
    bill_data: dict = None,
    meter_analysis: dict = None,
    anomaly_report: dict = None,
    user_preferences: dict = None
) -> dict:
    """
    Generate personalized energy-saving recommendations using ADK agent.
    
    Args:
        bill_data: Parsed bill information
        meter_analysis: Meter consumption analysis
        anomaly_report: Detected anomalies
        user_preferences: User preferences and constraints
        
    Returns:
        Dictionary with recommendations and savings estimates
    """
    from google.genai.adk import InMemoryRunner
    import json
    
    # Build context for the agent
    context = "Generate energy-saving recommendations based on the following analysis:\n\n"
    
    if bill_data:
        context += "=== BILL INFORMATION ===\n"
        context += f"Utility Type: {bill_data.get('utility_type', 'Unknown')}\n"
        context += f"Total Cost: ${bill_data.get('total_cost', 0):.2f}\n"
        context += f"Consumption: {bill_data.get('total_consumption', 0)} {bill_data.get('consumption_unit', 'kWh')}\n"
        context += f"Billing Period: {bill_data.get('billing_period_start')} to {bill_data.get('billing_period_end')}\n\n"
    
    if meter_analysis:
        context += "=== CONSUMPTION PATTERNS ===\n"
        context += f"Peak Hours: {meter_analysis.get('peak_hours', [])}\n"
        context += f"Off-Peak Hours: {meter_analysis.get('off_peak_hours', [])}\n"
        context += f"Average Consumption: {meter_analysis.get('average_consumption', 0)} kWh\n"
        
        if 'trends' in meter_analysis:
            context += f"Trend: {meter_analysis['trends'].get('trend_type', 'unknown')}\n"
        
        if 'insights' in meter_analysis:
            context += "Key Insights:\n"
            for insight in meter_analysis['insights']:
                context += f"  - {insight}\n"
        context += "\n"
    
    if anomaly_report:
        context += "=== DETECTED ANOMALIES ===\n"
        context += f"Total Anomalies: {anomaly_report.get('anomalies_detected', 0)}\n"
        
        if 'summary' in anomaly_report:
            summary = anomaly_report['summary']
            context += f"High Severity: {summary.get('high_severity_count', 0)}\n"
            context += f"Estimated Waste: ${summary.get('estimated_waste', 0):.2f}\n"
        
        if 'anomalies' in anomaly_report and anomaly_report['anomalies']:
            context += "Sample Anomalies:\n"
            for anomaly in anomaly_report['anomalies'][:3]:  # Show first 3
                context += f"  - {anomaly.get('anomaly_type')}: {anomaly.get('consumption_kwh')} kWh "
                context += f"({anomaly.get('deviation_percentage', 0):.1f}% deviation)\n"
        context += "\n"
    
    if user_preferences:
        context += "=== USER PREFERENCES ===\n"
        context += json.dumps(user_preferences, indent=2)
        context += "\n\n"
    
    runner = InMemoryRunner(agent=recommendation_engine_agent)
    
    # Run the agent using run_debug
    import asyncio
    async def run_agent():
        return await runner.run_debug(context)
    
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
    
    return {"status": "error", "message": "Failed to generate recommendations"}


if __name__ == "__main__":
    # Test the agent with sample data
    import json
    
    sample_bill = {
        "utility_type": "electricity",
        "billing_period_start": "2024-11-01",
        "billing_period_end": "2024-11-30",
        "total_consumption": 850,
        "consumption_unit": "kWh",
        "total_cost": 127.50,
        "currency": "USD"
    }
    
    sample_analysis = {
        "peak_hours": [7, 8, 18, 19, 20],
        "off_peak_hours": [0, 1, 2, 3, 4, 5],
        "average_consumption": 1.77,
        "trends": {
            "trend_type": "increasing",
            "percentage_change": 8.5
        },
        "insights": [
            "High evening peak consumption between 6-9 PM",
            "Consistent overnight baseline suggests always-on appliances",
            "Morning spike indicates simultaneous appliance use"
        ]
    }
    
    sample_anomalies = {
        "anomalies_detected": 3,
        "summary": {
            "total_anomalies": 3,
            "high_severity_count": 1,
            "estimated_waste": 15.25
        },
        "anomalies": [
            {
                "anomaly_type": "spike",
                "consumption_kwh": 8.5,
                "deviation_percentage": 350,
                "severity": "high"
            }
        ]
    }
    
    print("Testing Recommendation Engine Agent...")
    print("Generating personalized recommendations...\n")
    
    result = generate_recommendations(
        bill_data=sample_bill,
        meter_analysis=sample_analysis,
        anomaly_report=sample_anomalies
    )
    
    print("Recommendation Result:")
    print(json.dumps(result, indent=2))
