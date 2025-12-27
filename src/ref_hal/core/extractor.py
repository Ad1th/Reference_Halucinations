import os
import sys
import re
import pdfplumber
from ..utils.text import normalize_newlines

def get_references(pdf_path: str) -> list[str]:
    """Open a PDF, find the References section, and return a list of individual reference strings."""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    texts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                texts.append(t)

    text = "\n".join(texts)
    text = normalize_newlines(text)
    
    # Case-insensitive search for References header
    match = re.search(r'(?i)(?:\n|^)\s*(?:[0-9]+\.?\s*)?(?:References|Bibliography)\s*(?:\n|$)', text)
    
    if not match:
        return []
        
    refs_text = text[match.end():].strip()
    
    # Regex to find citation markers like [1], [2]...
    citation_pattern = re.compile(r'(?:^|\n)(\[\d+\])')
    parts = citation_pattern.split(refs_text)
    
    references = []
    if len(parts) < 2:
         # Fallback: if no [N] markers found, we might need a more sophisticated split in the future
         return []

    i = 1
    while i < len(parts):
        marker = parts[i]
        content = parts[i+1] if i+1 < len(parts) else ""
        full_ref = (marker + " " + content).strip()
        # Clean up newlines within the reference (unwrap)
        full_ref_clean = re.sub(r'\s+', ' ', full_ref)
        references.append(full_ref_clean)
        i += 2
        
    return references
