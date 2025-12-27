import re
from difflib import SequenceMatcher

def clean_title(title: str) -> str:
    """Removes HTML tags and extra whitespace from a title."""
    if not title:
        return ""
    # Remove HTML tags
    title = re.sub(r"<[^>]+>", "", title)
    # Remove extra whitespace
    title = " ".join(title.split())
    return title

def title_similarity(input_title: str, dblp_title: str) -> float:
    """Compute similarity score between two titles in range [0, 1]."""
    if not input_title or not dblp_title:
        return 0.0
    return SequenceMatcher(None, input_title.lower(), dblp_title.lower()).ratio()

def normalize_newlines(text: str) -> str:
    """Standardizes newlines in a text block."""
    return text.replace('\r\n', '\n').replace('\r', '\n')
