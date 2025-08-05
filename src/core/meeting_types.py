"""
Meeting type configurations for different types of scheduling requests.
"""

from typing import Dict, List, Any
from dataclasses import dataclass

@dataclass
class MeetingTypeConfig:
    """Configuration for a specific meeting type."""
    
    name: str
    duration_minutes: int
    title_template: str
    description_template: str
    attendees: List[str]
    calendar_id: str = "primary"
    buffer_minutes: int = 15  # Buffer time after meeting
    
    def format_title(self, **kwargs) -> str:
        """Format the meeting title with provided parameters."""
        return self.title_template.format(**kwargs)
    
    def format_description(self, **kwargs) -> str:
        """Format the meeting description with provided parameters."""
        return self.description_template.format(**kwargs)


class MeetingTypeManager:
    """Manages different meeting type configurations."""
    
    def __init__(self):
        self.meeting_types = {
            "demo": MeetingTypeConfig(
                name="Product Demo",
                duration_minutes=30,
                title_template="Delve Product Demo - {user_name}",
                description_template=(
                    "Product demonstration call to showcase Delve's AI-native compliance automation platform.\n\n"
                    "Agenda:\n"
                    "• Platform overview and key features\n"
                    "• Discussion of your specific use case\n"
                    "• Q&A session\n"
                    "• Next steps for implementation\n\n"
                    "Join URL will be provided before the meeting."
                ),
                attendees=["sales@delve.ai"],
                buffer_minutes=15
            ),
            
            "technical_support": MeetingTypeConfig(
                name="Technical Support Call",
                duration_minutes=60,
                title_template="Technical Support - {issue_type}",
                description_template=(
                    "Technical support call to resolve implementation and configuration issues.\n\n"
                    "Agenda:\n"
                    "• Issue diagnosis and troubleshooting\n"
                    "• Step-by-step resolution guidance\n"
                    "• Best practices review\n"
                    "• Follow-up action items\n\n"
                    "Please have your system details ready for faster resolution.\n"
                    "Join URL will be provided before the meeting."
                ),
                attendees=["support@delve.ai", "engineering@delve.ai"],
                buffer_minutes=15
            ),
            
            "sales_discussion": MeetingTypeConfig(
                name="Sales Discussion",
                duration_minutes=45,
                title_template="Sales Discussion - {company_name}",
                description_template=(
                    "Sales discussion to explore Delve's solutions for your organization.\n\n"
                    "Agenda:\n"
                    "• Business requirements analysis\n"
                    "• Solution fit assessment\n"
                    "• Pricing and licensing discussion\n"
                    "• Implementation timeline\n"
                    "• Contract and next steps\n\n"
                    "Join URL will be provided before the meeting."
                ),
                attendees=["sales@delve.ai", "solutions@delve.ai"],
                buffer_minutes=30  # Longer buffer for sales calls
            ),
            
            "compliance_consultation": MeetingTypeConfig(
                name="Compliance Consultation",
                duration_minutes=45,
                title_template="Compliance Consultation - {framework}",
                description_template=(
                    "Specialized consultation on compliance frameworks and audit preparation.\n\n"
                    "Agenda:\n"
                    "• Compliance framework review ({framework})\n"
                    "• Gap analysis and requirements\n"
                    "• Delve's compliance automation capabilities\n"
                    "• Implementation roadmap\n"
                    "• Audit preparation strategies\n\n"
                    "Join URL will be provided before the meeting."
                ),
                attendees=["compliance@delve.ai", "solutions@delve.ai"],
                buffer_minutes=15
            ),
            
            "onboarding_session": MeetingTypeConfig(
                name="Customer Onboarding",
                duration_minutes=60,
                title_template="Customer Onboarding - {company_name}",
                description_template=(
                    "Welcome session to get your team started with Delve.\n\n"
                    "Agenda:\n"
                    "• Platform walkthrough and setup\n"
                    "• User account configuration\n"
                    "• Initial compliance assessment\n"
                    "• Training resources and documentation\n"
                    "• Success metrics and milestones\n\n"
                    "Join URL will be provided before the meeting."
                ),
                attendees=["success@delve.ai", "support@delve.ai"],
                buffer_minutes=15
            )
        }
        
        # Keywords that help identify meeting types from user messages
        self.detection_keywords = {
            "demo": [
                "demo", "demonstration", "showcase", "overview", "walkthrough", 
                "show me", "see the platform", "product tour", "quick look"
            ],
            "technical_support": [
                "support", "help", "issue", "problem", "error", "bug", "troubleshoot",
                "not working", "configuration", "setup", "implementation", "technical"
            ],
            "sales_discussion": [
                "sales", "pricing", "cost", "license", "contract", "purchase", "buy",
                "quote", "proposal", "business", "enterprise", "commercial"
            ],
            "compliance_consultation": [
                "compliance", "audit", "soc2", "iso27001", "gdpr", "hipaa", "framework",
                "regulation", "certification", "assessment", "gap analysis"
            ],
            "onboarding_session": [
                "onboarding", "getting started", "setup", "training", "new customer",
                "implementation", "kickoff", "welcome", "first steps"
            ]
        }
    
    def get_meeting_type(self, meeting_type_key: str) -> MeetingTypeConfig:
        """Get meeting type configuration by key."""
        return self.meeting_types.get(meeting_type_key)
    
    def get_all_meeting_types(self) -> Dict[str, MeetingTypeConfig]:
        """Get all available meeting types."""
        return self.meeting_types.copy()
    
    def detect_meeting_type(self, message_content: str) -> str:
        """
        Detect the most likely meeting type from message content.
        
        Args:
            message_content: User's message content
            
        Returns:
            Meeting type key or 'demo' as default
        """
        content_lower = message_content.lower()
        
        # Score each meeting type based on keyword matches
        scores = {}
        for meeting_type, keywords in self.detection_keywords.items():
            score = sum(1 for keyword in keywords if keyword in content_lower)
            if score > 0:
                scores[meeting_type] = score
        
        if not scores:
            return "demo"  # Default to demo if no keywords match
        
        # Return the meeting type with the highest score
        return max(scores.items(), key=lambda x: x[1])[0]
    
    def format_meeting_selection_options(self) -> str:
        """Format meeting type options for user selection."""
        options = []
        icons = {
            "demo": "📊",
            "technical_support": "🔧", 
            "sales_discussion": "💼",
            "compliance_consultation": "🛡️",
            "onboarding_session": "🚀"
        }
        
        for i, (key, config) in enumerate(self.meeting_types.items(), 1):
            icon = icons.get(key, "📅")
            options.append(
                f"{i}. {icon} **{config.name}** ({config.duration_minutes} min)\n"
                f"   Perfect for: {self._get_meeting_purpose(key)}"
            )
        
        return "\n\n".join(options)
    
    def _get_meeting_purpose(self, meeting_type_key: str) -> str:
        """Get a brief description of what each meeting type is for."""
        purposes = {
            "demo": "Platform overview and feature demonstration",
            "technical_support": "Implementation help and troubleshooting",
            "sales_discussion": "Pricing, contracts, and business requirements",
            "compliance_consultation": "SOC2, GDPR, HIPAA framework guidance",
            "onboarding_session": "Getting started and initial setup"
        }
        return purposes.get(meeting_type_key, "General meeting")
    
    def get_meeting_type_by_number(self, selection_number: int) -> str:
        """Get meeting type key by selection number (1-based)."""
        meeting_keys = list(self.meeting_types.keys())
        if 1 <= selection_number <= len(meeting_keys):
            return meeting_keys[selection_number - 1]
        return None


# Global instance
meeting_type_manager = MeetingTypeManager()