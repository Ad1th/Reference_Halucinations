import os
import sys
import re
import pdfplumber

def get_references(pdf_path: str) -> list[str]:
    """Open a PDF, find the References section, and return a list of individual reference strings."""
    if not os.path.exists(pdf_path):
        print(f"Error: file not found: {pdf_path}", file=sys.stderr)
        return []

    texts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                texts.append(t)

    text = "\n".join(texts)
    
    # Case-insensitive search for References header
    match = re.search(r'(?i)(?:\n|^)\s*(?:[0-9]+\.?\s*)?(?:References|Bibliography)\s*(?:\n|$)', text)
    
    if match:
        refs_text = text[match.end():].strip()
    else:
        return []
        
    # Normalize newlines
    refs_text = refs_text.replace('\r\n', '\n')
    
    # Regex to find citation markers like [1], [2]...
    citation_pattern = re.compile(r'(?:^|\n)(\[\d+\])')
    parts = citation_pattern.split(refs_text)
    
    references = []
    # If len(parts) < 2, it means we didn't find [N] markers. 
    # For now, return the whole blob as one item or empty list? 
    # Let's return empty and handle it, or maybe return [refs_text] if non-empty?
    # User asked for 'extract references', implies list.
    if len(parts) < 2:
         # Fallback: if no [N] markers found, maybe return the whole thing?
         # But the user logic specifically relied on [N].
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