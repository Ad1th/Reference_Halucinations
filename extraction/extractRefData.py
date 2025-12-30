import requests
import sys
from pathlib import Path

GROBID_URL = "http://localhost:8070/api/processReferences"


def extract_references_xml(pdf_path: str) -> str:
    pdf = Path(pdf_path)
    if not pdf.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    with open(pdf, "rb") as f:
        response = requests.post(
            GROBID_URL,
            files={"input": f},
            timeout=120
        )

    if response.status_code != 200:
        raise RuntimeError("GROBID failed to process the PDF")

    return response.text


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extractRefData.py <pdf_path>")
        sys.exit(1)

    xml = extract_references_xml(sys.argv[1])
    print(xml)