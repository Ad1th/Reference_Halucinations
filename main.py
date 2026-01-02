import sys
import os

# Allow imports from project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from extraction.extractRefData import extract_references_xml
from extraction.extractTitle import extract_titles_from_grobid_xml
from verification.dblp import verify_title_with_dblp, classify_reference

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

    # 2. Extract titles from GROBID XML
    titles = extract_titles_from_grobid_xml(xml)

    # 3. Verify each title using DBLP
    results = []

    for title in titles:
        res = verify_title_with_dblp(title)
        res = classify_reference(res)
        results.append(res)

    # Sort references
    results.sort(key=lambda r: SORT_ORDER[r["final_label"]])

    # Print results
    for r in results:
        print(r)


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
