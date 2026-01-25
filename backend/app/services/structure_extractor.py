"""
Box 1: Structure Extractor - The Input Layer.

Converts Word documents (.docx) into a structured, machine-readable ContractMap.
Preserves hierarchy (Sections, Subsections, Paragraphs) and assigns SHA-256 hashes
for drift detection during redlining.

Zero Data Retention: Text is processed in RAM only, never persisted.
"""

import hashlib
import io
from typing import List, Dict, Optional
from dataclasses import dataclass, field

from docx import Document  # python-docx

from app.services.text_normalizer import normalize_text


@dataclass
class ContractNode:
    """A single structural unit (paragraph) of the contract."""
    id: str                     # Unique Drift Hash (SHA-256)
    text: str                   # Normalized Text
    style: str                  # "Heading 1", "Normal", "List Paragraph"
    section_index: int          # 0 = Preamble, 1 = Definitions...
    original_text: str = ""     # Pre-normalized text for exact matching
    start_offset: int = 0       # Character offset in full document
    is_modified: bool = False   # Flag for redlining


@dataclass
class ContractMap:
    """The machine-readable skeleton of the document."""
    nodes: List[ContractNode] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)
    full_text: str = ""         # Complete document text for fallback searches
    
    def get_node_by_hash(self, node_hash: str) -> Optional[ContractNode]:
        """Find a node by its SHA-256 hash."""
        return next((n for n in self.nodes if n.id == node_hash), None)
    
    def get_nodes_by_section(self, section_index: int) -> List[ContractNode]:
        """Get all nodes in a specific section."""
        return [n for n in self.nodes if n.section_index == section_index]
    
    def get_all_text(self) -> str:
        """Concatenate all node texts for full-document operations."""
        return "\n".join(n.text for n in self.nodes)
    
    def to_hash_map(self) -> Dict[str, str]:
        """Return hash -> text mapping for quick lookups."""
        return {n.id: n.text for n in self.nodes}


class StructureExtractor:
    """
    Extract structure from DOCX or raw text.
    
    Usage:
        extractor = StructureExtractor()
        contract_map = extractor.extract_from_docx(file_bytes)
        # or
        contract_map = extractor.extract_from_text(raw_text)
    """
    
    def extract_from_docx(self, file_bytes: bytes) -> ContractMap:
        """
        Parse binary DOCX to preserve Sections/Headings structure.
        
        Uses python-docx to read the XML tree directly, extracting:
        - Paragraph styles (Heading 1, Normal, etc.)
        - Section boundaries based on heading styles
        - SHA-256 hash for each paragraph
        
        Args:
            file_bytes: Binary content of the .docx file
            
        Returns:
            ContractMap with hierarchical structure and hashes
        """
        doc = Document(io.BytesIO(file_bytes))
        contract_map = ContractMap()
        
        current_section = 0
        current_offset = 0
        full_text_parts = []
        
        for para in doc.paragraphs:
            original_text = para.text
            clean_text = normalize_text(original_text)
            
            if not clean_text:
                continue  # Skip empty whitespace lines
            
            # Detect Section Breaks based on Heading styles
            style_name = para.style.name if para.style else "Normal"
            if "Heading" in style_name:
                current_section += 1
            
            # Create Drift Hash (SHA-256 of normalized text)
            node_hash = self._hash_paragraph(clean_text)
            
            node = ContractNode(
                id=node_hash,
                text=clean_text,
                original_text=original_text,
                style=style_name,
                section_index=current_section,
                start_offset=current_offset,
            )
            contract_map.nodes.append(node)
            
            full_text_parts.append(clean_text)
            current_offset += len(clean_text) + 1  # +1 for newline
        
        # Store metadata
        contract_map.full_text = "\n".join(full_text_parts)
        contract_map.metadata = {
            "total_paragraphs": str(len(contract_map.nodes)),
            "detected_sections": str(current_section),
            "source_type": "docx",
        }
        
        return contract_map
    
    def extract_from_text(self, text: str) -> ContractMap:
        """
        Fallback for raw text (Demo Mode / Quick Scan).
        
        Loses style info but maintains hashing for Drift Detection.
        Used when Word Add-in sends body.text instead of file bytes.
        
        Args:
            text: Raw text from document
            
        Returns:
            ContractMap with flat structure (all section_index=0)
        """
        contract_map = ContractMap()
        
        # Split by double newlines (paragraphs) or single newlines
        paragraphs = self._split_into_paragraphs(text)
        
        current_offset = 0
        full_text_parts = []
        
        for para_text in paragraphs:
            original_text = para_text
            clean_text = normalize_text(para_text)
            
            if not clean_text:
                continue
            
            node_hash = self._hash_paragraph(clean_text)
            
            contract_map.nodes.append(ContractNode(
                id=node_hash,
                text=clean_text,
                original_text=original_text,
                style="Unknown",
                section_index=0,  # Flat structure for text-only
                start_offset=current_offset,
            ))
            
            full_text_parts.append(clean_text)
            current_offset += len(clean_text) + 1
        
        contract_map.full_text = "\n".join(full_text_parts)
        contract_map.metadata = {
            "total_paragraphs": str(len(contract_map.nodes)),
            "detected_sections": "0",
            "source_type": "text",
        }
        
        return contract_map
    
    def _hash_paragraph(self, text: str) -> str:
        """
        Generate SHA-256 hash for a paragraph.
        
        This is the "anchor" used for drift detection. If a user edits
        a clause while analysis is running, the hash won't match and
        we can detect the discrepancy.
        
        Args:
            text: Normalized paragraph text
            
        Returns:
            SHA-256 hex digest (64 characters)
        """
        return hashlib.sha256(text.encode('utf-8')).hexdigest()
    
    def _split_into_paragraphs(self, text: str) -> List[str]:
        """
        Smart paragraph splitting for raw text.
        
        Handles:
        - Double newlines (explicit paragraph breaks)
        - Single newlines followed by capital letters (likely new paragraphs)
        - Numbered/bulleted lists
        
        Args:
            text: Raw document text
            
        Returns:
            List of paragraph strings
        """
        # First, normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Split on double newlines first (clear paragraph breaks)
        chunks = text.split('\n\n')
        
        paragraphs = []
        for chunk in chunks:
            chunk = chunk.strip()
            if chunk:
                # For single-newline chunks, check if they look like separate paragraphs
                lines = chunk.split('\n')
                if len(lines) == 1:
                    paragraphs.append(chunk)
                else:
                    # Check if lines are part of same paragraph or separate
                    current_para = []
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        # Heuristic: numbered items or lines starting with caps are new paragraphs
                        if self._looks_like_new_paragraph(line) and current_para:
                            paragraphs.append(' '.join(current_para))
                            current_para = [line]
                        else:
                            current_para.append(line)
                    if current_para:
                        paragraphs.append(' '.join(current_para))
        
        return paragraphs
    
    def _looks_like_new_paragraph(self, line: str) -> bool:
        """Check if a line looks like the start of a new paragraph."""
        if not line:
            return False
        
        # Numbered list items: "1.", "2.", "(a)", "(i)", etc.
        import re
        numbered_pattern = r'^(\d+\.|\(\d+\)|\([a-z]\)|\([ivxlc]+\)|\d+\))'
        if re.match(numbered_pattern, line, re.IGNORECASE):
            return True
        
        # Bullet points
        if line[0] in '•-*►▪':
            return True
        
        # All caps (likely a heading)
        if line.isupper() and len(line) > 3:
            return True
        
        return False


# Convenience function for API usage
def extract_contract_structure(
    content: bytes = None,
    text: str = None,
    content_type: str = None
) -> ContractMap:
    """
    Extract contract structure from file bytes or raw text.
    
    Args:
        content: Binary file content (for DOCX)
        text: Raw text content (fallback)
        content_type: MIME type of the file
        
    Returns:
        ContractMap with structure and hashes
    """
    extractor = StructureExtractor()
    
    if content and content_type:
        if "wordprocessingml" in content_type or content_type.endswith(".docx"):
            return extractor.extract_from_docx(content)
    
    if text:
        return extractor.extract_from_text(text)
    
    # If content provided but not DOCX, try to decode as text
    if content:
        try:
            decoded_text = content.decode('utf-8')
            return extractor.extract_from_text(decoded_text)
        except UnicodeDecodeError:
            pass
    
    raise ValueError("Must provide either DOCX file bytes or raw text")
