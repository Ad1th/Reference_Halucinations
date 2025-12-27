# Entry point script; gets PDF path from CLI and sends it to verification/checker.py for processing.
import argparse
import sys
import json
from verification.checker import verify_references

def main():
    parser = argparse.ArgumentParser(description="Clean Reference Checker")
    parser.add_argument("pdf_path", nargs="?", default="data/raw/paper.pdf")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        results = verify_references(args.pdf_path)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for res in results:
                print("-" * 30)
                print(f"TITLE:  {res['extracted_title']}")
                print(f"STATUS: {res['status']} (Conf: {res.get('confidence', 0)})")
                if res.get('matched_title'):
                    print(f"DBLP:   {res['matched_title']}")
                print(f"REF:    {res['reference']}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
