import argparse
import os
import sys
import pdfplumber


def extract_references(pdf_path: str) -> str:
    """Open a PDF, extract text from pages (skipping pages with no text),
    and return the section after the first occurrence of 'References'.
    """
    if not os.path.exists(pdf_path):
        print(f"Error: file not found: {pdf_path}", file=sys.stderr)
        sys.exit(2)

    texts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                texts.append(t)

    text = "\n".join(texts)
    if "References" in text:
        return text.split("References", 1)[-1]
    # If there's no explicit 'References' header, return empty string
    return ""


def main():
    parser = argparse.ArgumentParser(description="Extract references section from a PDF file")
    parser.add_argument("file", nargs="?", default="paper.pdf", help="Path to the PDF file (default: paper.pdf)")
    args = parser.parse_args()

    refs = extract_references(args.file)
    if not refs:
        print("No References section found or PDF has no extractable text.")
        sys.exit(0)

    # Print the references text to stdout
    print(refs)


if __name__ == "__main__":
    main()