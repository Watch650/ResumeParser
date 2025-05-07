import re
import json
import os
from pyvi import ViTokenizer
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration for Vietnamese and English
CONFIG = {
    "skills": {
        "technical": [
            "PHP Laravel", "NuxtJS", "Linux", "HTML/CSS", "SASS",
            "Jquery", "JavaScript", "Python", "Java", "SQL",
            "React", "Vue", "Angular", "Django", "Flask"
        ],
        "soft": [
            "Giao tiếp", "Làm việc nhóm", "Quản lý thời gian",
            "communication", "teamwork", "time management"
        ]
    },
    "degrees": {
        "vi": ["cử nhân", "thạc sĩ", "tiến sĩ", "kỹ sư", "cao đẳng", "đại họchọc"],
        "en": ["bachelor", "master", "phd", "engineer", "college"]
    },
    "locations": [
        "Hanoi", "Ho Chi Minh", "Da Nang", "Hải Phòng",
        "Vietnam", "Việt Nam", "TP.HCM", "Đà Nẵng"
    ],
    "languages": [
        "Giao tiếp", "IELTS", "TOEIC", "TOEFL",
        "English", "Tiếng Anh", "Japanese"
    ]
}

def detect_language(text: str) -> str:
    """Detect language with Vietnamese character check"""
    try:
        if re.search(r'[àáảãạăằắẳẵặâầấẩẫậđèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ]', text):
            return "vi"
        return "en"
    except:
        return "en"

def extract_name(text: str) -> Optional[str]:
    """Enhanced name extraction for Vietnamese and English"""
    # Vietnamese patterns
    vi_patterns = [
        r"(Họ tên|Tên đầy đủ)[:\s]*([^\n]+)",
        r"^(Ông|Bà|Anh|Chị)\s+([^\n]+)"
    ]
    # English patterns
    en_patterns = [
        r"(Full Name|Name)[:\s]*([^\n]+)",
        r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}$"
    ]

    # Try Vietnamese patterns first
    for pattern in vi_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            name = match.group(2).strip()
            return ' '.join([word.capitalize() for word in name.split()])

    # Try English patterns
    for pattern in en_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            name = match.group(2 if "Full Name" in pattern else 1).strip()
            return ' '.join([word.capitalize() for word in name.split()])

    # Fallback: Look for the most name-like line
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    for line in lines[:5]:  # Check first 5 lines
        words = line.split()
        if 2 <= len(words) <= 4 and all(word[0].isupper() for word in words if word):
            return line
    return None

def extract_birth_year(text: str) -> Optional[str]:
    """Extract birth year from various formats"""
    patterns = [
        r"(sinh năm|năm sinh|birth year|year of birth)[:\s]*(\d{4})",
        r"\b(19\d{2}|20[01]\d)\b(?![^\d]{1,5}\d)"  # Exclude phone numbers
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(2)
    return None

def extract_contact_info(text: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract email and phone with Vietnamese support"""
    # Email extraction
    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
    email = email_match.group(0) if email_match else None

    # Phone extraction (Vietnamese and international formats)
    phone_match = re.search(
        r'(?:\+?84|0)(?:\d){9,10}|'  # Vietnamese format
        r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,}\)?[-.\s]?\d{3}[-.\s]?\d{4}',  # International
        text
    )
    phone = phone_match.group(0) if phone_match else None

    return email, phone

def extract_location(text: str) -> Optional[str]:
    """Extract location from known Vietnamese places"""
    for location in CONFIG["locations"]:
        if re.search(rf'\b{re.escape(location)}\b', text, re.IGNORECASE):
            return location
    return None

def extract_skills(text: str) -> List[str]:
    """Extract skills from predefined list with word boundaries"""
    found_skills = []
    text_lower = text.lower()

    for skill in CONFIG["skills"]["technical"] + CONFIG["skills"]["soft"]:
        if re.search(rf'\b{re.escape(skill.lower())}\b', text_lower):
            found_skills.append(skill)

    return list(set(found_skills))

def extract_education(text: str) -> Dict[str, Optional[str]]:
    """Extract education information with time period"""
    result = {
        "truong": None,
        "thoi_gian": None,
        "chuyen_nganh": None
    }

    # School extraction
    school_match = re.search(
        r'(?:Trường|Đại học|Học viện|University|College)\s*[:\-]?\s*([^\n,]+)',
        text,
        re.IGNORECASE
    )
    if school_match:
        result["truong"] = school_match.group(1).strip()

    # Major extraction
    major_match = re.search(
        r'(?:Ngành|Chuyên ngành|Major|Field)[:\-]?\s*([^\n,]+)',
        text,
        re.IGNORECASE
    )
    if major_match:
        result["chuyen_nganh"] = major_match.group(1).strip()

    # Time period extraction
    time_match = re.search(
        r'(\d{4}\s*[~\-]\s*\d{4}|'
        r'(?:Tháng|Month )?\d{1,2}/\d{4}\s*[~\-]\s*(?:Tháng|Month )?\d{1,2}/\d{4}|'
        r'\d{4}\s*[~\-]\s*(?:nay|present))',
        text,
        re.IGNORECASE
    )
    if time_match:
        result["thoi_gian"] = time_match.group(1)

    return result

def extract_experience_years(text: str) -> int:
    """Calculate total years of experience"""
    year_matches = re.findall(r'\b(20\d{2}|19\d{2})\b', text)
    if len(year_matches) >= 2:
        years = sorted([int(y) for y in year_matches])
        return years[-1] - years[0]
    return 0

def extract_language_skills(text: str) -> Optional[str]:
    """Extract language proficiency"""
    for lang in CONFIG["languages"]:
        if re.search(rf'\b{re.escape(lang)}\b', text, re.IGNORECASE):
            return lang
    return None

def extract_introduction(text: str) -> Optional[str]:
    """Extract the most paragraph-like text as introduction"""
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    for p in paragraphs:
        if len(p.split()) > 20:  # Select the first substantial paragraph
            return p
    return None

def extract_info(text: str) -> Dict[str, any]:
    """Main extraction function for the desired fields"""
    lang = detect_language(text)

    # Extract all fields
    name = extract_name(text)
    email, phone = extract_contact_info(text)
    birth_year = extract_birth_year(text)
    location = extract_location(text)
    skills = extract_skills(text)
    education = extract_education(text)
    experience_years = extract_experience_years(text)
    language_skill = extract_language_skills(text)
    introduction = extract_introduction(text)

    return {
        "ho_ten": name,
        "ngay_sinh": birth_year,
        "so_dien_thoai": phone,
        "email": email,
        "khu_vuc": location,
        "kinh_nghiem_nam": experience_years if experience_years > 0 else None,
        "trinh_do_hoc_van": education,
        "ngoai_ngu": language_skill,
        "ky_nang_chinh": skills,
        "gioi_thieu": introduction
    }

def process_files(input_dir: str, output_dir: str):
    """Process all files in input directory and save results"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    processed_count = 0
    error_count = 0

    for filename in os.listdir(input_dir):
        if filename.endswith(".txt"):
            input_path = os.path.join(input_dir, filename)
            output_filename = f"{os.path.splitext(filename)[0]}_parsed.json"
            output_path = os.path.join(output_dir, output_filename)

            try:
                with open(input_path, 'r', encoding='utf-8') as file:
                    resume_text = file.read()

                extracted = extract_info(resume_text)

                with open(output_path, 'w', encoding='utf-8') as outfile:
                    json.dump(extracted, outfile, indent=2, ensure_ascii=False)

                logger.info(f"Processed: {filename}")
                processed_count += 1
            except Exception as e:
                logger.error(f"Error processing {filename}: {str(e)}")
                error_count += 1

    logger.info(f"Processing completed. Success: {processed_count}, Errors: {error_count}")

if __name__ == "__main__":
    input_dir = "text_extract"
    output_dir = "info_parse"

    process_files(input_dir, output_dir)