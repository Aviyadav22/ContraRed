"""
Text Normalization Utility for Input Hygiene.

Cleans up Word document text before regex matching.
Handles: non-breaking spaces, smart quotes, soft hyphens, etc.
"""

import re
import unicodedata


def normalize_text(text: str) -> str:
    """
    Normalize text from Word documents for reliable regex matching.
    
    Handles common Word artifacts:
    - Non-breaking spaces (\xa0) → regular space
    - Smart quotes ("") → straight quotes ("")
    - Soft hyphens → removed
    - Zero-width characters → removed
    - Multiple spaces → single space
    - Various dashes → standard hyphen
    
    Args:
        text: Raw text from Word document
        
    Returns:
        Normalized text safe for regex matching
    """
    if not text:
        return ""
    
    # === CHARACTER REPLACEMENTS ===
    
    # Non-breaking space → regular space
    text = text.replace('\xa0', ' ')
    text = text.replace('\u00a0', ' ')
    
    # Smart quotes → straight quotes
    text = text.replace('"', '"')  # Left double quote
    text = text.replace('"', '"')  # Right double quote
    text = text.replace(''', "'")  # Left single quote
    text = text.replace(''', "'")  # Right single quote
    text = text.replace('„', '"')  # German opening quote
    text = text.replace('‟', '"')  # Double high-reversed-9 quote
    
    # Soft hyphen → removed (invisible hyphen for line breaks)
    text = text.replace('\xad', '')
    text = text.replace('\u00ad', '')
    
    # Various dashes → standard hyphen
    text = text.replace('–', '-')  # En dash
    text = text.replace('—', '-')  # Em dash
    text = text.replace('‐', '-')  # Hyphen
    text = text.replace('‑', '-')  # Non-breaking hyphen
    text = text.replace('−', '-')  # Minus sign
    
    # Ellipsis → three dots
    text = text.replace('…', '...')
    
    # === ZERO-WIDTH CHARACTERS ===
    
    # Remove zero-width characters (invisible, break regex)
    zero_width = [
        '\u200b',  # Zero-width space
        '\u200c',  # Zero-width non-joiner
        '\u200d',  # Zero-width joiner
        '\ufeff',  # Byte order mark / Zero-width no-break space
        '\u2060',  # Word joiner
    ]
    for char in zero_width:
        text = text.replace(char, '')
    
    # === WHITESPACE NORMALIZATION ===
    
    # Convert various newline formats to standard
    text = text.replace('\r\n', '\n')
    text = text.replace('\r', '\n')
    
    # Collapse multiple spaces (but preserve newlines)
    text = re.sub(r'[ \t]+', ' ', text)
    
    # Strip leading/trailing whitespace from lines
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)
    
    # === UNICODE NORMALIZATION ===
    
    # NFC normalization: compose characters (é vs e + combining accent)
    text = unicodedata.normalize('NFC', text)
    
    return text.strip()


def normalize_for_search(text: str) -> str:
    """
    Aggressive normalization for search matching.
    
    Additional transformations:
    - Lowercase
    - Remove extra whitespace
    - Keep only essential punctuation
    
    Use this for comparing/deduping, not for display.
    """
    text = normalize_text(text)
    text = text.lower()
    text = ' '.join(text.split())  # Collapse all whitespace
    return text


# Unit tests
if __name__ == "__main__":
    # Test non-breaking space
    test1 = "unlimited\xa0liability"
    assert "unlimited liability" in normalize_text(test1)
    print("✓ Non-breaking space handled")
    
    # Test smart quotes
    test2 = '"shall not"'
    assert '"shall not"' == normalize_text(test2)
    print("✓ Smart quotes handled")
    
    # Test soft hyphen
    test3 = "indemnifi\xadcation"
    assert "indemnification" == normalize_text(test3)
    print("✓ Soft hyphen handled")
    
    # Test zero-width characters
    test4 = "term\u200bination"
    assert "termination" == normalize_text(test4)
    print("✓ Zero-width characters handled")
    
    # Test em dash
    test5 = "this—that"
    assert "this-that" == normalize_text(test5)
    print("✓ Em dash handled")
    
    print("\nAll tests passed!")
