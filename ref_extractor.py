import argparse
import os
import sys
import re
import pdfplumber

def extract_references(pdf_path: str) -> str:
    """Open a PDF, extract text from pages (skipping pages with no text),
    and return the section after the first occurrence of 'References'.
    """
    if not os.path.exists(pdf_path):
        print(f"Error: file not found: {pdf_path}", file=sys.stderr)
        sys.exit(2)

    texts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                texts.append(t)

    text = "\n".join(texts)
    
    # Case-insensitive search for References header
    # We look for standalone lines or headers like "REFERENCES", "References", "Bibliography"
    # This regex looks for the word at the start of a line or preceded by newlines, possibly with numbering.
    match = re.search(r'(?i)(?:\n|^)\s*(?:[0-9]+\.?\s*)?(?:References|Bibliography)\s*(?:\n|$)', text)
    
    if match:
        return text[match.end():].strip()
        
    return ""


def extract_title(reference_entry: str) -> str:
    """Attempt to extract the title from a reference string using heuristics."""
    # Heuristic 1: Text within quotes (standard for many citation styles)
    # Matches "Title," or "Title." or just "Title"
    match = re.search(r'[“"](.*?)[”"]', reference_entry)
    if match:
        return match.group(1)
    
    return ""

def main():
    parser = argparse.ArgumentParser(description="Extract references section from a PDF file")
    parser.add_argument("file", nargs="?", default="paper.pdf", help="Path to the PDF file (default: paper.pdf)")
    args = parser.parse_args()

    refs_text = extract_references(args.file)
    if not refs_text:
        print("No References section found or PDF has no extractable text.")
        sys.exit(0)

    # Initial split by bracketed numbers (e.g. [1], [2])
    # This is a common format for CS/Engineering papers
    # We use a lookahead to split but keep the delimiter or just re-match
    
    # Simple split strategy: find [N] at start of lines or preceded by newline
    # But references line wrapping makes this tricky. 
    # Let's split by `\n[` which is a strong signal for new reference
    
    # Normalize newlines
    refs_text = refs_text.replace('\r\n', '\n')
    
    # Regex to find citation markers like [1], [2]...
    # We assume references start with [number]
    citation_pattern = re.compile(r'(?:^|\n)(\[\d+\])')
    
    parts = citation_pattern.split(refs_text)
    
    # parts[0] is usually empty or text before first citation
    # Then we have pairs: marker, content
    
    current_ref = ""
    references = []
    
    # If the text doesn't look like [1] format, just print raw text
    if len(parts) < 2:
        print("Could not parse individual references (format might not be [N]). Printing raw text:")
        print(refs_text)
        return

    # Skip first empty part if necessary
    start_idx = 1 if not parts[0].strip() else 0
    
    # Reconstruct references
    # parts list alternate between marker, text, marker, text
    # e.g. ['', '[1]', ' Author ...', '[2]', ' Author ...']
    
    i = 1
    while i < len(parts):
        marker = parts[i]
        content = parts[i+1] if i+1 < len(parts) else ""
        full_ref = (marker + " " + content).strip()
        # Clean up newlines within the reference (unwrap)
        full_ref_clean = re.sub(r'\s+', ' ', full_ref)
        
        references.append(full_ref_clean)
        i += 2

    for ref in references:
        print("-" * 40)
        print(f"Reference: {ref}")
        title = extract_title(ref)
        if title:
            print(f"Title: {title}")
        else:
            print("Title: (not found)")

if __name__ == "__main__":
    main()