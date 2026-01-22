"""
Multi-step reference verification pipeline with detailed reporting.

Steps:
1. Pre-metadata check (DBLP title matching only)
2. Author name matching to boost confidence
3. Regex re-extraction for UNVERIFIED/SUSPICIOUS
4. Gemini API metadata matching for remaining issues
5. pdfplumber + Gemini extraction as final fallback

Outputs results to fluff/ folder with step-by-step change tracking.
"""
import sys
import os
from datetime import datetime
from typing import List, Dict, Tuple

# Allow imports from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extraction.extractRefData import extract_references_xml
from extraction.extractMetadata import extract_references_metadata
from extraction.pdfplumber_extract import extract_references_text, extract_titles_with_regex
from verification.dblp import verify_title_with_dblp, query_dblp, extract_candidates, title_similarity, SIMILARITY_THRESHOLD
from verification.utils import compare_author_lists, compare_years
from verification.gemini import gemini_metadata_match, gemini_extract_titles_from_text, gemini_verify_reference_exists, gemini_batch_verify


SORT_ORDER = {
    "VERIFIED": 0,
    "REVIEW": 1,
    "UNVERIFIED": 2
}


class VerificationReport:
    """Handles report generation and change tracking."""
    
    def __init__(self, output_path: str):
        self.output_path = output_path
        self.lines = []
        self.changes = []  # Track category changes
    
    def write(self, text: str = ""):
        """Add line to report."""
        self.lines.append(text)
        print(text)  # Also print to console
    
    def section(self, title: str):
        """Add section header."""
        self.write("")
        self.write("=" * 80)
        self.write(title)
        self.write("=" * 80)
    
    def subsection(self, title: str):
        """Add subsection header."""
        self.write("")
        self.write("-" * 60)
        self.write(title)
        self.write("-" * 60)
    
    def track_change(self, ref_num: int, title: str, old_label: str, new_label: str, reason: str):
        """Track a category change."""
        change = {
            "ref_num": ref_num,
            "title": title[:60] + "..." if len(title) > 60 else title,
            "old_label": old_label,
            "new_label": new_label,
            "reason": reason
        }
        self.changes.append(change)
    
    def report_changes(self, step_name: str):
        """Report changes from the current step."""
        if not self.changes:
            self.write(f"\nNo changes in {step_name}")
            return
        
        self.subsection(f"Changes from {step_name}")
        for c in self.changes:
            self.write(f"  [{c['ref_num']}] {c['old_label']} -> {c['new_label']}")
            self.write(f"      Title: {c['title']}")
            self.write(f"      Reason: {c['reason']}")
        self.changes = []  # Reset for next step
    
    def save(self):
        """Save report to file."""
        with open(self.output_path, 'w') as f:
            f.write("\n".join(self.lines))
        print(f"\n>>> Report saved to: {self.output_path}")


def print_statistics(report: VerificationReport, results: List[Dict], title: str = "SUMMARY"):
    """Print verification statistics."""
    total = len(results)
    stats = {"VERIFIED": 0, "REVIEW": 0, "UNVERIFIED": 0}
    
    for r in results:
        label = r.get("final_label") or r.get("dblp_verification", {}).get("final_label", "UNKNOWN")
        if label in stats:
            stats[label] += 1
    
    report.section(title)
    report.write(f"Total References: {total}")
    report.write("-" * 40)
    report.write(f"✓ VERIFIED:   {stats['VERIFIED']:3d}  ({100*stats['VERIFIED']/total:.1f}%)")
    report.write(f"? REVIEW:     {stats['REVIEW']:3d}  ({100*stats['REVIEW']/total:.1f}%)")
    report.write(f"✗ UNVERIFIED: {stats['UNVERIFIED']:3d}  ({100*stats['UNVERIFIED']/total:.1f}%)")


def step1_pre_metadata_check(pdf_path: str, report: VerificationReport) -> Tuple[str, List[Dict]]:
    """
    Step 1: Initial DBLP title-based verification.
    Returns (xml, results)
    """
    report.section("STEP 1: PRE-METADATA CHECK (Title-based DBLP Verification)")
    
    # Extract references
    report.write("Extracting references from PDF via GROBID...")
    xml = extract_references_xml(pdf_path)
    grobid_refs = extract_references_metadata(xml)
    report.write(f"Extracted {len(grobid_refs)} references")
    
    # Verify each - pass authors for better matching on short titles
    results = []
    for i, ref in enumerate(grobid_refs, 1):
        title = ref["title"]
        authors = ref.get("authors", [])
        dblp_result = verify_title_with_dblp(title, authors)
        
        combined = {
            "ref_num": i,
            "grobid": ref,
            "dblp_verification": dblp_result,
            "final_label": dblp_result["final_label"],
            "final_confidence": dblp_result["confidence"]
        }
        results.append(combined)
    
    # Sort and print
    results.sort(key=lambda r: SORT_ORDER[r["final_label"]])
    
    for r in results:
        grobid = r["grobid"]
        dblp = r["dblp_verification"]
        
        report.write(f"\n[{r['ref_num']}] {r['final_label']}")
        report.write(f"    GROBID Title:  {grobid['title']}")
        report.write(f"    GROBID Authors: {', '.join(grobid['authors']) if grobid['authors'] else 'N/A'}")
        report.write(f"    GROBID Year:   {grobid['year'] or 'N/A'}")
        
        if dblp.get("dblp_metadata"):
            dm = dblp["dblp_metadata"]
            report.write(f"    ---")
            report.write(f"    DBLP Title:    {dm.get('title', 'N/A')}")
            report.write(f"    DBLP Authors:  {', '.join(dm.get('authors', [])) if dm.get('authors') else 'N/A'}")
            report.write(f"    DBLP Year:     {dm.get('year', 'N/A')}")
            report.write(f"    DBLP Venue:    {dm.get('venue', 'N/A')}")
        
        report.write(f"    Confidence: {dblp['confidence']}")
    
    print_statistics(report, results, "PRE-METADATA CHECK SUMMARY")
    
    return xml, results


def step2_author_matching(results: List[Dict], report: VerificationReport) -> List[Dict]:
    """
    Step 2: Apply author name matching to boost/adjust confidence.
    This applies to ALL references with DBLP matches.
    For UNVERIFIED refs (no DBLP result), retry the query.
    """
    report.section("STEP 2: AUTHOR NAME MATCHING")
    
    for r in results:
        old_label = r["final_label"]
        old_conf = r["final_confidence"]
        
        grobid = r["grobid"]
        dblp = r["dblp_verification"]
        dblp_meta = dblp.get("dblp_metadata")




        # # For UNVERIFIED refs, retry DBLP query (may have failed due to network/rate limit)
        # if not dblp_meta and old_label == "UNVERIFIED":
        #     title = grobid.get("title", "")
        #     authors = grobid.get("authors", [])
        #     if title:
        #         retry_result = verify_title_with_dblp(title, authors)
        #         retry_result = classify_reference(retry_result)
        #         if retry_result.get("dblp_metadata"):
        #             # Update the reference with new result
        #             r["dblp_verification"] = retry_result
        #             dblp = retry_result
        #             dblp_meta = retry_result.get("dblp_metadata")
        #             # If the retry found a match with high confidence, update label
        #             if retry_result["status"] == "FOUND":
        #                 r["final_label"] = retry_result["final_label"]
        #                 r["final_confidence"] = retry_result["confidence"]
        #                 report.track_change(
        #                     r["ref_num"],
        #                     title,
        #                     old_label,
        #                     retry_result["final_label"],
        #                     f"DBLP retry successful - Confidence: {retry_result['confidence']:.3f}"
        #                 )
        #                 old_label = retry_result["final_label"]
        #                 old_conf = retry_result["confidence"]
        
        # For UNVERIFIED refs, we rely on Step 1. Retrying here is redundant and risks rate limits.
        # We only process if we already have metadata from Step 1.
        
        if not dblp_meta:
            continue
        
        # Compare authors
        author_score = compare_author_lists(
            grobid.get("authors", []),
            dblp_meta.get("authors", [])
        )
        
        # Compare years
        year_score = compare_years(
            grobid.get("year"),
            dblp_meta.get("year")
        )
        
        # Store metadata match scores
        r["author_match_score"] = round(author_score, 3)
        r["year_match_score"] = round(year_score, 3)
        
        # Adjust confidence based on metadata matching
        # For SUSPICIOUS refs with good author match, weight authors more heavily
        title_conf = dblp["confidence"]
        
        # If title confidence is low but authors match well, trust the author match more
        if title_conf < 0.5 and author_score >= 0.8:
            # Weight: title 30%, authors 50%, year 20%
            adjusted_conf = title_conf * 0.3 + author_score * 0.5 + year_score * 0.2
        else:
            # Standard weight: title 60%, authors 30%, year 10%
            adjusted_conf = title_conf * 0.6 + author_score * 0.3 + year_score * 0.1
        
        r["final_confidence"] = round(adjusted_conf, 3)
        
        # Reclassify based on adjusted confidence
        if adjusted_conf >= 0.7 and old_label in ["REVIEW", "UNVERIFIED"]:
            r["final_label"] = "VERIFIED"
            report.track_change(
                r["ref_num"], 
                grobid["title"], 
                old_label, 
                "VERIFIED",
                f"Author match: {author_score:.2f}, Year match: {year_score:.2f}, Adjusted conf: {adjusted_conf:.3f}"
            )
        elif adjusted_conf >= 0.5 and old_label == "UNVERIFIED":
            # Promote UNVERIFIED (with metadata) to REVIEW if metadata partially matches
            r["final_label"] = "REVIEW"
            report.track_change(
                r["ref_num"],
                grobid["title"],
                old_label,
                "REVIEW",
                f"Partial metadata match - Author: {author_score:.2f}, Year: {year_score:.2f}"
            )
        elif adjusted_conf < 0.5 and old_label == "VERIFIED":
            # Demote if metadata doesn't match well
            r["final_label"] = "REVIEW"
            report.track_change(
                r["ref_num"],
                grobid["title"],
                old_label,
                "REVIEW",
                f"Low metadata match - Author: {author_score:.2f}, Year: {year_score:.2f}"
            )
    
    report.report_changes("Author Matching")
    print_statistics(report, results, "POST-AUTHOR MATCHING SUMMARY")
    
    return results


def step3_regex_reextraction(pdf_path: str, results: List[Dict], report: VerificationReport) -> List[Dict]:
    """
    Step 3: Try regex-based title extraction for UNVERIFIED references.
    """
    report.section("STEP 3: REGEX RE-EXTRACTION FOR UNVERIFIED")
    
    # Get problematic references
    problematic = [r for r in results if r["final_label"] == "UNVERIFIED"]
    
    if not problematic:
        report.write("No UNVERIFIED references to process.")
        return results
    
    report.write(f"Found {len(problematic)} problematic references")
    
    # Extract raw text
    try:
        raw_text = extract_references_text(pdf_path)
        
        # Check if the PDF has spacing issues (text extracted without spaces)
        # This happens with some PDF encodings
        if raw_text and _pdf_has_spacing_issues(raw_text):
            report.write("WARNING: PDF has encoding issues - text extracted without proper word spacing.")
            report.write("Skipping regex re-extraction as it cannot improve on GROBID results.")
            print_statistics(report, results, "POST-REGEX SUMMARY (SKIPPED)")
            return results
        
        regex_titles = extract_titles_with_regex(raw_text)
        report.write(f"Extracted {len(regex_titles)} titles via regex")
    except Exception as e:
        report.write(f"Regex extraction failed: {e}")
        return results
    
    # Try to match and re-verify
    for r in problematic:
        old_label = r["final_label"]
        grobid_title = r["grobid"]["title"]
        
        # Find potential regex match
        from difflib import SequenceMatcher
        best_match = None
        best_score = 0.0
        
        for regex_ref in regex_titles:
            score = SequenceMatcher(None, grobid_title.lower(), regex_ref["title"].lower()).ratio()
            if score > best_score:
                best_score = score
                best_match = regex_ref
        
        # If we found a better title, re-verify with DBLP
        if best_match and best_score > 0.5 and best_match["title"] != grobid_title:
            corrected_title = best_match["title"]
            report.write(f"\n  Trying corrected title for [{r['ref_num']}]:")
            report.write(f"    Original: {grobid_title}")
            report.write(f"    Corrected: {corrected_title}")
            
            # Re-verify with DBLP
            new_dblp = verify_title_with_dblp(corrected_title)
            new_dblp = classify_reference(new_dblp)
            
            if new_dblp["confidence"] > r["final_confidence"]:
                r["dblp_verification"] = new_dblp
                r["final_confidence"] = new_dblp["confidence"]
                r["corrected_title"] = corrected_title
                
                if new_dblp["final_label"] == "VERIFIED":
                    r["final_label"] = "VERIFIED"
                    report.track_change(
                        r["ref_num"],
                        grobid_title,
                        old_label,
                        "VERIFIED",
                        f"Regex re-extraction found: '{corrected_title}'"
                    )
    
    report.report_changes("Regex Re-extraction")
    print_statistics(report, results, "POST-REGEX SUMMARY")
    
    return results


def _pdf_has_spacing_issues(text: str) -> bool:
    """
    Check if PDF text was extracted without proper word spacing.
    
    This detects PDFs that are encoded in a way that pdfplumber can't extract
    spaces between words (all text comes out concatenated).
    """
    # Sample some lines and check for abnormally long "words" without spaces
    lines = [l for l in text.split('\n') if len(l) > 30][:50]  # Sample up to 50 lines
    
    long_word_count = 0
    total_words = 0
    
    for line in lines:
        words = line.split()
        for word in words:
            total_words += 1
            # A "word" longer than 30 chars with mixed case or all lowercase is likely concatenated
            if len(word) > 30:
                # Check if it has lowercase letters (not just an acronym or URL)
                if any(c.islower() for c in word) and not word.startswith('http'):
                    long_word_count += 1
    
    # If more than 2% of "words" are abnormally long, the PDF has spacing issues
    # This is a conservative threshold - even a few concatenated words indicates problems
    if total_words > 0 and long_word_count / total_words > 0.02:
        return True
    
    return False


def step4_gemini_batch_verification(results: List[Dict], report: VerificationReport) -> List[Dict]:
    """
    Step 4: Use Gemini API in BATCH mode to verify remaining unverified references.
    Sends all references at once to avoid rate limiting.
    """
    report.section("STEP 4: GEMINI BATCH VERIFICATION")
    
    # Find all remaining unverified references
    candidates = [r for r in results 
                  if r["final_label"] in ["REVIEW", "UNVERIFIED"]]
    
    if not candidates:
        report.write("No candidates for Gemini verification.")
        return results
    
    report.write(f"Processing {len(candidates)} references with Gemini (batch mode)...")
    
    # Build batch request
    batch_data = []
    for r in candidates:
        grobid = r["grobid"]
        dblp_meta = r["dblp_verification"].get("dblp_metadata")
        
        batch_data.append({
            "ref_num": r["ref_num"],
            "grobid_title": grobid["title"],
            "grobid_authors": grobid.get("authors", []),
            "grobid_year": grobid.get("year"),
            "dblp_title": dblp_meta.get("title") if dblp_meta else None,
            "dblp_authors": dblp_meta.get("authors", []) if dblp_meta else [],
            "dblp_year": dblp_meta.get("year") if dblp_meta else None,
            "current_confidence": r["final_confidence"]
        })
    
    # Call Gemini with batch
    try:
        batch_results = gemini_batch_verify(batch_data)
    except Exception as e:
        report.write(f"Gemini batch verification failed: {e}")
        return results
    
    # Process results
    for r in candidates:
        ref_num = r["ref_num"]
        gemini_result = batch_results.get(ref_num, {})
        
        if not gemini_result:
            continue
        
        old_label = r["final_label"]
        grobid = r["grobid"]
        
        r["gemini_verification"] = gemini_result
        
        if gemini_result.get("verified") and gemini_result.get("confidence", 0) >= 0.7:
            r["final_label"] = "VERIFIED"
            r["final_confidence"] = max(r["final_confidence"], gemini_result["confidence"])
            r["verification_source"] = "gemini"
            report.track_change(
                ref_num,
                grobid["title"],
                old_label,
                "VERIFIED",
                f"Gemini verified: {gemini_result.get('reasoning', 'N/A')[:60]}"
            )
        elif gemini_result.get("exists") is False:
             # If explicit non-existence, keep as UNVERIFIED (or flag specifically if needed)
             pass
    
    report.report_changes("Gemini Batch Verification")
    print_statistics(report, results, "POST-GEMINI SUMMARY")
    
    return results


def step5_final_summary(results: List[Dict], report: VerificationReport) -> List[Dict]:
    """
    Step 5: Final summary - no more API calls, just summarize remaining issues.
    """
    report.section("STEP 5: FINAL ANALYSIS")
    
    # Get remaining unverified
    unverified = [r for r in results if r["final_label"] == "UNVERIFIED"]
    review = [r for r in results if r["final_label"] == "REVIEW"]
    
    if unverified:
        report.write(f"\nUNVERIFIED ({len(unverified)} references):")
        report.write("These references could not be found in DBLP. Possible reasons:")
        report.write("  - Published in non-CS venues (medical journals, physics, etc.)")
        report.write("  - Very recent publications not yet indexed")
        report.write("  - Books, technical reports, or theses")
        report.write("  - Potentially hallucinated references")
        for r in unverified:
            report.write(f"\n  [{r['ref_num']}] {r['grobid']['title'][:70]}...")
            if r['grobid'].get('authors'):
                report.write(f"       Authors: {', '.join(r['grobid']['authors'][:3])}")
    
    # if suspicious:
    #     report.write(f"\nSUSPICIOUS ({len(suspicious)} references):")
    #     report.write("These had partial DBLP matches but metadata didn't align well:")
    #     for r in suspicious:
    #         report.write(f"\n  [{r['ref_num']}] {r['grobid']['title'][:70]}")
    #         report.write(f"       Confidence: {r['final_confidence']:.3f}")
    #         if r.get('author_match_score'):
    #             report.write(f"       Author match: {r['author_match_score']:.2f}, Year match: {r.get('year_match_score', 0):.2f}")
    
    if review:
        report.write(f"\nREVIEW ({len(review)} references):")
        report.write("These need manual verification:")
        for r in review:
            report.write(f"\n  [{r['ref_num']}] {r['grobid']['title'][:70]}")
    
    print_statistics(report, results, "FINAL SUMMARY")
    
    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Multi-step reference verification pipeline")
    parser.add_argument("pdf_path", help="Path to PDF file")
    parser.add_argument("--skip-gemini", action="store_true", help="Skip Gemini API steps (4 & 5)")
    parser.add_argument("--skip-regex", action="store_true", help="Skip regex re-extraction (step 3)")
    args = parser.parse_args()
    
    pdf_path = args.pdf_path
    
    # Create output file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"fluff/verification_report_{timestamp}.txt"
    
    report = VerificationReport(output_path)
    report.section(f"REFERENCE VERIFICATION REPORT")
    report.write(f"PDF: {pdf_path}")
    report.write(f"Timestamp: {datetime.now().isoformat()}")
    report.write(f"Threshold: SIMILARITY_THRESHOLD = {SIMILARITY_THRESHOLD}")
    report.write(f"Options: skip-gemini={args.skip_gemini}, skip-regex={args.skip_regex}")
    
    # Run pipeline
    xml, results = step1_pre_metadata_check(pdf_path, report)
    results = step2_author_matching(results, report)
    
    if not args.skip_regex:
        results = step3_regex_reextraction(pdf_path, results, report)
    else:
        report.section("STEP 3: SKIPPED (--skip-regex)")
    
    if not args.skip_gemini:
        results = step4_gemini_batch_verification(results, report)
    else:
        report.section("STEP 4: SKIPPED (--skip-gemini)")
    
    results = step5_final_summary(results, report)
    
    # Final sorted output
    results.sort(key=lambda r: SORT_ORDER[r["final_label"]])
    
    report.section("FINAL RESULTS (Sorted by Status)")
    for r in results:
        grobid = r["grobid"]
        report.write(f"\n[{r['ref_num']}] {r['final_label']} (conf: {r['final_confidence']:.3f})")
        report.write(f"    Title: {grobid['title']}")
        if r.get("corrected_title"):
            report.write(f"    Corrected: {r['corrected_title']}")
        if r.get("verification_source"):
            report.write(f"    Source: {r['verification_source']}")
    
    # Save report
    report.save()


if __name__ == "__main__":
    main()
