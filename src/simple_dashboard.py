"""Simplified Streamlit dashboard for testing the Slack Support AI Agent."""

import streamlit as st
import asyncio
import json
from datetime import datetime
import sys
import os

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.core.config import settings
from src.models.schemas import SupportMessage, MessageCategory, UrgencyLevel
from src.simple_workflow import simple_workflow
from src.integrations.ollama_client import ollama_client
from src.integrations.vector_store import vector_store


st.set_page_config(
    page_title="Delve AI Support Agent - Simple Dashboard",
    page_icon="🤖",
    layout="wide"
)


def main():
    """Main dashboard function."""
    st.title("🤖 Delve Slack Support AI Agent - Test Dashboard")
    
    # Sidebar for navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox(
        "Select Page",
        ["Test Agent", "System Health", "Configuration"]
    )
    
    if page == "Test Agent":
        show_test_agent()
    elif page == "System Health":
        show_system_health()
    elif page == "Configuration":
        show_configuration()


def show_test_agent():
    """Test the AI agent with custom messages."""
    st.header("🧪 Test AI Agent")
    
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
    
    if st.button("🚀 Test Agent", type="primary"):
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
                            st.subheader("🤖 Agent Response")
                            st.write(result["final_response"])
                            
                            if result.get("sources"):
                                st.subheader("📚 Sources")
                                for source in result["sources"]:
                                    st.write(f"• {source}")
                        
                        with col2:
                            st.subheader("📊 Processing Details")
                            
                            st.write(f"**Escalated:** {'Yes' if result['escalated'] else 'No'}")
                            st.write(f"**Processing Time:** {result['processing_time']:.2f}s" if result["processing_time"] else "N/A")
                            
                            st.write("**Agents Used:**")
                            for i, agent in enumerate(result["agents_used"]):
                                confidence = result["confidence_scores"][i] if i < len(result["confidence_scores"]) else 0
                                st.write(f"• {agent}: {confidence:.2f}")
                    
                except Exception as e:
                    st.error(f"❌ Error testing agent: {str(e)}")
                    st.write("**Error details:**")
                    st.code(str(e))
        else:
            st.warning("⚠️ Please enter a test message.")
    
    # Example queries
    st.subheader("📝 Example Test Queries")
    
    examples = [
        "How do I configure SSO for my team?",
        "We need help with our SOC2 audit documentation", 
        "What are your pricing plans?",
        "Can we schedule a demo for next week?",
        "The API is returning 500 errors",
        "How do I export user activity logs?",
        "What compliance certifications do you have?"
    ]
    
    cols = st.columns(2)
    for i, example in enumerate(examples):
        with cols[i % 2]:
            if st.button(f"📝 {example}", key=f"example_{i}"):
                st.session_state["test_message"] = example
                st.rerun()


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
        final_state = await simple_workflow.process_message(test_message)
        
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
    st.header("🏥 System Health")
    
    # Health check function
    async def check_system_health():
        try:
            ollama_healthy = await ollama_client.health_check()
            vector_healthy = await vector_store.health_check()
            workflow_healthy = await simple_workflow.health_check()
            
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
    
    if st.button("🔄 Refresh Health Status"):
        with st.spinner("Checking system health..."):
            health_status = asyncio.run(check_system_health())
            st.session_state.health_status = health_status
    
    # Get health status from session state or use defaults
    health_status = getattr(st.session_state, 'health_status', {
        "ollama": False,
        "vector_store": False,
        "workflow": False,
        "overall": False
    })
    
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
    
    if health_status.get("error"):
        st.error(f"Health check error: {health_status['error']}")


def show_configuration():
    """Show configuration details."""
    st.header("⚙️ Configuration")
    
    st.subheader("Current Settings")
    
    try:
        config_data = {
            "Ollama Base URL": settings.ollama_base_url,
            "Confidence Threshold": settings.confidence_threshold,
            "Max Response Time": f"{settings.max_response_time}s",
            "Environment": settings.environment,
            "Log Level": settings.log_level,
            "Host": settings.host,
            "Port": settings.port
        }
        
        for key, value in config_data.items():
            st.write(f"**{key}:** {value}")
            
    except Exception as e:
        st.error(f"Error loading configuration: {e}")
    
    st.subheader("Environment Setup")
    
    st.write("Make sure you have these environment variables set:")
    
    env_vars = [
        ("SLACK_BOT_TOKEN", "Your Slack bot token"),
        ("SLACK_SIGNING_SECRET", "Your Slack signing secret"),
        ("PINECONE_API_KEY", "Your Pinecone API key"),
        ("OLLAMA_BASE_URL", "Ollama server URL (default: http://localhost:11434)")
    ]
    
    for var, description in env_vars:
        st.write(f"• **{var}**: {description}")
    
    st.subheader("Quick Setup Guide")
    
    st.write("1. **Start Ollama:**")
    st.code("ollama serve\nollama pull llama3.2:3b")
    
    st.write("2. **Create .env file:**")
    st.code("cp .env.example .env\n# Edit .env with your API keys")
    
    st.write("3. **Run the application:**")
    st.code("python3 -m src.main")


if __name__ == "__main__":
    main()