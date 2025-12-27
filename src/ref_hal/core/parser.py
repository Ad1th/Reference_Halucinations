import re

def extract_title(reference_text: str) -> str:
    """Attempts to isolate the title from a reference string."""
    # Heuristic: Find first quoted string or segment between authors and venue
    # This is a placeholder for more advanced parsing logic
    
    # 1. Look for quoted text
    quoted = re.search(r'["“](.*?)["”]', reference_text)
    if quoted:
        return quoted.group(1).strip()
    
    # 2. Look for text between marker and first period (very naive)
    # [1] Author, "Title", Venue -> Title
    # [1] Author. Title. Venue -> Title
    # Remove citation marker [N]
    clean_ref = re.sub(r'^\[\d+\]\s*', '', reference_text)
    
    # Try to find a pattern: Lastname, Firstname, "Title", ...
    # Or: Lastname, Title, Year.
    parts = clean_ref.split('.')
    if len(parts) > 1:
        # Often the second part is the title if authors come first
        # But this is very brittle. 
        # For now, let's just return the first part after authors if we can find it.
        # Just returning the whole thing minus marker for now if no quotes found
        return parts[0].strip()
        
    return clean_ref
