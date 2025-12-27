import argparse
import sys
import json
from .core.verifier import verify_references

def main():
    parser = argparse.ArgumentParser(description="Verify references in a PDF file for hallucinations.")
    parser.add_argument("pdf_path", help="Path to the PDF file")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    args = parser.parse_args()

    try:
        results = verify_references(args.pdf_path)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for res in results:
            print("-" * 50)
            print(f"REF: {res['reference']}")
            print(f"EXTRACTED TITLE: {res['extracted_title']}")
            print(f"STATUS: {res['status']} (Conf: {res.get('confidence', 0)})")
            if res['match']:
                match = res['match']
                print(f"MATCHED TITLE: {match['title']}")
                print(f"AUTHORS: {', '.join(match['authors'])}")
                print(f"VENUE: {match['venue']} ({match['year']})")

if __name__ == "__main__":
    main()
