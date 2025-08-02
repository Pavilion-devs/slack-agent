#!/usr/bin/env python3
"""
Dashboard Runner for Delve Slack Support AI Agent

This script provides a web-based dashboard to test the improved RAG system.
Run this script to launch a Streamlit dashboard for interactive testing.

Usage:
    python run_dashboard.py

Requirements:
    - Ollama running with llama3.2:3b model
    - Virtual environment activated with dependencies installed
    - Streamlit installed (pip install streamlit)
"""

import streamlit as st
import asyncio
import sys
import os
from datetime import datetime

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__)))

from src.core.config import settings
from src.models.schemas import SupportMessage, MessageCategory, UrgencyLevel
from src.workflows.improved_workflow import ImprovedWorkflow
from src.core.rag_system import rag_system
from src.agents.rag_agent import RAGAgent


# Page configuration
st.set_page_config(
    page_title="Delve AI Support Agent - Testing Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main > div {
        padding-top: 2rem;
    }
    .stAlert {
        margin-top: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .success-metric {
        color: #0e7e3e;
        font-weight: bold;
    }
    .warning-metric {
        color: #f39c12;
        font-weight: bold;
    }
    .error-metric {
        color: #e74c3c;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


def main():
    """Main dashboard function."""
    st.title("🤖 Delve AI Support Agent - Testing Dashboard")
    st.markdown("**Test the improved LangChain-based RAG system with interactive questions**")
    
    # Sidebar for navigation and settings
    st.sidebar.title("🔧 Dashboard Controls")
    page = st.sidebar.selectbox(
        "Select Testing Mode",
        ["🧪 Interactive Testing", "📊 Batch Testing", "🏥 System Health", "⚙️ Configuration", "📖 Test Cases"]
    )
    
    # Initialize system check
    if 'system_initialized' not in st.session_state:
        st.session_state.system_initialized = False
    
    # Main content based on page selection
    if page == "🧪 Interactive Testing":
        show_interactive_testing()
    elif page == "📊 Batch Testing":
        show_batch_testing()
    elif page == "🏥 System Health":
        show_system_health()
    elif page == "⚙️ Configuration":
        show_configuration()
    elif page == "📖 Test Cases":
        show_test_cases()


def show_interactive_testing():
    """Interactive testing interface."""
    st.header("🧪 Interactive Testing")
    
    # System initialization check
    if not check_system_ready():
        return
    
    st.markdown("""
    Test the AI agent with your own questions. The system will:
    - Detect compliance frameworks (SOC2, HIPAA, GDPR, ISO27001)
    - Provide confidence scores and escalation recommendations
    - Show processing time and source citations
    """)
    
    # Input section
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Pre-populate with example if button was clicked
        default_message = st.session_state.get("test_message", "")
        test_message = st.text_area(
            "💬 Enter your question:",
            value=default_message,
            placeholder="How does SOC2 compliance work with Delve?",
            height=120,
            help="Ask about compliance frameworks, technical configuration, pricing, or any other topic"
        )
        
        # Clear the session state after using it
        if "test_message" in st.session_state:
            del st.session_state["test_message"]
    
    with col2:
        st.markdown("**Optional Settings:**")
        category = st.selectbox(
            "Category",
            ["Auto-detect"] + [cat.value for cat in MessageCategory],
            help="Manually set the message category"
        )
        
        urgency = st.selectbox(
            "Urgency",
            ["Auto-detect"] + [level.value for level in UrgencyLevel],
            help="Set urgency level (Critical messages always escalate)"
        )
        
        show_details = st.checkbox("Show detailed metadata", value=True)
    
    # Test button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Test Agent", type="primary", use_container_width=True):
            if test_message.strip():
                test_single_message(test_message, category, urgency, show_details)
            else:
                st.warning("⚠️ Please enter a test message.")
    
    # Example questions
    st.markdown("---")
    st.subheader("📝 Quick Test Examples")
    
    example_categories = {
        "🔒 Compliance": [
            "How does SOC2 compliance work with Delve?",
            "What are the HIPAA requirements for healthcare data?",
            "Can you help with GDPR data subject rights?",
            "How do I get ISO27001 certification?"
        ],
        "🛠️ Technical": [
            "How do I configure API authentication?",
            "How do I set up SAML SSO?",
            "What API endpoints are available?",
            "How do I export audit logs?"
        ],
        "📊 General": [
            "What is Delve?",
            "What services does Delve provide?",
            "How does compliance automation work?",
            "What industries do you serve?"
        ],
        "💼 Sales & Support": [
            "What are your pricing plans?",
            "Can we schedule a demo?",
            "I need to speak with sales",
            "Do you offer enterprise discounts?"
        ]
    }
    
    # Display examples in columns
    cols = st.columns(2)
    col_index = 0
    
    for category_name, examples in example_categories.items():
        with cols[col_index % 2]:
            st.markdown(f"**{category_name}**")
            for example in examples:
                if st.button(
                    f"📝 {example[:40]}{'...' if len(example) > 40 else ''}", 
                    key=f"example_{hash(example)}",
                    help=example
                ):
                    st.session_state["test_message"] = example
                    st.rerun()
        col_index += 1


def test_single_message(message: str, category: str, urgency: str, show_details: bool):
    """Test a single message and display results."""
    with st.spinner("🔄 Processing your question..."):
        try:
            result = asyncio.run(process_test_message(message, category, urgency))
            
            if result:
                display_test_results(result, show_details)
            else:
                st.error("❌ Failed to process the message. Please check the system health.")
                
        except Exception as e:
            st.error(f"❌ Error processing message: {str(e)}")
            with st.expander("🔍 Error Details"):
                st.code(str(e))


async def process_test_message(message: str, category: str, urgency: str):
    """Process a test message through the workflow."""
    try:
        # Initialize RAG system if needed
        if not rag_system.is_initialized:
            await rag_system.initialize()
        
        # Create support message
        test_message = SupportMessage(
            message_id=f"dashboard_test_{datetime.now().timestamp()}",
            channel_id="dashboard_test",
            user_id="dashboard_user",
            timestamp=datetime.now(),
            content=message,
            thread_ts=None
        )
        
        # Set category and urgency if specified
        if category != "Auto-detect":
            test_message.category = MessageCategory(category)
        if urgency != "Auto-detect":
            test_message.urgency_level = UrgencyLevel(urgency)
        
        # Process through workflow
        workflow = ImprovedWorkflow()
        start_time = datetime.now()
        response = await workflow.process_message(test_message)
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return {
            "response": response,
            "processing_time": processing_time,
            "message": test_message
        }
        
    except Exception as e:
        st.error(f"Error in test processing: {e}")
        return None


def display_test_results(result, show_details):
    """Display test results in a formatted way."""
    response = result["response"]
    processing_time = result["processing_time"]
    
    # Main results
    st.success("✅ Message processed successfully!")
    
    # Key metrics in columns
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        confidence_color = "success-metric" if response.confidence_score >= 0.8 else "warning-metric" if response.confidence_score >= 0.6 else "error-metric"
        st.markdown(f'<div class="metric-card"><span class="{confidence_color}">Confidence<br>{response.confidence_score:.2f}</span></div>', unsafe_allow_html=True)
    
    with col2:
        time_color = "success-metric" if processing_time < 15 else "warning-metric" if processing_time < 30 else "error-metric"
        st.markdown(f'<div class="metric-card"><span class="{time_color}">Time<br>{processing_time:.1f}s</span></div>', unsafe_allow_html=True)
    
    with col3:
        escalation_color = "error-metric" if response.should_escalate else "success-metric"
        escalation_text = "Yes" if response.should_escalate else "No"
        st.markdown(f'<div class="metric-card"><span class="{escalation_color}">Escalate<br>{escalation_text}</span></div>', unsafe_allow_html=True)
    
    with col4:
        source_count = len(response.sources) if response.sources else 0
        st.markdown(f'<div class="metric-card"><span class="success-metric">Sources<br>{source_count}</span></div>', unsafe_allow_html=True)
    
    # Response content
    st.markdown("---")
    st.subheader("💬 AI Response")
    st.markdown(response.response_text)
    
    # Additional details in expandable sections
    if response.should_escalate:
        with st.expander("⚠️ Escalation Details", expanded=True):
            st.warning(f"**Reason:** {response.escalation_reason}")
    
    if response.sources:
        with st.expander(f"📚 Sources ({len(response.sources)})", expanded=False):
            for i, source in enumerate(response.sources, 1):
                st.write(f"{i}. {source}")
    
    if show_details and hasattr(response, 'metadata') and response.metadata:
        with st.expander("🔍 Detailed Metadata", expanded=False):
            metadata = response.metadata
            
            if metadata.get('frameworks_detected'):
                st.write(f"**Frameworks Detected:** {', '.join(metadata['frameworks_detected'])}")
            if metadata.get('intent_classified'):
                st.write(f"**Intent Classification:** {metadata['intent_classified']}")
            if metadata.get('retrieved_docs_count'):
                st.write(f"**Documents Retrieved:** {metadata['retrieved_docs_count']}")
            
            # Show all metadata
            st.json(metadata)


def show_batch_testing():
    """Batch testing with predefined test cases."""
    st.header("📊 Batch Testing")
    
    if not check_system_ready():
        return
    
    st.markdown("""
    Run a comprehensive test suite with predefined questions to evaluate system performance.
    This helps validate the system's accuracy and consistency across different types of questions.
    """)
    
    # Test suite selection
    test_suites = {
        "🎯 Quick Validation": [
            ("What is Delve?", MessageCategory.GENERAL, 0.8),
            ("How does SOC2 compliance work?", MessageCategory.COMPLIANCE, 0.8),
            ("What are the HIPAA requirements?", MessageCategory.COMPLIANCE, 0.8),
            ("How do I configure SSO?", MessageCategory.TECHNICAL, 0.6),
            ("What is quantum computing?", MessageCategory.GENERAL, 0.3)  # Should escalate
        ],
        "🔒 Compliance Focus": [
            ("How does SOC2 Type II compliance work?", MessageCategory.COMPLIANCE, 0.8),
            ("What HIPAA controls does Delve implement?", MessageCategory.COMPLIANCE, 0.8),
            ("Can you help with GDPR data subject rights?", MessageCategory.COMPLIANCE, 0.8),
            ("What are ISO27001 security controls?", MessageCategory.COMPLIANCE, 0.8),
            ("How do I handle data classification for GDPR?", MessageCategory.COMPLIANCE, 0.7)
        ],
        "🛠️ Technical Deep Dive": [
            ("How do I configure API authentication?", MessageCategory.TECHNICAL, 0.6),
            ("What API endpoints are available?", MessageCategory.TECHNICAL, 0.7),
            ("How do I set up SAML SSO?", MessageCategory.TECHNICAL, 0.6),
            ("How do I export audit logs?", MessageCategory.TECHNICAL, 0.7),
            ("Can I integrate with Active Directory?", MessageCategory.TECHNICAL, 0.6)
        ],
        "🧪 Full Comprehensive": [
            ("What is Delve?", MessageCategory.GENERAL, 0.8),
            ("How does SOC2 compliance work?", MessageCategory.COMPLIANCE, 0.8),
            ("What are the HIPAA requirements?", MessageCategory.COMPLIANCE, 0.8),
            ("How do I configure API authentication?", MessageCategory.TECHNICAL, 0.6),
            ("What are your pricing plans?", MessageCategory.BILLING, 0.6),
            ("Can we schedule a demo?", MessageCategory.DEMO, 0.6),
            ("What is quantum computing?", MessageCategory.GENERAL, 0.3),
            ("The API is down!", MessageCategory.TECHNICAL, 0.5)
        ]
    }
    
    selected_suite = st.selectbox("Choose Test Suite:", list(test_suites.keys()))
    
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("🚀 Run Test Suite", type="primary"):
            run_batch_tests(test_suites[selected_suite])
    
    with col2:
        show_test_details = st.checkbox("Show individual test details", value=False)


def run_batch_tests(test_cases):
    """Run a batch of test cases."""
    progress_bar = st.progress(0)
    status_text = st.empty()
    results_container = st.container()
    
    results = []
    
    for i, (question, category, expected_confidence) in enumerate(test_cases):
        status_text.text(f"Testing {i+1}/{len(test_cases)}: {question[:50]}...")
        progress_bar.progress((i + 1) / len(test_cases))
        
        try:
            result = asyncio.run(process_test_message(question, category.value, "Auto-detect"))
            
            if result:
                response = result["response"]
                processing_time = result["processing_time"]
                
                # Evaluate result
                confidence_met = response.confidence_score >= expected_confidence
                time_acceptable = processing_time < 30
                
                results.append({
                    "question": question,
                    "expected_confidence": expected_confidence,
                    "actual_confidence": response.confidence_score,
                    "processing_time": processing_time,
                    "escalated": response.should_escalate,
                    "confidence_met": confidence_met,
                    "time_acceptable": time_acceptable,
                    "passed": confidence_met and time_acceptable,
                    "response": response.response_text[:100] + "..."
                })
            else:
                results.append({
                    "question": question,
                    "error": "Failed to process",
                    "passed": False
                })
                
        except Exception as e:
            results.append({
                "question": question,
                "error": str(e),
                "passed": False
            })
    
    # Display results summary
    status_text.text("✅ Testing completed!")
    display_batch_results(results)


def display_batch_results(results):
    """Display batch test results."""
    st.markdown("---")
    st.subheader("📊 Test Results Summary")
    
    # Calculate metrics
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r.get('passed', False))
    successful_results = [r for r in results if 'error' not in r]
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        pass_rate = (passed_tests / total_tests) * 100
        color = "🟢" if pass_rate >= 80 else "🟡" if pass_rate >= 60 else "🔴"
        st.metric("Pass Rate", f"{color} {pass_rate:.1f}%", f"{passed_tests}/{total_tests}")
    
    with col2:
        if successful_results:
            avg_confidence = sum(r['actual_confidence'] for r in successful_results) / len(successful_results)
            st.metric("Avg Confidence", f"{avg_confidence:.2f}")
        else:
            st.metric("Avg Confidence", "N/A")
    
    with col3:
        if successful_results:
            avg_time = sum(r['processing_time'] for r in successful_results) / len(successful_results)
            time_color = "🟢" if avg_time < 15 else "🟡" if avg_time < 30 else "🔴"
            st.metric("Avg Time", f"{time_color} {avg_time:.1f}s")
        else:
            st.metric("Avg Time", "N/A")
    
    with col4:
        escalated_count = sum(1 for r in successful_results if r.get('escalated', False))
        st.metric("Escalated", f"{escalated_count}/{len(successful_results)}")
    
    # Detailed results
    with st.expander("📋 Detailed Test Results", expanded=True):
        for i, result in enumerate(results, 1):
            if result.get('passed'):
                st.success(f"✅ Test {i}: {result['question'][:60]}...")
            elif 'error' in result:
                st.error(f"❌ Test {i}: {result['question'][:60]}... - Error: {result['error']}")
            else:
                st.warning(f"⚠️ Test {i}: {result['question'][:60]}... - Review needed")
            
            if 'actual_confidence' in result:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"Confidence: {result['actual_confidence']:.2f} (expected ≥{result['expected_confidence']})")
                with col2:
                    st.write(f"Time: {result['processing_time']:.1f}s")
                with col3:
                    st.write(f"Escalated: {'Yes' if result['escalated'] else 'No'}")


def show_system_health():
    """Show system health and diagnostics."""
    st.header("🏥 System Health")
    
    st.markdown("Check the health and status of all system components.")
    
    if st.button("🔄 Run Health Check", type="primary"):
        run_health_check()
    
    # Display cached health status if available
    if 'health_status' in st.session_state:
        display_health_status(st.session_state.health_status)


def run_health_check():
    """Run comprehensive health check."""
    with st.spinner("🔍 Checking system health..."):
        health_status = asyncio.run(check_system_health())
        st.session_state.health_status = health_status
        display_health_status(health_status)


async def check_system_health():
    """Check system health asynchronously."""
    try:
        # Initialize and check RAG system
        if not rag_system.is_initialized:
            await rag_system.initialize()
        
        rag_healthy = await rag_system.health_check()
        rag_initialized = rag_system.is_initialized
        
        # Test agent functionality
        agent = RAGAgent()
        test_message = SupportMessage(
            message_id="health_check",
            channel_id="test",
            user_id="test",
            timestamp=datetime.now(),
            content="What is Delve?"
        )
        
        try:
            start_time = datetime.now()
            response = await agent.process_message(test_message)
            processing_time = (datetime.now() - start_time).total_seconds()
            agent_healthy = response is not None and processing_time < 60
        except Exception as e:
            agent_healthy = False
            processing_time = None
        
        # Test workflow
        try:
            workflow = ImprovedWorkflow()
            workflow_response = await workflow.process_message(test_message)
            workflow_healthy = workflow_response is not None
        except:
            workflow_healthy = False
        
        overall_healthy = all([rag_healthy, rag_initialized, agent_healthy, workflow_healthy])
        
        return {
            "rag_system": rag_healthy,
            "rag_initialized": rag_initialized,
            "agent": agent_healthy,
            "workflow": workflow_healthy,
            "overall": overall_healthy,
            "processing_time": processing_time,
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        return {
            "rag_system": False,
            "rag_initialized": False,
            "agent": False,
            "workflow": False,
            "overall": False,
            "error": str(e),
            "timestamp": datetime.now()
        }


def display_health_status(health_status):
    """Display health status results."""
    timestamp = health_status.get('timestamp', 'Unknown')
    st.write(f"*Last checked: {timestamp}*")
    
    # Overall status
    if health_status.get('overall'):
        st.success("🟢 System is healthy and ready!")
    else:
        st.error("🔴 System has health issues!")
    
    # Component status
    col1, col2, col3, col4 = st.columns(4)
    
    components = [
        ("RAG System", health_status.get('rag_system', False)),
        ("Vector DB", health_status.get('rag_initialized', False)),
        ("RAG Agent", health_status.get('agent', False)),
        ("Workflow", health_status.get('workflow', False))
    ]
    
    for i, (name, status) in enumerate(components):
        with [col1, col2, col3, col4][i]:
            status_icon = "🟢" if status else "🔴"
            status_text = "Healthy" if status else "Error"
            st.metric(name, f"{status_icon} {status_text}")
    
    # Performance metrics
    if health_status.get('processing_time'):
        st.info(f"⚡ Test query processing time: {health_status['processing_time']:.2f}s")
    
    # Error details
    if health_status.get('error'):
        with st.expander("🔍 Error Details"):
            st.code(health_status['error'])
            
            st.markdown("**Troubleshooting Steps:**")
            st.markdown("""
            1. Ensure Ollama is running: `ollama serve`
            2. Check if llama3.2:3b model is available: `ollama pull llama3.2:3b`
            3. Verify virtual environment is activated
            4. Check if all dependencies are installed: `pip install -r requirements.txt`
            """)


def show_configuration():
    """Show system configuration."""
    st.header("⚙️ System Configuration")
    
    st.markdown("Current system settings and environment configuration.")
    
    try:
        # Display key settings
        config_data = {
            "Ollama Base URL": getattr(settings, 'ollama_base_url', 'Not set'),
            "Environment": getattr(settings, 'environment', 'Not set'),
            "Log Level": getattr(settings, 'log_level', 'Not set'),
            "Confidence Threshold": getattr(settings, 'confidence_threshold', 'Not set'),
            "Chunk Size": getattr(settings, 'chunk_size', 'Not set'),
            "Retrieval K": getattr(settings, 'retrieval_k', 'Not set'),
        }
        
        st.subheader("📋 Current Settings")
        for key, value in config_data.items():
            st.write(f"**{key}:** `{value}`")
            
    except Exception as e:
        st.error(f"Error loading configuration: {e}")
    
    st.markdown("---")
    st.subheader("🔧 Quick Setup Guide")
    
    st.markdown("**Prerequisites:**")
    st.code("""
# 1. Start Ollama
ollama serve

# 2. Pull the model
ollama pull llama3.2:3b

# 3. Activate virtual environment
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt
    """)
    
    st.markdown("**Testing Commands:**")
    st.code("""
# Manual testing
python run_manual_test.py

# Dashboard
python run_dashboard.py
# or: streamlit run src/simple_dashboard.py

# Main application
python -m src.main
    """)


def show_test_cases():
    """Show test cases documentation."""
    st.header("📖 Test Cases Reference")
    
    st.markdown("""
    This section provides comprehensive test cases for validating the AI support agent.
    Use these questions to test different aspects of the system.
    """)
    
    # Load and display test cases from markdown file
    try:
        with open("test_cases.md", "r") as f:
            test_cases_content = f.read()
        
        st.markdown(test_cases_content)
        
    except FileNotFoundError:
        st.warning("Test cases file not found. Here are some quick examples:")
        
        st.markdown("""
        ### Quick Test Examples
        
        **Compliance Questions:**
        - How does SOC2 compliance work with Delve?
        - What are the HIPAA requirements for healthcare data?
        - Can you help with GDPR data subject rights?
        - What are ISO27001 security controls?
        
        **Technical Questions:**
        - How do I configure API authentication?
        - How do I set up SAML SSO?
        - What API endpoints are available?
        - How do I export audit logs?
        
        **General Questions:**
        - What is Delve?
        - What services does Delve provide?
        - How does compliance automation work?
        
        **Edge Cases:**
        - What is quantum computing? (should escalate)
        - The API is down! (should escalate)
        - Can we schedule a demo? (should escalate)
        """)


def check_system_ready():
    """Check if the system is ready for testing."""
    if not st.session_state.system_initialized:
        with st.spinner("🔄 Initializing system..."):
            try:
                # Test system initialization
                result = asyncio.run(initialize_system())
                st.session_state.system_initialized = result
                
                if result:
                    st.success("✅ System initialized and ready for testing!")
                else:
                    st.error("❌ System initialization failed!")
                    show_initialization_help()
                    return False
                    
            except Exception as e:
                st.error(f"❌ System initialization error: {e}")
                show_initialization_help()
                return False
    
    return True


async def initialize_system():
    """Initialize the system for testing."""
    try:
        await rag_system.initialize()
        return rag_system.is_initialized
    except Exception:
        return False


def show_initialization_help():
    """Show help for system initialization issues."""
    with st.expander("🔧 Troubleshooting System Initialization"):
        st.markdown("""
        **Common Issues:**
        
        1. **Ollama not running:**
           ```bash
           ollama serve
           ```
        
        2. **Model not available:**
           ```bash
           ollama pull llama3.2:3b
           ```
        
        3. **Virtual environment not activated:**
           ```bash
           source venv/bin/activate
           ```
        
        4. **Dependencies missing:**
           ```bash
           pip install -r requirements.txt
           ```
        
        5. **Check Ollama status:**
           ```bash
           curl http://localhost:11434/api/tags
           ```
        """)


if __name__ == "__main__":
    main()