"""Data models and schemas for the Slack Support AI Agent."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class UrgencyLevel(str, Enum):
    """Message urgency levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MessageCategory(str, Enum):
    """Message categories for routing."""
    TECHNICAL = "technical"
    COMPLIANCE = "compliance"
    BILLING = "billing"
    DEMO = "demo"
    GENERAL = "general"


class ResolutionStatus(str, Enum):
    """Resolution status of messages."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


class SupportMessage(BaseModel):
    """Support message data model."""
    message_id: str
    channel_id: str
    user_id: str
    timestamp: datetime
    content: str
    thread_ts: Optional[str] = None
    urgency_level: UrgencyLevel = UrgencyLevel.MEDIUM
    category: MessageCategory = MessageCategory.GENERAL
    confidence_score: Optional[float] = None
    resolution_status: ResolutionStatus = ResolutionStatus.PENDING
    assigned_agent: Optional[str] = None
    response_time: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class KnowledgeEntry(BaseModel):
    """Knowledge base entry data model."""
    doc_id: str
    title: str
    content: str
    category: MessageCategory = MessageCategory.GENERAL
    last_updated: datetime
    usage_count: int = 0
    effectiveness_score: float = 0.0
    tags: List[str] = Field(default_factory=list)
    source_url: Optional[str] = None


class AgentResponse(BaseModel):
    """Response from an AI agent."""
    agent_name: str
    response_text: str
    confidence_score: float
    processing_time: float = 0.0
    sources: List[str] = Field(default_factory=list)
    should_escalate: bool = False
    escalation_reason: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentState(BaseModel):
    """State object for LangGraph workflow."""
    message: SupportMessage
    agent_responses: List[AgentResponse] = Field(default_factory=list)
    final_response: Optional[str] = None
    escalated: bool = False
    processing_started: datetime = Field(default_factory=datetime.now)
    processing_completed: Optional[datetime] = None


class ComplianceQuery(BaseModel):
    """Compliance-specific query model."""
    framework: str  # SOC2, ISO27001, GDPR, HIPAA
    query_text: str
    urgency: UrgencyLevel = UrgencyLevel.MEDIUM
    audit_context: Optional[str] = None


class DemoRequest(BaseModel):
    """Demo scheduling request model."""
    requester_email: str
    company_name: str
    preferred_times: List[datetime]
    demo_type: str = "general"  # general, compliance, technical
    specific_requirements: Optional[str] = None
    attendee_count: int = 1


class AnalyticsEvent(BaseModel):
    """Analytics event for tracking."""
    event_type: str
    timestamp: datetime = Field(default_factory=datetime.now)
    user_id: Optional[str] = None
    channel_id: Optional[str] = None
    agent_name: Optional[str] = None
    response_time: Optional[float] = None
    confidence_score: Optional[float] = None
    escalated: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)