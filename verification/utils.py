# Shared text utility functions; provides cleaning and similarity logic used by both extraction and verification modules.
import re
from difflib import SequenceMatcher
from typing import List, Tuple

def clean_title(title: str) -> str:
    """Removes HTML tags and extra whitespace from a title."""
    if not title:
        return ""
    # Remove HTML tags
    title = re.sub(r"<[^>]+>", "", title)
    # Remove extra whitespace
    title = " ".join(title.split())
    return title


def fix_grobid_title_errors(title: str) -> str:
    """
    Fix common GROBID extraction errors in titles.
    - Fix missing spaces in compound words (e.g., "schemabased" -> "schema-based")
    - Fix missing hyphens in compound terms
    """
    if not title:
        return ""
    
    # Common compound words that GROBID may concatenate
    # Format: (wrong, correct)
    compound_fixes = [
        (r'\bschemabased\b', 'schema-based'),
        (r'\bschemaagnostic\b', 'schema-agnostic'),
        (r'\bdatabased\b', 'data-based'),
        (r'\bdatadriven\b', 'data-driven'),
        (r'\bmultiway\b', 'multi-way'),
        (r'\bmultiscale\b', 'multi-scale'),
        (r'\bcrosssilo\b', 'cross-silo'),
        (r'\blowresource\b', 'low-resource'),
        (r'\bpretrained\b', 'pre-trained'),
        (r'\bfinetuning\b', 'fine-tuning'),
        (r'\bfinetune\b', 'fine-tune'),
        (r'\bprompttuning\b', 'prompt-tuning'),
        (r'\bzerolabeled\b', 'zero-labeled'),
        (r'\bzeroshot\b', 'zero-shot'),
        (r'\bfewshot\b', 'few-shot'),
        (r'\bendtoend\b', 'end-to-end'),
        (r'\bstateoftheart\b', 'state-of-the-art'),
        (r'\brealtime\b', 'real-time'),
        (r'\brealworld\b', 'real-world'),
        (r'\blargescale\b', 'large-scale'),
        (r'\bhighresolution\b', 'high-resolution'),
        (r'\binstanceoptimal\b', 'instance-optimal'),
        (r'\buseroptimized\b', 'user-optimized'),
        (r'\butilityoptimized\b', 'utility-optimized'),
    ]
    
    result = title
    for wrong, correct in compound_fixes:
        result = re.sub(wrong, correct, result, flags=re.IGNORECASE)
    
    return result


def normalize_title_for_search(title: str) -> str:
    """
    Normalize a title for DBLP search - combines cleaning and GROBID error fixes.
    """
    title = clean_title(title)
    title = fix_grobid_title_errors(title)
    return title

def title_similarity(input_title: str, dblp_title: str) -> float:
    """Compute similarity score between two titles in range [0, 1]."""
    if not input_title or not dblp_title:
        return 0.0
    return SequenceMatcher(None, input_title.lower(), dblp_title.lower()).ratio()

def normalize_newlines(text: str) -> str:
    """Standardizes newlines in a text block."""
    return text.replace('\r\n', '\n').replace('\r', '\n')


# ============================================================================
# AUTHOR NAME MATCHING
# ============================================================================

def parse_author_name(name: str) -> Tuple[str, str]:
    """
    Parse an author name into (first_name, last_name).
    Ignores middle names, initials, and disambiguation numbers (e.g., "0001").
    
    Examples:
        "Jon Louis Bentley" -> ("jon", "bentley")
        "Raymond J. Mooney" -> ("raymond", "mooney")
        "Nan Tang 0001" -> ("nan", "tang")
        "Peter van Oosterom" -> ("peter", "oosterom")  # "van" treated as middle
    """
    if not name:
        return ("", "")
    
    # Remove disambiguation numbers like "0001", "0002"
    name = re.sub(r'\s*\d{4}\s*$', '', name)
    
    # Remove periods from initials
    name = name.replace('.', ' ')
    
    # Split and filter out empty parts
    parts = [p.strip() for p in name.split() if p.strip()]
    
    if not parts:
        return ("", "")
    
    if len(parts) == 1:
        return ("", parts[0].lower())
    
    # First part is first name, last part is last name
    # Everything in between is ignored (middle names, particles like "van", "de")
    first = parts[0].lower()
    last = parts[-1].lower()
    
    return (first, last)


def author_name_match(name1: str, name2: str) -> float:
    """
    Compare two author names, focusing on first and last names only.
    Returns a score between 0 and 1.
    
    Scoring:
        - Exact match on both first and last: 1.0
        - Last name match + first initial match: 0.9
        - Last name match only: 0.7
        - Fuzzy last name match: 0.5
        - No match: 0.0
    """
    first1, last1 = parse_author_name(name1)
    first2, last2 = parse_author_name(name2)
    
    if not last1 or not last2:
        return 0.0
    
    # Exact last name match
    if last1 == last2:
        # Exact first name match
        if first1 == first2:
            return 1.0
        # First initial match
        if first1 and first2 and first1[0] == first2[0]:
            return 0.9
        # Last name only match
        return 0.7
    
    # Fuzzy last name match (handle typos, transliteration)
    last_sim = SequenceMatcher(None, last1, last2).ratio()
    if last_sim > 0.85:
        return 0.5
    
    return 0.0


def compare_author_lists(grobid_authors: List[str], dblp_authors: List[str]) -> float:
    """
    Compare two lists of authors and return an overall match score.
    
    Strategy:
        1. For each GROBID author, find best matching DBLP author
        2. Average the best match scores
        3. Apply penalty if author counts differ significantly
    
    Returns score in [0, 1].
    """
    if not grobid_authors or not dblp_authors:
        return 0.0
    
    # Find best match for each GROBID author
    match_scores = []
    for g_author in grobid_authors:
        best_score = 0.0
        for d_author in dblp_authors:
            score = author_name_match(g_author, d_author)
            best_score = max(best_score, score)
        match_scores.append(best_score)
    
    if not match_scores:
        return 0.0
    
    avg_score = sum(match_scores) / len(match_scores)
    
    # Apply penalty for author count mismatch
    count_ratio = min(len(grobid_authors), len(dblp_authors)) / max(len(grobid_authors), len(dblp_authors))
    
    # Final score combines match quality with count similarity
    return avg_score * (0.7 + 0.3 * count_ratio)


def compare_years(grobid_year: str, dblp_year: str) -> float:
    """
    Compare publication years.
    
    Returns:
        1.0 if exact match
        0.8 if within 1 year (common for preprint -> publication)
        0.5 if within 2 years
        0.0 otherwise
    """
    if not grobid_year or not dblp_year:
        return 0.5  # Neutral if missing
    
    try:
        g_year = int(str(grobid_year)[:4])
        d_year = int(str(dblp_year)[:4])
        diff = abs(g_year - d_year)
        
        if diff == 0:
            return 1.0
        elif diff == 1:
            return 0.8
        elif diff == 2:
            return 0.5
        else:
            return 0.0
    except (ValueError, TypeError):
        return 0.5  # Neutral if parsing fails
