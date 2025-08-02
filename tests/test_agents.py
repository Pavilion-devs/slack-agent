"""Tests for AI agents."""

import pytest
import asyncio
from datetime import datetime

from src.models.schemas import SupportMessage, MessageCategory, UrgencyLevel
from src.agents.intake_agent import IntakeAgent
from src.agents.rag_agent import RAGAgent


class TestIntakeAgent:
    """Test cases for IntakeAgent."""
    
    @pytest.fixture
    def intake_agent(self):
        return IntakeAgent()
    
    @pytest.fixture
    def sample_message(self):
        return SupportMessage(
            message_id="test_123",
            channel_id="C123456",
            user_id="U123456",
            timestamp=datetime.now(),
            content="How do I set up GDPR compliance?",
            thread_ts=None
        )
    
    @pytest.mark.asyncio
    async def test_process_message_success(self, intake_agent, sample_message):
        """Test successful message processing."""
        response = await intake_agent.process_message(sample_message)
        
        assert response is not None
        assert response.agent_name == "intake_agent"
        assert response.confidence_score >= 0.0
        assert response.confidence_score <= 1.0
        assert len(response.response_text) > 0
    
    @pytest.mark.asyncio
    async def test_compliance_message_routing(self, intake_agent):
        """Test that compliance messages are properly categorized."""
        message = SupportMessage(
            message_id="test_compliance",
            channel_id="C123456",
            user_id="U123456",
            timestamp=datetime.now(),
            content="We need help with SOC2 audit documentation",
            thread_ts=None,
            category=MessageCategory.COMPLIANCE  # Explicitly set the category
        )
        
        response = await intake_agent.process_message(message)
        
        # Should provide appropriate response and route correctly
        assert response.response_text is not None
        assert len(response.response_text) > 0
        assert "routing_decision" in response.metadata
        # The routing decision should be appropriate for compliance
        assert response.metadata["routing_decision"] in ["compliance_agent", "knowledge_agent"]
    
    def test_estimate_response_time(self, intake_agent):
        """Test response time estimation."""
        time_estimate = intake_agent._estimate_response_time(
            MessageCategory.TECHNICAL, 
            UrgencyLevel.HIGH
        )
        
        assert isinstance(time_estimate, str)
        assert "minute" in time_estimate.lower()
    
    def test_escalation_decision(self, intake_agent, sample_message):
        """Test escalation logic."""
        # Low confidence should trigger escalation
        should_escalate = intake_agent.should_escalate(0.5, sample_message)
        assert should_escalate
        
        # High confidence should not trigger escalation
        should_escalate = intake_agent.should_escalate(0.9, sample_message)
        assert not should_escalate
        
        # Critical urgency should trigger escalation
        sample_message.urgency_level = UrgencyLevel.CRITICAL
        should_escalate = intake_agent.should_escalate(0.9, sample_message)
        assert should_escalate


class TestRAGAgent:
    """Test cases for RAGAgent."""
    
    @pytest.fixture
    def rag_agent(self):
        return RAGAgent()
    
    @pytest.fixture
    def sample_message(self):
        return SupportMessage(
            message_id="test_456",
            channel_id="C123456",
            user_id="U123456",
            timestamp=datetime.now(),
            content="How do I configure API authentication?",
            thread_ts=None
        )
    
    @pytest.mark.asyncio
    async def test_process_message_basic(self, rag_agent, sample_message):
        """Test basic message processing with RAG agent."""
        response = await rag_agent.process_message(sample_message)
        
        assert response is not None
        assert isinstance(response.response_text, str)
        assert response.confidence_score >= 0.0
        assert response.confidence_score <= 1.0
    
    def test_should_escalate_low_confidence(self, rag_agent, sample_message):
        """Test escalation logic for low confidence."""
        should_escalate = rag_agent.should_escalate(0.3, sample_message)
        assert should_escalate
        
    def test_should_escalate_high_confidence(self, rag_agent, sample_message):
        """Test escalation logic for high confidence.""" 
        should_escalate = rag_agent.should_escalate(0.8, sample_message)
        assert not should_escalate