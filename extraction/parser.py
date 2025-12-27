# Isolates paper titles from raw reference strings; gets strings from pdf.py and sends cleaned titles to checker.py.
import re

def extract_title(reference_text: str) -> str:
    """
    Isolates the title from an academic reference string.
    Expected format: [N] Authors. Year. Title. Venue.
    """
    # 1. Remove the citation marker [N]
    clean_ref = re.sub(r'^\[\d+\]\s*', '', reference_text).strip()
    
    # 2. Heuristic: Quoted text is almost always the title
    quoted = re.search(r'["“](.*?)["”]', clean_ref)
    if quoted:
        return quoted.group(1).strip()
    
    # 3. Split by periods
    # Most ACM/IEEE refs are: Authors. Year. Title. Venue.
    parts = [p.strip() for p in clean_ref.split('.') if p.strip()]
    
    # Filter out very short parts like 'n' or 'd' from [n.d.]
    parts = [p for p in parts if len(p) > 2 or p.isdigit()]
    
    if len(parts) >= 3:
        # Check if parts[1] is a year (4 digits) or [n.d.]
        if re.match(r'^\d{4}$', parts[1]) or "n.d" in parts[1].lower():
            return parts[2]
        return parts[1]
        
    if len(parts) > 1:
        return parts[1]
        
    return clean_ref
