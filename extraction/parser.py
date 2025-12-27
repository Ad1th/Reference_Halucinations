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
    
    if len(parts) >= 3:
        # Check if parts[1] is a year (4 digits)
        if re.match(r'^\d{4}$', parts[1]):
            # If parts[1] is the year, parts[2] is likely the title
            return parts[2]
        
        # If parts[0] is authors and there is no year part, 
        # parts[1] might be the title
        return parts[1]
        
    # Fallback to the second part if we have at least authors + title
    if len(parts) > 1:
        return parts[1]
        
    return clean_ref
