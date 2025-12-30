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
    candidates = []
    hits = dblp_response.get("result", {}).get("hits", {}).get("hit", [])
    if isinstance(hits, dict): hits = [hits]
    for hit in hits:
        info = hit.get("info", {})
        candidates.append({
            "title": clean_title(info.get("title")),
            "authors": info.get("authors", {}).get("author", []),
            "year": info.get("year")
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
        matched_title,
        year
    }
    """
    dblp_response = query_dblp(title)
    candidates = extract_candidates(dblp_response)

    if not candidates:
        return {
            "input_title": title,
            "status": "NOT_FOUND",
            "confidence": 0.0
        }

    scored = []
    for c in candidates:
        score = title_similarity(title, c["title"])
        scored.append((score, c))

    scored.sort(reverse=True, key=lambda x: x[0])
    best_score, best_match = scored[0]

    if best_score < SIMILARITY_THRESHOLD:
        return {
            "input_title": title,
            "status": "NOT_FOUND",
            "confidence": round(best_score, 3)
        }

    # Ambiguity check
    if len(scored) > 1:
        second_score = scored[1][0]
        if abs(best_score - second_score) < AMBIGUITY_GAP:
            return {
                "input_title": title,
                "status": "AMBIGUOUS",
                "confidence": round(best_score, 3),
                "candidates": [c["title"] for _, c in scored[:2]]
            }

    return {
        "input_title": title,
        "status": "FOUND",
        "confidence": round(best_score, 3),
        "matched_title": best_match["title"],
        "year": best_match.get("year")
    }