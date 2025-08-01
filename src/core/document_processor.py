"""
Advanced document processing with metadata-aware chunking for Delve knowledge base.
Based on patterns from LangChain notebooks for optimal RAG performance.
"""

import re
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


logger = logging.getLogger(__name__)


@dataclass
class ChunkMetadata:
    """Metadata for knowledge base chunks."""
    source: str
    section: str
    subsection: Optional[str] = None
    frameworks: List[str] = None
    topics: List[str] = None
    chunk_id: str = ""
    confidence_weight: float = 1.0
    level: str = "general"


class DelveDocumentProcessor:
    """
    Intelligent document processor for Delve knowledge base.
    Implements metadata-aware chunking respecting document structure.
    """
    
    def __init__(self):
        # Framework keywords for automatic tagging
        self.framework_keywords = {
            "SOC2": ["soc2", "soc 2", "service organization control", "trust services"],
            "HIPAA": ["hipaa", "health insurance portability", "phi", "protected health information"],
            "GDPR": ["gdpr", "general data protection regulation", "data subject rights", "privacy"],
            "ISO27001": ["iso27001", "iso 27001", "information security management", "isms"],
            "PCI_DSS": ["pci dss", "payment card industry", "cardholder data"]
        }
        
        # Topic keywords for categorization
        self.topic_keywords = {
            "compliance_automation": ["automation", "ai-powered", "automated"],
            "implementation": ["timeline", "implementation", "setup", "onboarding"],
            "pricing": ["pricing", "cost", "subscription", "billing"],
            "technical": ["integration", "api", "technical", "architecture"],
            "support": ["support", "customer success", "help", "assistance"],
            "company_info": ["founded", "funding", "growth", "company"]
        }
        
        # Initialize text splitter with Delve-optimized settings
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n## ", "\n### ", "\n\n", "\n", " ", ""],
            length_function=len
        )
    
    def process_knowledge_file(self, file_path: str) -> List[Document]:
        """
        Process the Delve knowledge file into structured chunks with metadata.
        
        Args:
            file_path: Path to the knowledge file
            
        Returns:
            List of Document objects with enhanced metadata
        """
        try:
            logger.info(f"Processing knowledge file: {file_path}")
            
            # Load the document
            loader = TextLoader(file_path)
            documents = loader.load()
            
            if not documents:
                logger.error("No documents loaded from file")
                return []
            
            content = documents[0].page_content
            
            # Extract structured sections
            sections = self._extract_sections(content)
            
            # Process each section into chunks
            all_chunks = []
            for section_data in sections:
                chunks = self._create_section_chunks(section_data)
                all_chunks.extend(chunks)
            
            logger.info(f"Created {len(all_chunks)} chunks from {len(sections)} sections")
            return all_chunks
            
        except Exception as e:
            logger.error(f"Error processing knowledge file: {e}")
            return []
    
    def _extract_sections(self, content: str) -> List[Dict[str, Any]]:
        """Extract structured sections from the knowledge base content."""
        sections = []
        
        # Split by main sections (##)
        main_sections = re.split(r'\n## ', content)
        
        for i, section_content in enumerate(main_sections):
            if not section_content.strip():
                continue
                
            # Extract section title
            lines = section_content.split('\n')
            section_title = lines[0].strip().replace('# ', '').replace('## ', '')
            
            # Extract metadata if present
            metadata_match = re.search(r'\*\*Metadata\*\*:\s*([^\n]+)', section_content)
            metadata_tags = []
            if metadata_match:
                metadata_tags = [tag.strip() for tag in metadata_match.group(1).split(',')]
            
            # Split into subsections (###)
            subsections = re.split(r'\n### ', section_content)
            
            if len(subsections) > 1:
                # Multiple subsections
                for j, subsection in enumerate(subsections):
                    if not subsection.strip():
                        continue
                        
                    subsection_lines = subsection.split('\n')
                    subsection_title = subsection_lines[0].strip().replace('### ', '')
                    
                    sections.append({
                        'section': section_title,
                        'subsection': subsection_title if j > 0 else None,
                        'content': subsection,
                        'metadata_tags': metadata_tags,
                        'section_index': i,
                        'subsection_index': j
                    })
            else:
                # Single section
                sections.append({
                    'section': section_title,
                    'subsection': None,
                    'content': section_content,
                    'metadata_tags': metadata_tags,
                    'section_index': i,
                    'subsection_index': 0
                })
        
        return sections
    
    def _create_section_chunks(self, section_data: Dict[str, Any]) -> List[Document]:
        """Create chunks from a section with appropriate metadata."""
        content = section_data['content']
        section = section_data['section']
        subsection = section_data.get('subsection')
        metadata_tags = section_data.get('metadata_tags', [])
        
        # Split content into chunks
        chunks = self.text_splitter.split_text(content)
        
        documents = []
        for i, chunk in enumerate(chunks):
            # Generate chunk metadata
            chunk_metadata = self._generate_chunk_metadata(
                chunk, section, subsection, metadata_tags, i
            )
            
            # Create document with metadata
            doc = Document(
                page_content=chunk,
                metadata={
                    'source': 'knowledge_restructured.txt',
                    'section': section,
                    'subsection': subsection,
                    'frameworks': chunk_metadata.frameworks,
                    'topics': chunk_metadata.topics,
                    'chunk_id': chunk_metadata.chunk_id,
                    'confidence_weight': chunk_metadata.confidence_weight,
                    'level': chunk_metadata.level,
                    'chunk_index': i
                }
            )
            
            documents.append(doc)
        
        return documents
    
    def _generate_chunk_metadata(
        self, 
        chunk_content: str, 
        section: str, 
        subsection: Optional[str],
        metadata_tags: List[str],
        chunk_index: int
    ) -> ChunkMetadata:
        """Generate metadata for a chunk based on its content and context."""
        
        # Extract frameworks mentioned
        frameworks = []
        content_lower = chunk_content.lower()
        
        for framework, keywords in self.framework_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                frameworks.append(framework)
        
        # Add frameworks from metadata tags
        for tag in metadata_tags:
            if tag.upper() in self.framework_keywords:
                frameworks.append(tag.upper())
        
        # Remove duplicates
        frameworks = list(set(frameworks))
        
        # Extract topics
        topics = []
        for topic, keywords in self.topic_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                topics.append(topic)
        
        # Add topics from metadata tags
        topics.extend([tag for tag in metadata_tags if tag not in frameworks])
        topics = list(set(topics))
        
        # Determine confidence weight based on content quality
        confidence_weight = self._calculate_confidence_weight(chunk_content, frameworks)
        
        # Determine level
        level = self._determine_level(section, subsection, frameworks)
        
        # Generate chunk ID
        section_clean = re.sub(r'[^\w\s-]', '', section).strip().replace(' ', '_').lower()
        subsection_clean = re.sub(r'[^\w\s-]', '', subsection or '').strip().replace(' ', '_').lower()
        
        if subsection_clean:
            chunk_id = f"delve_{section_clean}_{subsection_clean}_{chunk_index:03d}"
        else:
            chunk_id = f"delve_{section_clean}_{chunk_index:03d}"
        
        return ChunkMetadata(
            source='knowledge_restructured.txt',
            section=section,
            subsection=subsection,
            frameworks=frameworks,
            topics=topics,
            chunk_id=chunk_id,
            confidence_weight=confidence_weight,
            level=level
        )
    
    def _calculate_confidence_weight(self, content: str, frameworks: List[str]) -> float:
        """Calculate confidence weight based on content characteristics."""
        weight = 0.7  # Base weight
        
        # Higher weight for framework-specific content
        if frameworks:
            weight += 0.2
        
        # Higher weight for detailed content
        if len(content) > 500:
            weight += 0.1
        
        # Higher weight for content with specific details (timelines, metrics)
        if re.search(r'\d+.*(?:hours?|days?|weeks?|months?)', content.lower()):
            weight += 0.1
        
        # Higher weight for content with citations or examples
        if any(keyword in content.lower() for keyword in ['example', 'case study', 'testimonial']):
            weight += 0.1
        
        return min(weight, 1.0)
    
    def _determine_level(self, section: str, subsection: Optional[str], frameworks: List[str]) -> str:
        """Determine the specificity level of the content."""
        if frameworks:
            return "framework_specific"
        elif subsection and any(keyword in section.lower() for keyword in ['technical', 'implementation', 'integration']):
            return "technical_detailed" 
        elif 'overview' in section.lower() or 'background' in section.lower():
            return "company_overview"
        else:
            return "general"


# Global instance
document_processor = DelveDocumentProcessor()