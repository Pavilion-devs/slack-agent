"""
Setup script for the bidirectional Slack responder agent system.

This script initializes all components and connects them together:
- Supabase session manager
- Slack thread manager  
- Responder agent
- LangGraph workflow integration
"""

import os
import asyncio
import logging
from typing import Optional
from dotenv import load_dotenv

from slack_sdk.web.async_client import AsyncWebClient
from slack_bolt.async_app import AsyncApp

from src.core.session_manager import SessionManager
from src.integrations.slack_thread_manager import SlackThreadManager
from src.agents.responder_agent import ResponderAgent, ResponderConfig
from src.workflows.langgraph_workflow import LangGraphWorkflow

logger = logging.getLogger(__name__)


class ResponderSystemSetup:
    """Setup and initialization for the complete responder system."""
    
    def __init__(self):
        """Initialize setup with environment configuration."""
        load_dotenv()
        
        # Required environment variables
        self.supabase_url = os.getenv("SUPABASE_URL", "https://rnoovneiewigakqmruyo.supabase.co")
        self.supabase_key = os.getenv("SUPABASE_KEY", "sb_publishable_87rTsrEwY4vfK9knFAevqw_Nje4xWmU") 
        self.slack_bot_token = os.getenv("SLACK_BOT_TOKEN")
        self.slack_signing_secret = os.getenv("SLACK_SIGNING_SECRET")
        self.escalation_channel = os.getenv("ESCALATION_CHANNEL", "support-escalations")
        
        # System components
        self.session_manager: Optional[SessionManager] = None
        self.thread_manager: Optional[SlackThreadManager] = None
        self.responder_agent: Optional[ResponderAgent] = None
        self.slack_app: Optional[AsyncApp] = None
        self.workflow: Optional[LangGraphWorkflow] = None
        
        logger.info("ResponderSystemSetup initialized")
    
    async def initialize_system(self) -> bool:
        """Initialize all system components and connect them."""
        try:
            logger.info("🚀 Initializing bidirectional Slack responder system...")
            
            # 1. Validate environment
            if not self._validate_environment():
                return False
            
            # 2. Initialize session manager
            await self._setup_session_manager()
            
            # 3. Initialize Slack components
            await self._setup_slack_components()
            
            # 4. Initialize responder agent
            await self._setup_responder_agent()
            
            # 5. Connect to LangGraph workflow
            await self._setup_workflow_integration()
            
            # 6. Setup platform handlers
            await self._setup_platform_handlers()
            
            # 7. Register Slack event handlers
            await self._setup_slack_handlers()
            
            logger.info("✅ Responder system initialized successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize responder system: {e}")
            return False
    
    def _validate_environment(self) -> bool:
        """Validate required environment variables."""
        required_vars = {
            'SLACK_BOT_TOKEN': self.slack_bot_token,
            'SLACK_SIGNING_SECRET': self.slack_signing_secret
        }
        
        missing_vars = [name for name, value in required_vars.items() if not value]
        
        if missing_vars:
            logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
            return False
        
        logger.info("Environment validation passed")
        return True
    
    async def _setup_session_manager(self):
        """Initialize the Supabase session manager."""
        logger.info("Setting up session manager...")
        
        self.session_manager = SessionManager(
            supabase_url=self.supabase_url,
            supabase_key=self.supabase_key
        )
        
        # Test connection
        stats = await self.session_manager.get_session_stats()
        logger.info(f"Session manager connected. Current stats: {stats}")
    
    async def _setup_slack_components(self):
        """Initialize Slack client and thread manager."""
        logger.info("Setting up Slack components...")
        
        # Initialize Slack client
        slack_client = AsyncWebClient(token=self.slack_bot_token)
        
        # Test Slack connection
        auth_response = await slack_client.auth_test()
        if not auth_response["ok"]:
            raise Exception(f"Slack auth failed: {auth_response.get('error')}")
        
        logger.info(f"Slack connected as: {auth_response['user']}")
        
        # Initialize thread manager
        self.thread_manager = SlackThreadManager(
            slack_client=slack_client,
            session_manager=self.session_manager,
            escalation_channel=self.escalation_channel
        )
        
        # Initialize Slack Bolt app for interactive components
        self.slack_app = AsyncApp(
            token=self.slack_bot_token,
            signing_secret=self.slack_signing_secret
        )
    
    async def _setup_responder_agent(self):
        """Initialize the responder agent."""
        logger.info("Setting up responder agent...")
        
        config = ResponderConfig(
            escalation_channel=self.escalation_channel,
            auto_escalate_timeout=300,  # 5 minutes
            max_history_context=10,
            enable_smart_routing=True
        )
        
        self.responder_agent = ResponderAgent(
            session_manager=self.session_manager,
            thread_manager=self.thread_manager,
            config=config
        )
        
        logger.info("Responder agent initialized")
    
    async def _setup_workflow_integration(self):
        """Connect responder agent to LangGraph workflow."""
        logger.info("Setting up workflow integration...")
        
        # Get the existing workflow instance (assuming it's a singleton)
        from src.workflows.langgraph_workflow import langgraph_workflow
        self.workflow = langgraph_workflow
        
        # Connect responder agent
        self.workflow.set_responder_agent(self.responder_agent)
        
        logger.info("Workflow integration completed")
    
    async def _setup_platform_handlers(self):
        """Setup message handlers for different platforms."""
        logger.info("Setting up platform handlers...")
        
        # Chainlit handler
        async def chainlit_handler(user_id: str, message: str, session_id: str):
            """Forward message to Chainlit user."""
            # This would integrate with Chainlit's message system
            # For now, we'll log it
            logger.info(f"[Chainlit] Message for user {user_id}: {message}")
            
            # In a real implementation, this would:
            # 1. Find the active Chainlit session for the user
            # 2. Send the message through Chainlit's WebSocket connection
            # 3. Update the conversation UI
        
        # Website handler
        async def website_handler(user_id: str, message: str, session_id: str):
            """Forward message to website user."""
            logger.info(f"[Website] Message for user {user_id}: {message}")
            
            # In a real implementation, this would:
            # 1. Use WebSocket or Server-Sent Events
            # 2. Push the message to the user's browser
            # 3. Update the chat interface
        
        # Register platform handlers
        self.responder_agent.register_platform_handler("Chainlit", chainlit_handler)
        self.responder_agent.register_platform_handler("Website", website_handler)
        
        logger.info("Platform handlers registered")
    
    async def _setup_slack_handlers(self):
        """Setup Slack Bolt app event handlers."""
        logger.info("Setting up Slack event handlers...")
        
        # Accept ticket button handler
        @self.slack_app.action("accept_ticket")
        async def handle_accept_ticket(ack, body, client):
            await self.thread_manager.handle_accept_ticket(ack, body, client)
        
        # View history button handler
        @self.slack_app.action("view_history")
        async def handle_view_history(ack, body, client):
            await self.thread_manager.handle_view_history(ack, body, client)
        
        # Close ticket button handler
        @self.slack_app.action("close_ticket")
        async def handle_close_ticket(ack, body, client):
            await self.thread_manager.handle_close_ticket(ack, body, client)
        
        # Message handler for thread replies
        @self.slack_app.message(f"#{self.escalation_channel}")
        async def handle_thread_message(message, say, client):
            # Only process messages in threads
            if message.get("thread_ts"):
                await self.thread_manager.process_thread_reply(
                    channel=message["channel"],
                    thread_ts=message["thread_ts"],
                    message_text=message["text"],
                    user_id=message["user"],
                    user_name=await self._get_user_name(client, message["user"]),
                    user_message_callback=self.responder_agent._forward_to_user
                )
        
        logger.info("Slack event handlers registered")
    
    async def _get_user_name(self, client, user_id: str) -> str:
        """Get Slack user's display name."""
        try:
            user_info = await client.users_info(user=user_id)
            if user_info["ok"]:
                user = user_info["user"]
                return user.get("display_name") or user.get("real_name") or user.get("name", "Unknown")
        except Exception as e:
            logger.warning(f"Failed to get user name for {user_id}: {e}")
        
        return "Unknown User"
    
    async def start_slack_app(self):
        """Start the Slack Bolt app."""
        if not self.slack_app:
            raise Exception("Slack app not initialized")
        
        logger.info("🚀 Starting Slack app...")
        await self.slack_app.async_start(port=int(os.getenv("SLACK_APP_PORT", 3000)))
    
    async def health_check(self) -> dict:
        """Perform system health check."""
        logger.info("Performing system health check...")
        
        health = {
            'session_manager': False,
            'thread_manager': False,
            'responder_agent': False,
            'workflow_integration': False,
            'slack_connection': False
        }
        
        try:
            # Session manager health
            if self.session_manager:
                stats = await self.session_manager.get_session_stats()
                health['session_manager'] = True
            
            # Thread manager health
            if self.thread_manager:
                await self.thread_manager.slack.auth_test()
                health['thread_manager'] = True
            
            # Responder agent health
            if self.responder_agent:
                agent_health = await self.responder_agent.health_check()
                health['responder_agent'] = all(agent_health.values())
            
            # Workflow integration
            health['workflow_integration'] = (
                self.workflow is not None and 
                self.workflow.responder_agent is not None
            )
            
            # Slack connection
            if self.slack_app:
                health['slack_connection'] = True
            
        except Exception as e:
            logger.error(f"Health check error: {e}")
        
        logger.info(f"Health check results: {health}")
        return health
    
    async def get_system_stats(self) -> dict:
        """Get comprehensive system statistics."""
        stats = {
            'responder_system': {},
            'sessions': {},
            'escalations': {}
        }
        
        if self.responder_agent:
            stats['responder_system'] = await self.responder_agent.get_responder_stats()
        
        if self.session_manager:
            stats['sessions'] = await self.session_manager.get_session_stats()
        
        if self.thread_manager:
            stats['escalations'] = await self.thread_manager.get_escalation_stats()
        
        return stats


# Global instance
responder_setup = ResponderSystemSetup()


async def initialize_responder_system() -> bool:
    """Initialize the complete responder system."""
    return await responder_setup.initialize_system()


async def start_responder_system():
    """Start the responder system (including Slack app)."""
    success = await initialize_responder_system()
    if not success:
        raise Exception("Failed to initialize responder system")
    
    # Start Slack app
    await responder_setup.start_slack_app()


if __name__ == "__main__":
    # For testing/development
    async def main():
        print("🧪 Testing responder system setup...")
        
        # Initialize system
        success = await initialize_responder_system()
        if success:
            print("✅ System initialization successful!")
            
            # Run health check
            health = await responder_setup.health_check()
            print(f"🏥 Health check: {health}")
            
            # Get stats
            stats = await responder_setup.get_system_stats()
            print(f"📊 System stats: {stats}")
            
        else:
            print("❌ System initialization failed!")
    
    asyncio.run(main())