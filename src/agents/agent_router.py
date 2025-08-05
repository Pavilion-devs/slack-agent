"""Agent Router for intelligent message distribution."""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from src.models.schemas import SupportMessage, AgentResponse
from src.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class AgentRouter:
    """Routes messages to the most appropriate agent based on content and context."""
    
    def __init__(self):
        self.agents: List[BaseAgent] = []
        self.fallback_agent: Optional[BaseAgent] = None
        self.routing_stats = {
            "total_routed": 0,
            "agent_usage": {},
            "escalation_rate": 0.0
        }
    
    def register_agent(self, agent: BaseAgent, is_fallback: bool = False):
        """Register an agent with the router."""
        self.agents.append(agent)
        self.routing_stats["agent_usage"][agent.name] = 0
        
        if is_fallback:
            self.fallback_agent = agent
        
        logger.info(f"Registered agent: {agent.name}")
    
    async def route_message(self, message: SupportMessage) -> AgentResponse:
        """Route a message to the most appropriate agent."""
        self.routing_stats["total_routed"] += 1
        
        # Find the best agent for this message
        selected_agent = await self._select_agent(message)
        
        if not selected_agent:
            logger.warning(f"No agent found for message {message.message_id}")
            return self._create_error_response(message)
        
        # Track usage
        self.routing_stats["agent_usage"][selected_agent.name] += 1
        
        try:
            # Process the message with the selected agent
            logger.info(f"Routing message {message.message_id} to {selected_agent.name}")
            response = await selected_agent.process_message(message)
            
            # Log the processing
            selected_agent.log_processing(message, response)
            
            # Update escalation stats
            if response.should_escalate:
                self.routing_stats["escalation_rate"] = (
                    self.routing_stats["escalation_rate"] * 0.9 + 0.1
                )
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing message with {selected_agent.name}: {e}")
            return self._create_error_response(message, str(e))
    
    async def _select_agent(self, message: SupportMessage) -> Optional[BaseAgent]:
        """Select the most appropriate agent for the message."""
        # Check each agent to see if they can handle the message
        capable_agents = []
        
        for agent in self.agents:
            try:
                if agent.should_handle(message):
                    capable_agents.append(agent)
            except Exception as e:
                logger.error(f"Error checking agent {agent.name}: {e}")
                continue
        
        if capable_agents:
            # For now, return the first capable agent
            # In the future, we could implement more sophisticated selection logic
            return capable_agents[0]
        
        # Return fallback agent if no specific agent can handle it
        return self.fallback_agent
    
    def _create_error_response(
        self, 
        message: SupportMessage, 
        error_message: str = "I'm experiencing technical difficulties"
    ) -> AgentResponse:
        """Create an error response when routing fails."""
        return AgentResponse(
            agent_name="router",
            response_text=f"{error_message}. Let me escalate this to our support team.",
            confidence_score=0.0,
            sources=[],
            should_escalate=True,
            escalation_reason="Routing error or no capable agent found",
            metadata={"error": True, "original_message_id": message.message_id}
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """Check the health of all registered agents."""
        health_status = {
            "router_healthy": True,
            "total_agents": len(self.agents),
            "agent_health": {},
            "fallback_agent": self.fallback_agent.name if self.fallback_agent else None
        }
        
        for agent in self.agents:
            try:
                is_healthy = await agent.health_check()
                health_status["agent_health"][agent.name] = is_healthy
                if not is_healthy:
                    health_status["router_healthy"] = False
            except Exception as e:
                logger.error(f"Health check failed for {agent.name}: {e}")
                health_status["agent_health"][agent.name] = False
                health_status["router_healthy"] = False
        
        return health_status
    
    def get_routing_stats(self) -> Dict[str, Any]:
        """Get routing statistics."""
        return {
            **self.routing_stats,
            "agent_health_status": {
                agent.name: "healthy" for agent in self.agents
            }
        }
    
    def reset_stats(self):
        """Reset routing statistics."""
        self.routing_stats = {
            "total_routed": 0,
            "agent_usage": {agent.name: 0 for agent in self.agents},
            "escalation_rate": 0.0
        }