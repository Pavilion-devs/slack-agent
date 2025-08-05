"""Multi-Agent System Manager that orchestrates all specialized agents."""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.agents.base_agent import BaseAgent
from src.agents.agent_router import AgentRouter
from src.agents.demo_scheduler import DemoSchedulerAgent
from src.agents.technical_support import TechnicalSupportAgent
from src.agents.escalation_agent import EscalationAgent
from src.agents.enhanced_rag_agent import EnhancedRAGAgent
from src.models.schemas import SupportMessage, AgentResponse
from src.core.config import settings

logger = logging.getLogger(__name__)


class MultiAgentSystem:
    """Orchestrates multiple specialized agents to handle support requests."""
    
    def __init__(self):
        self.router = AgentRouter()
        self.agents = {}
        self.escalation_agent = None
        self.system_initialized = False
        self.performance_stats = {
            "total_processed": 0,
            "total_escalated": 0,
            "average_response_time": 0.0,
            "agent_performance": {}
        }
    
    async def initialize(self) -> bool:
        """Initialize all agents and the routing system."""
        if self.system_initialized:
            return True
            
        try:
            logger.info("Initializing Multi-Agent System...")
            
            # Create and initialize specialized agents
            demo_agent = DemoSchedulerAgent()
            technical_agent = TechnicalSupportAgent()
            rag_agent = EnhancedRAGAgent()
            escalation_agent = EscalationAgent()
            
            # Initialize RAG agent (requires async initialization)
            logger.info("Initializing RAG agent...")
            try:
                rag_initialized = await rag_agent.initialize()
                if not rag_initialized:
                    logger.error("Failed to initialize RAG agent - returned False")
                    return False
                logger.info("RAG agent initialized successfully")
            except Exception as e:
                logger.error(f"Exception during RAG agent initialization: {e}")
                return False
            
            # Register agents with router
            self.router.register_agent(demo_agent)
            self.router.register_agent(technical_agent)
            self.router.register_agent(rag_agent, is_fallback=True)  # RAG as fallback
            
            # Store agents for direct access
            self.agents = {
                "demo_scheduler": demo_agent,
                "technical_support": technical_agent,
                "enhanced_rag": rag_agent,
                "escalation": escalation_agent
            }
            
            self.escalation_agent = escalation_agent
            
            # Verify individual agents are healthy (not full system health check)
            logger.info("Running individual agent health checks...")
            all_agents_healthy = True
            
            for name, agent in self.agents.items():
                try:
                    agent_healthy = await agent.health_check()
                    if not agent_healthy:
                        logger.error(f"Agent {name} failed health check")
                        all_agents_healthy = False
                    else:
                        logger.info(f"Agent {name} passed health check")
                except Exception as e:
                    logger.error(f"Agent {name} health check failed with exception: {e}")
                    all_agents_healthy = False
            
            # Check router health
            try:
                router_health = await self.router.health_check()
                if not router_health.get("router_healthy", False):
                    logger.error("Router health check failed")
                    all_agents_healthy = False
                else:
                    logger.info("Router passed health check")
            except Exception as e:
                logger.error(f"Router health check failed with exception: {e}")
                all_agents_healthy = False
            
            if not all_agents_healthy:
                logger.error("Some agents failed health checks")
                return False
            
            logger.info("All agents and router passed health checks")
            
            self.system_initialized = True
            logger.info("Multi-Agent System initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Multi-Agent System: {e}")
            return False
    
    async def process_message(self, message: SupportMessage) -> AgentResponse:
        """Process a support message through the multi-agent system."""
        start_time = datetime.now()
        
        # Ensure system is initialized
        if not await self.initialize():
            return self._create_system_error_response(message)
        
        try:
            logger.info(f"Processing message {message.message_id} through multi-agent system")
            
            # Route message to appropriate agent
            response = await self.router.route_message(message)
            
            # Handle escalation if needed
            if response.should_escalate:
                logger.info(f"Escalating message {message.message_id}: {response.escalation_reason}")
                escalation_response = await self.escalation_agent.process_escalation(
                    message, response, response.escalation_reason
                )
                
                # Combine original response with escalation
                combined_response = self._combine_responses(response, escalation_response)
                response = combined_response
            
            # Update performance statistics
            processing_time = (datetime.now() - start_time).total_seconds()
            self._update_performance_stats(response, processing_time)
            
            logger.info(
                f"Message {message.message_id} processed by {response.agent_name} "
                f"in {processing_time:.2f}s with confidence {response.confidence_score:.2f}"
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing message {message.message_id}: {e}")
            return self._create_system_error_response(message, str(e))
    
    def _combine_responses(self, original: AgentResponse, escalation: AgentResponse) -> AgentResponse:
        """Combine original agent response with escalation response."""
        # Use escalation response as primary, but include original metadata
        combined_metadata = {
            **original.metadata,
            **escalation.metadata,
            "original_agent": original.agent_name,
            "original_confidence": original.confidence_score,
            "escalated_by": "multi_agent_system"
        }
        
        return AgentResponse(
            agent_name=f"{original.agent_name} + escalation",
            response_text=escalation.response_text,
            confidence_score=escalation.confidence_score,
            sources=original.sources + escalation.sources,
            should_escalate=True,  # Preserve escalation status for monitoring
            escalation_reason=original.escalation_reason,  # Preserve original reason
            metadata=combined_metadata
        )
    
    def _create_system_error_response(self, message: SupportMessage, error: str = None) -> AgentResponse:
        """Create error response when system fails."""
        error_text = (
            "I'm experiencing technical difficulties with our AI system. "
            "Let me immediately connect you with our support team for assistance."
        )
        
        if error:
            logger.error(f"System error for message {message.message_id}: {error}")
        
        return AgentResponse(
            agent_name="multi_agent_system",
            response_text=error_text,
            confidence_score=0.0,
            sources=[],
            should_escalate=True,
            escalation_reason=f"Multi-agent system error: {error}" if error else "System initialization failed",
            metadata={"system_error": True, "error_details": error}
        )
    
    def _update_performance_stats(self, response: AgentResponse, processing_time: float):
        """Update system performance statistics."""
        self.performance_stats["total_processed"] += 1
        
        if response.should_escalate:
            self.performance_stats["total_escalated"] += 1
        
        # Update average response time (exponential moving average)
        current_avg = self.performance_stats["average_response_time"]
        self.performance_stats["average_response_time"] = (
            current_avg * 0.9 + processing_time * 0.1
        )
        
        # Update agent-specific performance
        agent_name = response.agent_name.split(" + ")[0]  # Remove escalation suffix
        if agent_name not in self.performance_stats["agent_performance"]:
            self.performance_stats["agent_performance"][agent_name] = {
                "total_processed": 0,
                "total_escalated": 0,
                "average_confidence": 0.0,
                "average_response_time": 0.0
            }
        
        agent_stats = self.performance_stats["agent_performance"][agent_name]
        agent_stats["total_processed"] += 1
        
        if response.should_escalate:
            agent_stats["total_escalated"] += 1
        
        # Update agent average confidence
        current_conf = agent_stats["average_confidence"]
        agent_stats["average_confidence"] = (
            current_conf * 0.9 + response.confidence_score * 0.1
        )
        
        # Update agent average response time
        current_time = agent_stats["average_response_time"]
        agent_stats["average_response_time"] = (
            current_time * 0.9 + processing_time * 0.1
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of all agents and the routing system."""
        if not self.system_initialized:
            return {
                "system_healthy": False,
                "error": "System not initialized"
            }
        
        try:
            # Check router health
            router_health = await self.router.health_check()
            
            # Check individual agent health
            agent_health = {}
            for name, agent in self.agents.items():
                try:
                    agent_health[name] = await agent.health_check()
                except Exception as e:
                    logger.error(f"Health check failed for {name}: {e}")
                    agent_health[name] = False
            
            system_healthy = (
                router_health["router_healthy"] and
                all(agent_health.values())
            )
            
            return {
                "system_healthy": system_healthy,
                "router_health": router_health,
                "agent_health": agent_health,
                "performance_stats": self.performance_stats,
                "agents_registered": len(self.agents),
                "system_initialized": self.system_initialized
            }
            
        except Exception as e:
            logger.error(f"System health check failed: {e}")
            return {
                "system_healthy": False,
                "error": str(e)
            }
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics."""
        escalation_rate = 0.0
        if self.performance_stats["total_processed"] > 0:
            escalation_rate = (
                self.performance_stats["total_escalated"] / 
                self.performance_stats["total_processed"]
            )
        
        return {
            **self.performance_stats,
            "escalation_rate": escalation_rate,
            "router_stats": self.router.get_routing_stats(),
            "agents_active": len(self.agents),
            "system_uptime": "N/A",  # Would track actual uptime
            "target_response_time": 30.0,  # seconds
            "target_escalation_rate": 0.3  # 30%
        }
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get information about all registered agents."""
        agent_info = {}
        
        for name, agent in self.agents.items():
            agent_info[name] = {
                "name": agent.name,
                "type": type(agent).__name__,
                "confidence_threshold": agent.confidence_threshold,
                "specialties": getattr(agent, 'specialties', []),
                "last_health_check": "healthy"  # Would track actual health
            }
        
        return {
            "agents": agent_info,
            "total_agents": len(self.agents),
            "routing_enabled": True,
            "escalation_enabled": self.escalation_agent is not None
        }
    
    async def reset_system(self):
        """Reset the system (for testing or recovery)."""
        logger.info("Resetting Multi-Agent System...")
        
        self.system_initialized = False
        self.agents.clear()
        self.router.reset_stats()
        self.performance_stats = {
            "total_processed": 0,
            "total_escalated": 0,
            "average_response_time": 0.0,
            "agent_performance": {}
        }
        
        # Re-initialize
        await self.initialize()


# Global instance for the application
multi_agent_system = MultiAgentSystem()