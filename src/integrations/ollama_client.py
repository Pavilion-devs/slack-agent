"""Ollama integration for embeddings and chat completions."""

import logging
from typing import List, Dict, Any, Optional
import asyncio

import ollama
from langchain_ollama import OllamaEmbeddings, OllamaLLM

from src.core.config import settings


logger = logging.getLogger(__name__)


class OllamaClient:
    """Client for interacting with Ollama for embeddings and completions."""
    
    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.embedding_model = "llama3.2:3b"  # Using the same model for embeddings
        self.chat_model = "llama3.2:3b"
        
        # Initialize LangChain components
        self.embeddings = OllamaEmbeddings(
            base_url=self.base_url,
            model=self.embedding_model
        )
        
        self.llm = OllamaLLM(
            base_url=self.base_url,
            model=self.chat_model,
            temperature=0.1  # Low temperature for consistent responses
        )
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        try:
            # Run embedding generation in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None, 
                self.embeddings.embed_documents, 
                texts
            )
            
            logger.info(f"Generated embeddings for {len(texts)} texts")
            return embeddings
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        try:
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None,
                self.embeddings.embed_query,
                text
            )
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise
    
    async def generate_response(
        self, 
        prompt: str, 
        system_message: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None
    ) -> str:
        """Generate a chat completion response."""
        try:
            # Construct the full prompt
            full_prompt = prompt
            if system_message:
                full_prompt = f"System: {system_message}\n\nUser: {prompt}"
            
            # Configure LLM parameters
            llm = OllamaLLM(
                base_url=self.base_url,
                model=self.chat_model,
                temperature=temperature
            )
            
            # Generate response in thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                llm.invoke,
                full_prompt
            )
            
            logger.info(f"Generated response with {len(response)} characters")
            return response
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise
    
    async def analyze_query_intent(self, query: str) -> Dict[str, Any]:
        """Analyze the intent and category of a user query."""
        system_message = """You are an expert at analyzing customer support queries. 
        Analyze the following query and return a JSON response with:
        - category: one of [technical, compliance, billing, demo, general]
        - urgency: one of [low, medium, high, critical]
        - confidence: float between 0.0 and 1.0
        - key_topics: list of key topics/keywords
        - requires_escalation: boolean
        
        Be concise and accurate in your analysis."""
        
        try:
            response = await self.generate_response(
                prompt=f"Analyze this support query: {query}",
                system_message=system_message,
                temperature=0.1
            )
            
            # Parse JSON response (in a real implementation, you might want more robust parsing)
            import json
            try:
                analysis = json.loads(response)
                return analysis
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                return {
                    "category": "general",
                    "urgency": "medium",
                    "confidence": 0.5,
                    "key_topics": [],
                    "requires_escalation": False
                }
            
        except Exception as e:
            logger.error(f"Error analyzing query intent: {e}")
            # Return safe defaults
            return {
                "category": "general",
                "urgency": "medium", 
                "confidence": 0.5,
                "key_topics": [],
                "requires_escalation": False
            }
    
    async def generate_knowledge_response(
        self, 
        query: str, 
        context_documents: List[str],
        max_tokens: int = 500
    ) -> Dict[str, Any]:
        """Generate a response based on query and retrieved context documents."""
        
        # Prepare context
        context = "\n\n".join([f"Document {i+1}: {doc}" for i, doc in enumerate(context_documents)])
        
        system_message = """You are a helpful customer support AI assistant for Delve. 
        Use the provided context documents to answer the user's question accurately and helpfully.
        
        Guidelines:
        - Only use information from the provided context
        - If the context doesn't contain enough information, say so clearly
        - Provide specific, actionable answers when possible
        - Include relevant links or references from the context
        - Be concise but comprehensive
        - If unsure, recommend escalation to human support
        
        Format your response as JSON with:
        - response: the main response text
        - confidence: float between 0.0 and 1.0
        - sources_used: list of document numbers used
        - requires_escalation: boolean
        """
        
        prompt = f"""Context Documents:
{context}

User Question: {query}

Please provide a helpful response based on the context above."""
        
        try:
            response = await self.generate_response(
                prompt=prompt,
                system_message=system_message,
                temperature=0.1
            )
            
            # Parse JSON response
            import json
            try:
                parsed_response = json.loads(response)
                return parsed_response
            except json.JSONDecodeError:
                # Fallback response
                return {
                    "response": response,
                    "confidence": 0.7,
                    "sources_used": list(range(len(context_documents))),
                    "requires_escalation": False
                }
                
        except Exception as e:
            logger.error(f"Error generating knowledge response: {e}")
            return {
                "response": "I apologize, but I'm having trouble processing your request right now. Please try again or contact our support team for assistance.",
                "confidence": 0.0,
                "sources_used": [],
                "requires_escalation": True
            }
    
    async def health_check(self) -> bool:
        """Check if Ollama server is healthy and model is available."""
        try:
            # Try to generate a simple embedding
            test_embedding = await self.generate_embedding("test")
            
            if test_embedding and len(test_embedding) > 0:
                logger.info("Ollama health check passed")
                return True
            else:
                logger.error("Ollama health check failed - empty embedding")
                return False
                
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False


# Global Ollama client instance
ollama_client = OllamaClient()