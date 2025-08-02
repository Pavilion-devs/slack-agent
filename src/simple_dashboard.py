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
from src.workflows.improved_workflow import ImprovedWorkflow
from src.core.rag_system import rag_system
from src.agents.rag_agent import RAGAgent


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
                            if result['escalated'] and result.get('escalation_reason'):
                                st.write(f"**Escalation Reason:** {result['escalation_reason']}")
                            st.write(f"**Processing Time:** {result['processing_time']:.2f}s" if result["processing_time"] else "N/A")
                            
                            st.write("**Agents Used:**")
                            for i, agent in enumerate(result["agents_used"]):
                                confidence = result["confidence_scores"][i] if i < len(result["confidence_scores"]) else 0
                                st.write(f"• {agent}: {confidence:.2f}")
                            
                            # Show metadata if available
                            if result.get('metadata'):
                                metadata = result['metadata']
                                if metadata.get('frameworks_detected'):
                                    st.write(f"**Frameworks Detected:** {', '.join(metadata['frameworks_detected'])}")
                                if metadata.get('intent_classified'):
                                    st.write(f"**Intent:** {metadata['intent_classified']}")
                    
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
        # Initialize RAG system if needed
        if not rag_system.is_initialized:
            await rag_system.initialize()
        
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
        
        # Process through improved workflow
        workflow = ImprovedWorkflow()
        start_time = datetime.now()
        response = await workflow.process_message(test_message)
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return {
            "final_response": response.response_text,
            "escalated": response.should_escalate,
            "agents_used": [response.agent_name],
            "confidence_scores": [response.confidence_score],
            "processing_time": processing_time,
            "sources": response.sources if response.sources else [],
            "escalation_reason": response.escalation_reason,
            "metadata": response.metadata if hasattr(response, 'metadata') else {}
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
            # Check RAG system
            rag_healthy = await rag_system.health_check()
            
            # Check if RAG system is initialized
            if not rag_system.is_initialized:
                await rag_system.initialize()
            
            rag_initialized = rag_system.is_initialized
            
            # Test RAG agent
            agent = RAGAgent()
            test_message = SupportMessage(
                message_id="health_check",
                channel_id="test",
                user_id="test",
                timestamp=datetime.now(),
                content="What is Delve?"
            )
            
            try:
                response = await agent.process_message(test_message)
                agent_healthy = response is not None
            except:
                agent_healthy = False
            
            overall_healthy = rag_healthy and rag_initialized and agent_healthy
            
            return {
                "rag_system": rag_healthy,
                "rag_initialized": rag_initialized,
                "agent": agent_healthy,
                "overall": overall_healthy
            }
        except Exception as e:
            return {
                "rag_system": False,
                "rag_initialized": False,
                "agent": False,
                "overall": False,
                "error": str(e)
            }
    
    if st.button("🔄 Refresh Health Status"):
        with st.spinner("Checking system health..."):
            health_status = asyncio.run(check_system_health())
            st.session_state.health_status = health_status
    
    # Get health status from session state or use defaults
    health_status = getattr(st.session_state, 'health_status', {
        "rag_system": False,
        "rag_initialized": False,
        "agent": False,
        "overall": False
    })
    
    # Display health status
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        status = "🟢 Healthy" if health_status.get("overall", False) else "🔴 Unhealthy"
        st.metric("Overall Status", status)
    
    with col2:
        status = "🟢 OK" if health_status.get("rag_system", False) else "🔴 Error"
        st.metric("RAG System", status)
    
    with col3:
        status = "🟢 OK" if health_status.get("rag_initialized", False) else "🔴 Error"
        st.metric("Vector Database", status)
    
    with col4:
        status = "🟢 OK" if health_status.get("agent", False) else "🔴 Error"
        st.metric("RAG Agent", status)
    
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
    
    st.write("Optional environment variables:")
    
    env_vars = [
        ("SLACK_BOT_TOKEN", "Your Slack bot token (optional for testing)"),
        ("SLACK_SIGNING_SECRET", "Your Slack signing secret (optional for testing)"),
        ("OPENAI_API_KEY", "OpenAI API key (optional, uses Ollama by default)"),
        ("OLLAMA_BASE_URL", "Ollama server URL (default: http://localhost:11434)")
    ]
    
    for var, description in env_vars:
        st.write(f"• **{var}**: {description}")
    
    st.subheader("Quick Setup Guide")
    
    st.write("1. **Start Ollama:**")
    st.code("ollama serve\nollama pull llama3.2:3b")
    
    st.write("2. **Test the system:**")
    st.code("python run_manual_test.py")
    
    st.write("3. **Run this dashboard:**")
    st.code("streamlit run src/simple_dashboard.py")
    
    st.write("4. **Run the main application:**")
    st.code("python3 -m src.main")


if __name__ == "__main__":
    main()