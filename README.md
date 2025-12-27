# Reference Hallucination Checker

A modular Python tool designed to extract bibliographic references from research papers (PDFs) and verify their existence using the DBLP API to detect "hallucinated" or incorrect citations.

## 🚀 Quick Start

To run the tool with the default paper (`data/raw/paper.pdf`):

```bash
./.venv/bin/python3 main.py
```

To run with a specific PDF:

```bash
./.venv/bin/python3 main.py path/to/your/paper.pdf
```

To get results in JSON format:

```bash
./.venv/bin/python3 main.py --json
```

## 📂 Project Structure

```text
Reference_Halucinations/
├── data/
│   ├── raw/                # Input PDFs
│   └── output/             # Verification reports (JSON/CSV)
├── src/
│   └── ref_hal/            # Main package
│       ├── core/           # Extraction and Verification logic
│       ├── services/       # External API integrations (DBLP)
│       ├── utils/          # Text cleaning and similarity helpers
│       └── cli.py          # Command-line interface
├── tests/                  # Unit and integration tests
├── main.py                 # Application entry point
└── requirements.txt        # Project dependencies
```

## 🔄 Data Flow

When you run the command, the data moves through the application following this pipeline:

1.  **Entry Point (`main.py` & `src/ref_hal/cli.py`)**:
    *   The user provides a `pdf_path`.
    *   `cli.py` parses the arguments and calls `verify_references(pdf_path)` in the **Verifier**.

2.  **Orchestration (`src/ref_hal/core/verifier.py`)**:
    *   Coordinates the flow between extraction, parsing, and external verification.
    *   Calls the **Extractor** to get a list of references.

3.  **PDF Extraction (`src/ref_hal/core/extractor.py`)**:
    *   Uses `pdfplumber` to read the PDF and looks for "References" or "Bibliography" sections.
    *   Uses **Text Utils** (`normalize_newlines`) to clean the text.
    *   Uses regex to split text into individual reference strings (e.g., `[1] Author, "Title"...`).
    *   **Returns**: A list of raw reference strings.

4.  **Reference Parsing (`src/ref_hal/core/parser.py`)**:
    *   For each reference string, the **Parser** uses heuristics (like looking for quoted text) to isolate the **Paper Title**.
    *   **Returns**: The extracted title string.

5.  **External Lookup (`src/ref_hal/services/dblp.py`)**:
    *   The Verifier sends the extracted title to the **DBLP Service**.
    *   `dblp.py` handles the HTTP request to the [DBLP API](https://dblp.org/faq/How+to+use+the+dblp+search+API.html).
    *   **Returns**: A list of candidate paper objects (Title, Authors, Year, Venue).

6.  **Similarity Check (`src/ref_hal/utils/text.py`)**:
    *   The Verifier compares the extracted title with DBLP results using `title_similarity` (Levenshtein distance ratio).
    *   If the score is above the threshold (0.6), it is marked as **FOUND**.

7.  **Final Output**:
    *   The **CLI** receives the results and either prints a formatted report or saves it as JSON.

## 🛠 Installation

1. Create a virtual environment:
   ```bash
   python3 -m venv .venv
   ```
2. Install dependencies:
   ```bash
   ./.venv/bin/pip install -r requirements.txt
   ```
