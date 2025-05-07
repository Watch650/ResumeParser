# file_router.py
import os
import sys
import logging
from pathlib import Path
from langdetect import detect, LangDetectException
from tqdm import tqdm
from extractors.pdf_extractor import extract_pdf_text
from extractors.docx_extractor import extract_docx_text
from utils.cleaner import clean_extracted_text

def configure_logging(log_dir: Path):
    """Configure logging to use specified directory"""
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "file_router.log"

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def get_script_directory() -> Path:
    """Returns the directory where the script is located"""
    return Path(__file__).parent

def extract_text(file_path: Path) -> str:
    """Extract and clean text from supported file types"""
    ext = file_path.suffix.lower()
    raw_text = ""

    try:
        if ext == '.pdf':
            raw_text = extract_pdf_text(str(file_path))
        elif ext == '.docx':
            raw_text = extract_docx_text(str(file_path))
        else:
            logging.warning(f"Unsupported file format: {file_path.name}")
            return ""
    except Exception as e:
        logging.error(f"Error extracting {file_path.name}: {str(e)}")
        return ""

    return clean_extracted_text(raw_text)

def detect_language_safe(text: str) -> str:
    """Robust language detection with error handling"""
    try:
        clean_text = text.strip()
        if len(clean_text) < 50:  # Minimum characters for reliable detection
            return 'unknown'
        return detect(clean_text)
    except LangDetectException:
        return 'unknown'

def process_file(input_path: Path, output_base: Path) -> str:
    """Process a single file and route to language-specific folder"""
    try:
        text = extract_text(input_path)
        if not text:
            logging.warning(f"No text extracted from {input_path.name}")
            return 'error'

        lang = detect_language_safe(text)
        lang_folder = 'vietnamese' if lang == 'vi' else 'english'

        output_dir = output_base / lang_folder
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / f"{input_path.stem}_extracted.txt"

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text)

        return lang_folder

    except Exception as e:
        logging.error(f"Error processing {input_path.name}: {str(e)}")
        return 'error'

def main():
    base_dir = get_script_directory()

    # Configure paths
    input_dir = base_dir / "CV"
    output_base = base_dir / "text_extract"
    log_dir = base_dir / "logs"

    # Setup logging
    configure_logging(log_dir)
    logging.info(f"Starting file routing from: {input_dir}")

    # Get supported files
    supported_ext = ['.pdf', '.docx']
    input_files = [f for f in input_dir.glob('*') if f.suffix.lower() in supported_ext]

    if not input_files:
        logging.error("No supported files found in input directory!")
        sys.exit(1)

    # Process files
    results = {'vietnamese': 0, 'english': 0, 'error': 0}

    for file in tqdm(input_files, desc="Routing files"):
        result = process_file(file, output_base)
        results[result] += 1

    # Print summary
    logging.info("Processing Summary")
    logging.info(f"├── Total files: {len(input_files)}")
    logging.info(f"├── Vietnamese: {results['vietnamese']}")
    logging.info(f"├── English: {results['english']}")
    logging.info(f"└── Errors: {results['error']}")
    logging.info(f"Output organized in: {output_base}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Process interrupted by user")
        sys.exit(0)
    except Exception as e:
        logging.critical(f"Unexpected error: {str(e)}")
        sys.exit(1)