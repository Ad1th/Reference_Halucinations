# Orchestrates the reference verification workflow; gets data from extraction modules and sends final results to main.py.
from extraction.pdf import get_references
from extraction.parser import extract_title
from verification.dblp import query_dblp, extract_candidates
from verification.utils import title_similarity

# This file calls  parser and pdf.py to extract references and their titles manually by regex.
# Then it calls dblp.py to query DBLP for the titles.
# Then it calls utils.py to calculate the similarity between the extracted titles and the DBLP titles.
# This can be modified to be used as a fallback if the GROBID does not work.


def verify_references(pdf_path: str):
    references = get_references(pdf_path)
    results = []
    
    # Set to False to disable DBLP API lookups and speed up extraction, and True if we want to verify the references with DBLP.
    ENABLE_DBLP_CHECK = False 

    for ref in references:
        title = extract_title(ref)
        result = {
            "reference": ref,
            "extracted_title": title,
            "status": "NOT_CHECKED",
            "confidence": 0.0,
            "matched_title": None
        }

        if ENABLE_DBLP_CHECK and title:
            dblp_res = query_dblp(title)
            candidates = extract_candidates(dblp_res)
            
            best_match = None
            max_score = 0.0
            
            for candidate in candidates:
                score = title_similarity(title, candidate["title"])
                if score > max_score:
                    max_score = score
                    best_match = candidate
            
            if best_match and max_score >= 0.6: # SIMILARITY_THRESHOLD
                result["status"] = "FOUND"
                result["confidence"] = round(max_score, 3)
                result["matched_title"] = best_match["title"]
                result["match_info"] = best_match
            else:
                result["status"] = "NOT_FOUND"
                result["confidence"] = round(max_score, 3)
        
        results.append(result)
    return results
