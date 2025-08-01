"""Streamlit dashboard for testing and monitoring the Slack Support AI Agent."""

import streamlit as st
import asyncio
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
import sys
import os

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.core.config import settings
from src.models.schemas import SupportMessage, MessageCategory, UrgencyLevel
from src.workflows.support_workflow import support_workflow
from src.integrations.ollama_client import ollama_client
from src.integrations.vector_store import vector_store


st.set_page_config(
    page_title="Delve AI Support Agent Dashboard",
    page_icon="🤖",
    layout="wide"
)


def main():
    """Main dashboard function."""
    st.title("🤖 Delve Slack Support AI Agent Dashboard")
    
    # Sidebar for navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox(
        "Select Page",
        ["Overview", "Test Agent", "System Health", "Analytics", "Knowledge Base"]
    )
    
    if page == "Overview":
        show_overview()
    elif page == "Test Agent":
        show_test_agent()
    elif page == "System Health":
        show_system_health()
    elif page == "Analytics":
        show_analytics()
    elif page == "Knowledge Base":
        show_knowledge_base()


def show_overview():
    """Show system overview."""
    st.header("System Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Status", "🟢 Active")
    
    with col2:
        st.metric("Uptime", "24h 32m")
    
    with col3:
        st.metric("Messages Processed", "1,247")
    
    with col4:
        st.metric("Automation Rate", "68%")
    
    # Architecture diagram
    st.subheader("System Architecture")
    
    architecture_mermaid = """
    graph TD
        A[Slack Message] --> B[Intake Agent]
        B --> C{Route Decision}
        C -->|Knowledge| D[Knowledge Agent]
        C -->|Compliance| E[Compliance Agent]
        C -->|Demo| F[Demo Agent]
        C -->|Escalate| G[Human Escalation]
        D --> H{Confidence > 80%?}
        H -->|Yes| I[Send Response]
        H -->|No| G
        E --> I
        F --> I
        G --> J[Human Agent]
        I --> K[Update Analytics]
    """
    
    st.text("System Flow:")
    st.text("""
    1. Message received from Slack
    2. Intake Agent processes and routes
    3. Specialized agents handle specific queries
    4. Knowledge Agent searches vector database
    5. Response sent or escalated to humans
    6. Analytics updated for continuous improvement
    """)
    
    # Recent Activity
    st.subheader("Recent Activity")
    
    # Mock data for demo
    recent_data = pd.DataFrame({
        'Time': pd.date_range(start='2024-01-01 09:00', periods=10, freq='1H'),
        'Type': ['Technical', 'Compliance', 'Billing', 'Demo', 'General'] * 2,
        'Status': ['Resolved', 'Escalated', 'Resolved', 'Resolved', 'Escalated'] * 2,
        'Response Time (s)': [12, 45, 8, 15, 67, 23, 34, 11, 19, 88]
    })
    
    st.dataframe(recent_data, use_container_width=True)


def show_test_agent():
    """Test the AI agent with custom messages."""
    st.header("Test AI Agent")
    
    st.write("Test the AI agent with custom messages to see how it responds.")
    
    # Test input
    col1, col2 = st.columns([3, 1])
    
    with col1:
        test_message = st.text_area(
            "Enter your test message:",
            placeholder="How do I set up GDPR compliance in Delve?",
            height=100
        )
    
    with col2:
        category = st.selectbox(
            "Category (optional)",
            ["Auto-detect"] + [cat.value for cat in MessageCategory]
        )
        
        urgency = st.selectbox(
            "Urgency (optional)",
            ["Auto-detect"] + [level.value for level in UrgencyLevel]
        )
    
    if st.button("Test Agent", type="primary"):
        if test_message.strip():
            with st.spinner("Processing message through AI workflow..."):
                try:
                    # Test the workflow
                    result = asyncio.run(test_agent_workflow(test_message, category, urgency))
                    
                    if result:
                        st.success("✅ Agent processed successfully!")
                        
                        # Display results
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.subheader("Agent Response")
                            st.write(result["final_response"])
                            
                            if result.get("sources"):
                                st.subheader("Sources")
                                for source in result["sources"]:
                                    st.write(f"• {source}")
                        
                        with col2:
                            st.subheader("Processing Details")
                            st.json({
                                "Escalated": result["escalated"],
                                "Agents Used": result["agents_used"],
                                "Confidence Scores": result["confidence_scores"],
                                "Processing Time": f"{result['processing_time']:.2f}s" if result["processing_time"] else "N/A"
                            })
                    
                except Exception as e:
                    st.error(f"Error testing agent: {str(e)}")
        else:
            st.warning("Please enter a test message.")
    
    # Example queries
    st.subheader("Example Test Queries")
    
    examples = [
        "How do I configure SSO for my team?",
        "We need help with our SOC2 audit documentation",
        "What are your pricing plans?",
        "Can we schedule a demo for next week?",
        "The API is returning 500 errors",
        "How do I export user activity logs?",
        "What compliance certifications do you have?"
    ]
    
    for example in examples:
        if st.button(f"📝 {example}", key=f"example_{hash(example)}"):
            st.session_state.test_message = example


async def test_agent_workflow(message: str, category: str = "Auto-detect", urgency: str = "Auto-detect"):
    """Test the agent workflow with a message."""
    try:
        # Create test support message
        test_message = SupportMessage(
            message_id=f"test_{datetime.now().timestamp()}",
            channel_id="test_channel",
            user_id="test_user",
            timestamp=datetime.now(),
            content=message,
            thread_ts=None
        )
        
        # Override category and urgency if specified
        if category != "Auto-detect":
            test_message.category = MessageCategory(category)
        if urgency != "Auto-detect":
            test_message.urgency_level = UrgencyLevel(urgency)
        
        # Process through workflow
        final_state = await support_workflow.process_message(test_message)
        
        # Get the best response
        best_response = None
        if final_state.agent_responses:
            non_intake_responses = [r for r in final_state.agent_responses if r.agent_name != "intake_agent"]
            if non_intake_responses:
                best_response = max(non_intake_responses, key=lambda r: r.confidence_score)
        
        return {
            "final_response": final_state.final_response or "No response generated",
            "escalated": final_state.escalated,
            "agents_used": [r.agent_name for r in final_state.agent_responses],
            "confidence_scores": [r.confidence_score for r in final_state.agent_responses],
            "processing_time": (
                final_state.processing_completed - final_state.processing_started
            ).total_seconds() if final_state.processing_completed else None,
            "sources": best_response.sources if best_response else []
        }
        
    except Exception as e:
        st.error(f"Error in workflow test: {e}")
        return None


def show_system_health():
    """Show system health status."""
    st.header("System Health")
    
    # Health check function
    async def check_system_health():
        try:
            ollama_healthy = await ollama_client.health_check()
            vector_healthy = await vector_store.health_check()
            workflow_healthy = await support_workflow.health_check()
            
            return {
                "ollama": ollama_healthy,
                "vector_store": vector_healthy,
                "workflow": workflow_healthy,
                "overall": all([ollama_healthy, vector_healthy, workflow_healthy])
            }
        except Exception as e:
            return {
                "ollama": False,
                "vector_store": False,
                "workflow": False,
                "overall": False,
                "error": str(e)
            }
    
    if st.button("Refresh Health Status"):
        with st.spinner("Checking system health..."):
            health_status = asyncio.run(check_system_health())
    else:
        # Default status
        health_status = {
            "ollama": True,
            "vector_store": True,
            "workflow": True,
            "overall": True
        }
    
    # Display health status
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        status = "🟢 Healthy" if health_status.get("overall", False) else "🔴 Unhealthy"
        st.metric("Overall Status", status)
    
    with col2:
        status = "🟢 OK" if health_status.get("ollama", False) else "🔴 Error"
        st.metric("Ollama (LLM)", status)
    
    with col3:
        status = "🟢 OK" if health_status.get("vector_store", False) else "🔴 Error"
        st.metric("Vector Store", status)
    
    with col4:
        status = "🟢 OK" if health_status.get("workflow", False) else "🔴 Error"
        st.metric("Workflow", status)
    
    # Configuration
    st.subheader("Configuration")
    
    config_data = {
        "Ollama Base URL": settings.ollama_base_url,
        "Confidence Threshold": settings.confidence_threshold,
        "Max Response Time": f"{settings.max_response_time}s",
        "Environment": settings.environment,
        "Log Level": settings.log_level
    }
    
    for key, value in config_data.items():
        st.text(f"{key}: {value}")


def show_analytics():
    """Show analytics and metrics."""
    st.header("Analytics & Metrics")
    
    # Mock analytics data
    dates = pd.date_range(start='2024-01-01', end='2024-01-07', freq='D')
    
    # Message volume chart
    st.subheader("Message Volume")
    
    volume_data = pd.DataFrame({
        'Date': dates,
        'Messages': [45, 52, 38, 61, 43, 67, 59],
        'Automated': [31, 37, 26, 42, 29, 48, 41],
        'Escalated': [14, 15, 12, 19, 14, 19, 18]
    })
    
    fig_volume = px.line(
        volume_data, 
        x='Date', 
        y=['Messages', 'Automated', 'Escalated'],
        title="Daily Message Volume"
    )
    st.plotly_chart(fig_volume, use_container_width=True)
    
    # Response time distribution
    st.subheader("Response Time Distribution")
    
    response_times = [5, 12, 8, 23, 15, 7, 34, 11, 19, 6, 42, 9, 27, 13, 18]
    
    fig_response = px.histogram(
        x=response_times,
        nbins=10,
        title="Response Time Distribution (seconds)"
    )
    st.plotly_chart(fig_response, use_container_width=True)
    
    # Category breakdown
    st.subheader("Query Categories")
    
    category_data = pd.DataFrame({
        'Category': ['Technical', 'Compliance', 'Billing', 'Demo', 'General'],
        'Count': [45, 23, 18, 12, 32],
        'Automation Rate': [72, 65, 89, 83, 58]
    })
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig_cat = px.pie(
            category_data, 
            values='Count', 
            names='Category',
            title="Query Distribution"
        )
        st.plotly_chart(fig_cat, use_container_width=True)
    
    with col2:
        fig_auto = px.bar(
            category_data, 
            x='Category', 
            y='Automation Rate',
            title="Automation Rate by Category (%)"
        )
        st.plotly_chart(fig_auto, use_container_width=True)


def show_knowledge_base():
    """Show knowledge base management."""
    st.header("Knowledge Base Management")
    
    # Knowledge base stats
    async def get_kb_stats():
        try:
            stats = await vector_store.get_index_stats()
            return stats
        except Exception as e:
            return {"error": str(e)}
    
    if st.button("Refresh Stats"):
        with st.spinner("Getting knowledge base statistics..."):
            kb_stats = asyncio.run(get_kb_stats())
    else:
        kb_stats = {"total_vectors": 1247, "dimension": 4096}
    
    if "error" not in kb_stats:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Documents", kb_stats.get("total_vectors", "N/A"))
        
        with col2:
            st.metric("Vector Dimension", kb_stats.get("dimension", "N/A"))
        
        with col3:
            st.metric("Index Fullness", f"{kb_stats.get('index_fullness', 0)*100:.1f}%")
    
    # Add new knowledge
    st.subheader("Add Knowledge Entry")
    
    with st.form("add_knowledge"):
        title = st.text_input("Title")
        content = st.text_area("Content", height=150)
        category = st.selectbox("Category", [cat.value for cat in MessageCategory])
        tags = st.text_input("Tags (comma-separated)")
        source_url = st.text_input("Source URL (optional)")
        
        if st.form_submit_button("Add Entry"):
            if title and content:
                st.success("Knowledge entry would be added (demo mode)")
            else:
                st.error("Please fill in title and content")
    
    # Search knowledge base
    st.subheader("Search Knowledge Base")
    
    search_query = st.text_input("Search query:")
    
    if st.button("Search") and search_query:
        with st.spinner("Searching knowledge base..."):
            # Mock search results
            results = [
                {"title": "GDPR Compliance Setup", "score": 0.92, "category": "compliance"},
                {"title": "API Authentication Guide", "score": 0.87, "category": "technical"},
                {"title": "User Management Tutorial", "score": 0.81, "category": "general"}
            ]
            
            st.write(f"Found {len(results)} results:")
            
            for result in results:
                with st.expander(f"{result['title']} (Score: {result['score']:.2f})"):
                    st.write(f"Category: {result['category'].title()}")
                    st.write("Content preview would be shown here...")


if __name__ == "__main__":
    main()