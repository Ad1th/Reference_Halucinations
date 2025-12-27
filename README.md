# Reference Hallucination Checker

A simplified Python tool designed to extract bibliographic references from research papers (PDFs) and verify their existence using the DBLP API to detect "hallucinated" or incorrect citations.

## 🚀 Quick Start

To run the tool with the default paper (`data/raw/paper.pdf`):

```bash
./.venv/bin/python3 main.py
```

To run with a specific PDF:

```bash
./.venv/bin/python3 main.py data/raw/your_paper.pdf
```

## 📂 Project Structure

```text
Reference_Halucinations/
├── data/
│   ├── raw/                # Input PDFs
│   └── output/             # Verification reports (Future)
├── extraction/             # Folder 1: Getting data OUT
│   ├── pdf.py              # Reads PDF and extracts raw reference strings
│   └── parser.py           # Isolates paper titles from raw strings
├── verification/           # Folder 2: Checking data
│   ├── dblp.py             # External API integration (DBLP)
│   ├── checker.py          # Orchestrator that coordinates the workflow
│   └── utils.py            # Shared cleaning and similarity constants
├── main.py                 # Application entry point
└── requirements.txt        # Project dependencies
```

## 🔄 Data Flow

When you run the command, the data moves through the application following this simplified pipeline:

1.  **Entry Point (`main.py`)**:
    *   Gets the `pdf_path` from CLI (defaults to `paper.pdf`).
    *   Calls `verify_references(pdf_path)` in `verification/checker.py`.

2.  **Orchestration (`verification/checker.py`)**:
    *   Coordinates the flow between extraction and verification.
    *   Calls `get_references` in `extraction/pdf.py`.

3.  **PDF Extraction (`extraction/pdf.py`)**:
    *   Uses `pdfplumber` to extract text from the "References" section.
    *   Splits text into individual reference strings (e.g., `[1] Author, Title...`).
    *   **Returns**: A list of raw reference strings.

4.  **Reference Parsing (`extraction/parser.py`)**:
    *   For each reference, it isolates the **Paper Title** using format heuristics.
    *   **Returns**: The extracted title string.

5.  **External Lookup (`verification/dblp.py`)**:
    *   *(Integration in progress)* Sends the title to the DBLP API to find matching publications.
    *   **Returns**: A list of candidate paper objects.

6.  **Similarity Check (`verification/utils.py`)**:
    *   Provides logic to compare extracted titles with API results.

7.  **Final Output**:
    *   `main.py` prints the results to your terminal.

## 🛠 Installation

1. Create a virtual environment:
   ```bash
   python3 -m venv .venv
   ```
2. Install dependencies:
   ```bash
   ./.venv/bin/pip install -r requirements.txt
   ```
