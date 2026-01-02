# Queries DBLP API for publication metadata; gets titles from checker.py and sends candidate matches back [Verification logic integration pending].
#updating this to get titles from extractTitles, which are extracted from the XML using BeautifulSoup, which is extracted from the PDF using GROBID.
import requests
from typing import List, Dict
from verification.utils import clean_title
from difflib import SequenceMatcher

SIMILARITY_THRESHOLD = 0.6
AMBIGUITY_GAP = 0.05

DBLP_API_URL = "https://dblp.org/search/publ/api"

def query_dblp(title: str) -> dict:
    params = {"q": title, "format": "json", "h": 5}
    headers = {"User-Agent": "HalluciCheck/0.1"}
    try:
        response = requests.get(DBLP_API_URL, params=params, headers=headers, timeout=10)
        return response.json() if response.status_code == 200 else {}
    except:
        return {}

def extract_candidates(dblp_response: dict) -> list:
    """Extract candidate matches from DBLP response with full metadata."""
    candidates = []
    hits = dblp_response.get("result", {}).get("hits", {}).get("hit", [])
    if isinstance(hits, dict): hits = [hits]
    for hit in hits:
        info = hit.get("info", {})
        
        # Extract authors - can be a list or single dict
        authors_data = info.get("authors", {}).get("author", [])
        if isinstance(authors_data, dict):
            authors_data = [authors_data]
        
        # Normalize author format - can be string or dict with "text" key
        authors = []
        for a in authors_data:
            if isinstance(a, str):
                authors.append(a)
            elif isinstance(a, dict):
                authors.append(a.get("text", ""))
        
        candidates.append({
            "title": clean_title(info.get("title")),
            "authors": authors,
            "year": info.get("year"),
            "venue": info.get("venue"),
            "type": info.get("type"),  # e.g., "Conference and Workshop Papers"
            "doi": info.get("doi"),
            "url": info.get("url"),
            "pages": info.get("pages"),
            "volume": info.get("volume")
        })
    return candidates

def title_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def verify_title_with_dblp(title: str) -> Dict:
    """
    Verifies whether a title exists in DBLP.

    Returns:
    {
        input_title,
        status: FOUND | NOT_FOUND | AMBIGUOUS,
        confidence,
        dblp_metadata: {title, authors, year, venue, type, doi, url, pages, volume}
    }
    """
    dblp_response = query_dblp(normalize_query(title))
    candidates = extract_candidates(dblp_response)

    if not candidates:
        return {
            "input_title": title,
            "status": "NOT_FOUND",
            "confidence": 0.0,
            "dblp_metadata": None
        }

    scored = []
    for c in candidates:
        base = title_similarity(title, c["title"])
        penalty = length_penalty(title)
        score = base * penalty
        scored.append((score, c))

    scored.sort(reverse=True, key=lambda x: x[0])
    best_score, best_match = scored[0]

    if best_score < SIMILARITY_THRESHOLD:
        return {
            "input_title": title,
            "status": "NOT_FOUND",
            "confidence": round(best_score, 3),
            "dblp_metadata": None
        }

    # Ambiguity check
    if len(scored) > 1:
        second_score = scored[1][0]
        if abs(best_score - second_score) < AMBIGUITY_GAP:
            return {
                "input_title": title,
                "status": "AMBIGUOUS",
                "confidence": round(best_score, 3),
                "candidates": [c["title"] for _, c in scored[:2]],
                "dblp_metadata": best_match  # Include best match metadata
            }

    return {
        "input_title": title,
        "status": "FOUND",
        "confidence": round(best_score, 3),
        "matched_title": best_match["title"],
        "year": best_match.get("year"),
        "dblp_metadata": best_match  # Full metadata from DBLP
    }

def normalize_query(title: str) -> str:
    """
    Shorten and normalize title for DBLP search.
    """
    title = clean_title(title)
    tokens = title.split()
    return " ".join(tokens[:6])  # first 6 tokens work best empirically


def length_penalty(title: str) -> float:
    """
    Penalize very short / generic titles.
    """
    words = len(title.split())
    if words <= 3:
        return 0.5
    if words <= 5:
        return 0.75
    return 1.0


def classify_reference(result: Dict) -> Dict:
    """
    Assign final reference category.
    """
    title = result["input_title"]
    words = len(title.split())
    conf = result.get("confidence", 0.0)

    if result["status"] == "FOUND":
        result["final_label"] = "VERIFIED"

    elif result["status"] == "AMBIGUOUS":
        result["final_label"] = "REVIEW"

    else:  # NOT_FOUND
        if words <= 4:
            result["final_label"] = "SUSPICIOUS"
        elif conf < 0.4:
            result["final_label"] = "UNVERIFIED"
        else:
            result["final_label"] = "UNVERIFIED"

    return result