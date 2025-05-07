import fitz  # PyMuPDF
import docx  # python-docx
import os
import pytesseract
import pdf2image
import logging
from typing import Optional

# Configure logging
logging.basicConfig(
    filename='cv_extraction.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def extract_text_from_pdf(path: str) -> str:
    """Extract text from a PDF using PyMuPDF."""
    try:
        doc = fitz.open(path)
        full_text = []
        for page in doc:
            text = page.get_text()
            if text:  # Only add if text was found
                full_text.append(text)
        return "\n".join(full_text).strip()
    except Exception as e:
        logging.error(f"Error reading PDF {path}: {str(e)}")
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

def extract_text_from_docx(path):
    """Extract text from a DOCX using python-docx."""
    try:
        doc = docx.Document(path)
        full_text = []

        for element in doc.element.body:
            # Handle paragraphs
            if element.tag.endswith('p'):
                para = docx.text.paragraph.Paragraph(element, doc)
                full_text.append(para.text)
            # Handle tables
            elif element.tag.endswith('tbl'):
                table = docx.table.Table(element, doc)
                for row in table.rows:
                    row_text = []
                    for cell in row.cells:
                        cell_text = []
                        for para in cell.paragraphs:
                            cell_text.append(para.text)
                        row_text.append(" | ".join(cell_text))
                    full_text.append("\t".join(row_text))

        return "\n".join(full_text).strip()
    except Exception as e:
        print(f"Error reading DOCX: {e}")
        return ""

def extract_text(
    file_path: str,
    ocr_lang: str = "eng+vie+jpn",
    attempt_ocr: bool = True,
    ocr_page_limit: Optional[int] = None
) -> str:
    """
    Extract text from a file (PDF or DOCX).

    Args:
        file_path: Path to the file
        ocr_lang: Languages for OCR (Tesseract format)
        attempt_ocr: Whether to attempt OCR if direct extraction fails
        ocr_page_limit: Maximum number of pages to OCR (None for all)

    Returns:
        Extracted text as string
    """
    if not os.path.exists(file_path):
        logging.error(f"File not found: {file_path}")
        return ""

    ext = os.path.splitext(file_path)[1].lower()
    text = ""

    if ext == ".pdf":
        text = extract_text_from_pdf(file_path)
        if attempt_ocr and not text.strip():
            logging.info(f"Attempting OCR for {file_path}")
            text = ocr_pdf(file_path, lang=ocr_lang, page_limit=ocr_page_limit)
    elif ext == ".docx":
        text = extract_text_from_docx(file_path)
    else:
        logging.warning(f"Unsupported file type: {file_path}")

    return text

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
    output_dir = "text_extract"

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