# utils/ocr.py
import pdf2image
import pytesseract
import logging
from PIL import Image
from typing import List

def preprocess_image(image: Image.Image) -> Image.Image:
    # Convert to grayscale
    gray = image.convert('L')
    # Binarize (simple thresholding)
    bw = gray.point(lambda x: 0 if x < 150 else 255, '1')
    return bw

def ocr_pdf(path: str, lang: str = "eng+vie", page_limit=None) -> str:
    try:
        logging.info(f"Running OCR on: {path}")
        images: List[Image.Image] = pdf2image.convert_from_path(path, dpi=300)
        text_parts = []

        for i, img in enumerate(images):
            if page_limit is not None and i >= page_limit:
                break

            logging.info(f"Processing page {i+1}/{len(images)}")
            preprocessed = preprocess_image(img)
            ocr_text = pytesseract.image_to_string(preprocessed, lang=lang, config="--psm 6")
            text_parts.append(ocr_text)

        return "\n\n".join(text_parts).strip()

    except Exception as e:
        logging.error(f"OCR failed for {path}: {e}")
        return ""
