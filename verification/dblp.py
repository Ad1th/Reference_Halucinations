# Queries DBLP API for publication metadata; gets titles from checker.py and sends candidate matches back [Verification logic integration pending].
import requests
from typing import List, Dict
from verification.utils import clean_title

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
