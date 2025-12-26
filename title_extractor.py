import re

def extract_title(reference_entry: str) -> str:
    """Attempt to extract the title from a reference string using heuristics."""
    # Heuristic 1: Text within quotes (standard for many citation styles)
    # Matches "Title," or "Title." or just "Title"
    match = re.search(r'[“"](.*?)[”"]', reference_entry)
    if match:
        return match.group(1)
    
    return ""
