# utils/cleaner.py
import re
from bs4 import BeautifulSoup

def remove_html(text):
    return ''.join(BeautifulSoup(text, "html.parser").stripped_strings)

def clean_extracted_text(text: str) -> str:
    # Remove unwanted prefix at the beginning of the text
    text = re.sub(r"^` x", "", text)

    # Normalize line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    sections = ["PERSONAL DETAILS", "PROFESSIONAL SUMMARY", "SKILLS",
                "EDUCATION", "PROJECTS", "WORK EXPERIENCE"]
    for section in sections:
        text = re.sub(rf"(?i){section}\s+{section}", section, text)

    # Remove unwanted artifacts
    text = re.sub(r'©.*\.(vn|com)', '', text)
    text = re.sub(r'Page \d+ of \d+', '', text)
    text = re.sub(r'Trang \d+ / \d+', '', text)

    # Collapse too many newlines or spaces
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)

    # Fix missing space after period
    text = re.sub(r'(?<=[a-zA-Z])\.(?=[A-Z])', '. ', text)

    # Handling non-breaking spaces and other whitespace
    text = text.replace('\u00A0', ' ')  # Non-breaking space

    # Remove HTML tags
    text = remove_html(text)

    # Common OCR character fixes
    replacements = {
        '': '📍',
        'ﬁ': 'fi',
        '–': '-',  # en-dash to hyphen
        '’': "'",  # right single quotation mark
        '‘': "'",  # left single quotation mark
        '“': '"',  # left double quotation mark
        '”': '"',  # right double quotation mark
        '©': '(C)',  # Special handling for copyright symbol
    }
    for wrong, right in replacements.items():
        text = text.replace(wrong, right)

    section_titles = [
        "MỤC TIÊU", "HỌC VẤN", "DỰ ÁN", "KY NANG",
        "Website", "Github", "Source code", "Demo sản phẩm"
    ]
    for title in section_titles:
        text = re.sub(rf"(?i)^{title}", title, text)

    # Clean contact details: phone, email, and GitHub links
    text = re.sub(r'([+]\d{10,15})', r'Phone: \1', text)  # Format phone number
    text = re.sub(r'[\w\.-]+@[\w\.-]+', r'Email: \g<0>', text)  # Format email
    text = re.sub(r'github\.com/[\w\.-]+', r'GitHub: \g<0>', text)  # Format GitHub URL

    # Clean the date formats for consistency
    text = re.sub(r'(\d{2}/\d{4})', r'\g<1>', text)  # Normalize date formats if needed

    return text.strip()


