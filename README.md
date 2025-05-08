# CV Parser (Vietnamese + English)

This project extracts structured information from Vietnamese and English CVs (PDF or DOCX), including name, contact, skills, education, experience, and languages. It auto-detects the language and routes outputs accordingly.

---

## 📦 External Requirements

Please install these system-level dependencies **before** running the project:

| Dependency     | Version                    | Description                                  |
|----------------|----------------------------|----------------------------------------------|
| Python         | 3.12.7+                    | Recommended interpreter                      |
| Poppler        | 24.08.0                    | Required for accurate PDF text extraction    |
| Tesseract-OCR  | Latest / 5.x+              | OCR fallback for scanned/non-text PDFs       |
| PyTorch        | Compatible w/ Transformers | Required for spaCy's transformer pipeline    |
| Transformers   | Latest                     | Used for spaCy's `en_core_web_trf` model     |

### Linux (Debian/Ubuntu)

```bash
sudo apt update
sudo apt install poppler-utils tesseract-ocr
```


### MacOS (Homebrew)

```bash
brew install poppler tesseract
```


## Python Setup

### 1. Clone the repo

```bash
git clone https://github.com/Watch650/ResumeParser.git
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Download spaCy models

```bash
python -m spacy download en_core_web_trf
```


## Folder Structure

```
cv-parser/
├── CV/                     # Drop .pdf/.docx files here
├── text_extract/           # Output: Cleaned text per language
├── parsed_data/            # Output: Structured JSON data
├── extractors/             # Text extractors (PDF, DOCX)
├── utils/                  # Helper utilities (cleaning, OCR)
├── file_router.py          # Routes and processes input CV files
├── file_parser_en.py       # English CV parser
└── file_parser_vn.py       # Vietnamese CV parser
```


## How to Use

### 1. Drops files

Place `.pdf` or `.docx` files in the `CV/` folder.

### 2. Extract & route text

```bash
python file_router.py
```

### 3. Parse CVs

```bash
python file_parser_en.py   # For English CVs
python file_parser_vn.py   # For Vietnamese CVs
```

## Ouput Format

Each parsed CV will be saved to: `parsed_data/extracted_cv_data.json`. Sample entry:
```bash
{
  "ho_ten": "Vu Hoang Lan",
  "email": "example@gmail.com",
  "so_dien_thoai": "+84987654321",
  "hoc_van": [...],
  "kinh_nghiem": [...],
  "ky_nang": [...],
  "ngoai_ngu": [...],
  "source_file": "CV_1_extracted_text.txt"
}
```

## Logging
Logs are saved in: `logs/`