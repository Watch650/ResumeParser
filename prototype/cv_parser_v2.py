import os
import re
import json
# from pyvi import ViTokenizer
from datetime import datetime
from langdetect import detect, DetectorFactory
from typing import Dict, List, Optional, Tuple

# Set deterministic language detection
DetectorFactory.seed = 0

# Configuration
CONFIG = {
    "skills": {
        "all": [
            # Technical (English/Vietnamese)
            "python", "java", "sql", "machine learning", "máy học",
            "html/css", "javascript", "react", "django",
            # Soft skills
            "communication", "teamwork", "giao tiếp", "làm việc nhóm"
        ]
    },
    "degrees": {
        "all": [
            "bachelor", "master", "phd", "engineer",
            "cử nhân", "thạc sĩ", "tiến sĩ", "kỹ sư"
        ]
    },
    "job_titles": {
        "all": [
            "developer", "engineer", "manager", "analyst",
            "lập trình viên", "kỹ sư", "quản lý", "chuyên viên"
        ]
    }
}

# Language detection with fallback
def detect_field_language(text: str) -> Tuple[str, float]:
    """Detect language with confidence score for a text snippet"""
    try:
        # Check for Vietnamese characters first
        vi_chars = len(re.findall(r'[àáảãạăằắẳẵặâầấẩẫậđèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ]', text))
        if vi_chars / max(1, len(text)) > 0.1:
            return ("vi", 0.9 + (vi_chars / len(text)) * 0.1)

        # Use langdetect for non-Vietnamese text
        lang = detect(text)
        return (lang, 0.8) if lang == "vi" else ("en", 0.8)
    except:
        return ("en", 0.5)  # Fallback to English

# Bilingual text processing
# def preprocess_text(text: str, lang: str) -> str:
#     text = text.lower()
#     if lang == "vi":
#         text = ViTokenizer.tokenize(text)
#     return text

# Extractors
def extract_mixed_name(text: str) -> Optional[str]:
    """Name extraction that works for both languages"""
    # Vietnamese patterns
    vi_patterns = [
        r"(họ tên|tên đầy đủ)[:\s]*([^\n]+)",
        r"^(ông|bà|anh|chị)\s+([^\n]+)"
    ]
    # English patterns
    en_patterns = [
        r"(?:full name|name)[:\s]*([^\n]+)",
        r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}(?=\n)"
    ]

    # Try all patterns and pick the most confident match
    candidates = []
    for pattern in vi_patterns:
        if match := re.search(pattern, text, re.IGNORECASE):
            lang, conf = detect_field_language(match.group(0))
            candidates.append((match.group(2).strip(), conf))

    for pattern in en_patterns:
        if match := re.search(pattern, text, re.IGNORECASE):
            lang, conf = detect_field_language(match.group(0))
            candidates.append((match.group(1).strip(), conf))

    if candidates:
        return max(candidates, key=lambda x: x[1])[0]
    return None

def extract_phone(text: str) -> Optional[str]:
    phone_match = re.search(r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text)
    return phone_match.group(0) if phone_match else None

def extract_email(text: str) -> Optional[str]:
    email_match = re.search(r"\b[\w\.-]+@[\w\.-]+\.\w+\b", text)
    return email_match.group(0) if email_match else None

def extract_hybrid_skills(text: str) -> List[str]:
    """Skill extraction without language dependency"""
    found = []
    text_lower = text.lower()
    for skill in CONFIG["skills"]["all"]:
        if re.search(rf'\b{re.escape(skill)}\b', text_lower):
            found.append(skill)
    return list(set(found))

def extract_education(text: str, lang: str) -> Dict[str, Optional[str]]:
    result = {"school": None, "degree": None}

    school_keywords = {
        "en": ["university", "college", "institute"],
        "vi": ["đại học", "học viện", "trường"]
    }

    # School extraction
    for kw in school_keywords[lang]:
        match = re.search(rf'{kw}[^\n,]{0,50}', text, re.IGNORECASE)
        if match:
            result["school"] = match.group(0).strip().title()
            break

    # Degree extraction
    for degree in CONFIG["degrees"][lang]:
        if re.search(rf'\b{re.escape(degree)}\b', text, re.IGNORECASE):
            result["degree"] = degree.title()
            break

    return result

def extract_experience(text: str, lang: str) -> Dict[str, any]:
    exp = {"years": 0, "positions": []}

    # Position titles
    for title in CONFIG["job_titles"][lang]:
        if re.search(rf'\b{re.escape(title)}\b', text, re.IGNORECASE):
            exp["positions"].append(title.title())

    # Year calculation (works for both languages)
    year_matches = re.findall(r'\b(20\d{2}|19\d{2})\b', text)
    if len(year_matches) >= 2:
        years = sorted([int(y) for y in year_matches])
        exp["years"] = years[-1] - years[0]

    return exp

def process_cv_sections(text: str) -> Dict[str, any]:
    """Smart section-based parsing with mixed language support"""
    # Split into logical sections (heuristic)
    sections = {
        "personal": "",
        "education": "",
        "experience": "",
        "skills": ""
    }

    # Simple section detector (customize as needed)
    section_headers = {
        "personal": r"(thông tin cá nhân|personal info)",
        "education": r"(học vấn|education|qualifications)",
        "experience": r"(kinh nghiệm|experience|work history)",
        "skills": r"(kỹ năng|skills|technical skills)"
    }

    current_section = None
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue

        # Check for new section
        for section, pattern in section_headers.items():
            if re.search(pattern, line, re.IGNORECASE):
                current_section = section
                break

        # Add content to current section
        if current_section:
            sections[current_section] += line + "\n"

    return sections

# Main Parser
def parse_hybrid_cv(text: str) -> Dict[str, any]:
    """Main parser handling mixed-language CVs"""
    sections = process_cv_sections(text)

    # Field-specific processing
    name = extract_mixed_name(sections["personal"] or text)
    email = extract_email(text)
    phone = extract_phone(text)

    # Education with language auto-detection
    edu_text = sections["education"]
    edu_lang, _ = detect_field_language(edu_text)

    # Experience with language auto-detection
    exp_text = sections["experience"]
    exp_lang, _ = detect_field_language(exp_text)

    return {
        "metadata": {
            "primary_language": detect_field_language(text)[0],
            "mixed_content": True if len({detect_field_language(s)[0] for s in sections.values()}) > 1 else False
        },
        "personal": {
            "name": name,
            "email": email,
            "phone": phone
        },
        "education": {
            "text": edu_text.strip(),
            "detected_language": edu_lang,
            "degrees": [d for d in CONFIG["degrees"]["all"] if re.search(rf'\b{d}\b', edu_text.lower())],
            "institutions": re.findall(r'(?:(?:đại học|học viện|university|college)\s+[^\n,]+)', edu_text, re.IGNORECASE)
        },
        "experience": {
            "text": exp_text.strip(),
            "detected_language": exp_lang,
            "positions": [p for p in CONFIG["job_titles"]["all"] if re.search(rf'\b{p}\b', exp_text.lower())],
            "duration_years": len(re.findall(r'\b(20\d{2}|19\d{2})\b', exp_text)) // 2  # Approximate
        },
        "skills": {
            "all": extract_hybrid_skills(sections["skills"] or text),
            "technical": [],
            "soft": []
        }
    }

# File Processing
def process_files(input_dir: str, output_dir: str):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for filename in os.listdir(input_dir):
        if filename.endswith(".txt"):
            input_path = os.path.join(input_dir, filename)
            output_path = os.path.join(output_dir, f"{os.path.splitext(filename)[0]}_parsed.json")

            try:
                with open(input_path, 'r', encoding='utf-8') as f:
                    cv_text = f.read()

                parsed = parse_hybrid_cv(cv_text)

                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(parsed, f, indent=2, ensure_ascii=False)

                print(f"Processed: {filename} ({parsed['language']})")
            except Exception as e:
                print(f"Error in {filename}: {str(e)}")

if __name__ == "__main__":
    process_files("text_extract", "info_parse")