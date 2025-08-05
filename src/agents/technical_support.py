"""Technical Support Agent for handling SSO, SAML, API, and integration issues."""

import logging
from typing import Dict, Any, List, Optional
import re

from src.agents.base_agent import BaseAgent
from src.models.schemas import SupportMessage, AgentResponse
from src.core.config import settings

logger = logging.getLogger(__name__)


class TechnicalSupportAgent(BaseAgent):
    """Agent specialized in handling technical support issues."""
    
    def __init__(self):
        super().__init__("technical_support")
        self.technical_keywords = [
            'sso', 'saml', 'oauth', 'api', 'integration', 'error', 'bug',
            'not working', 'failing', 'broken', 'configure', 'setup',
            'authentication', 'authorization', 'token', 'webhook', 'endpoint'
        ]
        self.knowledge_base = self._load_technical_knowledge()
    
    def should_handle(self, message: SupportMessage) -> bool:
        """Determine if this agent should handle technical issues."""
        intent = self.extract_message_intent(message)
        content_lower = message.content.lower()
        
        # Handle explicit technical issues
        if intent.get('is_technical_issue'):
            return True
        
        # Handle error messages or technical terms
        technical_patterns = [
            r'\b\d{3}\s*error\b',  # HTTP error codes
            r'\bapi\s+error\b',
            r'\bconnection\s+failed\b',
            r'\btimeout\b',
            r'\bunauthorized\b',
            r'\bforbidden\b'
        ]
        
        for pattern in technical_patterns:
            if re.search(pattern, content_lower):
                return True
        
        return False
    
    async def process_message(self, message: SupportMessage) -> AgentResponse:
        """Process technical support requests."""
        logger.info(f"Technical support processing message: {message.message_id}")
        
        try:
            # Analyze the technical issue
            issue_analysis = self._analyze_technical_issue(message)
            
            # Generate appropriate response
            if issue_analysis['severity'] == 'critical':
                response_text = await self._handle_critical_issue(issue_analysis)
                confidence = 0.95
                should_escalate = True
                escalation_reason = f"Critical technical issue: {issue_analysis['issue_type']}"
            elif issue_analysis['issue_type'] in self.knowledge_base:
                response_text = await self._generate_solution_response(issue_analysis)
                confidence = 0.85
                should_escalate = False
                escalation_reason = None
            else:
                response_text = await self._handle_unknown_issue(issue_analysis)
                confidence = 0.60
                should_escalate = True
                escalation_reason = f"Unknown technical issue requiring engineer review"
            
            return self.format_response(
                response_text=response_text,
                confidence_score=confidence,
                sources=["Technical Documentation", "Integration Guides", "Troubleshooting KB"],
                should_escalate=should_escalate,
                escalation_reason=escalation_reason,
                metadata={
                    "agent_type": "technical_support",
                    "issue_analysis": issue_analysis,
                    "technical_area": issue_analysis.get('issue_type', 'unknown')
                }
            )
            
        except Exception as e:
            logger.error(f"Error in technical support: {e}")
            return self.format_response(
                response_text="I encountered an issue while analyzing your technical problem. Let me escalate this to our engineering team for immediate assistance.",
                confidence_score=0.2,
                should_escalate=True,
                escalation_reason=f"Technical support agent error: {str(e)}"
            )
    
    def _analyze_technical_issue(self, message: SupportMessage) -> Dict[str, Any]:
        """Analyze the technical issue to determine type and severity."""
        content_lower = message.content.lower()
        urgency = self.detect_urgency(message)
        
        analysis = {
            "issue_type": "unknown",
            "severity": urgency,
            "error_codes": [],
            "systems_affected": [],
            "potential_solutions": []
        }
        
        # Detect issue types
        issue_patterns = {
            "sso": ["sso", "single sign", "saml", "oauth", "authentication"],
            "api": ["api", "endpoint", "webhook", "integration", "http"],
            "configuration": ["config", "setup", "configure", "setting"],
            "connectivity": ["connection", "timeout", "network", "unreachable"],
            "authorization": ["unauthorized", "forbidden", "access denied", "permission"]
        }
        
        for issue_type, keywords in issue_patterns.items():
            if any(keyword in content_lower for keyword in keywords):
                analysis["issue_type"] = issue_type
                break
        
        # Extract error codes
        error_code_pattern = r'\b[4-5]\d{2}\b'
        analysis["error_codes"] = re.findall(error_code_pattern, content_lower)
        
        # Detect affected systems
        system_indicators = {
            "production": ["production", "prod", "live"],
            "staging": ["staging", "test", "dev"],
            "api": ["api", "endpoint"],
            "dashboard": ["dashboard", "ui", "interface"]
        }
        
        for system, indicators in system_indicators.items():
            if any(indicator in content_lower for indicator in indicators):
                analysis["systems_affected"].append(system)
        
        return analysis
    
    async def _handle_critical_issue(self, analysis: Dict[str, Any]) -> str:
        """Handle critical technical issues that need immediate escalation."""
        issue_type = analysis.get('issue_type', 'unknown')
        error_codes = analysis.get('error_codes', [])
        systems_affected = analysis.get('systems_affected', [])
        
        response = "🚨 **CRITICAL ISSUE DETECTED** - I'm immediately escalating this to our engineering team.\n\n"
        
        if 'production' in systems_affected:
            response += "⚡ Since this affects production systems, our engineers will respond within 15 minutes.\n\n"
        
        if error_codes:
            response += f"📊 **Error Details:**\n"
            for code in error_codes:
                if code.startswith('5'):
                    response += f"• {code} - Server error detected\n"
                elif code.startswith('4'):
                    response += f"• {code} - Client/authentication error detected\n"
            response += "\n"
        
        response += "🔧 **Immediate Actions:**\n"
        
        if issue_type == "api":
            response += "• Engineering team alerted for API investigation\n"
            response += "• Checking system health and monitoring dashboards\n"
        elif issue_type == "sso":
            response += "• SSO/authentication team notified\n"
            response += "• Checking identity provider status\n"
        
        response += "\n📞 **Next Steps:**\n"
        response += "• You'll receive a direct message from our engineering team within 15 minutes\n"
        response += "• We'll provide regular updates every 30 minutes until resolved\n"
        response += "• Post-mortem report will be shared once issue is resolved"
        
        return response
    
    async def _generate_solution_response(self, analysis: Dict[str, Any]) -> str:
        """Generate a solution response for known technical issues."""
        issue_type = analysis.get('issue_type', 'unknown')
        knowledge = self.knowledge_base.get(issue_type, {})
        
        response = f"🔧 **{issue_type.upper()} Issue - I can help with this!**\n\n"
        
        # Add specific guidance based on issue type
        if issue_type == "sso":
            response += self._generate_sso_guidance(analysis)
        elif issue_type == "api":
            response += self._generate_api_guidance(analysis)
        elif issue_type == "configuration":
            response += self._generate_config_guidance(analysis)
        else:
            response += knowledge.get('general_guidance', 
                "Let me connect you with our technical team for specific guidance on this issue.")
        
        response += "\n\n💡 **Additional Resources:**\n"
        response += "• 📚 [Technical Documentation](https://docs.delve.com)\n"
        response += "• 🔗 [Integration Guides](https://docs.delve.com/integrations)\n"
        response += "• 🛠️ [Troubleshooting Guide](https://docs.delve.com/troubleshooting)\n\n"
        
        response += "If these steps don't resolve the issue, I'll escalate to our engineering team for personalized assistance."
        
        return response
    
    def _generate_sso_guidance(self, analysis: Dict[str, Any]) -> str:
        """Generate SSO-specific guidance."""
        return (
            "**SSO Configuration Steps:**\n\n"
            "1. **Identity Provider Setup:**\n"
            "   • Verify your IdP is properly configured\n"
            "   • Check SAML/OAuth endpoints are accessible\n"
            "   • Ensure certificates are valid and not expired\n\n"
            "2. **Delve Configuration:**\n"
            "   • Navigate to Settings > Authentication\n"
            "   • Verify SSO provider settings match your IdP\n"
            "   • Test connection using the built-in test tool\n\n"
            "3. **Common Issues:**\n"
            "   • **401 Errors:** Check API keys and authentication headers\n"
            "   • **403 Errors:** Verify user permissions and group mappings\n"
            "   • **Timeouts:** Check network connectivity and firewall rules\n\n"
            "4. **Active Directory Integration:**\n"
            "   • Ensure proper group synchronization\n"
            "   • Verify user attribute mappings\n"
            "   • Test with a sample user account"
        )
    
    def _generate_api_guidance(self, analysis: Dict[str, Any]) -> str:
        """Generate API-specific guidance."""
        error_codes = analysis.get('error_codes', [])
        
        guidance = (
            "**API Troubleshooting Steps:**\n\n"
            "1. **Authentication Check:**\n"
            "   • Verify API key is valid and active\n"
            "   • Check request headers include proper authorization\n"
            "   • Ensure API key has required permissions\n\n"
        )
        
        if '401' in error_codes:
            guidance += (
                "2. **401 Unauthorized - Specific Steps:**\n"
                "   • Regenerate API key from Delve dashboard\n"
                "   • Check Authorization header format: `Bearer <your-api-key>`\n"
                "   • Verify endpoint URL is correct\n\n"
            )
        
        if '403' in error_codes:
            guidance += (
                "2. **403 Forbidden - Specific Steps:**\n"
                "   • Check API key permissions in Settings > API\n"
                "   • Verify your account has access to requested resources\n"
                "   • Contact admin to grant necessary permissions\n\n"
            )
        
        if '500' in error_codes or '502' in error_codes or '503' in error_codes:
            guidance += (
                "2. **Server Error - Immediate Escalation Needed:**\n"
                "   • This indicates a problem on our end\n"
                "   • I'm escalating this to our engineering team\n"
                "   • You'll receive a response within 15 minutes\n\n"
            )
        
        guidance += (
            "3. **Rate Limiting:**\n"
            "   • Check for 429 status codes\n"
            "   • Implement exponential backoff\n"
            "   • Consider upgrading API limits if needed\n\n"
            "4. **Testing Tools:**\n"
            "   • Use Postman or curl for manual testing\n"
            "   • Check our API status page: status.delve.com\n"
            "   • Review API logs in your Delve dashboard"
        )
        
        return guidance
    
    def _generate_config_guidance(self, analysis: Dict[str, Any]) -> str:
        """Generate configuration-specific guidance."""
        return (
            "**Configuration Troubleshooting:**\n\n"
            "1. **Verify Settings:**\n"
            "   • Check all required fields are populated\n"
            "   • Ensure URLs and endpoints are accessible\n"
            "   • Validate configuration syntax\n\n"
            "2. **Test Connectivity:**\n"
            "   • Use built-in connection test tools\n"
            "   • Check firewall and network settings\n"
            "   • Verify DNS resolution\n\n"
            "3. **Common Configuration Issues:**\n"
            "   • Incorrect webhook URLs\n"
            "   • Missing or invalid certificates\n"
            "   • Firewall blocking outbound connections\n"
            "   • Timezone or formatting mismatches\n\n"
            "4. **Validation Steps:**\n"
            "   • Save and test configuration\n"
            "   • Monitor logs for error messages\n"
            "   • Verify data flow end-to-end"
        )
    
    async def _handle_unknown_issue(self, analysis: Dict[str, Any]) -> str:
        """Handle unknown technical issues."""
        return (
            "🔍 I've analyzed your technical issue and while I can see this needs specialized attention, "
            "I want to make sure you get the most accurate solution.\n\n"
            "I'm escalating this to our engineering team who can:\n"
            "• Provide detailed troubleshooting steps\n"
            "• Access system logs and diagnostics\n"
            "• Implement fixes if needed\n"
            "• Schedule a screen-share session if helpful\n\n"
            "**Expected Response Time:** Within 30 minutes during business hours\n\n"
            "In the meantime, if you have additional error messages, logs, or screenshots, "
            "please share them - they'll help our engineers diagnose the issue faster."
        )
    
    def _load_technical_knowledge(self) -> Dict[str, Any]:
        """Load technical knowledge base."""
        return {
            "sso": {
                "common_issues": ["authentication_failed", "certificate_expired", "user_mapping"],
                "general_guidance": "SSO issues typically involve identity provider configuration or user mapping problems."
            },
            "api": {
                "common_issues": ["authentication", "rate_limiting", "endpoint_errors"],
                "general_guidance": "API issues often stem from authentication, rate limiting, or endpoint configuration problems."
            },
            "configuration": {
                "common_issues": ["webhook_setup", "integration_config", "network_connectivity"],
                "general_guidance": "Configuration issues usually involve settings validation or network connectivity."
            },
            "connectivity": {
                "common_issues": ["firewall", "dns", "timeout"],
                "general_guidance": "Connectivity issues typically involve network, firewall, or DNS configuration."
            }
        }
    
    async def health_check(self) -> bool:
        """Check if technical support agent is healthy."""
        try:
            # Verify knowledge base is loaded
            return len(self.knowledge_base) > 0 and len(self.technical_keywords) > 0
        except Exception as e:
            logger.error(f"Technical support health check failed: {e}")
            return False