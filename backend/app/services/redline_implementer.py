"""
Box 3: Redline Implementer - The Output Layer.

Surgically applies AI suggestions to the user's live document.
Handles "AI Drift" where the AI's quoted text doesn't exactly match
the document by using fuzzy matching.

Key features:
- Anchor search using paragraph hash (Box 1)
- Fuzzy reconciliation using Levenshtein distance (rapidfuzz)
- Track Changes OOXML generation for lawyer review
"""

from typing import Optional, Tuple
from dataclasses import dataclass

from rapidfuzz import fuzz, process

from app.services.structure_extractor import ContractMap, ContractNode
from app.core.config import settings


@dataclass
class TextAnchor:
    """Location of text within a document."""
    found: bool
    text: str
    start_offset: int
    end_offset: int
    paragraph_hash: Optional[str] = None
    match_confidence: float = 1.0  # 1.0 = exact match, <1.0 = fuzzy match
    match_method: str = "exact"  # "hash", "exact", "fuzzy"


@dataclass
class RedlineResult:
    """Result of applying a redline suggestion."""
    success: bool
    original: str
    replacement: str
    track_changes_ooxml: str
    anchor: Optional[TextAnchor] = None
    error: Optional[str] = None


class RedlineImplementer:
    """
    Apply redlines with fuzzy text matching.
    
    Handles the challenge of "AI Drift" where the AI's suggested
    original text doesn't exactly match the document due to:
    - Minor changes to punctuation/spacing
    - Truncation in AI output
    - Inconsistent formatting
    
    Uses a multi-strategy approach:
    1. Hash lookup (fastest, most reliable from Box 1)
    2. Exact text match
    3. Fuzzy match using Levenshtein distance
    """
    
    def __init__(self, threshold: Optional[float] = None):
        """
        Initialize with fuzzy matching threshold.
        
        Args:
            threshold: Minimum similarity score (0.0-1.0) for fuzzy matches.
                      Defaults to settings.FUZZY_MATCH_THRESHOLD.
        """
        self.threshold = threshold or settings.FUZZY_MATCH_THRESHOLD
    
    def find_anchor(
        self,
        target_text: str,
        contract_map: Optional[ContractMap] = None,
        document_text: Optional[str] = None,
        paragraph_hash: Optional[str] = None
    ) -> TextAnchor:
        """
        Multi-strategy anchor search.
        
        Strategy 1: Hash match (if paragraph_hash provided)
        Strategy 2: Exact text match
        Strategy 3: Fuzzy match using Levenshtein distance
        
        Args:
            target_text: The text to find in the document
            contract_map: ContractMap from Box 1 (for hash lookup)
            document_text: Raw document text (for text matching)
            paragraph_hash: SHA-256 hash from Box 1 (for hash lookup)
            
        Returns:
            TextAnchor with location and confidence information
        """
        # Strategy 1: Hash lookup (fastest, most reliable)
        if paragraph_hash and contract_map:
            node = contract_map.get_node_by_hash(paragraph_hash)
            if node:
                return TextAnchor(
                    found=True,
                    text=node.text,
                    start_offset=node.start_offset,
                    end_offset=node.start_offset + len(node.text),
                    paragraph_hash=node.id,
                    match_confidence=1.0,
                    match_method="hash"
                )
        
        # Get text to search in
        if contract_map:
            full_text = contract_map.full_text or contract_map.get_all_text()
        elif document_text:
            full_text = document_text
        else:
            return TextAnchor(
                found=False,
                text=target_text,
                start_offset=-1,
                end_offset=-1,
                match_confidence=0.0,
                match_method="none"
            )
        
        # Strategy 2: Exact text match
        start_idx = full_text.find(target_text)
        if start_idx != -1:
            return TextAnchor(
                found=True,
                text=target_text,
                start_offset=start_idx,
                end_offset=start_idx + len(target_text),
                match_confidence=1.0,
                match_method="exact"
            )
        
        # Strategy 3: Fuzzy match
        return self._fuzzy_find(target_text, full_text, contract_map)
    
    def _fuzzy_find(
        self,
        target_text: str,
        full_text: str,
        contract_map: Optional[ContractMap] = None
    ) -> TextAnchor:
        """
        Fuzzy search using Levenshtein distance.
        
        First checks against ContractMap nodes for efficiency,
        then falls back to sliding window search.
        """
        # If we have ContractMap, search in nodes first
        if contract_map and contract_map.nodes:
            node_texts = [node.text for node in contract_map.nodes]
            
            # Find best matching node
            result = process.extractOne(
                target_text,
                node_texts,
                scorer=fuzz.ratio
            )
            
            if result:
                matched_text, score, idx = result
                normalized_score = score / 100.0
                
                if normalized_score >= self.threshold:
                    node = contract_map.nodes[idx]
                    return TextAnchor(
                        found=True,
                        text=matched_text,
                        start_offset=node.start_offset,
                        end_offset=node.start_offset + len(matched_text),
                        paragraph_hash=node.id,
                        match_confidence=normalized_score,
                        match_method="fuzzy"
                    )
        
        # Fallback: Sliding window fuzzy search on raw text
        # This is slower but catches cases where target spans multiple nodes
        best_match = self._sliding_window_fuzzy(target_text, full_text)
        return best_match
    
    def _sliding_window_fuzzy(
        self,
        target_text: str,
        full_text: str
    ) -> TextAnchor:
        """
        Sliding window fuzzy search for when target might span nodes.
        
        Uses a window roughly the size of target text and slides through
        the document looking for best match.
        """
        target_len = len(target_text)
        window_size = target_len
        
        best_score = 0.0
        best_start = -1
        best_text = ""
        
        # Slide window through text
        for start in range(0, len(full_text) - window_size + 1, max(1, window_size // 4)):
            window = full_text[start:start + window_size]
            score = fuzz.ratio(target_text, window) / 100.0
            
            if score > best_score:
                best_score = score
                best_start = start
                best_text = window
        
        # Also check slightly larger windows
        for size_delta in [int(window_size * 0.1), int(window_size * 0.2)]:
            for offset in [-size_delta, 0, size_delta]:
                if best_start >= 0:
                    adj_start = max(0, best_start + offset)
                    adj_end = min(len(full_text), adj_start + window_size + size_delta)
                    adj_window = full_text[adj_start:adj_end]
                    score = fuzz.ratio(target_text, adj_window) / 100.0
                    
                    if score > best_score:
                        best_score = score
                        best_start = adj_start
                        best_text = adj_window
        
        if best_score >= self.threshold:
            return TextAnchor(
                found=True,
                text=best_text,
                start_offset=best_start,
                end_offset=best_start + len(best_text),
                match_confidence=best_score,
                match_method="fuzzy"
            )
        
        return TextAnchor(
            found=False,
            text=target_text,
            start_offset=-1,
            end_offset=-1,
            match_confidence=best_score,
            match_method="none"
        )
    
    def generate_track_changes_ooxml(
        self,
        original: str,
        replacement: str,
        author: str = "ContraRed AI"
    ) -> str:
        """
        Generate Word-compatible Track Changes XML.
        
        Creates OOXML that shows:
        - Original text with strikethrough (red)
        - Replacement text with underline (green)
        
        Args:
            original: Original clause text
            replacement: Suggested replacement text
            author: Author name for track changes
            
        Returns:
            OOXML package string
        """
        from datetime import datetime
        
        # Escape XML special characters
        def escape_xml(text: str) -> str:
            return (text
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&apos;"))
        
        original_escaped = escape_xml(original)
        replacement_escaped = escape_xml(replacement)
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # Generate proper Track Changes OOXML
        ooxml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<pkg:package xmlns:pkg="http://schemas.microsoft.com/office/2006/xmlPackage">
  <pkg:part pkg:name="/_rels/.rels" pkg:contentType="application/vnd.openxmlformats-package.relationships+xml">
    <pkg:xmlData>
      <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
        <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
      </Relationships>
    </pkg:xmlData>
  </pkg:part>
  <pkg:part pkg:name="/word/document.xml" pkg:contentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml">
    <pkg:xmlData>
      <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
        <w:body>
          <w:p>
            <!-- Deleted text (strikethrough, red) -->
            <w:del w:id="1" w:author="{author}" w:date="{timestamp}">
              <w:r>
                <w:rPr>
                  <w:strike/>
                  <w:color w:val="DC2626"/>
                </w:rPr>
                <w:delText>{original_escaped}</w:delText>
              </w:r>
            </w:del>
            <w:r><w:t xml:space="preserve"> </w:t></w:r>
            <!-- Inserted text (underline, green) -->
            <w:ins w:id="2" w:author="{author}" w:date="{timestamp}">
              <w:r>
                <w:rPr>
                  <w:u w:val="single"/>
                  <w:color w:val="16A34A"/>
                </w:rPr>
                <w:t>{replacement_escaped}</w:t>
              </w:r>
            </w:ins>
          </w:p>
        </w:body>
      </w:document>
    </pkg:xmlData>
  </pkg:part>
</pkg:package>'''
        
        return ooxml
    
    def apply_redline(
        self,
        original_text: str,
        suggested_text: str,
        contract_map: Optional[ContractMap] = None,
        document_text: Optional[str] = None,
        paragraph_hash: Optional[str] = None
    ) -> RedlineResult:
        """
        Full redline workflow: find anchor → generate diff → return OOXML.
        
        Args:
            original_text: The original clause to replace
            suggested_text: The AI-suggested replacement
            contract_map: ContractMap from Box 1
            document_text: Raw document text (fallback)
            paragraph_hash: SHA-256 hash for hash-based lookup
            
        Returns:
            RedlineResult with OOXML and confidence information
        """
        # Find the text in the document
        anchor = self.find_anchor(
            target_text=original_text,
            contract_map=contract_map,
            document_text=document_text,
            paragraph_hash=paragraph_hash
        )
        
        if not anchor.found:
            return RedlineResult(
                success=False,
                original=original_text,
                replacement=suggested_text,
                track_changes_ooxml="",
                anchor=anchor,
                error=f"Could not find anchor text in document (best score: {anchor.match_confidence:.2f})"
            )
        
        # Generate Track Changes OOXML
        # Use the actually-found text as the original for accuracy
        ooxml = self.generate_track_changes_ooxml(
            original=anchor.text,
            replacement=suggested_text
        )
        
        return RedlineResult(
            success=True,
            original=anchor.text,
            replacement=suggested_text,
            track_changes_ooxml=ooxml,
            anchor=anchor
        )


# Convenience function
def apply_redline_suggestion(
    original: str,
    replacement: str,
    contract_map: Optional[ContractMap] = None,
    paragraph_hash: Optional[str] = None
) -> Tuple[bool, str, float]:
    """
    Quick redline application.
    
    Args:
        original: Original clause text
        replacement: Suggested replacement
        contract_map: ContractMap from Box 1
        paragraph_hash: Hash for lookup
        
    Returns:
        Tuple of (success, ooxml, confidence)
    """
    implementer = RedlineImplementer()
    result = implementer.apply_redline(
        original_text=original,
        suggested_text=replacement,
        contract_map=contract_map,
        paragraph_hash=paragraph_hash
    )
    
    confidence = result.anchor.match_confidence if result.anchor else 0.0
    return result.success, result.track_changes_ooxml, confidence
