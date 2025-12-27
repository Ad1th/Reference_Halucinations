import requests
from typing import List, Dict, Optional
from ..utils.text import clean_title

DBLP_API_URL = "https://dblp.org/search/publ/api"

def query_dblp(title: str) -> dict:
    """Queries the DBLP API for a given publication title."""
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

def extract_authors(authors_block: Dict) -> List[str]:
    """Extracts author names from the DBLP response info block."""
    authors = authors_block.get("author", [])
    if isinstance(authors, list):
        return [a.get("text") if isinstance(a, dict) else a for a in authors]
    if isinstance(authors, dict):
        return [authors.get("text")]
    if isinstance(authors, str):
        return [authors]
    return []

def extract_candidates(dblp_response: dict) -> list:
    """Extract candidate publications from DBLP response."""
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
            "year": info.get("year"),
            "dblp_id": info.get("key"),
            "url": info.get("url")
        })
    return candidates
