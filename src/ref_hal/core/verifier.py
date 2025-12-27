from .extractor import get_references
from .parser import extract_title
from ..services.dblp import query_dblp, extract_candidates
from ..utils.text import title_similarity

SIMILARITY_THRESHOLD = 0.6

def verify_references(pdf_path: str):
    """
    Full workflow: Extract references -> Extract titles -> Verify via DBLP.
    """
    references = get_references(pdf_path)
    results = []
    
    for ref in references:
        title = extract_title(ref)
        verification = {
            "reference": ref,
            "extracted_title": title,
            "status": "NOT_CHECKED",
            "match": None
        }
        
        if title:
            dblp_res = query_dblp(title)
            candidates = extract_candidates(dblp_res)
            
            best_match = None
            max_score = 0.0
            
            for candidate in candidates:
                score = title_similarity(title, candidate["title"])
                if score > max_score:
                    max_score = score
                    best_match = candidate
            
            if best_match and max_score >= SIMILARITY_THRESHOLD:
                verification["status"] = "FOUND"
                verification["confidence"] = round(max_score, 3)
                verification["match"] = best_match
            else:
                verification["status"] = "NOT_FOUND"
                verification["confidence"] = round(max_score, 3)
        
        results.append(verification)
    
    return results
