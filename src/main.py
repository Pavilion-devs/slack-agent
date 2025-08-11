"""Main application entry point for the Slack Support AI Agent."""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

from src.core.config import settings
from src.integrations.slack_client import slack_client
from src.core.rag_system import rag_system
# NOTE: Import workflow and multi-agent system lazily to avoid circular imports
from src.models.schemas import SupportMessage

# Global responder setup (initialized during startup)
responder_setup_global = None

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/app.log', mode='a') if settings.environment == 'production' else logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    logger.info("Starting up Slack Support AI Agent...")
    
    # Health checks on startup
    try:
        # Initialize new LangGraph workflow system (replaces old multi-agent system)
        from src.workflows.delve_langgraph_workflow import delve_langgraph_workflow
        workflow_healthy = await delve_langgraph_workflow.health_check()
        if not workflow_healthy:
            logger.warning("LangGraph workflow health check failed - will attempt initialization on first request")
        
        # Initialize bidirectional responder system for escalations
        try:
            from src.setup_responder_system import ResponderSystemSetup
            global responder_setup_global
            responder_setup_global = ResponderSystemSetup()
            success = await responder_setup_global.initialize_system()
            responder_agent = responder_setup_global.responder_agent if success else None
            
            if responder_agent:
                # Connect responder agent to workflow for handling escalations
                delve_langgraph_workflow.set_responder_agent(responder_agent)
                logger.info("Responder system initialized and connected to LangGraph workflow")
            else:
                logger.warning("Responder system initialization failed - falling back to legacy escalations")
        except Exception as responder_error:
            logger.warning(f"Could not initialize responder system: {responder_error} - using legacy escalations")
            responder_setup_global = None
        
        logger.info("Application startup completed (using LangGraph workflow)")
        
    except Exception as e:
        logger.error(f"Error during startup: {e}")
    
    yield
    
    # Cleanup
    logger.info("Shutting down Slack Support AI Agent...")


# Create FastAPI app
app = FastAPI(
    title="Delve Slack Support AI Agent",
    description="Intelligent AI agent for automating Slack support",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    """Root endpoint for health checks."""
    return {"message": "Delve Slack Support AI Agent is running", "status": "healthy"}


@app.get("/health")
async def health_check():
    """Comprehensive health check endpoint."""
    try:
        # Check new LangGraph workflow system
        from src.workflows.delve_langgraph_workflow import delve_langgraph_workflow
        
        workflow_healthy = await delve_langgraph_workflow.health_check()
        
        health_status = {
            "status": "healthy" if workflow_healthy else "degraded",
            "components": {
                "langgraph_workflow": "healthy" if workflow_healthy else "unhealthy"
            },
            "workflow_type": "langgraph",
            "timestamp": datetime.now().isoformat()
        }
        
        status_code = 200 if health_status["status"] == "healthy" else 503
        return JSONResponse(content=health_status, status_code=status_code)
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return JSONResponse(
            content={"status": "unhealthy", "error": str(e)},
            status_code=503
        )


@app.post("/slack/events")
async def slack_events(request: Request):
    """Handle Slack events webhook."""
    try:
        body = await request.json()
        
        # Handle Slack URL verification
        if body.get("type") == "url_verification":
            return {"challenge": body.get("challenge")}
        
        # Handle message events
        if body.get("type") == "event_callback":
            event = body.get("event", {})
            
            if event.get("type") == "message" and not event.get("bot_id"):
                # Create support message
                support_message = SupportMessage(
                    message_id=event["ts"],
                    channel_id=event["channel"],
                    user_id=event["user"],
                    timestamp=datetime.fromtimestamp(float(event["ts"])),
                    content=event["text"],
                    thread_ts=event.get("thread_ts")
                )
                
                # Process asynchronously
                asyncio.create_task(process_support_message(support_message))
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Error handling Slack event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/slack/interactive")
async def slack_interactive(request: Request):
    """Handle Slack interactive button clicks."""
    try:
        # Use the global responder system initialized during startup
        global responder_setup_global
        
        if not responder_setup_global or not responder_setup_global.thread_manager:
            logger.error("Responder system not available for interactive requests")
            return {"status": "error", "message": "Responder system not available"}
        
        # Parse the Slack payload
        form_data = await request.form()
        payload_str = form_data.get("payload")
        
        if not payload_str:
            raise HTTPException(status_code=400, detail="No payload found")
        
        # Parse JSON payload
        import json
        payload = json.loads(payload_str)
        
        logger.info(f"Received interactive payload: {payload}")
        
        # Respond immediately to satisfy Slack's 3s requirement, then process in background
        async def noop_ack():
            return None

        async def process_interaction():
            try:
                if payload.get("type") != "block_actions":
                    logger.warning(f"Unsupported interactive payload type: {payload.get('type')}")
                    return

                action = payload["actions"][0]
                action_id = action["action_id"]

                # Backward-compatibility mapping for legacy buttons
                # take_ownership -> accept_ticket, view_context -> view_history
                mapped_action_id = {
                    "take_ownership": "accept_ticket",
                    "view_context": "view_history",
                }.get(action_id, action_id)

                logger.info(f"Processing action: {action_id} (mapped: {mapped_action_id})")

                tm = responder_setup_global.thread_manager

                if mapped_action_id == "accept_ticket":
                    await tm.handle_accept_ticket(noop_ack, payload, tm.slack)
                elif mapped_action_id == "view_history":
                    await tm.handle_view_history(noop_ack, payload, tm.slack)
                elif mapped_action_id == "close_ticket":
                    await tm.handle_close_ticket(noop_ack, payload, tm.slack)
                else:
                    logger.warning(f"Unknown action_id: {action_id}")
            except Exception as e:
                logger.error(f"Interactive processing error: {e}")

        # Kick off async processing
        asyncio.create_task(process_interaction())

        # Immediate OK to Slack
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Error handling Slack interactive request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def process_support_message(message: SupportMessage):
    """Process support message through the workflow."""
    try:
        logger.info(f"Processing support message: {message.message_id}")
        
        # Use new LangGraph workflow system
        from src.workflows.delve_langgraph_workflow import delve_langgraph_workflow
        
        # Run through LangGraph workflow
        final_state = await delve_langgraph_workflow.process_message(message)
        
        # Log results
        logger.info(
            f"Message {message.message_id} processed successfully. "
            f"Escalated: {final_state.escalated}, "
            f"Agents used: {len(final_state.agent_responses)}"
        )
        
    except Exception as e:
        logger.error(f"Error processing support message {message.message_id}: {e}")
        
        # Send fallback response
        try:
            await slack_client.send_response(
                message,
                "I'm experiencing technical difficulties. Please try again or contact our support team directly."
            )
        except Exception as fallback_error:
            logger.error(f"Fallback response also failed: {fallback_error}")


@app.post("/test/message")
async def test_message(request: Request):
    """Test endpoint for processing messages without Slack."""
    try:
        data = await request.json()
        
        # Create test support message
        test_message = SupportMessage(
            message_id=f"test_{datetime.now().timestamp()}",
            channel_id="test_channel",
            user_id="test_user",
            timestamp=datetime.now(),
            content=data.get("message", "Test message"),
            thread_ts=None
        )
        
        # Use new LangGraph workflow system
        from src.workflows.delve_langgraph_workflow import delve_langgraph_workflow
        
        # Process through LangGraph workflow
        final_state = await delve_langgraph_workflow.process_message(test_message)
        
        # Return results
        return {
            "message_id": test_message.message_id,
            "final_response": final_state.final_response,
            "escalated": final_state.escalated,
            "agents_used": [r.agent_name for r in final_state.agent_responses],
            "confidence_scores": [r.confidence_score for r in final_state.agent_responses],
            "processing_time": (
                final_state.processing_completed - final_state.processing_started
            ).total_seconds() if final_state.processing_completed else None
        }
        
    except Exception as e:
        logger.error(f"Error in test endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_stats():
    """Get system statistics."""
    try:
        # Get stats from new LangGraph workflow system
        from src.workflows.delve_langgraph_workflow import delve_langgraph_workflow
        from src.workflows.langgraph_workflow import langgraph_workflow
        
        workflow_stats = delve_langgraph_workflow.get_stats()
        langgraph_health = await langgraph_workflow.health_check()
        
        return {
            "workflow": workflow_stats,
            "langgraph_health": langgraph_health,
            "system_type": "langgraph_based",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return {"error": str(e)}


if __name__ == "__main__":
    # Create logs directory if it doesn't exist
    import os
    os.makedirs("logs", exist_ok=True)
    
    # Run the application
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.environment == "development",
        log_level=settings.log_level.lower()
    )