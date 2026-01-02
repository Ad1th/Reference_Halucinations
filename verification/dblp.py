# Queries DBLP API for publication metadata; gets titles from checker.py and sends candidate matches back [Verification logic integration pending].
#updating this to get titles from extractTitles, which are extracted from the XML using BeautifulSoup, which is extracted from the PDF using GROBID.
import requests
from typing import List, Dict
from verification.utils import clean_title
from difflib import SequenceMatcher

SIMILARITY_THRESHOLD = 0.7  # Updated from 0.6 to require higher confidence
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


def verify_title_with_dblp(title: str, authors: List[str] = None) -> Dict:
    """
    Verifies whether a title exists in DBLP.
    For short titles (<=4 words), also tries author-based search.

    Returns:
    {
        input_title,
        status: FOUND | NOT_FOUND | AMBIGUOUS,
        confidence,
        dblp_metadata: {title, authors, year, venue, type, doi, url, pages, volume}
    }
    """
    # Standard title search
    dblp_response = query_dblp(normalize_query(title))
    candidates = extract_candidates(dblp_response)
    
    # For short titles, also try author-based search
    words = len(title.split())
    if words <= 4 and authors:
        first_author = authors[0].split()[-1] if authors else ""  # Last name
        if first_author:
            author_query = f"{title} {first_author}"
            author_response = query_dblp(author_query)
            author_candidates = extract_candidates(author_response)
            # Merge candidates, avoiding duplicates
            seen_titles = {c["title"].lower() for c in candidates}
            for ac in author_candidates:
                if ac["title"].lower() not in seen_titles:
                    candidates.append(ac)
                    seen_titles.add(ac["title"].lower())

    if not candidates:
        return {
            "input_title": title,
            "status": "NOT_FOUND",
            "confidence": 0.0,
            "dblp_metadata": None
        }

    scored = []
    for c in candidates:
        raw_score = title_similarity(title, c["title"])
        penalty = length_penalty(title, raw_score)
        score = raw_score * penalty
        scored.append((score, raw_score, c))

    scored.sort(reverse=True, key=lambda x: x[0])
    best_score, best_raw, best_match = scored[0]

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
                "candidates": [c["title"] for _, _, c in scored[:2]],
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


def length_penalty(title: str, raw_similarity: float = 0.0) -> float:
    """
    Penalize very short / generic titles, BUT reduce penalty for near-exact matches.
    
    For classic papers like "Random forests" or "Bagging predictors", 
    if the raw similarity is very high (>0.9), we trust it more.
    """
    words = len(title.split())
    
    # Near-exact matches for short titles should be trusted
    if raw_similarity > 0.95:
        # Very high similarity - minimal penalty even for short titles
        if words <= 2:
            return 0.85
        if words <= 3:
            return 0.9
        if words <= 5:
            return 0.95
        return 1.0
    elif raw_similarity > 0.85:
        # Good similarity - reduced penalty
        if words <= 2:
            return 0.75
        if words <= 3:
            return 0.8
        if words <= 5:
            return 0.85
        return 1.0
    else:
        # Standard penalty for lower similarity
        if words <= 3:
            return 0.5
        if words <= 5:
            return 0.75
        return 1.0


def classify_reference(result: Dict) -> Dict:
    """
    Assign final reference category.
    
    Short titles (<=4 words) are only marked SUSPICIOUS if:
    - NOT_FOUND in DBLP AND
    - Confidence is low (suggests no good partial match either)
    """
    title = result["input_title"]
    words = len(title.split())
    conf = result.get("confidence", 0.0)

    if result["status"] == "FOUND":
        result["final_label"] = "VERIFIED"

    elif result["status"] == "AMBIGUOUS":
        result["final_label"] = "REVIEW"

    else:  # NOT_FOUND
        # Short titles with low confidence are suspicious
        # But if there's some confidence (partial match), it might just be a variant
        if words <= 4 and conf < 0.3:
            result["final_label"] = "SUSPICIOUS"
        else:
            result["final_label"] = "UNVERIFIED"

    return result