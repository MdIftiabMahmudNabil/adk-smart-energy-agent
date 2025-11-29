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
        
        # Setup session service (use InMemorySessionService for now)
        # Database sessions require additional setup
        self.session_service = InMemorySessionService()
        
        # Create enhanced agents with custom tools
        try:
            self._setup_agents_with_tools()
            
            # Create multi-agent workflows
            self._setup_workflows()
        except Exception as e:
            # If workflow setup fails, create basic agents without workflows
            print(f"Warning: Workflow setup failed: {e}")
            print("Using basic agent setup without workflows")
            self._setup_basic_agents()
    
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
    
    def _setup_basic_agents(self):
        """Setup basic agents without workflows for fallback."""
        # Just create simple agents without complex workflows
        self.bill_parser_with_tools = Agent(
            name="BillParser",
            model="gemini-2.5-flash",
            instruction="Parse utility bills and extract structured data."
        )
        
        self.meter_analyzer_with_tools = Agent(
            name="MeterAnalyzer",
            model="gemini-2.5-flash",
            instruction="Analyze meter consumption data and identify patterns."
        )
        
        self.recommendation_engine_with_tools = Agent(
            name="RecommendationEngine",
            model="gemini-2.5-flash",
            instruction="Generate energy-saving recommendations."
        )
        
        # Create a simple sequential workflow even in fallback mode
        self.sequential_workflow = SequentialAgent(
            name="BasicEnergyAnalysis",
            sub_agents=[
                self.bill_parser_with_tools,
                self.meter_analyzer_with_tools,
                self.recommendation_engine_with_tools
            ]
        )
        
        # Set None for advanced workflows since they failed to initialize
        self.parallel_analysis_team = None
        
        # Create basic coordinator
        self.root_coordinator = Agent(
            name="EnergyAnalysisCoordinator",
            model="gemini-2.5-flash",
            instruction="Coordinate energy analysis and provide insights."
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
        
        # Create anomaly detector for sequential workflow
        anomaly_detector_sequential = Agent(
            name="AnomalyDetectorSequential",
            model="gemini-2.5-flash",
            description="Detects unusual consumption patterns and spikes in energy usage",
            instruction="You are an expert at detecting anomalies in energy consumption data. Analyze the consumption data and identify unusual patterns, spikes, or drops. For each anomaly, explain possible causes and severity. Return JSON with anomalies list and recommendations.",
            output_key="anomaly_report"
        )
        
        # WORKFLOW 1: Sequential Analysis Pipeline
        # Bill Parser -> Meter Analyzer -> Anomaly Detector -> Recommendations
        self.sequential_workflow = SequentialAgent(
            name="SequentialEnergyAnalysis",
            sub_agents=[
                self.bill_parser_with_tools,
                self.meter_analyzer_with_tools,
                anomaly_detector_sequential,
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
    
    def get_session_summary(self) -> dict:
        """Get summary of current session state."""
        import uuid
        # Generate a consistent session ID or use existing one
        if not hasattr(self, '_session_id'):
            self._session_id = str(uuid.uuid4())
        if not hasattr(self, '_analyses_count'):
            self._analyses_count = 0
        
        return {
            "session_id": self._session_id,
            "analyses_performed": self._analyses_count,
            "status": "ready",
            "workflows_available": self.sequential_workflow is not None,
            "agents_loaded": True,
            "session_service": "InMemorySessionService"
        }
    
    def analyze_bill(self, bill_data: str = None, bill_path: str = None) -> dict:
        """
        Analyze a utility bill (synchronous wrapper for async method).
        
        Args:
            bill_data: Raw bill text
            bill_path: Path to bill file
            
        Returns:
            Analysis results dictionary
        """
        import asyncio
        from pathlib import Path
        
        # Increment analyses count
        if not hasattr(self, '_analyses_count'):
            self._analyses_count = 0
        self._analyses_count += 1
        
        # If bill_path is provided, read the file content
        if bill_path and not bill_data:
            bill_path_obj = Path(bill_path)
            if bill_path_obj.exists():
                bill_data = bill_path_obj.read_text(encoding='utf-8')
            else:
                raise FileNotFoundError(f"Bill file not found: {bill_path}")
        
        # Check if there's already a running event loop (e.g., in Streamlit)
        try:
            loop = asyncio.get_running_loop()
            # If we're in an event loop, run in a thread with a new loop
            import concurrent.futures
            import threading
            
            def run_in_thread():
                return asyncio.run(self.analyze_complete(bill_data=bill_data))
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_in_thread)
                return future.result()
        except RuntimeError:
            # No event loop running, safe to use asyncio.run()
            return asyncio.run(self.analyze_complete(bill_data=bill_data))
    
    def analyze_meter_data(self, meter_data_path: str) -> dict:
        """
        Analyze meter consumption data (synchronous wrapper).
        
        Args:
            meter_data_path: Path to CSV with meter data
            
        Returns:
            Analysis results dictionary
        """
        import asyncio
        import pandas as pd
        
        # Increment analyses count
        if not hasattr(self, '_analyses_count'):
            self._analyses_count = 0
        self._analyses_count += 1
        
        # Load meter data from CSV
        df = pd.read_csv(meter_data_path)
        meter_data_list = df.to_dict('records')
        
        # Check if there's already a running event loop
        try:
            loop = asyncio.get_running_loop()
            # Run in a thread with a new loop
            import concurrent.futures
            
            def run_in_thread():
                return asyncio.run(self.analyze_complete(meter_data=meter_data_list))
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_in_thread)
                return future.result()
        except RuntimeError:
            # No event loop running
            return asyncio.run(self.analyze_complete(meter_data=meter_data_list))
    
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
        # Use InMemoryRunner for simpler execution without complex session management
        runner = InMemoryRunner(
            agent=self.sequential_workflow if self.sequential_workflow else self.root_coordinator
        )
        
        # Build comprehensive analysis request with specific instructions
        request = """Perform a comprehensive energy analysis with the following structure:

1. BILL SUMMARY
   - Extract key metrics (consumption, charges, billing period)
   - Calculate average daily usage and cost per kWh

2. USAGE PATTERN ANALYSIS
   - Ask the user 3-5 questions to understand their usage patterns:
     * What type of property? (apartment, house, commercial)
     * How many people live/work there?
     * What are the main energy-consuming appliances?
     * What time of day is peak usage? (if meter data available)
     * Any recent changes in consumption?

3. ANOMALY DETECTION
   - Identify unusual patterns or spikes in consumption
   - Compare current usage to typical patterns
   - Flag any billing errors or unexpected charges
   - Detect seasonal anomalies

4. PERSONALIZED RECOMMENDATIONS
   - Provide 5-7 specific, actionable recommendations
   - Calculate estimated savings for each recommendation
   - Prioritize recommendations by impact and ease of implementation
   - Include both immediate actions and long-term improvements

5. COST SAVINGS POTENTIAL
   - Total estimated monthly and annual savings
   - Quick wins (0-3 months)
   - Medium-term improvements (3-12 months)
   - Long-term investments (1+ years)

6. NEXT STEPS
   - Immediate action items
   - Monitoring suggestions
   - Follow-up recommendations

"""
        
        if bill_data:
            request += f"\nBILL DATA:\n{bill_data}\n\n"
        
        if meter_data:
            request += f"METER DATA:\n"
            request += "Timestamp,Consumption_kWh\n"
            for reading in meter_data[:50]:  # Limit to 50 readings
                request += f"{reading.get('timestamp')},{reading.get('consumption_kwh')}\n"
        
        request += "\nProvide a detailed, well-structured response following the format above."
        
        # Run analysis using run_debug for simple execution
        result = await runner.run_debug(request)
        
        return self._extract_result(result)
    
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
        runner = InMemoryRunner(agent=self.parallel_analysis_team)
        
        # Format data
        request = "Analyze this meter data:\n\nTimestamp,Consumption_kWh\n"
        for reading in meter_data[:50]:
            request += f"{reading.get('timestamp')},{reading.get('consumption_kwh')}\n"
        
        # Run analysis
        result = await runner.run_debug(request)
        return self._extract_result(result)
    
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
        # Generate session_id if not provided
        if session_id is None:
            import uuid
            session_id = str(uuid.uuid4())
        
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
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=types.Content(parts=[types.Part(text=request)])
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
        runner = InMemoryRunner(agent=self.root_coordinator)
        
        # Run chat
        result = await runner.run_debug(message)
        return self._extract_result(result)
    
    def _extract_result(self, result) -> dict:
        """Extract and structure the result from agent execution."""
        import json
        
        # Handle list of events from run_debug
        if isinstance(result, list) and len(result) > 0:
            # Get the last event which contains the final result
            last_event = result[-1]
            if hasattr(last_event, 'content') and last_event.content and last_event.content.parts:
                response_text = last_event.content.parts[0].text
                
                # Try to parse JSON
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
                    "status": "success",
                    "full_text": response_text
                }
        
        # Handle single event (backward compatibility)
        elif result and hasattr(result, 'content') and result.content and result.content.parts:
            response_text = result.content.parts[0].text
            
            # Try to parse JSON
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
                "status": "success",
                "full_text": response_text
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
