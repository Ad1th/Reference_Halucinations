import argparse
import sys
from ref_extractor import get_references
from title_extractor import extract_title

def main():
    parser = argparse.ArgumentParser(description="Extract references and titles from a PDF file")
    parser.add_argument("file", nargs="?", default="paper.pdf", help="Path to the PDF file (default: paper.pdf)")
    args = parser.parse_args()

    # Get references using the ref_extractor module
    references = get_references(args.file)
    
    if not references:
        print("No References section found or PDF has no extractable text / recognizable format.")
        sys.exit(0)

    # Process and print references
    for ref in references:
        print("-" * 40)
        print(f"Reference: {ref}")
        
        # Extract title using the title_extractor module
        title = extract_title(ref)
        if title:
            print(f"Title: {title}")
        else:
            print("Title: (not found)")

if __name__ == "__main__":
    main()
