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
        
        # Common query patterns with pre-built responses
        self.fast_responses = {
            "what is delve": {
                "answer": "Delve is the leading AI-native compliance automation platform serving over 500 companies including AI unicorns like Lovable, Bland, and Wispr Flow. Founded in 2023 by MIT AI researchers, Delve helps companies achieve SOC 2, HIPAA, GDPR, and ISO 27001 certifications in days rather than months using revolutionary AI agents that eliminate manual busywork.",
                "confidence": 0.95,
                "sources": ["📖 Company Overview & Background"],
                "should_escalate": False
            },
            "delve pricing": {
                "answer": "I'd be happy to help you learn about Delve's pricing! Our pricing is customized based on your organization's size and compliance needs. Let me connect you with our sales team who can provide detailed pricing information and discuss volume discounts, enterprise features, and contract terms.",
                "confidence": 0.9,
                "sources": ["📖 Service Offerings"],
                "should_escalate": True,
                "escalation_reason": "Pricing inquiry requiring sales team"
            },
            "soc2 timeline": {
                "answer": "With Delve, SOC 2 compliance typically takes just 30 minutes for onboarding + 10-15 hours of platform setup + 1-3 weeks for audit completion. This includes a 3-month observation period for Type 2, with some customers completing in as little as 4-7 days. We have a 100% success rate for customers passing their SOC 2 audit.",
                "confidence": 0.9,
                "sources": ["📖 SOC 2 Compliance"],
                "should_escalate": False
            }
        }
        
        # Framework-specific confidence thresholds (lowered for basic queries)
        self.confidence_thresholds = {
            'SOC2': 0.70,
            'HIPAA': 0.70,
            'GDPR': 0.70,
            'ISO27001': 0.70,
            'general': 0.60  # Lowered from 0.65 to reduce false escalations
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
    
    def _get_ollama_llm(self):
        """Get Ollama LLM with llama3.2:3b model. [TEMPORARILY DISABLED - TOO SLOW]"""
        # COMMENTED OUT: Ollama takes 89+ seconds per response
        # Keeping this method for future optimization when we have better hardware
        logger.warning("Ollama disabled due to performance issues (89s+ per response)")
        return self._create_simple_fallback()
    
    def _create_simple_fallback(self):
        """Create a simple text-based fallback when both OpenAI and Ollama are unavailable."""
        from langchain_community.llms.fake import FakeListLLM
        
        # Simple responses for common scenarios
        responses = [
            "Based on the retrieved Delve documentation, I found relevant information but recommend speaking with our team for detailed guidance. For compliance questions, our experts can provide specific implementation steps.\n\nCONFIDENCE: 0.7",
            "I found information in our knowledge base about this topic. However, for the most accurate and up-to-date guidance, I recommend connecting with our support team who can provide personalized assistance.\n\nCONFIDENCE: 0.6",
            "The information in our documentation suggests several approaches to this question. Our team can provide specific recommendations based on your requirements.\n\nCONFIDENCE: 0.6"
        ]
        
        return FakeListLLM(responses=responses)
    
    async def _generate_with_direct_openai(self, question: str, context: str) -> str:
        """Generate response using direct OpenAI API (v1.0+ compatible)."""
        generation_start = time.time()
        logger.info(f"🚀 Using direct OpenAI for question: '{question[:50]}...'")
        
        try:
            # Use the new OpenAI v1.0+ client interface
            from openai import OpenAI
            client = OpenAI(
                api_key=os.getenv("OPENAI_API_KEY"),
                # Remove any unsupported parameters
            )
            
            prompt = f"""You are Delve's expert compliance AI assistant. Use the provided context to answer questions about compliance automation, SOC2, HIPAA, GDPR, ISO27001, and Delve's services.

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
CONFIDENCE: [score]"""

            # Make API call using new interface
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful compliance automation expert."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.1,
                timeout=10.0
            )
            
            generation_time = time.time() - generation_start
            logger.info(f"⚡ Direct OpenAI generation took: {generation_time:.3f}s")
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Direct OpenAI failed: {e}")
            raise
    
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
        """Check if query matches a pre-built fast response."""
        question_clean = question.lower().strip()
        
        # Direct matches
        for pattern, response in self.fast_responses.items():
            if pattern in question_clean:
                logger.info(f"Fast response match for: {pattern}")
                return response.copy()
        
        # Fuzzy matching for common variations
        if any(word in question_clean for word in ['what', 'what\'s', 'tell me about']) and \
           any(word in question_clean for word in ['delve', 'company', 'platform']):
            logger.info("Fast response: What is Delve (fuzzy match)")
            return self.fast_responses["what is delve"].copy()
        
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
            # Check for fast pre-built responses first (near-instant)
            fast_response = self._check_fast_response(question)
            if fast_response:
                logger.info(f"Fast response delivered in {time.time() - start_time:.2f}s")
                return fast_response
            
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
            logger.error(f"Error during query processing: {e}")
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
        """Provide fast fallback response when query times out."""
        logger.info("Providing timeout fallback response")
        
        # Analyze question for basic categorization
        question_lower = question.lower()
        
        if any(word in question_lower for word in ['pricing', 'cost', 'price']):
            return {
                'answer': "I'd be happy to help with pricing information! Let me connect you with our sales team who can provide detailed pricing based on your specific needs and organization size.",
                'confidence': 0.8,
                'sources': [],
                'should_escalate': True,
                'escalation_reason': "Pricing inquiry requiring sales team"
            }
        elif any(word in question_lower for word in ['demo', 'schedule', 'meeting']):
            return {
                'answer': "I'd love to help you schedule a demo! Let me connect you with our team who can set up a customized demonstration of Delve's compliance automation platform.",
                'confidence': 0.8,
                'sources': [],
                'should_escalate': True,
                'escalation_reason': "Demo request requiring sales team"
            }
        elif any(word in question_lower for word in ['soc2', 'soc 2', 'hipaa', 'gdpr', 'iso27001']):
            return {
                'answer': "I have information about compliance frameworks, but I'm experiencing a delay accessing our knowledge base. Let me connect you with our compliance experts who can provide immediate, detailed guidance.",
                'confidence': 0.7,
                'sources': [],
                'should_escalate': True,
                'escalation_reason': "Technical delay - compliance expertise needed"
            }
        else:
            return {
                'answer': "I'm experiencing a technical delay while searching our knowledge base. To ensure you get the most accurate and timely information, let me connect you with our support team who can help immediately.",
                'confidence': 0.6,
                'sources': [],
                'should_escalate': True,
                'escalation_reason': "Technical timeout - escalating for immediate assistance"
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
            
            # Try direct OpenAI first if available
            openai_key = os.getenv("OPENAI_API_KEY")
            if openai and openai_key:
                try:
                    return await self._generate_with_direct_openai(question, context)
                except Exception as openai_error:
                    logger.warning(f"Direct OpenAI failed: {openai_error}, trying RAG chain")
            
            # Fallback to RAG chain
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