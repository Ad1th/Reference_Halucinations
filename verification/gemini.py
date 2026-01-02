"""
Gemini API integration for metadata matching and title extraction.
Uses Google's Gemini API for:
1. Metadata comparison between GROBID and DBLP results
2. Extracting titles from raw PDF text for fallback verification
"""
import os
import json
import time
import requests
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# Try different models in order of preference
GEMINI_MODELS = [
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b", 
    "gemini-2.0-flash",
]
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def call_gemini(prompt: str, max_tokens: int = 2048, retries: int = 3) -> Optional[str]:
    """
    Call Gemini API with a prompt and return the response text.
    Tries multiple models if one fails.
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not found in environment variables")
    
    headers = {"Content-Type": "application/json"}
    params = {"key": GEMINI_API_KEY}
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": 0.1  # Low temperature for consistent results
        }
    }
    
    for model in GEMINI_MODELS:
        url = f"{GEMINI_API_BASE}/{model}:generateContent"
        
        for attempt in range(retries):
            try:
                response = requests.post(
                    url,
                    headers=headers,
                    params=params,
                    json=payload,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    candidates = result.get("candidates", [])
                    if candidates:
                        content = candidates[0].get("content", {})
                        parts = content.get("parts", [])
                        if parts:
                            return parts[0].get("text", "")
                    return None
                
                elif response.status_code == 429:
                    # Rate limited - wait and retry
                    wait_time = (attempt + 1) * 10
                    print(f"Rate limited on {model}, waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                
                else:
                    # Try next model
                    print(f"Model {model} failed with {response.status_code}, trying next...")
                    break
                    
            except Exception as e:
                print(f"Error with {model}: {e}")
                if attempt < retries - 1:
                    time.sleep(2)
                    continue
                break
    
    return None


def gemini_metadata_match(grobid_ref: Dict, dblp_metadata: Dict) -> Dict:
    """
    Use Gemini to compare GROBID extracted metadata with DBLP metadata.
    
    Returns:
        {
            "match": True/False,
            "confidence": 0.0-1.0,
            "reasoning": str,
            "field_matches": {title, authors, year, venue}
        }
    """
    prompt = f"""Compare these two bibliographic references and determine if they refer to the SAME publication.

REFERENCE FROM PDF (GROBID extraction):
- Title: {grobid_ref.get('title', 'N/A')}
- Authors: {', '.join(grobid_ref.get('authors', [])) if grobid_ref.get('authors') else 'N/A'}
- Year: {grobid_ref.get('year', 'N/A')}
- Venue: {grobid_ref.get('venue', 'N/A')}

REFERENCE FROM DBLP DATABASE:
- Title: {dblp_metadata.get('title', 'N/A')}
- Authors: {', '.join(dblp_metadata.get('authors', [])) if dblp_metadata.get('authors') else 'N/A'}
- Year: {dblp_metadata.get('year', 'N/A')}
- Venue: {dblp_metadata.get('venue', 'N/A')}

Consider:
1. Title similarity (ignore case, minor differences like periods, hyphens)
2. Author overlap (names may have variations, missing middle names, initials)
3. Year (may differ by 1-2 years between preprint and publication)
4. Venue (conference/journal names may be abbreviated differently)

Respond ONLY with valid JSON in this exact format:
{{"match": true/false, "confidence": 0.0-1.0, "reasoning": "brief explanation", "field_matches": {{"title": true/false, "authors": true/false, "year": true/false, "venue": true/false}}}}
"""
    
    response = call_gemini(prompt)
    
    if not response:
        return {"match": False, "confidence": 0.0, "reasoning": "Gemini API failed", "field_matches": {}}
    
    try:
        # Extract JSON from response (handle markdown code blocks)
        json_str = response.strip()
        if json_str.startswith("```"):
            json_str = json_str.split("```")[1]
            if json_str.startswith("json"):
                json_str = json_str[4:]
        json_str = json_str.strip()
        
        result = json.loads(json_str)
        return result
    except json.JSONDecodeError:
        return {"match": False, "confidence": 0.0, "reasoning": f"Failed to parse Gemini response: {response[:200]}", "field_matches": {}}


def gemini_extract_titles_from_text(raw_text: str, problematic_titles: List[str]) -> List[Dict]:
    """
    Use Gemini to extract and correct titles from raw PDF reference text.
    
    Args:
        raw_text: Raw text from PDF containing references section
        problematic_titles: List of titles that failed verification (to focus extraction)
    
    Returns:
        List of {original_title, corrected_title, authors, year} dicts
    """
    # Truncate text if too long
    if len(raw_text) > 15000:
        raw_text = raw_text[:15000]
    
    titles_str = "\n".join([f"- {t}" for t in problematic_titles[:20]])  # Limit to 20
    
    prompt = f"""I have a PDF with references that were incorrectly extracted. Here are the problematic titles:

{titles_str}

Below is the raw text from the references section of the PDF. Please find the CORRECT full titles and metadata for the problematic references listed above.

RAW REFERENCE TEXT:
{raw_text}

For each problematic title, provide the corrected information. Respond ONLY with valid JSON array:
[
  {{"original": "original problematic title", "corrected_title": "correct full title", "authors": ["Author1", "Author2"], "year": "YYYY"}},
  ...
]

If a title cannot be found or corrected, set corrected_title to null.
"""
    
    response = call_gemini(prompt, max_tokens=4096)
    
    if not response:
        return []
    
    try:
        json_str = response.strip()
        if json_str.startswith("```"):
            json_str = json_str.split("```")[1]
            if json_str.startswith("json"):
                json_str = json_str[4:]
        json_str = json_str.strip()
        
        result = json.loads(json_str)
        return result if isinstance(result, list) else []
    except json.JSONDecodeError:
        return []


def gemini_verify_reference_exists(title: str, authors: List[str], year: str) -> Dict:
    """
    Ask Gemini to verify if a reference exists and provide correct metadata.
    
    This is a fallback for papers not found in DBLP (e.g., non-CS papers, books).
    
    Returns:
        {
            "exists": True/False/Unknown,
            "confidence": 0.0-1.0,
            "corrected_metadata": {title, authors, year, venue, type},
            "reasoning": str
        }
    """
    authors_str = ", ".join(authors) if authors else "Unknown"
    
    prompt = f"""Verify if this academic reference is a REAL publication:

Title: {title}
Authors: {authors_str}
Year: {year or 'Unknown'}

Based on your knowledge:
1. Does this publication exist?
2. If yes, provide the correct/complete metadata
3. What type of publication is it? (journal article, conference paper, book, book chapter, technical report, thesis, preprint)

IMPORTANT: Be conservative. If you're not certain, say "unknown".

Respond ONLY with valid JSON:
{{"exists": true/false/"unknown", "confidence": 0.0-1.0, "corrected_metadata": {{"title": "...", "authors": ["..."], "year": "...", "venue": "...", "type": "..."}}, "reasoning": "..."}}
"""
    
    response = call_gemini(prompt)
    
    if not response:
        return {"exists": "unknown", "confidence": 0.0, "corrected_metadata": None, "reasoning": "Gemini API failed"}
    
    try:
        json_str = response.strip()
        if json_str.startswith("```"):
            json_str = json_str.split("```")[1]
            if json_str.startswith("json"):
                json_str = json_str[4:]
        json_str = json_str.strip()
        
        result = json.loads(json_str)
        return result
    except json.JSONDecodeError:
        return {"exists": "unknown", "confidence": 0.0, "corrected_metadata": None, "reasoning": f"Parse error: {response[:200]}"}


def gemini_batch_verify(references: List[Dict]) -> Dict[int, Dict]:
    """
    Verify multiple references in a single Gemini call to avoid rate limiting.
    
    Args:
        references: List of dicts with ref_num, grobid_title, grobid_authors, 
                   grobid_year, dblp_title, dblp_authors, dblp_year, current_confidence
    
    Returns:
        Dict mapping ref_num to verification result
    """
    if not references:
        return {}
    
    # Build the reference list for the prompt
    refs_text = ""
    for i, ref in enumerate(references, 1):
        refs_text += f"""
Reference #{ref['ref_num']}:
  PDF Title: {ref['grobid_title']}
  PDF Authors: {', '.join(ref['grobid_authors']) if ref['grobid_authors'] else 'N/A'}
  PDF Year: {ref['grobid_year'] or 'N/A'}
"""
        if ref.get('dblp_title'):
            refs_text += f"""  DBLP Match Title: {ref['dblp_title']}
  DBLP Authors: {', '.join(ref['dblp_authors']) if ref['dblp_authors'] else 'N/A'}
  DBLP Year: {ref['dblp_year'] or 'N/A'}
  Current Confidence: {ref['current_confidence']:.3f}
"""
        else:
            refs_text += "  (No DBLP match found)\n"
    
    prompt = f"""Analyze these academic references and verify if they are real publications.

For references WITH a DBLP match: Determine if the PDF reference and DBLP match refer to the SAME publication.
For references WITHOUT a DBLP match: Determine if the reference appears to be a real publication (may be from non-CS venues, books, etc.)

{refs_text}

For EACH reference, provide:
1. verified: true if you're confident this is a real, correctly matched publication
2. exists: true/false if the publication exists at all (use false only if likely hallucinated)
3. confidence: 0.0-1.0 
4. reasoning: brief explanation

Be GENEROUS with verification for references that have matching DBLP data - small title variations, author name differences (initials, middle names), and year differences of 1-2 years are normal.

Respond with a JSON object mapping ref_num to result:
{{
  "1": {{"verified": true/false, "exists": true/false, "confidence": 0.9, "reasoning": "Authors and title match well"}},
  "2": {{"verified": false, "exists": true, "confidence": 0.5, "reasoning": "Title similar but authors don't match"}},
  ...
}}

ONLY output valid JSON, no explanation outside the JSON.
"""
    
    response = call_gemini(prompt, max_tokens=4096)
    
    if not response:
        return {}
    
    try:
        json_str = response.strip()
        if json_str.startswith("```"):
            json_str = json_str.split("```")[1]
            if json_str.startswith("json"):
                json_str = json_str[4:]
        json_str = json_str.strip()
        
        result = json.loads(json_str)
        
        # Convert string keys to int
        return {int(k): v for k, v in result.items()}
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Failed to parse Gemini batch response: {e}")
        print(f"Response was: {response[:500]}")
        return {}


if __name__ == "__main__":
    # Quick test
    test_grobid = {
        "title": "Random forests",
        "authors": ["Leo Breiman"],
        "year": "2001"
    }
    test_dblp = {
        "title": "Random Forests.",
        "authors": ["Leo Breiman"],
        "year": "2001",
        "venue": "Machine Learning"
    }
    
    print("Testing Gemini metadata match...")
    result = gemini_metadata_match(test_grobid, test_dblp)
    print(json.dumps(result, indent=2))
