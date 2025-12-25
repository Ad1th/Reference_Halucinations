import requests
from difflib import SequenceMatcher
from typing import List, Dict, Optional
import re


DBLP_API_URL = "https://dblp.org/search/publ/api"
SIMILARITY_THRESHOLD = 0.6

def query_dblp(title: str) -> dict:
    params = {
        "q": title,
        "format": "json",
        "h": 10
    }

    headers = {
        "User-Agent": "HalluciCheck/0.1 (academic-research)"
    }

    try:
        response = requests.get(
            DBLP_API_URL,
            params=params,
            headers=headers,
            timeout=10
        )
        if response.status_code != 200:
            return {}
        return response.json()
    except requests.RequestException:
        return {}

def clean_title(title: str) -> str:
    if not title:
        return ""
    return re.sub(r"<[^>]+>", "", title)

def extract_candidates(dblp_response: dict) -> list:
    """
    Extract candidate publications from DBLP response.
    Returns list of dicts:
    {
        'title': str,
        'authors': list[str],
        'venue': str,
        'year': int,
        'dblp_id': str
    }
    """
    candidates = []

    hits = dblp_response.get("result", {}).get("hits", {}).get("hit", [])

    if isinstance(hits, dict):
        hits = [hits]

    for hit in hits:
        info = hit.get("info", {})

        candidates.append({
    "title": clean_title(info.get("title")),
    "authors": extract_authors(info.get("authors", {})),
    "venue": info.get("venue"),
    "year": safe_int(info.get("year")),
    "dblp_id": info.get("key")
    })

    return candidates



def extract_authors(authors_block: Dict) -> List[str]:
    """
    Normalize author information from DBLP.

    Args:
        authors_block (dict): DBLP authors field.

    Returns:
        List[str]: List of author names.
    """
    authors = authors_block.get("author", [])
    if isinstance(authors, list):
        return authors
    if isinstance(authors, dict):
        return [authors.get("text")]
    if isinstance(authors, str):
        return [authors]
    return []




def safe_int(value) -> Optional[int]:
    """
    Safely convert value to int.

    Args:
        value: Input value.

    Returns:
        int or None
    """
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

def title_similarity(input_title: str, dblp_title: str) -> float:
    """
    Compute similarity score between two titles.
    Returns value in [0, 1].
    """
    if not input_title or not dblp_title:
        return 0.0
    return SequenceMatcher(None, input_title.lower(), dblp_title.lower()).ratio()

def find_best_match(title: str, candidates: list):
    """
    Returns best matching candidate and its similarity score.
    If no reasonable match, returns None.
    """
    best_match = None
    best_score = 0.0

    for candidate in candidates:
        score = title_similarity(title, candidate.get("title"))
        if score > best_score:
            best_score = score
            best_match = candidate

    if best_score < SIMILARITY_THRESHOLD:
        return None

    best_match["confidence"] = round(best_score, 3)
    return best_match

def verify_title(title: str) -> dict:
    """
    Verify whether a title exists in DBLP.
    Returns:
    {
        'input_title': str,
        'status': 'FOUND' | 'NOT_FOUND' | 'AMBIGUOUS',
        'confidence': float,
        'matched_title': str | None,
        'authors': list[str],
        'venue': str,
        'year': int
    }
    """
    dblp_response = query_dblp(title)
    candidates = extract_candidates(dblp_response)
    match = find_best_match(title, candidates)

    if not match:
        return {
            "input_title": title,
            "status": "NOT_FOUND",
            "confidence": 0.0
        }

    return {
        "input_title": title,
        "status": "FOUND",
        "confidence": match.get("confidence"),
        "matched_title": match.get("title"),
        "authors": match.get("authors"),
        "venue": match.get("venue"),
        "year": match.get("year"),
        "dblp_id": match.get("dblp_id")
    }

if __name__ == "__main__":
    test_title = "The Google File System"
    result = verify_title(test_title)
    print(result)