# Extracts raw reference strings from PDF files; gets data from .pdf files and sends list of strings to verification/checker.py.
import os
import re
import pdfplumber
from verification.utils import normalize_newlines

def get_references(pdf_path: str) -> list[str]:
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF missing: {pdf_path}")
    texts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            # Lowering x_tolerance (default is 3) ensures smaller gaps between characters are treated as spaces.
            t = page.extract_text(x_tolerance=1.5)
            if t: texts.append(t)
    text = normalize_newlines("\n".join(texts))
    match = re.search(r'(?i)(?:\n|^)\s*(?:[0-9]+\.?\s*)?(?:References|Bibliography)\s*(?:\n|$)', text)
    if not match: return []
    refs_text = text[match.end():].strip()
    citation_pattern = re.compile(r'(?:^|\n)(\[\d+\])')
    parts = citation_pattern.split(refs_text)
    references = []
    i = 1
    while i < len(parts):
        content = (parts[i] + " " + parts[i+1]).strip()
        references.append(re.sub(r'\s+', ' ', content))
        i += 2
    return references
