# Orchestrates the reference verification workflow; gets data from extraction modules and sends final results to main.py.
from extraction.pdf import get_references
from extraction.parser import extract_title
from verification.dblp import query_dblp, extract_candidates
from verification.utils import title_similarity

def verify_references(pdf_path: str):
    references = get_references(pdf_path)
    results = []
    
    for ref in references:
        title = extract_title(ref)
        results.append({
            "reference": ref,
            "extracted_title": title,
            "status": "NOT_CHECKED"
        })
    return results
