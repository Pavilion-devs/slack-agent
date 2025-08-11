"""
Advanced RAG system using FAISS and HuggingFace embeddings.
Implements patterns from LangChain notebooks for optimal retrieval performance.
"""

import os
import logging
import asyncio
import time
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from functools import lru_cache
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:
    HuggingFaceEmbeddings = None

from langchain_core.embeddings.embeddings import Embeddings
from sentence_transformers import SentenceTransformer
from typing import List
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None

try:
    import openai
except ImportError:
    openai = None
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

from src.core.document_processor import document_processor


logger = logging.getLogger(__name__)


class CustomHuggingFaceEmbeddings(Embeddings):
    """
    Custom embeddings class that fixes the dict/string error in langchain-huggingface.
    Based on solution from GitHub issue #17773.
    """
    
    def __init__(self, model_name: str, **kwargs):
        self.model_name = model_name
        self.model = SentenceTransformer(model_name, **kwargs)
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple documents."""
        # Ensure all inputs are strings
        clean_texts = [str(text).replace("\n", " ") if isinstance(text, str) else str(text) for text in texts]
        embeddings = self.model.encode(clean_texts)
        return embeddings.tolist()
    
    def embed_query(self, text: str) -> List[float]:
        """Embed a single query."""
        # Time the embedding process
        embed_start = time.time()
        
        # Ensure input is string
        clean_text = str(text).replace("\n", " ") if isinstance(text, str) else str(text)
        embedding = self.model.encode([clean_text])
        
        embed_time = time.time() - embed_start
        logger.info(f"🧮 Query embedding took: {embed_time:.3f}s")
        
        return embedding[0].tolist()


class DelveRAGSystem:
    """
    Advanced RAG system optimized for Delve compliance knowledge base.
    Uses FAISS for cost-effective local vector storage and HuggingFace embeddings.
    Includes aggressive timeouts, caching, and fast fallbacks for <20s responses.
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
        
        # Performance settings
        self.max_query_timeout = 18.0  # Aggressive 18s timeout
        self.retrieval_timeout = 5.0   # 5s for retrieval
        self.generation_timeout = 12.0  # 12s for generation
        
        # Simple in-memory cache for common queries
        self.query_cache = {}
        self.cache_max_size = 100
        self.cache_ttl = 3600  # 1 hour
        
        # Let OpenAI handle all responses intelligently - no hardcoded answers
        self.fast_responses = {}
        
        # Framework-specific confidence thresholds (trust LLM more)
        self.confidence_thresholds = {
            'SOC2': 0.40,
            'HIPAA': 0.40,
            'GDPR': 0.40,
            'ISO27001': 0.40,
            'general': 0.30  # Trust OpenAI LLM to make smart decisions
        }
        
        # Initialize embeddings
        self._initialize_embeddings()
    
    def _initialize_embeddings(self):
        """Initialize HuggingFace embeddings model."""
        try:
            logger.info(f"Initializing custom embeddings model: {self.embeddings_model_name}")
            # Use custom embeddings class to avoid dict/string error
            self.embeddings = CustomHuggingFaceEmbeddings(
                model_name=self.embeddings_model_name
            )
            logger.info("Custom embeddings model initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize embeddings: {e}")
            # Fallback to original if available
            if HuggingFaceEmbeddings:
                try:
                    logger.info("Trying fallback to original HuggingFaceEmbeddings...")
                    self.embeddings = HuggingFaceEmbeddings(
                        model_name=self.embeddings_model_name,
                        model_kwargs={'device': 'cpu'},
                        encode_kwargs={'normalize_embeddings': True}
                    )
                    logger.info("Fallback embeddings initialized")
                except Exception as fallback_error:
                    logger.error(f"Fallback also failed: {fallback_error}")
                    raise
            else:
                raise
    
    async def initialize(self) -> bool:
        """
        Initialize the RAG system with default knowledge base.
        
        Returns:
            bool: True if successful, False otherwise
        """
        knowledge_file_path = "knowledge_restructured.txt"
        return await self.initialize_knowledge_base(knowledge_file_path)
    
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
            llm = self._get_llm()
            
            # Always use PromptTemplate for consistency, especially with Ollama
            prompt_template = PromptTemplate.from_template("""You are Delve's expert compliance AI assistant. Use the provided context to answer questions about compliance automation, SOC2, HIPAA, GDPR, ISO27001, and Delve's services.

INSTRUCTIONS:
1. Base your answers primarily on the provided context
2. Be specific and cite relevant information from the context
3. If the context doesn't have enough details, say "I don't have the complete details on that in my docs right now. Let me connect you with our support team for the most accurate information."
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
CONFIDENCE: [score]""")
            
            # Setup RAG chain with proper variable passing
            self.rag_chain = (
                {"context": self.retriever, "question": RunnablePassthrough()}
                | prompt_template
                | llm
                | StrOutputParser()
            )
            
            logger.info("Retriever and RAG chain setup completed")
            
        except Exception as e:
            logger.error(f"Failed to setup retriever and chain: {e}")
            raise
    
    def _get_llm(self):
        """Get the best available LLM (prioritize OpenAI for speed)."""
        # Prioritize OpenAI for much faster responses
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            logger.info("Using OpenAI GPT-4o-mini for fast responses")
            try:
                return ChatOpenAI(
                    model="gpt-4o-mini",
                    temperature=0.1,
                    max_tokens=500,
                    request_timeout=10.0,  # Use request_timeout instead of timeout
                    api_key=openai_key     # Explicitly pass the API key
                )
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI: {e}, using fallback")
                return self._create_simple_fallback()
        else:
            # Fallback to Ollama (commented out the slow part)
            logger.warning("No OpenAI key found, using fallback responses")
            return self._create_simple_fallback()
    
    
    def _create_simple_fallback(self):
        """Create a fallback that escalates when no LLM is available."""
        from langchain_community.llms.fake import FakeListLLM
        
        # Only provide this when absolutely no LLM is available
        responses = [
            "I'm experiencing technical difficulties accessing my language model. Let me connect you with our support team who can provide immediate assistance.\n\nCONFIDENCE: 0.1"
        ]
        
        return FakeListLLM(responses=responses)
    
    
    def _get_cache_key(self, question: str, frameworks: Optional[List[str]] = None) -> str:
        """Generate cache key for query."""
        key_data = f"{question.lower().strip()}"
        if frameworks:
            key_data += f"_{'_'.join(sorted(frameworks))}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _check_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Check if response is in cache and still valid."""
        if cache_key in self.query_cache:
            cached_result, timestamp = self.query_cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                logger.info(f"Cache hit for query: {cache_key[:8]}...")
                return cached_result
            else:
                # Remove expired entry
                del self.query_cache[cache_key]
        return None
    
    def _cache_response(self, cache_key: str, response: Dict[str, Any]):
        """Cache response with TTL."""
        # Implement simple LRU by removing oldest entries
        if len(self.query_cache) >= self.cache_max_size:
            oldest_key = min(self.query_cache.keys(), 
                           key=lambda k: self.query_cache[k][1])
            del self.query_cache[oldest_key]
        
        self.query_cache[cache_key] = (response, time.time())
        logger.debug(f"Cached response for query: {cache_key[:8]}...")
    
    def _check_fast_response(self, question: str) -> Optional[Dict[str, Any]]:
        """No more hardcoded responses - let OpenAI handle everything intelligently."""
        return None

    async def query(self, question: str, frameworks: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Query the knowledge base with enhanced retrieval, caching, and aggressive timeouts.
        
        Args:
            question: User's question
            frameworks: Optional list of specific frameworks to focus on
            
        Returns:
            Dict containing answer, confidence, sources, and metadata
        """
        start_time = time.time()
        
        if not self.is_initialized:
            return {
                'answer': "Knowledge base not initialized. Please contact support.",
                'confidence': 0.0,
                'sources': [],
                'should_escalate': True,
                'escalation_reason': "Knowledge base initialization failed"
            }
        
        try:
            # No more fast responses - trust OpenAI to be smart
            
            # Check cache
            cache_key = self._get_cache_key(question, frameworks)
            cached_result = self._check_cache(cache_key)
            if cached_result:
                logger.info(f"Cached response delivered in {time.time() - start_time:.2f}s")
                return cached_result
            
            # Apply aggressive timeout to entire query process
            try:
                result = await asyncio.wait_for(
                    self._process_query_with_timeout(question, frameworks),
                    timeout=self.max_query_timeout
                )
                
                # Cache successful result
                self._cache_response(cache_key, result)
                
                logger.info(f"RAG query completed in {time.time() - start_time:.2f}s")
                return result
                
            except asyncio.TimeoutError:
                logger.warning(f"Query timed out after {self.max_query_timeout}s")
                return self._get_timeout_fallback(question)
            
        except Exception as e:
            import traceback
            logger.error(f"Error during query processing: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return {
                'answer': "I'm experiencing technical difficulties. Let me get a human agent to help you.",
                'confidence': 0.0,
                'sources': [],
                'should_escalate': True,
                'escalation_reason': f"Query processing error: {str(e)}"
            }
    
    async def _process_query_with_timeout(self, question: str, frameworks: Optional[List[str]] = None) -> Dict[str, Any]:
        """Process query with internal timeouts for each stage."""
        try:
            # Enhanced retrieval with timeout
            logger.info(f"Starting retrieval for question: '{question}' with frameworks: {frameworks}")
            retrieved_docs = await asyncio.wait_for(
                self._enhanced_retrieve(question, frameworks),
                timeout=self.retrieval_timeout
            )
            
            logger.info(f"Retrieved {len(retrieved_docs)} documents")
            for i, doc in enumerate(retrieved_docs[:3]):  # Log first 3 docs
                section = doc.metadata.get('section', 'unknown')
                content_preview = doc.page_content[:100].replace('\n', ' ')
                logger.debug(f"Doc {i+1}: '{content_preview}...' (section: {section})")
            
            if not retrieved_docs:
                logger.warning(f"No documents retrieved for question: '{question}'")
                return {
                    'answer': "I couldn't find relevant information for your question. Let me connect you with a human expert.",
                    'confidence': 0.0,
                    'sources': [],
                    'should_escalate': True,
                    'escalation_reason': "No relevant documents retrieved"
                }
            
            # Generate response with timeout
            response = await asyncio.wait_for(
                self._generate_response(question, retrieved_docs),
                timeout=self.generation_timeout
            )
            
            # Extract confidence score
            confidence = self._extract_confidence_score(response)
            logger.info(f"Extracted confidence score: {confidence}")
            logger.debug(f"Response content for confidence extraction: {response[:100]}...")
            
            # Determine if escalation is needed
            should_escalate, escalation_reason = self._should_escalate(
                confidence, question, frameworks, retrieved_docs
            )
            logger.info(f"Escalation decision - Should escalate: {should_escalate}, Reason: {escalation_reason}")
            
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
            
        except asyncio.TimeoutError:
            raise  # Re-raise timeout to be caught by parent
        except Exception as e:
            logger.error(f"Error in _process_query_with_timeout: {e}")
            raise
    
    def _get_timeout_fallback(self, question: str) -> Dict[str, Any]:
        """Provide fallback response when query times out - let LLM handle with retrieved context."""
        logger.info("Query timeout - providing intelligent fallback")
        
        return {
            'answer': "I'm experiencing a brief delay accessing our knowledge base. Let me connect you with our support team who can provide immediate assistance with your question.",
            'confidence': 0.3,
            'sources': [],
            'should_escalate': True,
            'escalation_reason': "Query timeout - escalating for immediate assistance"
        }
    
    async def _enhanced_retrieve(self, question: str, frameworks: Optional[List[str]] = None) -> List[Document]:
        """Enhanced retrieval with framework filtering and query expansion."""
        try:
            # Time the retrieval process
            retrieval_start = time.time()
            logger.info(f"🔍 Starting document retrieval for: '{question[:50]}...'")
            
            # Basic retrieval
            docs = self.retriever.invoke(question)
            
            retrieval_time = time.time() - retrieval_start
            logger.info(f"⏱️ Document retrieval took: {retrieval_time:.3f}s (found {len(docs)} docs)")
            
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
        """Generate response using the RAG chain or direct OpenAI."""
        try:
            # Prepare context from documents
            context_start = time.time()
            context = "\n\n".join([doc.page_content for doc in docs])
            context_time = time.time() - context_start
            logger.info(f"📝 Context preparation took: {context_time:.3f}s ({len(context)} chars)")
            
            # Use RAG chain with OpenAI LLM
            generation_start = time.time()
            logger.info(f"🤖 Starting LLM generation for question: '{question[:50]}...'")
            response = self.rag_chain.invoke({
                "question": question,
                "context": context
            })
            
            generation_time = time.time() - generation_start
            logger.info(f"⏱️ LLM generation took: {generation_time:.3f}s")
            
            logger.debug(f"RAG chain response type: {type(response)}")
            logger.debug(f"RAG chain response: {str(response)[:100]}...")
            
            # Ensure response is a string
            if isinstance(response, dict):
                logger.debug(f"Response is dict with keys: {response.keys()}")
                response = response.get('content', response.get('text', str(response)))
            elif not isinstance(response, str):
                logger.debug(f"Converting {type(response)} to string")
                response = str(response)
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return f"I found relevant information but encountered an error processing it. Error: {str(e)}"
    
    def _extract_confidence_score(self, response) -> float:
        """Extract confidence score from response."""
        try:
            # Ensure response is a string
            if isinstance(response, dict):
                response = response.get('content', response.get('text', str(response)))
            elif not isinstance(response, str):
                response = str(response)
            
            logger.debug(f"Extracting confidence from response (first 200 chars): {response[:200]}")
            
            if "CONFIDENCE:" in response:
                confidence_line = response.split("CONFIDENCE:")[1].strip().split()[0]
                confidence = float(confidence_line)
                logger.debug(f"Found CONFIDENCE: {confidence}")
                return confidence
            else:
                logger.debug("No CONFIDENCE: found in response, using default 0.6")
                return 0.6  # Default medium confidence
        except Exception as e:
            logger.debug(f"Exception in confidence extraction: {e}, using default 0.6")
            return 0.6
    
    def _should_escalate(self, confidence: float, question: str, 
                        frameworks: Optional[List[str]], docs: List[Document]) -> Tuple[bool, str]:
        """Determine if the query should be escalated."""
        
        # Get threshold based on frameworks
        if frameworks:
            threshold = min(self.confidence_thresholds.get(fw, 0.65) for fw in frameworks)
            logger.debug(f"Using framework-specific threshold: {threshold} for frameworks: {frameworks}")
        else:
            threshold = self.confidence_thresholds['general']
            logger.debug(f"Using general threshold: {threshold}")
        
        logger.debug(f"Confidence check: {confidence} vs threshold {threshold}")
        if confidence < threshold:
            logger.info(f"Escalating due to low confidence: {confidence:.2f} < {threshold:.2f}")
            return True, f"Low confidence score ({confidence:.2f}) below threshold ({threshold:.2f})"
        
        # Check for urgent keywords
        urgent_keywords = ['urgent', 'asap', 'immediately', 'critical', 'emergency']
        if any(keyword in question.lower() for keyword in urgent_keywords):
            logger.info(f"Escalating due to urgent keywords in question: {question}")
            return True, "Urgent request detected"
        
        logger.debug(f"No escalation needed - confidence {confidence} above threshold {threshold}")
        return False, ""
    
    def _format_sources(self, docs: List[Document]) -> List[str]:
        """Format source information from retrieved documents."""
        sources = []
        for doc in docs:
            section = doc.metadata.get('section', 'Unknown')
            subsection = doc.metadata.get('subsection')
            frameworks = doc.metadata.get('frameworks', [])
            
            # Format as readable string
            source_text = f"📖 {section}"
            if subsection:
                source_text += f" > {subsection}"
            if frameworks:
                source_text += f" ({', '.join(frameworks)})"
            
            sources.append(source_text)
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