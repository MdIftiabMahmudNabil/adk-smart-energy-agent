"""
ADK-based Multi-Agent Energy Analysis Orchestrator

This module implements the Smart Energy Consumption Agent system using
Google ADK's Sequential and Parallel agent patterns.

Key Features:
- Sequential workflow for step-by-step analysis
- Parallel agents for concurrent processing
- Custom function tools integration
- Session management for stateful conversations
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from google.adk.agents import Agent, SequentialAgent, ParallelAgent
from google.adk.runners import InMemoryRunner, Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Import custom tools
from tools.adk_custom_tools import (
    calculate_consumption_statistics,
    detect_peak_hours,
    calculate_cost_by_rate_tier,
    estimate_savings_potential
)

# Import individual agents
from agents.adk_bill_parser import bill_parser_agent
from agents.adk_meter_analyzer import meter_analyzer_agent
from agents.adk_anomaly_detector import anomaly_detector_agent
from agents.adk_recommendation_engine import recommendation_engine_agent


class EnergyAgentOrchestrator:
    """
    Orchestrates multiple AI agents for comprehensive energy analysis.
    
    This class implements ADK's multi-agent patterns:
    - Sequential execution for ordered workflows
    - Parallel execution for independent analyses
    - Session management for conversation state
    - Custom tool integration
    """
    
    def __init__(self, use_database_sessions: bool = False):
        """
        Initialize the orchestrator with ADK agents.
        
        Args:
            use_database_sessions: If True, persist sessions to SQLite database
        """
        self.use_database_sessions = use_database_sessions
        
        # Setup session service
        if use_database_sessions:
            db_url = "sqlite:///data/processed/energy_agent_sessions.db"
            self.session_service = DatabaseSessionService(db_url=db_url)
        else:
            self.session_service = InMemorySessionService()
        
        # Create enhanced agents with custom tools
        self._setup_agents_with_tools()
        
        # Create multi-agent workflows
        self._setup_workflows()
    
    def _setup_agents_with_tools(self):
        """Setup agents with custom function tools."""
        
        # Enhanced Bill Parser with cost calculation tool
        self.bill_parser_with_tools = Agent(
            name="BillParserWithTools",
            model="gemini-2.5-flash",
            description="Parses bills and calculates costs using custom tools",
            instruction="""You are a bill parsing expert with calculation capabilities.
            
            Parse the bill data and use the calculate_cost_by_rate_tier tool to
            calculate accurate costs based on rate tiers.
            
            Return structured JSON with all extracted data.
            """,
            tools=[calculate_cost_by_rate_tier],
            output_key="parsed_bill"
        )
        
        # Enhanced Meter Analyzer with pattern detection tools
        self.meter_analyzer_with_tools = Agent(
            name="MeterAnalyzerWithTools",
            model="gemini-2.5-flash",
            description="Analyzes meter data with statistical and pattern detection tools",
            instruction="""You are a meter data analyst with powerful analysis tools.
            
            Use these tools to analyze consumption data:
            1. calculate_consumption_statistics - Get statistical metrics
            2. detect_peak_hours - Find high consumption periods
            
            Provide comprehensive analysis with insights.
            """,
            tools=[calculate_consumption_statistics, detect_peak_hours],
            output_key="meter_analysis"
        )
        
        # Enhanced Recommendation Engine with savings calculator
        self.recommendation_engine_with_tools = Agent(
            name="RecommendationEngineWithTools",
            model="gemini-2.5-flash",
            description="Generates recommendations with savings calculations",
            instruction="""You are an energy efficiency consultant with savings estimation tools.
            
            Based on the analysis from previous agents (available in session state):
            - {parsed_bill}
            - {meter_analysis}
            - {anomaly_report}
            
            Generate 5-7 personalized recommendations and use the 
            estimate_savings_potential tool to calculate precise savings for each.
            
            Prioritize recommendations by impact and ease of implementation.
            """,
            tools=[estimate_savings_potential],
            output_key="recommendations"
        )
    
    def _setup_workflows(self):
        """Setup Sequential and Parallel agent workflows."""
        
        # Create separate instances for parallel workflow to avoid parent conflicts
        meter_analyzer_parallel = Agent(
            name="MeterAnalyzerParallel",
            model="gemini-2.5-flash",
            description="Analyzes meter data with statistical and pattern detection tools",
            instruction="""You are a meter data analyst with powerful analysis tools.
            
            Use these tools to analyze consumption data:
            1. calculate_consumption_statistics - Get statistical metrics
            2. detect_peak_hours - Find high consumption periods
            
            Provide comprehensive analysis with insights.
            """,
            tools=[calculate_consumption_statistics, detect_peak_hours],
            output_key="meter_analysis"
        )
        
        anomaly_detector_parallel = Agent(
            name="AnomalyDetectorParallel",
            model="gemini-2.5-flash",
            description="Detects unusual consumption patterns and spikes in energy usage.",
            instruction="""You are an expert at detecting anomalies in energy consumption data.
            
            Analyze the consumption data and identify unusual patterns, spikes, or drops.
            For each anomaly, explain possible causes and severity.
            
            Return JSON with anomalies list and recommendations.
            """,
            output_key="anomaly_report"
        )
        
        # WORKFLOW 1: Sequential Analysis Pipeline
        # Bill Parser -> Meter Analyzer -> Anomaly Detector -> Recommendations
        self.sequential_workflow = SequentialAgent(
            name="SequentialEnergyAnalysis",
            sub_agents=[
                self.bill_parser_with_tools,
                self.meter_analyzer_with_tools,
                anomaly_detector_agent,
                self.recommendation_engine_with_tools
            ]
        )
        
        # WORKFLOW 2: Parallel Analysis for Speed
        # Meter Analyzer and Anomaly Detector run concurrently
        self.parallel_analysis_team = ParallelAgent(
            name="ParallelAnalysisTeam",
            sub_agents=[
                meter_analyzer_parallel,
                anomaly_detector_parallel
            ]
        )
        
        # WORKFLOW 3: Hybrid - Parallel analysis then Sequential recommendations
        # Note: Hybrid workflow requires separate agent instances to avoid parent conflicts
        # For production use, create dedicated agent instances for each workflow
        # self.hybrid_workflow = SequentialAgent(
        #     name="HybridEnergyAnalysis",
        #     sub_agents=[
        #         bill_parser_hybrid,
        #         self.parallel_analysis_team,
        #         recommendation_hybrid
        #     ]
        # )
        
        # Create a coordinator agent that decides which workflow to use
        self.root_coordinator = Agent(
            name="EnergyAnalysisCoordinator",
            model="gemini-2.0-flash-exp",
            description="Coordinates energy analysis by selecting appropriate workflow",
            instruction="""You are the coordinator for an energy analysis system.
            
            Based on the user's request, determine what analysis is needed:
            
            1. If user provides both bill AND meter data: Use hybrid workflow for comprehensive analysis
            2. If user provides only bill data: Use bill parser -> recommendations
            3. If user provides only meter data: Use meter analyzer -> anomaly detector -> recommendations
            4. For general questions: Provide guidance on what data is needed
            
            Always explain what analysis will be performed and what insights they can expect.
            """,
            output_key="coordination_plan"
        )
    
    async def analyze_complete(
        self,
        bill_data: str = None,
        meter_data: list = None,
        user_id: str = "default",
        session_id: str = None
    ) -> dict:
        """
        Perform complete energy analysis using hybrid workflow.
        
        Args:
            bill_data: Raw bill text or image data
            meter_data: List of meter readings
            user_id: User identifier for session management
            session_id: Session ID (creates new if None)
        
        Returns:
            Dictionary with complete analysis results
        """
        # Create runner with session management
        runner = Runner(
            agent=self.hybrid_workflow,
            app_name="SmartEnergyAgent",
            session_service=self.session_service
        )
        
        # Build analysis request
        request = "Perform complete energy analysis:\n\n"
        
        if bill_data:
            request += f"BILL DATA:\n{bill_data}\n\n"
        
        if meter_data:
            request += f"METER DATA:\n"
            request += "Timestamp,Consumption_kWh\n"
            for reading in meter_data[:50]:  # Limit to 50 readings
                request += f"{reading.get('timestamp')},{reading.get('consumption_kwh')}\n"
        
        # Run analysis - iterate through async generator
        last_event = None
        async for event in runner.run(
            user_id=user_id,
            session_id=session_id,
            new_message=request
        ):
            last_event = event
        
        return self._extract_result(last_event)
    
    async def analyze_with_parallel(
        self,
        meter_data: list,
        user_id: str = "default",
        session_id: str = None
    ) -> dict:
        """
        Analyze meter data using parallel agents for faster processing.
        
        Args:
            meter_data: List of meter readings
            user_id: User identifier
            session_id: Session ID
        
        Returns:
            Dictionary with parallel analysis results
        """
        runner = Runner(
            agent=self.parallel_analysis_team,
            app_name="SmartEnergyAgent",
            session_service=self.session_service
        )
        
        # Format data
        request = "Analyze this meter data:\n\nTimestamp,Consumption_kWh\n"
        for reading in meter_data[:50]:
            request += f"{reading.get('timestamp')},{reading.get('consumption_kwh')}\n"
        
        # Iterate through async generator
        last_event = None
        async for event in runner.run(
            user_id=user_id,
            session_id=session_id,
            new_message=request
        ):
            last_event = event
        
        return self._extract_result(last_event)
    
    async def analyze_sequential(
        self,
        bill_data: str,
        meter_data: list,
        user_id: str = "default",
        session_id: str = None
    ) -> dict:
        """
        Perform step-by-step sequential analysis.
        
        Args:
            bill_data: Raw bill data
            meter_data: List of meter readings
            user_id: User identifier
            session_id: Session ID
        
        Returns:
            Dictionary with sequential analysis results
        """
        runner = Runner(
            agent=self.sequential_workflow,
            app_name="SmartEnergyAgent",
            session_service=self.session_service
        )
        
        request = f"Analyze energy data:\n\nBILL:\n{bill_data}\n\n"
        request += "METER DATA:\nTimestamp,Consumption_kWh\n"
        for reading in meter_data[:50]:
            request += f"{reading.get('timestamp')},{reading.get('consumption_kwh')}\n"
        
        # Iterate through async generator
        last_event = None
        async for event in runner.run(
            user_id=user_id,
            session_id=session_id,
            new_message=request
        ):
            last_event = event
        
        return self._extract_result(last_event)
    
    async def chat(
        self,
        message: str,
        user_id: str = "default",
        session_id: str = None
    ) -> dict:
        """
        Interactive chat interface with session memory.
        
        Args:
            message: User message
            user_id: User identifier
            session_id: Session ID for conversation continuity
        
        Returns:
            Dictionary with response
        """
        runner = Runner(
            agent=self.root_coordinator,
            app_name="SmartEnergyAgent",
            session_service=self.session_service
        )
        
        # Iterate through async generator
        last_event = None
        async for event in runner.run(
            user_id=user_id,
            session_id=session_id,
            new_message=message
        ):
            last_event = event
        
        return self._extract_result(last_event)
    
    def _extract_result(self, result) -> dict:
        """Extract and structure the result from agent execution."""
        if result and hasattr(result, 'content') and result.content.parts:
            response_text = result.content.parts[0].text
            
            # Try to parse JSON
            import json
            try:
                if '{' in response_text and '}' in response_text:
                    json_start = response_text.index('{')
                    json_end = response_text.rindex('}') + 1
                    json_str = response_text[json_start:json_end]
                    return json.loads(json_str)
            except:
                pass
            
            # Return as text if not JSON
            return {
                "response": response_text,
                "status": "success"
            }
        
        return {
            "status": "error",
            "message": "No response from agent"
        }


if __name__ == "__main__":
    import asyncio
    import json
    from datetime import datetime, timedelta
    
    print("=== Testing ADK Multi-Agent Orchestrator ===\n")
    
    # Initialize orchestrator (use in-memory sessions for simple testing)
    orchestrator = EnergyAgentOrchestrator(use_database_sessions=False)
    
    # Generate sample data
    base_time = datetime(2024, 11, 1, 0, 0)
    sample_meter_data = []
    
    for hour in range(48):
        timestamp = base_time + timedelta(hours=hour)
        hour_of_day = timestamp.hour
        
        if 0 <= hour_of_day < 6:
            consumption = 0.8 + (hour % 3) * 0.1
        elif 6 <= hour_of_day < 9:
            consumption = 2.5 + (hour % 3) * 0.3
        elif 9 <= hour_of_day < 17:
            consumption = 1.5 + (hour % 4) * 0.2
        elif 17 <= hour_of_day < 22:
            consumption = 3.0 + (hour % 3) * 0.5
        else:
            consumption = 1.2 + (hour % 2) * 0.2
        
        # Add anomaly
        if hour == 10:
            consumption = 8.5
        
        sample_meter_data.append({
            "timestamp": timestamp.isoformat(),
            "consumption_kwh": round(consumption, 2)
        })
    
    sample_bill = """
    ACME Utility Company - Electric Bill
    Account: 123-456-789
    Billing Period: 11/01/2024 - 11/30/2024
    Total Usage: 850 kWh
    Total Amount Due: $127.50
    Due Date: 12/15/2024
    """
    
    async def test_workflows():
        print("1. Testing Parallel Analysis (faster)...")
        result = await orchestrator.analyze_with_parallel(
            meter_data=sample_meter_data,
            session_id="test-session-1"
        )
        print(json.dumps(result, indent=2))
        
        print("\n2. Testing Complete Hybrid Analysis...")
        result = await orchestrator.analyze_complete(
            bill_data=sample_bill,
            meter_data=sample_meter_data,
            session_id="test-session-2"
        )
        print(json.dumps(result, indent=2))
        
        print("\n3. Testing Interactive Chat with Session Memory...")
        result = await orchestrator.chat(
            "What were my peak usage hours?",
            session_id="test-session-2"  # Same session as analysis
        )
        print(json.dumps(result, indent=2))
    
    # Run tests
    asyncio.run(test_workflows())
    
    print("\n✅ Orchestrator testing complete!")
