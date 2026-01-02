# Reference Hallucination Checker

A Python tool that extracts bibliographic references from research papers (PDFs) using GROBID and verifies their existence using the DBLP API to detect "hallucinated" or incorrect citations.

## 🚀 Quick Start

### Prerequisites

1. **GROBID** must be running locally on port 8070:

   ```bash
   docker pull grobid/grobid:0.8.2-full
   docker run --rm --init -p 8070:8070 grobid/grobid:0.8.2-full
   ```

2. Verify GROBID is running:
   ```bash
   curl http://localhost:8070/api/isalive
   ```

### Run the Tool

```bash
python main.py <path_to_pdf>
```

Example:

```bash
python main.py paper.pdf
```

## 📂 Project Structure

```text
Reference_Halucinations/
├── data/
│   ├── raw/                    # Input PDFs
│   └── output/                 # Verification reports
├── extraction/                 # Reference extraction modules
│   ├── extractRefData.py       # Sends PDF to GROBID, returns XML
│   └── extractTitle.py         # Parses XML to extract paper titles
├── verification/               # Verification modules
│   ├── dblp.py                 # DBLP API queries & classification
│   ├── utils.py                # Title cleaning utilities
│   ├── checker.py              # Legacy orchestrator
│   └── verifier.py             # Verification helpers
├── tests/                      # Test suite
│   ├── unit/
│   └── integration/
├── main.py                     # Application entry point
└── requirements.txt            # Project dependencies
```

## 🔄 Data Flow

```
PDF → GROBID → XML → Title Extraction → DBLP Lookup → Classification → Report
```

1. **Entry Point (`main.py`)**

   - Accepts a PDF path from CLI
   - Orchestrates the extraction and verification pipeline

2. **GROBID Extraction (`extraction/extractRefData.py`)**

   - Sends PDF to local GROBID service (`http://localhost:8070/api/processReferences`)
   - Returns structured XML with parsed references

3. **Title Extraction (`extraction/extractTitle.py`)**

   - Parses GROBID XML using BeautifulSoup
   - Extracts paper titles from `<biblStruct>` elements
   - Returns a list of title strings

4. **DBLP Verification (`verification/dblp.py`)**

   - Queries DBLP API with normalized titles
   - Calculates similarity scores between extracted and matched titles
   - Handles ambiguous matches when multiple candidates are close

5. **Classification (`verification/dblp.py`)**

   - Assigns final labels based on verification results:

   | Label        | Description                                                     |
   | ------------ | --------------------------------------------------------------- |
   | `VERIFIED`   | Title found in DBLP with high confidence                        |
   | `REVIEW`     | Ambiguous match - multiple candidates with similar scores       |
   | `UNVERIFIED` | Title not found in DBLP                                         |
   | `SUSPICIOUS` | Short title (≤4 words) not found - likely incomplete extraction |

6. **Output**
   - Results are sorted by severity: VERIFIED → REVIEW → UNVERIFIED → SUSPICIOUS
   - Each result includes: input title, status, confidence score, and matched title (if found)

## 🛠 Installation

1. Create a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Install additional dependencies for XML parsing:
   ```bash
   pip install beautifulsoup4 lxml
   ```

## 📦 Dependencies

- `requests` - HTTP client for GROBID and DBLP APIs
- `beautifulsoup4` - XML parsing for GROBID output
- `lxml` - XML parser backend
- `pdfplumber` - PDF text extraction (legacy)

## ⚙️ Configuration

Key thresholds in `verification/dblp.py`:

| Parameter              | Value | Description                               |
| ---------------------- | ----- | ----------------------------------------- |
| `SIMILARITY_THRESHOLD` | 0.6   | Minimum score to consider a match         |
| `AMBIGUITY_GAP`        | 0.05  | Gap between top matches to flag ambiguity |

## 🐳 GROBID Setup

Pull and run GROBID with Docker:

```bash
# Pull the full image (includes all models)
docker pull grobid/grobid:0.8.2-full

# Run GROBID server
docker run --rm --init -p 8070:8070 grobid/grobid:0.8.2-full

# Verify it's running
curl http://localhost:8070/api/isalive
```

GROBID will be available at `http://localhost:8070`.

# Full pipeline

python main_pipeline.py paper.pdf

# Skip Gemini steps (if API quota exceeded)

python main_pipeline.py paper.pdf --skip-gemini

# Skip regex re-extraction

python main_pipeline.py paper.pdf --skip-regex
