"""
Advanced RAG system using FAISS and HuggingFace embeddings.
Implements patterns from LangChain notebooks for optimal retrieval performance.
"""

import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

from src.core.document_processor import document_processor


logger = logging.getLogger(__name__)


class DelveRAGSystem:
    """
    Advanced RAG system optimized for Delve compliance knowledge base.
    Uses FAISS for cost-effective local vector storage and HuggingFace embeddings.
    """
    
    def __init__(self, 
                 embeddings_model: str = "sentence-transformers/all-mpnet-base-v2",
                 vector_store_path: str = "data/vector_store"):
        
        self.embeddings_model_name = embeddings_model
        self.vector_store_path = vector_store_path
        self.embeddings = None
        self.vectorstore = None
        self.retriever = None
        self.rag_chain = None
        self.is_initialized = False
        
        # Framework-specific confidence thresholds
        self.confidence_thresholds = {
            'SOC2': 0.75,
            'HIPAA': 0.75,
            'GDPR': 0.75,
            'ISO27001': 0.75,
            'general': 0.65
        }
        
        # Initialize embeddings
        self._initialize_embeddings()
    
    def _initialize_embeddings(self):
        """Initialize HuggingFace embeddings model."""
        try:
            logger.info(f"Initializing embeddings model: {self.embeddings_model_name}")
            self.embeddings = HuggingFaceEmbeddings(
                model_name=self.embeddings_model_name,
                model_kwargs={'device': 'cpu'},  # Use CPU for compatibility
                encode_kwargs={'normalize_embeddings': True}  # Better similarity scores
            )
            logger.info("Embeddings model initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize embeddings: {e}")
            raise
    
    async def initialize_knowledge_base(self, knowledge_file_path: str) -> bool:
        """
        Initialize the knowledge base from the Delve knowledge file.
        
        Args:
            knowledge_file_path: Path to the knowledge_restructured.txt file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info("Initializing knowledge base...")
            
            # Check if vector store already exists
            if self._load_existing_vector_store():
                logger.info("Loaded existing vector store")
                self._setup_retriever_and_chain()
                self.is_initialized = True
                return True
            
            # Process knowledge file
            logger.info(f"Processing knowledge file: {knowledge_file_path}")
            documents = document_processor.process_knowledge_file(knowledge_file_path)
            
            if not documents:
                logger.error("No documents were processed from knowledge file")
                return False
            
            # Create vector store
            logger.info(f"Creating vector store with {len(documents)} documents...")
            self.vectorstore = FAISS.from_documents(documents, self.embeddings)
            
            # Save vector store
            self._save_vector_store()
            
            # Setup retriever and chain
            self._setup_retriever_and_chain()
            
            self.is_initialized = True
            logger.info("Knowledge base initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize knowledge base: {e}")
            return False
    
    def _load_existing_vector_store(self) -> bool:
        """Load existing vector store if available."""
        try:
            if os.path.exists(self.vector_store_path):
                logger.info("Loading existing vector store...")
                self.vectorstore = FAISS.load_local(
                    self.vector_store_path, 
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
                return True
            return False
        except Exception as e:
            logger.warning(f"Could not load existing vector store: {e}")
            return False
    
    def _save_vector_store(self):
        """Save vector store to disk."""
        try:
            os.makedirs(os.path.dirname(self.vector_store_path), exist_ok=True)
            self.vectorstore.save_local(self.vector_store_path)
            logger.info(f"Vector store saved to {self.vector_store_path}")
        except Exception as e:
            logger.error(f"Failed to save vector store: {e}")
    
    def _setup_retriever_and_chain(self):
        """Setup retriever and RAG chain."""
        try:
            # Create retriever with MMR for diversity
            self.retriever = self.vectorstore.as_retriever(
                search_type="mmr",  # Maximum Marginal Relevance for diversity
                search_kwargs={
                    "k": 5,           # Return top 5 results
                    "fetch_k": 20,    # Fetch 20 candidates for MMR
                    "lambda_mult": 0.7  # Balance between relevance and diversity
                }
            )
            
            # Create RAG prompt template
            prompt_template = ChatPromptTemplate.from_messages([
                ("system", """You are Delve's expert compliance AI assistant. Use the provided context to answer questions about compliance automation, SOC2, HIPAA, GDPR, ISO27001, and Delve's services.

INSTRUCTIONS:
1. Base your answers primarily on the provided context
2. Be specific and cite relevant information from the context
3. If the context doesn't contain enough information, say so clearly
4. For compliance questions, provide actionable guidance when possible
5. Mention relevant timelines, pricing, or implementation details when available

CONFIDENCE SCORING:
- Provide a confidence score (0.0-1.0) based on how well the context supports your answer
- High confidence (>0.8): Context directly answers the question with specific details
- Medium confidence (0.6-0.8): Context provides relevant but incomplete information  
- Low confidence (<0.6): Context is tangentially related or insufficient

Context: {context}

Question: {question}

Please provide your answer followed by your confidence score in the format:
CONFIDENCE: [score]"""),
            ])
            
            # Setup RAG chain (will use Ollama when available, fallback to simple retrieval)
            self.rag_chain = (
                {"context": self.retriever, "question": RunnablePassthrough()}
                | prompt_template
                | self._get_llm()
                | StrOutputParser()
            )
            
            logger.info("Retriever and RAG chain setup completed")
            
        except Exception as e:
            logger.error(f"Failed to setup retriever and chain: {e}")
            raise
    
    def _get_llm(self):
        """Get the best available LLM (OpenAI if key available, otherwise Ollama)."""
        # Check for OpenAI API key
        if os.getenv("OPENAI_API_KEY"):
            return ChatOpenAI(
                model="gpt-4o-mini",  # Cost-effective model
                temperature=0,        # Deterministic responses
                max_tokens=1000      # Reasonable response length
            )
        else:
            # Fallback to a simple response generator for now
            # In production, this would use Ollama
            logger.warning("No OpenAI API key found, using fallback LLM")
            return self._create_fallback_llm()
    
    def _create_fallback_llm(self):
        """Create a fallback LLM that uses retrieval without generation."""
        class FallbackLLM:
            def invoke(self, prompt_value):
                # Extract context from prompt
                context = prompt_value.messages[0].content.split("Context: ")[1].split("\n\nQuestion: ")[0]
                question = prompt_value.messages[0].content.split("Question: ")[1].split("\n\n")[0]
                
                return f"Based on the retrieved information: {context[:500]}...\n\nFor a complete answer to '{question}', please ensure OpenAI API key is configured.\n\nCONFIDENCE: 0.5"
        
        return FallbackLLM()
    
    async def query(self, question: str, frameworks: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Query the knowledge base with enhanced retrieval.
        
        Args:
            question: User's question
            frameworks: Optional list of specific frameworks to focus on
            
        Returns:
            Dict containing answer, confidence, sources, and metadata
        """
        if not self.is_initialized:
            return {
                'answer': "Knowledge base not initialized. Please contact support.",
                'confidence': 0.0,
                'sources': [],
                'should_escalate': True,
                'escalation_reason': "Knowledge base initialization failed"
            }
        
        try:
            # Enhanced retrieval with framework filtering
            retrieved_docs = await self._enhanced_retrieve(question, frameworks)
            
            if not retrieved_docs:
                return {
                    'answer': "I couldn't find relevant information for your question. Let me connect you with a human expert.",
                    'confidence': 0.0,
                    'sources': [],
                    'should_escalate': True,
                    'escalation_reason': "No relevant documents retrieved"
                }
            
            # Generate response using RAG chain
            response = await self._generate_response(question, retrieved_docs)
            
            # Extract confidence score
            confidence = self._extract_confidence_score(response)
            
            # Determine if escalation is needed
            should_escalate, escalation_reason = self._should_escalate(
                confidence, question, frameworks, retrieved_docs
            )
            
            # Prepare sources
            sources = self._format_sources(retrieved_docs)
            
            return {
                'answer': response,
                'confidence': confidence,
                'sources': sources,
                'should_escalate': should_escalate,
                'escalation_reason': escalation_reason,
                'retrieved_docs_count': len(retrieved_docs)
            }
            
        except Exception as e:
            logger.error(f"Error during query processing: {e}")
            return {
                'answer': "I'm experiencing technical difficulties. Let me get a human agent to help you.",
                'confidence': 0.0,
                'sources': [],
                'should_escalate': True,
                'escalation_reason': f"Query processing error: {str(e)}"
            }
    
    async def _enhanced_retrieve(self, question: str, frameworks: Optional[List[str]] = None) -> List[Document]:
        """Enhanced retrieval with framework filtering and query expansion."""
        try:
            # Basic retrieval
            docs = self.retriever.invoke(question)
            
            # Filter by frameworks if specified
            if frameworks:
                filtered_docs = []
                for doc in docs:
                    doc_frameworks = doc.metadata.get('frameworks', [])
                    if any(fw in doc_frameworks for fw in frameworks):
                        filtered_docs.append(doc)
                if filtered_docs:
                    docs = filtered_docs
            
            # Sort by confidence weight if available
            docs.sort(key=lambda x: x.metadata.get('confidence_weight', 0.5), reverse=True)
            
            return docs[:5]  # Return top 5
            
        except Exception as e:
            logger.error(f"Error in enhanced retrieval: {e}")
            return []
    
    async def _generate_response(self, question: str, docs: List[Document]) -> str:
        """Generate response using the RAG chain."""
        try:
            # Prepare context from documents
            context = "\n\n".join([doc.page_content for doc in docs])
            
            # Generate response
            response = self.rag_chain.invoke({
                "question": question,
                "context": context
            })
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return f"I found relevant information but encountered an error processing it. Error: {str(e)}"
    
    def _extract_confidence_score(self, response: str) -> float:
        """Extract confidence score from response."""
        try:
            if "CONFIDENCE:" in response:
                confidence_line = response.split("CONFIDENCE:")[1].strip().split()[0]
                return float(confidence_line)
            return 0.6  # Default medium confidence
        except:
            return 0.6
    
    def _should_escalate(self, confidence: float, question: str, 
                        frameworks: Optional[List[str]], docs: List[Document]) -> Tuple[bool, str]:
        """Determine if the query should be escalated."""
        
        # Get threshold based on frameworks
        if frameworks:
            threshold = min(self.confidence_thresholds.get(fw, 0.65) for fw in frameworks)
        else:
            threshold = self.confidence_thresholds['general']
        
        if confidence < threshold:
            return True, f"Low confidence score ({confidence:.2f}) below threshold ({threshold:.2f})"
        
        # Check for urgent keywords
        urgent_keywords = ['urgent', 'asap', 'immediately', 'critical', 'emergency']
        if any(keyword in question.lower() for keyword in urgent_keywords):
            return True, "Urgent request detected"
        
        return False, ""
    
    def _format_sources(self, docs: List[Document]) -> List[Dict[str, Any]]:
        """Format source information from retrieved documents."""
        sources = []
        for doc in docs:
            sources.append({
                'section': doc.metadata.get('section', 'Unknown'),
                'subsection': doc.metadata.get('subsection'),
                'frameworks': doc.metadata.get('frameworks', []),
                'confidence_weight': doc.metadata.get('confidence_weight', 0.5),
                'preview': doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
            })
        return sources
    
    async def health_check(self) -> bool:
        """Check if the RAG system is healthy."""
        try:
            if not self.is_initialized:
                return False
            
            # Test query
            test_result = await self.query("What is Delve?")
            return test_result['confidence'] > 0.0
            
        except Exception as e:
            logger.error(f"RAG system health check failed: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge base."""
        if not self.vectorstore:
            return {"status": "not_initialized"}
        
        return {
            "status": "initialized",
            "total_documents": self.vectorstore.index.ntotal,
            "embeddings_model": self.embeddings_model_name,
            "vector_store_path": self.vector_store_path
        }


# Global instance
rag_system = DelveRAGSystem()