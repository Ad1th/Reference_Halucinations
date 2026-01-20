import requests
import time
from typing import List, Dict, Optional
from verification.utils import clean_title, fix_grobid_title_errors
from difflib import SequenceMatcher

SIMILARITY_THRESHOLD = 0.7  # Updated from 0.6 to require higher confidence
AMBIGUITY_GAP = 0.05

DBLP_API_URL = "https://dblp.org/search/publ/api"

def query_dblp(title: str, num_results: int = 5) -> dict:
    time.sleep(1.0) # Polite rate limiting
    params = {"q": title, "format": "json", "h": num_results}
    headers = {"User-Agent": "HalluciCheck/0.1 (mailer@example.com)"} # Added contact info as per DBLP polite policy
    try:
        response = requests.get(DBLP_API_URL, params=params, headers=headers, timeout=10)
        if response.status_code == 429:
            print("  [DBLP] Rate limited! Sleeping for 5s...")
            time.sleep(5)
            # Retry once
            response = requests.get(DBLP_API_URL, params=params, headers=headers, timeout=10)
        
        return response.json() if response.status_code == 200 else {}
    except:
        return {}


def query_dblp_with_author(title: str, author: str, num_results: int = 10) -> dict:
    """Query DBLP with title and author name for better matching."""
    # Try combining title and author in query
    time.sleep(1.0) # Polite rate limiting
    query = f"{title} {author}"
    params = {"q": query, "format": "json", "h": num_results}
    headers = {"User-Agent": "HalluciCheck/0.1 (mailer@example.com)"}
    try:
        response = requests.get(DBLP_API_URL, params=params, headers=headers, timeout=10)
        if response.status_code == 429:
            print("  [DBLP] Rate limited! Sleeping for 5s...")
            time.sleep(5)
            # Retry once
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


def author_overlap_score(authors1: List[str], authors2: List[str]) -> float:
    """Calculate author overlap between two author lists."""
    if not authors1 or not authors2:
        return 0.0
    
    # Normalize author names (last name only, lowercase)
    def normalize(name: str) -> str:
        # Handle "Firstname Lastname" or "Lastname, Firstname"
        parts = name.replace(',', ' ').split()
        # Take the last word as surname (simplified)
        return parts[-1].lower() if parts else ""
    
    norm1 = set(normalize(a) for a in authors1 if a)
    norm2 = set(normalize(a) for a in authors2 if a)
    
    if not norm1 or not norm2:
        return 0.0
    
    overlap = len(norm1 & norm2)
    return overlap / max(len(norm1), len(norm2))


def verify_title_with_dblp(title: str, authors: Optional[List[str]] = None) -> Dict:
    """
    Verifies whether a title exists in DBLP.
    If authors are provided, uses them to improve matching for short/ambiguous titles.

    Returns:
    {
        input_title,
        status: FOUND | NOT_FOUND | LOW_CONFIDENCE | AMBIGUOUS,
        confidence,
        dblp_metadata: {title, authors, year, venue, type, doi, url, pages, volume}
    }
    """
    # First try title-only search
    dblp_response = query_dblp(normalize_query(title), num_results=10)
    candidates = extract_candidates(dblp_response)
    
    # Also search with author if we have authors (helps with common/short titles)
    # This catches cases where title alone returns wrong papers
    if authors:
        first_author = authors[0].split()[-1] if authors else ""  # Last name
        if first_author:
            author_response = query_dblp_with_author(title, first_author, num_results=10)
            author_candidates = extract_candidates(author_response)
            # Merge candidates, avoiding duplicates
            existing_titles = {c["title"].lower() for c in candidates}
            for c in author_candidates:
                if c["title"].lower() not in existing_titles:
                    candidates.append(c)

    if not candidates:
        return {
            "input_title": title,
            "status": "NOT_FOUND",
            "confidence": 0.0,
            "dblp_metadata": None
        }

    # Score candidates by both title similarity AND author overlap
    scored = []
    for c in candidates:
        raw_title_score = title_similarity(title, c["title"])
        penalty = length_penalty(title)
        
        # For near-exact title matches (>0.95), reduce the length penalty impact
        # A perfect title match is strong evidence even for short titles
        if raw_title_score > 0.95:
            penalty = max(penalty, 0.9)  # At least 0.9 for near-exact matches
        elif raw_title_score > 0.90:
            penalty = max(penalty, 0.85)  # Reduced penalty for very good matches
            
        base_score = raw_title_score * penalty
        
        # If we have authors, factor in author matching
        if authors and c.get("authors"):
            author_score = author_overlap_score(authors, c["authors"])
            # Combined score: weighted average
            # For short titles, weight author more heavily
            if len(title.split()) <= 4:
                combined = base_score * 0.4 + author_score * 0.6
            else:
                combined = base_score * 0.7 + author_score * 0.3
            scored.append((combined, base_score, author_score, c))
        else:
            scored.append((base_score, base_score, 0.0, c))

    scored.sort(reverse=True, key=lambda x: x[0])
    best_combined, best_title_score, best_author_score, best_match = scored[0]

    # Use combined score for threshold check
    if best_combined < SIMILARITY_THRESHOLD:
        # Still include metadata for author matching - low title similarity
        # might still be the right paper (short titles, abbreviations, etc.)
        return {
            "input_title": title,
            "status": "LOW_CONFIDENCE",
            "confidence": round(best_combined, 3),
            "title_similarity": round(best_title_score, 3),
            "author_similarity": round(best_author_score, 3),
            "dblp_metadata": best_match  # ALWAYS include for author matching
        }

    # Ambiguity check
    if len(scored) > 1:
        second_combined = scored[1][0]
        if abs(best_combined - second_combined) < AMBIGUITY_GAP:
            return {
                "input_title": title,
                "status": "AMBIGUOUS",
                "confidence": round(best_combined, 3),
                "candidates": [c["title"] for _, _, _, c in scored[:2]],
                "dblp_metadata": best_match  # Include best match metadata
            }

    return {
        "input_title": title,
        "status": "FOUND",
        "confidence": round(best_combined, 3),
        "matched_title": best_match["title"],
        "year": best_match.get("year"),
        "dblp_metadata": best_match  # Full metadata from DBLP
    }

def normalize_query(title: str) -> str:
    """
    Shorten and normalize title for DBLP search.
    Also fixes common GROBID extraction errors.
    """
    title = clean_title(title)
    title = fix_grobid_title_errors(title)  # Fix compound word errors
    tokens = title.split()
    return " ".join(tokens[:8])  # Increased from 6 to 8 for better matching


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

    elif result["status"] == "LOW_CONFIDENCE":
        # Has a DBLP candidate but low title similarity
        # Map weak matches to UNVERIFIED to be re-checked by author matching or Gemini
        # Unless confidence is decent (candidate might be correct)
        if conf > 0.4:
            result["final_label"] = "REVIEW"
        else:
            result["final_label"] = "UNVERIFIED"

    else:  # NOT_FOUND
        result["final_label"] = "UNVERIFIED"

    return result