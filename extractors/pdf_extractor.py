# extractors/pdf_extractor.py
import fitz
import pdfplumber
import logging
from utils.ocr import ocr_pdf

def extract_pdf_text(path: str) -> str:
    try:
        output = []

        # First, try using PyMuPDF (fitz) for text extraction
        with fitz.open(path) as doc:
            for page in doc:
                text = page.get_text().strip()
                if text:
                    output.append(text)

        # If PyMuPDF doesn't extract text, fall back to pdfplumber
        if not output:
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        output.append(text)

                    # Extract tables and store them at the end of the document
                    table_rows = []
                    for table in page.extract_tables():
                        for row in table:
                            row = [str(cell or "").strip() for cell in row]
                            table_rows.append(" | ".join(row))

                    if table_rows:
                        # Append all table rows as the last part of the text
                        if table_rows:
                            output.append("\n[TABLES BELOW]\n" + "\n".join(table_rows))

        # If still no text, use OCR as a last resort
        if not output:
            output.append(ocr_pdf(path))

        return "\n".join(output).strip()

    except Exception as e:
        logging.error(f"PDF extraction failed: {e}")
        return ""
