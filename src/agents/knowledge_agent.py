"""Knowledge agent for retrieving and processing documentation."""

import logging
from datetime import datetime
from typing import List, Tuple

from src.agents.base_agent import BaseAgent
from src.models.schemas import SupportMessage, AgentResponse, KnowledgeEntry
from src.integrations.ollama_client import ollama_client
from src.integrations.memory_vector_store import memory_vector_store


logger = logging.getLogger(__name__)


class KnowledgeAgent(BaseAgent):
    """Agent responsible for knowledge retrieval and response generation."""
    
    def __init__(self):
        super().__init__(name="knowledge_agent")
        self.max_context_docs = 5
        self.min_relevance_score = 0.4
    
    async def process_message(self, message: SupportMessage) -> AgentResponse:
        """Process message by retrieving relevant knowledge and generating response."""
        try:
            # Search for relevant knowledge entries
            relevant_entries = await self._search_knowledge(message)
            
            if not relevant_entries:
                return self._handle_no_knowledge_found(message)
            
            # Generate response based on retrieved knowledge
            response_data = await self._generate_knowledge_response(message, relevant_entries)
            
            # Update usage statistics for used documents
            await self._update_knowledge_usage(relevant_entries, response_data.get("was_helpful", True))
            
            # Prepare sources list
            sources = self._format_sources(relevant_entries)
            
            # Determine if escalation is needed
            confidence_score = response_data.get("confidence", 0.5)
            should_escalate = (
                response_data.get("requires_escalation", False) or 
                self.should_escalate(confidence_score, message)
            )
            
            escalation_reason = None
            if should_escalate:
                escalation_reason = "Low confidence in knowledge base match or complex query requiring human expertise"
            
            response = self.format_response(
                response_text=response_data.get("response", "I couldn't find a specific answer to your question."),
                confidence_score=confidence_score,
                sources=sources,
                should_escalate=should_escalate,
                escalation_reason=escalation_reason,
                metadata={
                    "documents_used": len(relevant_entries),
                    "relevance_scores": [score for _, score in relevant_entries],
                    "sources_used": response_data.get("sources_used", [])
                }
            )
            
            self.log_processing(message, response)
            return response
            
        except Exception as e:
            logger.error(f"Error in knowledge agent processing: {e}")
            return self._handle_processing_error(message, str(e))
    
    async def _search_knowledge(self, message: SupportMessage) -> List[Tuple[KnowledgeEntry, float]]:
        """Search for relevant knowledge entries."""
        try:
            # Search with category filter if available
            category_filter = message.category if message.category else None
            
            results = await memory_vector_store.search_knowledge(
                query=message.content,
                top_k=self.max_context_docs,
                category_filter=category_filter,
                min_score=self.min_relevance_score
            )
            
            logger.info(f"Found {len(results)} relevant knowledge entries")
            return results
            
        except Exception as e:
            logger.error(f"Error searching knowledge: {e}")
            return []
    
    async def _generate_knowledge_response(
        self, 
        message: SupportMessage, 
        relevant_entries: List[Tuple[KnowledgeEntry, float]]
    ) -> dict:
        """Generate response based on retrieved knowledge."""
        try:
            # Extract document contents
            context_documents = []
            for entry, score in relevant_entries:
                context = f"Title: {entry.title}\n"
                context += f"Content: {entry.content}\n"
                context += f"Category: {entry.category.value}\n"
                context += f"Tags: {', '.join(entry.tags)}\n"
                if entry.source_url:
                    context += f"Source: {entry.source_url}\n"
                context_documents.append(context)
            
            # Generate response using Ollama
            response_data = await ollama_client.generate_knowledge_response(
                query=message.content,
                context_documents=context_documents,
                max_tokens=500
            )
            
            return response_data
            
        except Exception as e:
            logger.error(f"Error generating knowledge response: {e}")
            return {
                "response": "I'm having trouble processing your request right now. Let me get a human to help you.",
                "confidence": 0.0,
                "sources_used": [],
                "requires_escalation": True
            }
    
    async def _update_knowledge_usage(
        self, 
        entries: List[Tuple[KnowledgeEntry, float]], 
        was_helpful: bool = True
    ):
        """Update usage statistics for knowledge entries."""
        try:
            for entry, _ in entries:
                await memory_vector_store.update_usage_stats(entry.doc_id, was_helpful)
        except Exception as e:
            logger.error(f"Error updating knowledge usage stats: {e}")
    
    def _format_sources(self, entries: List[Tuple[KnowledgeEntry, float]]) -> List[str]:
        """Format sources for display."""
        sources = []
        for entry, score in entries:
            source_text = f"{entry.title}"
            if entry.source_url:
                source_text += f" ({entry.source_url})"
            sources.append(source_text)
        return sources
    
    def _handle_no_knowledge_found(self, message: SupportMessage) -> AgentResponse:
        """Handle case when no relevant knowledge is found."""
        response_text = (
            "I couldn't find specific information about your question in our knowledge base. "
            "Let me connect you with a human agent who can better assist you."
        )
        
        return self.format_response(
            response_text=response_text,
            confidence_score=0.0,
            should_escalate=True,
            escalation_reason="No relevant knowledge found in database",
            metadata={"documents_found": 0}
        )
    
    def _handle_processing_error(self, message: SupportMessage, error: str) -> AgentResponse:
        """Handle processing errors gracefully."""
        response_text = (
            "I'm experiencing some technical difficulties right now. "
            "Let me get a human agent to help you immediately."
        )
        
        return self.format_response(
            response_text=response_text,
            confidence_score=0.0,
            should_escalate=True,
            escalation_reason=f"Knowledge agent processing error: {error}",
            metadata={"error": error}
        )
    
    async def add_knowledge_from_resolution(
        self, 
        message: SupportMessage, 
        resolution: str,
        human_agent: str
    ) -> bool:
        """Add new knowledge entry from a resolved support case."""
        try:
            # Create new knowledge entry
            entry = KnowledgeEntry(
                doc_id=f"resolution_{message.message_id}",
                title=f"Resolution for: {message.content[:50]}...",
                content=f"Question: {message.content}\n\nResolution: {resolution}",
                category=message.category,
                last_updated=datetime.now(),
                tags=[f"resolved_by_{human_agent}", message.category.value],
                source_url=None
            )
            
            # Add to vector store
            success = await memory_vector_store.add_knowledge_entry(entry)
            
            if success:
                logger.info(f"Added new knowledge entry from resolution: {entry.doc_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error adding knowledge from resolution: {e}")
            return False
    
    async def health_check(self) -> bool:
        """Check if knowledge agent dependencies are healthy."""
        try:
            # Test Ollama and vector store connections
            ollama_healthy = await ollama_client.health_check()
            vector_healthy = await memory_vector_store.health_check()
            
            return ollama_healthy and vector_healthy
            
        except Exception as e:
            logger.error(f"Knowledge agent health check failed: {e}")
            return False