import sys
import os

# Allow imports from project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from extraction.extractRefData import extract_references_xml
from extraction.extractMetadata import extract_references_metadata
from verification.dblp import verify_title_with_dblp

SORT_ORDER = {
    "VERIFIED": 0,
    "REVIEW": 1,
    "UNVERIFIED": 2,
    "SUSPICIOUS": 3
}



def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <pdf_path>")
        sys.exit(1)

    pdf_path = sys.argv[1]

    # 1. Extract references XML from PDF using GROBID
    xml = extract_references_xml(pdf_path)

    # 2. Extract full metadata from GROBID XML
    grobid_refs = extract_references_metadata(xml)

    # 3. Verify each reference using DBLP
    results = []

    for ref in grobid_refs:
        title = ref["title"]
        dblp_result = verify_title_with_dblp(title)
        
        # Combine GROBID metadata + DBLP verification result
        combined = {
            "grobid": ref,  # Full GROBID extracted metadata
            "dblp_verification": dblp_result  # DBLP verification + metadata
        }
        results.append(combined)

    # Sort references by verification status
    results.sort(key=lambda r: SORT_ORDER[r["dblp_verification"]["final_label"]])

    # Print results (pre-metadata check)
    print("=" * 80)
    print("PRE-METADATA CHECK RESULTS (Title-based DBLP Verification)")
    print("=" * 80)
    
    for i, r in enumerate(results, 1):
        grobid = r["grobid"]
        dblp = r["dblp_verification"]
        
        print(f"\n[{i}] {dblp['final_label']}")
        print(f"    GROBID Title:  {grobid['title']}")
        print(f"    GROBID Authors: {', '.join(grobid['authors']) if grobid['authors'] else 'N/A'}")
        print(f"    GROBID Year:   {grobid['year'] or 'N/A'}")
        
        if dblp.get("dblp_metadata"):
            dm = dblp["dblp_metadata"]
            print(f"    ---")
            print(f"    DBLP Title:    {dm.get('title', 'N/A')}")
            print(f"    DBLP Authors:  {', '.join(dm.get('authors', [])) if dm.get('authors') else 'N/A'}")
            print(f"    DBLP Year:     {dm.get('year', 'N/A')}")
            print(f"    DBLP Venue:    {dm.get('venue', 'N/A')}")
        
        print(f"    Confidence: {dblp['confidence']}")

    # Print statistics
    print("\n" + "=" * 80)
    print("PRE-METADATA CHECK SUMMARY")
    print("=" * 80)
    
    total = len(results)
    stats = {"VERIFIED": 0, "REVIEW": 0, "UNVERIFIED": 0, "SUSPICIOUS": 0}
    
    for r in results:
        stats[r["dblp_verification"]["final_label"]] += 1
    
    print(f"Total References: {total}")
    print("-" * 80)
    print(f"✓ VERIFIED:   {stats['VERIFIED']:3d}  ({100*stats['VERIFIED']/total:.1f}%)")
    print(f"? REVIEW:     {stats['REVIEW']:3d}  ({100*stats['REVIEW']/total:.1f}%)")
    print(f"✗ UNVERIFIED: {stats['UNVERIFIED']:3d}  ({100*stats['UNVERIFIED']/total:.1f}%)")
    print(f"⚠ SUSPICIOUS: {stats['SUSPICIOUS']:3d}  ({100*stats['SUSPICIOUS']/total:.1f}%)")
    print("=" * 80)


if __name__ == "__main__":
    main()



























# # Entry point script; gets PDF path from CLI and sends it to verification/checker.py for processing.
# # import argparse
# # import sys
# # import json
# # from verification.checker import verify_references

# import sys
# import os
# sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# from extraction.extractRefData import extract_references_xml
# from extraction.extractTitle import extract_titles_from_grobid_xml
# from verification.dblp import verify_title_with_dblp


# xml = extract_references_xml("paper.pdf") #To extract references from PDF, and return XML
# titles = extract_titles_from_grobid_xml(xml) #To extract titles from XML


# for t in titles:
#     # print(t)
#     result = verify_title_with_dblp(t)
#     print(result)
    



# # from extraction.extractRefData import extract_references_xml
# # from extraction.extractTitle import extract_titles_from_grobid_xml
# # from verification.dblp import verify_title_with_dblp

# # pdf_path = "paper2.pdf"

# xml = extract_references_xml(pdf_path)
# titles = extract_titles_from_grobid_xml(xml)

# for title in titles:
#     result = verify_title_with_dblp(title)
#     print(result)




# # def main():
# #     parser = argparse.ArgumentParser(description="Clean Reference Checker")
# #     parser.add_argument("pdf_path", nargs="?", default="data/raw/paper.pdf")
# #     parser.add_argument("--json", action="store_true")
# #     args = parser.parse_args()

# #     try:
# #         results = verify_references(args.pdf_path)
# #         if args.json:
# #             print(json.dumps(results, indent=2))
# #         else:
# #             for res in results:
# #                 print("-" * 30)
# #                 print(f"TITLE:  {res['extracted_title']}")
# #                 print(f"STATUS: {res['status']} (Conf: {res.get('confidence', 0)})")
# #                 if res.get('matched_title'):
# #                     print(f"DBLP:   {res['matched_title']}")
# #                 print(f"REF:    {res['reference']}")
# #     except Exception as e:
# #         print(f"Error: {e}")

# # if __name__ == "__main__":
# #     main()
