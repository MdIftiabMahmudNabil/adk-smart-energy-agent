"""Streamlit Dashboard for Smart Energy Consumption Agent."""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json
import tempfile
import shutil

from orchestrator.adk_orchestrator import EnergyAgentOrchestrator
from utils.config import DATA_RAW_DIR
from agents.adk_bill_parser import parse_bill_from_text, parse_bill_from_image

# Page configuration
st.set_page_config(
    page_title="Smart Energy Consumption Agent",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'orchestrator' not in st.session_state:
    st.session_state.orchestrator = EnergyAgentOrchestrator()
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None


def main():
    """Main dashboard application."""
    
    # Header
    st.title("⚡ Smart Energy Consumption Agent")
    st.markdown("*AI-powered energy analysis and recommendations*")
    st.divider()
    
    # Sidebar
    with st.sidebar:
        st.header("🎛️ Control Panel")
        
        analysis_type = st.radio(
            "Analysis Type",
            ["Bill Analysis", "Meter Analysis", "Complete Analysis"],
            help="Choose the type of analysis to perform"
        )
        
        st.divider()
        
        # Session info
        session_info = st.session_state.orchestrator.get_session_summary()
        st.subheader("💾 Session Info")
        st.caption(f"ID: {session_info.get('session_id', 'N/A')[:20]}...")
        st.caption(f"Analyses: {session_info.get('analyses_performed', 0)}")
        
        st.divider()
        
        # Show extracted bills count and download options
        if 'extracted_bills' in st.session_state and st.session_state.extracted_bills:
            bill_count = len(st.session_state.extracted_bills)
            st.subheader(f"📊 Extracted Data ({bill_count})")
            
            # Ask user if they want to save
            save_data = st.checkbox("💾 Save extracted data", value=False)
            
            if save_data:
                st.caption("Choose download format:")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # CSV Download
                    df = pd.DataFrame(st.session_state.extracted_bills)
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv,
                        file_name=f"bills_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                
                with col2:
                    # Excel Download
                    from io import BytesIO
                    buffer = BytesIO()
                    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                        df.to_excel(writer, sheet_name='Bills', index=False)
                    excel_data = buffer.getvalue()
                    
                    st.download_button(
                        label="📥 Download Excel",
                        data=excel_data,
                        file_name=f"bills_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
            else:
                st.caption("⚠️ Data will be discarded after session ends")
        
        st.divider()
        
        if st.button("🔄 Reset Session"):
            st.session_state.orchestrator = EnergyAgentOrchestrator()
            st.session_state.analysis_results = None
            if 'extracted_bills' in st.session_state:
                st.session_state.extracted_bills = []
            st.rerun()
    
    # Main content area
    if analysis_type == "Bill Analysis":
        show_bill_analysis()
    elif analysis_type == "Meter Analysis":
        show_meter_analysis()
    else:
        show_complete_analysis()
    
    # Show results if available
    if st.session_state.analysis_results:
        st.divider()
        show_results(st.session_state.analysis_results)


def show_bill_analysis():
    """Bill analysis interface."""
    st.header("📄 Utility Bill Analysis")
    st.markdown("Upload or paste your utility bill for AI-powered analysis")
    
    # Input type selection
    input_type = st.radio(
        "Input Method",
        ["📷 Upload Image", "📝 Paste Text", "📁 Use Sample"],
        horizontal=True
    )
    
    bill_data = None
    
    if input_type == "📷 Upload Image":
        st.subheader("Upload Bill Image")
        uploaded_file = st.file_uploader(
            "Upload bill image",
            type=['jpg', 'jpeg', 'png', 'pdf'],
            help="Gemini vision will extract data from the image"
        )
        
        if uploaded_file:
            # Show image preview
            if uploaded_file.type.startswith('image'):
                st.image(uploaded_file, caption="Bill Image Preview", use_container_width=True)
            
            # Save temporarily for processing
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp:
                tmp.write(uploaded_file.getvalue())
                temp_path = tmp.name
            
            if st.button("🔍 Analyze Bill Image", key="analyze_image"):
                with st.spinner("🤖 Using Gemini Vision to read bill..."):
                    bill_data = parse_bill_from_image(temp_path)
                    
                    if bill_data and bill_data.get('status') != 'error':
                        st.success("✅ Bill parsed successfully!")
                        st.json(bill_data)
                        
                        # Store in session state for download option
                        if 'extracted_bills' not in st.session_state:
                            st.session_state.extracted_bills = []
                        
                        bill_data['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        bill_data['source'] = 'image'
                        st.session_state.extracted_bills.append(bill_data)
                        
                        # Use parsed data for full analysis
                        with st.spinner("Generating recommendations..."):
                            result = st.session_state.orchestrator.analyze_bill(bill_data=bill_data)
                            st.session_state.analysis_results = result
                            st.rerun()
                    else:
                        st.error(f"❌ Failed to parse bill: {bill_data.get('message', 'Unknown error')}")
    
    elif input_type == "📝 Paste Text":
        st.subheader("Paste Bill Text")
        bill_text = st.text_area(
            "Paste your bill text here",
            height=200,
            placeholder="ACME Utility Company\nBilling Period: 11/01/2024 - 11/30/2024\nTotal Usage: 850 kWh\nTotal Cost: $127.50"
        )
        
        if bill_text and st.button("🔍 Analyze Bill Text", key="analyze_text"):
            with st.spinner("🤖 Parsing bill text..."):
                bill_data = parse_bill_from_text(bill_text)
                
                if bill_data and bill_data.get('status') != 'error':
                    st.success("✅ Bill parsed successfully!")
                    st.json(bill_data)
                    
                    # Store in session state for download option
                    if 'extracted_bills' not in st.session_state:
                        st.session_state.extracted_bills = []
                    
                    bill_data['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    bill_data['source'] = 'text'
                    st.session_state.extracted_bills.append(bill_data)
                    
                    # Use parsed data for full analysis
                    with st.spinner("Generating recommendations..."):
                        result = st.session_state.orchestrator.analyze_bill(bill_data=bill_data)
                        st.session_state.analysis_results = result
                        st.rerun()
                else:
                    st.error(f"❌ Failed to parse bill: {bill_data.get('message', 'Unknown error')}")
    
    else:  # Use Sample
        st.subheader("Use Sample Bill")
        
        # List available sample bills
        sample_bills = list(DATA_RAW_DIR.glob("sample_bill_*.txt"))
        
        if sample_bills:
            selected_bill = st.selectbox(
                "Select sample bill",
                sample_bills,
                format_func=lambda x: x.name
            )
            
            if st.button("🔍 Analyze Sample", key="analyze_sample"):
                with st.spinner("Analyzing bill..."):
                    result = st.session_state.orchestrator.analyze_bill(bill_path=str(selected_bill))
                    st.session_state.analysis_results = result
                    st.rerun()
        else:
            st.warning("No sample bills found. Run data_generation/generate_meter_data.py first.")


def show_meter_analysis():
    """Meter data analysis interface."""
    st.header("📊 Smart Meter Analysis")
    st.markdown("Analyze your smart meter data for patterns and anomalies")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Option 1: Upload Meter Data")
        uploaded_csv = st.file_uploader(
            "Upload meter data CSV",
            type=['csv'],
            help="CSV with columns: timestamp, consumption_kwh"
        )
        
        if uploaded_csv:
            temp_csv_path = DATA_RAW_DIR / f"temp_{uploaded_csv.name}"
            with open(temp_csv_path, 'wb') as f:
                f.write(uploaded_csv.getvalue())
            
            if st.button("🔍 Analyze Meter Data", key="analyze_meter_upload"):
                with st.spinner("Analyzing meter data..."):
                    result = st.session_state.orchestrator.analyze_meter_data(str(temp_csv_path))
                    st.session_state.analysis_results = result
                    st.rerun()
    
    with col2:
        st.subheader("Option 2: Use Sample Data")
        
        sample_data = list(DATA_RAW_DIR.glob("sample_meter_data_*.csv"))
        
        if sample_data:
            selected_data = st.selectbox(
                "Select sample meter data",
                sample_data,
                format_func=lambda x: x.name
            )
            
            if st.button("🔍 Analyze Sample Data", key="analyze_meter_sample"):
                with st.spinner("Analyzing meter data..."):
                    result = st.session_state.orchestrator.analyze_meter_data(str(selected_data))
                    st.session_state.analysis_results = result
                    st.rerun()
        else:
            st.warning("No sample data found.")


def show_complete_analysis():
    """Complete analysis interface."""
    st.header("🔬 Complete Energy Analysis")
    st.markdown("Comprehensive analysis combining bill and meter data")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Select Bill")
        bill_files = list(DATA_RAW_DIR.glob("sample_bill_*.txt"))
        if bill_files:
            selected_bill = st.selectbox("Bill file", bill_files, format_func=lambda x: x.name)
        else:
            st.warning("No bills found")
            selected_bill = None
    
    with col2:
        st.subheader("Select Meter Data")
        meter_files = list(DATA_RAW_DIR.glob("sample_meter_data_*.csv"))
        if meter_files:
            selected_meter = st.selectbox("Meter data", meter_files, format_func=lambda x: x.name)
        else:
            st.warning("No meter data found")
            selected_meter = None
    
    if selected_bill and selected_meter:
        if st.button("🔍 Run Complete Analysis", type="primary"):
            with st.spinner("Running comprehensive analysis..."):
                result = st.session_state.orchestrator.analyze_complete(
                    str(selected_bill),
                    str(selected_meter)
                )
                st.session_state.analysis_results = result
                st.rerun()


def show_results(results: dict):
    """Display analysis results."""
    st.header("📊 Analysis Results")
    
    if not results or results.get('status') == 'error':
        st.error(f"Analysis failed: {results.get('message', 'Unknown error')}")
        return
    
    # Handle new response format (text-based results)
    if 'response' in results or 'full_text' in results:
        response_text = results.get('full_text') or results.get('response', '')
        st.markdown(response_text)
        return
    
    # Create tabs for different result sections
    tabs = st.tabs(["📄 Bill Data", "📈 Patterns & Trends", "🚨 Anomalies", "💡 Recommendations"])
    
    # Tab 1: Bill Data
    with tabs[0]:
        show_bill_data(results)
    
    # Tab 2: Patterns
    with tabs[1]:
        show_patterns(results)
    
    # Tab 3: Anomalies
    with tabs[2]:
        show_anomalies(results)
    
    # Tab 4: Recommendations
    with tabs[3]:
        show_recommendations(results)


def show_bill_data(results: dict):
    """Display bill data section."""
    bill_parsing = results.get("steps", {}).get("bill_parsing")
    
    if not bill_parsing or "error" in bill_parsing:
        st.info("No bill data available")
        return
    
    bill_data = bill_parsing.get("bill_data", {})
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        consumption = bill_data.get("consumption", {}).get("value", 0)
        st.metric("Consumption", f"{consumption} kWh")
    
    with col2:
        total = bill_data.get("charges", {}).get("total_amount", 0)
        st.metric("Total Cost", f"${total:.2f}")
    
    with col3:
        rate = bill_data.get("rate_info", {}).get("rate_per_kwh", 0)
        st.metric("Rate", f"${rate:.4f}/kWh")
    
    with col4:
        confidence = bill_parsing.get("validation", {}).get("confidence", 0)
        st.metric("Confidence", f"{confidence:.1%}")
    
    # Bill period
    st.subheader("Billing Period")
    period = bill_data.get("billing_period", {})
    st.write(f"**{period.get('start_date', 'N/A')}** to **{period.get('end_date', 'N/A')}**")


def show_patterns(results: dict):
    """Display consumption patterns section."""
    meter_analysis = results.get("steps", {}).get("meter_analysis", {}).get("steps", {}).get("meter_analysis")
    
    if not meter_analysis:
        st.info("No pattern data available")
        return
    
    patterns = meter_analysis.get("patterns", {})
    
    if patterns.get("insufficient_data"):
        st.warning("Insufficient data for pattern analysis")
        return
    
    # Statistics
    st.subheader("📊 Consumption Statistics")
    stats = patterns.get("statistics", {})
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Average", f"{stats.get('average', 0):.2f} kWh")
    col2.metric("Median", f"{stats.get('median', 0):.2f} kWh")
    col3.metric("Min", f"{stats.get('min', 0):.2f} kWh")
    col4.metric("Max", f"{stats.get('max', 0):.2f} kWh")
    
    # Peak hours
    st.subheader("⏰ Usage Patterns")
    col1, col2 = st.columns(2)
    
    with col1:
        peak_hours = patterns.get("peak_hours", [])
        st.write("**Peak Hours:**")
        if peak_hours:
            st.write(", ".join([f"{h}:00" for h in peak_hours]))
        else:
            st.write("No distinct peak hours detected")
    
    with col2:
        off_peak = patterns.get("off_peak_hours", [])
        st.write("**Off-Peak Hours:**")
        if off_peak:
            st.write(", ".join([f"{h}:00" for h in off_peak]))
        else:
            st.write("No distinct off-peak hours detected")


def show_anomalies(results: dict):
    """Display anomalies section."""
    anomaly_detection = results.get("steps", {}).get("anomaly_detection") or \
                       results.get("steps", {}).get("meter_analysis", {}).get("steps", {}).get("anomaly_detection")
    
    if not anomaly_detection:
        st.info("No anomaly data available")
        return
    
    anomalies_found = anomaly_detection.get("anomalies_found", 0)
    
    if anomalies_found == 0:
        st.success("✅ No significant anomalies detected!")
        return
    
    st.subheader(f"🚨 {anomalies_found} Anomalies Detected")
    
    anomalies = anomaly_detection.get("anomalies", {}).get("details", [])
    
    for i, anomaly in enumerate(anomalies[:5], 1):
        severity = anomaly.get("severity", "medium")
        color = "🔴" if severity == "high" else "🟡"
        
        with st.expander(f"{color} Anomaly {i}: {anomaly.get('timestamp', 'Unknown')}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Consumption:** {anomaly.get('consumption_kwh', 0)} kWh")
                st.write(f"**Expected Max:** {anomaly.get('expected_max', 0)} kWh")
            
            with col2:
                st.write(f"**Deviation:** +{anomaly.get('deviation_percent', 0):.1f}%")
                st.write(f"**Severity:** {severity.upper()}")
            
            if "ai_explanation" in anomaly:
                st.info(anomaly["ai_explanation"])


def show_recommendations(results: dict):
    """Display recommendations section."""
    recommendations = results.get("steps", {}).get("recommendations") or \
                     results.get("steps", {}).get("comprehensive_recommendations")
    
    if not recommendations or "error" in recommendations:
        st.info("No recommendations available")
        return
    
    recs = recommendations.get("recommendations", [])
    
    if not recs:
        st.warning("No recommendations generated")
        return
    
    st.subheader("💡 Personalized Recommendations")
    
    # Show savings potential
    savings = recommendations.get("savings_potential", {})
    if "10%_reduction" in savings:
        scenario = savings["10%_reduction"]
        st.success(f"💰 Potential Savings: ${scenario['monthly_savings']:.2f}/month "
                  f"(${scenario['annual_savings']:.2f}/year) with 10% reduction")
    
    st.divider()
    
    # Display recommendations
    for i, rec in enumerate(recs[:6], 1):
        priority = rec.get("priority", "medium")
        impact = rec.get("impact", "medium")
        effort = rec.get("effort", "medium")
        
        priority_colors = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        priority_icon = priority_colors.get(priority, "🔵")
        
        with st.expander(f"{priority_icon} {i}. {rec.get('title', 'Recommendation')} [{priority.upper()}]"):
            st.write(rec.get("description", "No description available"))
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Impact", impact.title())
            col2.metric("Effort", effort.title())
            col3.metric("Est. Savings", f"{rec.get('estimated_savings_percent', 0):.1f}%")


if __name__ == "__main__":
    main()
