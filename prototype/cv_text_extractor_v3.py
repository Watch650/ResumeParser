import fitz  # PyMuPDF
import docx  # python-docx
import re
import os
import pytesseract
import pdf2image
import logging
from typing import Optional, List, Tuple
import pdfplumber

# Configure logging
logging.basicConfig(
    filename='cv_extraction.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def extract_text_from_pdf(path: str) -> str:
    """Extract clean text from PDF with structured tables"""
    try:
        output = []

        # First try PyMuPDF for regular text
        with fitz.open(path) as doc:
            for page in doc:
                text = page.get_text().strip()
                if text:
                    output.append(text)

        # Then use pdfplumber for tables if no text found
        if not output:
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text.strip():
                        output.append(text)

                    # Extract tables with clear formatting
                    tables = page.extract_tables()
                    for table in tables:
                        output.append("\n[TABLE]")
                        for row in table:
                            # Clean each cell and join with pipes
                            clean_row = [str(cell or "").strip() for cell in row]
                            output.append(" | ".join(clean_row))
                        output.append("[END TABLE]\n")

        return "\n".join(output).strip()

    except Exception as e:
        logging.error(f"PDF extraction failed for {path}: {str(e)}")
        return ""

def ocr_pdf(path: str, lang: str = "eng+vie+jpn", page_limit: Optional[int] = None) -> str:
    """Fallback OCR if text extraction fails."""
    try:
        images = pdf2image.convert_from_path(path)
        text = []
        for i, img in enumerate(images):
            if page_limit and i >= page_limit:
                break
            text.append(pytesseract.image_to_string(img, lang=lang))
        return "\n".join(text).strip()
    except Exception as e:
        logging.error(f"OCR failed for {path}: {str(e)}")
        return ""

def extract_text_from_docx(path: str) -> str:
    """Extract content from DOCX with proper formatting"""
    try:
        doc = docx.Document(path)
        output = []
        current_section = None

        for element in doc.element.body:
            # Handle paragraphs (section headers)
            if element.tag.endswith('p'):
                para = docx.text.paragraph.Paragraph(element, doc)
                text = para.text.strip()
                if text and text.isupper():  # Likely a section header
                    current_section = text
                    output.append(f"\n{text}\n{'-'*len(text)}")
                elif text:
                    output.append(text)

            # Handle tables with proper formatting
            elif element.tag.endswith('tbl'):
                table = docx.table.Table(element, doc)
                table_data = []

                for row in table.rows:
                    row_data = []
                    for cell in row.cells:
                        cell_text = ' '.join(p.text.strip() for p in cell.paragraphs if p.text.strip())
                        row_data.append(cell_text)
                    table_data.append(row_data)

                if table_data:
                    output.append(format_table(table_data))

        return '\n'.join(output).strip()

    except Exception as e:
        logging.error(f"DOCX extraction failed: {str(e)}")
        return ""

def format_table(table_data: list) -> str:
    """Format table data for clean output"""
    if not table_data:
        return ""

    # Determine column widths
    col_widths = [max(len(str(cell)) for cell in col)
                 for col in zip(*table_data)]

    formatted_lines = []
    for row in table_data:
        # Format each row with proper spacing
        formatted_row = []
        for i, cell in enumerate(row):
            formatted_row.append(f"{cell:{col_widths[i]}}")
        formatted_lines.append(" | ".join(formatted_row))

    return "\n".join(formatted_lines)

def clean_extracted_text(text: str) -> str:
    """Apply final cleaning to extracted text"""
    # Remove duplicate section headers
    sections = ["PERSONAL DETAILS", "PROFESSIONAL SUMMARY", "SKILLS",
               "EDUCATION", "PROJECTS", "WORK EXPERIENCE"]
    for section in sections:
        text = re.sub(rf"{section}\s+{section}", section, text)

    # Remove unwanted footers/headers
    text = re.sub(r'©.*\.(vn|com)', '', text)
    text = re.sub(r'Page \d+ of \d+', '', text)

    # Normalize whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)  # Max 2 newlines
    text = re.sub(r'[ \t]{2,}', ' ', text)  # Multiple spaces to one

    # Fix common OCR issues
    replacements = {
        '': '📍',
        '˜': '~',
        'ﬁ': 'fi'
    }
    for wrong, right in replacements.items():
        text = text.replace(wrong, right)

    return text.strip()

def extract_text(file_path: str) -> str:
    """Main extraction function with clean output"""
    ext = os.path.splitext(file_path)[1].lower()

    if ext == '.pdf':
        raw_text = extract_text_from_pdf(file_path)
        if not raw_text.strip() and ext == '.pdf':
            raw_text = ocr_pdf(file_path)
            raw_text = "OCR: " + raw_text
    elif ext == '.docx':
        raw_text = extract_text_from_docx(file_path)
    else:
        return ""

    return clean_extracted_text(raw_text)

def process_cv_file(input_path: str, output_path: Optional[str] = None) -> dict:
    """
    Process a CV file and save the extracted text.

    Args:
        input_path: Path to input file
        output_path: Path to save extracted text (None to skip saving)

    Returns:
        Dictionary with extraction results and metadata
    """
    result = {
        'input_path': input_path,
        'success': False,
        'method': None,
        'text': '',
        'error': None
    }

    text = extract_text(input_path)

    if text:
        result['success'] = True
        result['text'] = text
        result['method'] = 'direct' if not text.startswith('OCR') else 'ocr'

        if output_path:
            try:
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(text)
                result['output_path'] = output_path
            except Exception as e:
                result['error'] = f"Failed to save output: {str(e)}"
                logging.error(result['error'])
    else:
        result['error'] = "No text extracted"

    return result

if __name__ == "__main__":
    input_dir = "CV"
    output_dir = "text_extract_v3"

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for filename in os.listdir(input_dir):
        input_path = os.path.join(input_dir, filename)
        name, ext = os.path.splitext(filename)
        output_path = os.path.join(output_dir, f"{name}_text_extract.txt")

        if ext.lower() not in [".pdf", ".docx"]:
            logging.info(f"Skipping unsupported file type: {filename}")
            continue

        result = process_cv_file(input_path, output_path)

        if result['success']:
            print(f"Text extracted successfully -> {output_path}")
        else:
            print(f"Failed to extract text: {result.get('error', 'Unknown error')}")