"""
PDF text extraction using pdfplumber as fallback for GROBID failures.
Extracts raw text from the references section of a PDF.
"""
import re
from pathlib import Path
from typing import Optional, List, Dict

try:
    import pdfplumber
except ImportError:
    pdfplumber = None
    print("Warning: pdfplumber not installed. Run: pip install pdfplumber")


def extract_references_text(pdf_path: str) -> Optional[str]:
    """
    Extract raw text from the references section of a PDF.
    
    Returns the text starting from "References" heading to the end.
    """
    if not pdfplumber:
        raise ImportError("pdfplumber is required. Run: pip install pdfplumber")
    
    pdf = Path(pdf_path)
    if not pdf.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    
    full_text = ""
    
    with pdfplumber.open(pdf) as pdf_doc:
        for page in pdf_doc.pages:
            # Use layout extraction to preserve spaces between words
            # x_tolerance controls how close characters must be to be considered same word
            # y_tolerance controls line grouping
            text = page.extract_text(
                layout=True,
                x_tolerance=3,
                y_tolerance=3
            )
            if text:
                full_text += text + "\n"
    
    # If layout extraction produced text without spaces, try word-based extraction
    if full_text and _has_space_issues(full_text):
        full_text = _extract_with_words(pdf_path)
    
    # Find references section
    ref_patterns = [
        r'\n\s*References\s*\n',
        r'\n\s*REFERENCES\s*\n',
        r'\n\s*Bibliography\s*\n',
        r'\n\s*BIBLIOGRAPHY\s*\n',
    ]
    
    ref_start = None
    for pattern in ref_patterns:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            ref_start = match.start()
            break
    
    if ref_start is not None:
        return full_text[ref_start:]
    
    # If no explicit references section found, return last 30% of text
    # (references are usually at the end)
    cutoff = int(len(full_text) * 0.7)
    return full_text[cutoff:]


def _has_space_issues(text: str) -> bool:
    """
    Check if extracted text likely has spacing issues.
    Looks for long strings without spaces (e.g., concatenated words).
    """
    # Split into lines and check for abnormally long "words"
    for line in text.split('\n'):
        words = line.split()
        for word in words:
            # If a "word" is very long (>30 chars) and contains lowercase letters,
            # it's likely concatenated words
            if len(word) > 30 and any(c.islower() for c in word):
                return True
    return False


def _extract_with_words(pdf_path: str) -> str:
    """
    Extract text using word-level extraction with explicit spacing.
    This is more reliable for PDFs that don't preserve spaces well.
    """
    full_text = ""
    
    with pdfplumber.open(pdf_path) as pdf_doc:
        for page in pdf_doc.pages:
            # Extract individual words with positions
            words = page.extract_words(
                x_tolerance=3,
                y_tolerance=3,
                keep_blank_chars=True,
                use_text_flow=True
            )
            
            if not words:
                continue
            
            # Group words into lines based on y-position
            lines = []
            current_line = []
            current_y = None
            y_tolerance = 5  # pixels
            
            for word in words:
                word_y = word.get('top', 0)
                
                if current_y is None:
                    current_y = word_y
                    current_line.append(word['text'])
                elif abs(word_y - current_y) <= y_tolerance:
                    # Same line
                    current_line.append(word['text'])
                else:
                    # New line
                    if current_line:
                        lines.append(' '.join(current_line))
                    current_line = [word['text']]
                    current_y = word_y
            
            # Don't forget the last line
            if current_line:
                lines.append(' '.join(current_line))
            
            full_text += '\n'.join(lines) + '\n'
    
    return full_text


def extract_titles_with_regex(references_text: str) -> List[Dict]:
    """
    Extract reference titles using regex patterns.
    
    Common patterns:
    1. [1] Author. Year. Title. Venue.
    2. [1] Author, "Title", Venue, Year.
    3. Author et al. (Year) Title.
    """
    titles = []
    
    # Pattern 1: Numbered references [1], [2], etc.
    # Look for title after year or after author names
    pattern1 = r'\[(\d+)\]\s*([^[]+)'
    
    matches = re.findall(pattern1, references_text, re.MULTILINE)
    
    for num, content in matches:
        # Try to extract title from content
        # Common format: Authors. Year. Title. Venue.
        # Or: Authors. Title. Venue. Year.
        
        # Look for quoted titles
        quoted = re.search(r'"([^"]+)"', content)
        if quoted:
            titles.append({
                "ref_num": int(num),
                "title": quoted.group(1).strip(),
                "raw": content.strip()
            })
            continue
        
        # Look for title after year (e.g., "2020. Title Here.")
        year_title = re.search(r'\b(19|20)\d{2}\b[.\s]+([A-Z][^.]+\.)', content)
        if year_title:
            titles.append({
                "ref_num": int(num),
                "title": year_title.group(2).strip().rstrip('.'),
                "raw": content.strip()
            })
            continue
        
        # Fallback: take the longest sentence-like segment
        sentences = re.findall(r'([A-Z][^.]+\.)', content)
        if sentences:
            # Filter out author-like segments (contain "and", multiple commas)
            candidate_titles = [s for s in sentences 
                              if not re.search(r'\b(and|et al)\b', s.lower()) 
                              and s.count(',') < 3]
            if candidate_titles:
                # Take the longest one
                best = max(candidate_titles, key=len)
                titles.append({
                    "ref_num": int(num),
                    "title": best.strip().rstrip('.'),
                    "raw": content.strip()
                })
    
    return titles


def match_regex_titles_to_problematic(
    regex_titles: List[Dict],
    problematic_refs: List[Dict]
) -> List[Dict]:
    """
    Try to match regex-extracted titles to problematic references.
    
    Returns list of potential corrections.
    """
    from difflib import SequenceMatcher
    
    corrections = []
    
    for prob_ref in problematic_refs:
        prob_title = prob_ref.get("grobid", {}).get("title", "")
        if not prob_title:
            continue
        
        best_match = None
        best_score = 0.0
        
        for regex_ref in regex_titles:
            regex_title = regex_ref.get("title", "")
            if not regex_title:
                continue
            
            # Calculate similarity
            score = SequenceMatcher(None, prob_title.lower(), regex_title.lower()).ratio()
            
            if score > best_score and score > 0.5:
                best_score = score
                best_match = regex_ref
        
        if best_match and best_score > 0.6:
            corrections.append({
                "original_title": prob_title,
                "corrected_title": best_match["title"],
                "confidence": best_score,
                "raw_ref": best_match.get("raw", "")
            })
    
    return corrections


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python pdfplumber_extract.py <pdf_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    print(f"Extracting references from: {pdf_path}")
    refs_text = extract_references_text(pdf_path)
    
    print(f"\n{'='*60}")
    print("RAW REFERENCES TEXT (first 2000 chars):")
    print('='*60)
    print(refs_text[:2000] if refs_text else "No text extracted")
    
    print(f"\n{'='*60}")
    print("REGEX EXTRACTED TITLES:")
    print('='*60)
    titles = extract_titles_with_regex(refs_text)
    for t in titles[:20]:
        print(f"[{t['ref_num']}] {t['title']}")
