"""Tests for AI agents."""

import pytest
import asyncio
from datetime import datetime

from src.models.schemas import SupportMessage, MessageCategory, UrgencyLevel
from src.agents.intake_agent import IntakeAgent
from src.agents.knowledge_agent import KnowledgeAgent


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
            thread_ts=None
        )
        
        response = await intake_agent.process_message(message)
        
        # Should be categorized as compliance
        assert message.category == MessageCategory.COMPLIANCE
        assert "routing_decision" in response.metadata
    
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


class TestKnowledgeAgent:
    """Test cases for KnowledgeAgent."""
    
    @pytest.fixture
    def knowledge_agent(self):
        return KnowledgeAgent()
    
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
    async def test_process_message_no_knowledge(self, knowledge_agent, sample_message):
        """Test processing when no knowledge is found."""
        # Mock the search to return empty results
        knowledge_agent._search_knowledge = lambda msg: []
        
        response = await knowledge_agent.process_message(sample_message)
        
        assert response is not None
        assert response.should_escalate
        assert "knowledge" in response.escalation_reason.lower()
    
    def test_format_sources(self, knowledge_agent):
        """Test source formatting."""
        from src.models.schemas import KnowledgeEntry
        
        entries = [
            (KnowledgeEntry(
                doc_id="test1",
                title="Test Document 1",
                content="Test content",
                category=MessageCategory.TECHNICAL,
                last_updated=datetime.now(),
                source_url="https://example.com/doc1"
            ), 0.95),
            (KnowledgeEntry(
                doc_id="test2", 
                title="Test Document 2",
                content="Test content",
                category=MessageCategory.GENERAL,
                last_updated=datetime.now()
            ), 0.87)
        ]
        
        sources = knowledge_agent._format_sources(entries)
        
        assert len(sources) == 2
        assert "Test Document 1" in sources[0]
        assert "https://example.com/doc1" in sources[0]
        assert "Test Document 2" in sources[1]