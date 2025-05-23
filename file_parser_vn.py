# file_parser_vn.py

import os
import re
import json
import logging
from pathlib import Path
from tqdm import tqdm
from models.ner_model_vn import load_model_vn, process_text_chunks_vn, inspect_entity_outputs_vn, combine_entities_vn
from utils.reference_data import match_location, get_default_location, match_skills_from_text

def info_structure():
    """Initialize the information structure with default values"""
    return {
        "ho_ten": None,
        "ngay_sinh": None,
        "so_dien_thoai": None,
        "email": None,
        "khu_vuc": None,
        "kinh_nghiem_nam": None,
        "trinh_do_hoc_van": None,
        "ngoai_ngu": None,
        "ky_nang_chinh": [],
        "gioi_thieu": None,
    }

def extract_info(text: str, ner_vn):
    """Main function to extract all information from CV text"""
    entities_vn = process_text_chunks_vn(text, ner_vn)
    inspect_entity_outputs_vn(entities_vn)

    info = info_structure()

    try:
        # Extract personal information
        info.update(extract_personal_info(text, entities_vn))

        # Extract location information
        info.update(extract_location_info(text, entities_vn))

        # Extract contact information
        info.update(extract_contact_info(text))

        # Extract experience information
        info.update(extract_experience_info(text))

        # Extract education information
        info["trinh_do_hoc_van"] = extract_education_level(text, entities_vn)

        # Extract language information
        info["ngoai_ngu"] = extract_language_info(text)

        # Extract skills information
        info["ky_nang_chinh"] = extract_skills_info(text)

        # Extract summary information
        # info.update(extract_summary_info(text, info))

    except Exception as e:
        logging.error(f"Error extracting info: {str(e)}")

    return info

def extract_personal_info(text, entities):
    """Extract personal information (name, birth date)"""
    info = {}

    # Name extraction
    person_entities = combine_entities_vn(entities, "PERSON")
    if person_entities:
        # Function to calculate the score for a name (based on length and uppercase letter count)
        def name_score(name):
            return len(name), sum(1 for c in name if c.isupper())

        # Sort names by length and uppercase count, picking the one with the highest score
        info["ho_ten"] = max(person_entities, key=lambda name: name_score(name))
    else:
        info["ho_ten"] = None

    # Fallback name extraction
    if not info["ho_ten"]:
        first_lines = text.split('.')[:2]
        for line in first_lines:
            upper_line = re.search(r'^([A-ZÀ-Ỵ][A-ZÀ-Ỵ\s]{2,})$', line.strip())
            if upper_line:
                info["ho_ten"] = upper_line.group(1).title()
                break

    # Date of Birth extraction
    dob_match = re.search(r'\b(?:ngày\s*sinh|dob)?[:\s]*([0-3]?\d[/-][01]?\d[/-]\d{2,4})\b', text, re.IGNORECASE)
    if dob_match:
        info["ngay_sinh"] = dob_match.group(1)

    return info

def extract_location_info(text, entities):
    """Extract location information"""
    info = {}
    location_entities = combine_entities_vn(entities, "LOCATION")
    # location_entities = [e["word"] for e in entities if e["entity_group"] == "LOCATION"]

    # Check for location matches
    for location in location_entities:
        matched_province = match_location(location)
        if matched_province:
            info["khu_vuc"] = matched_province

    # Fallback location extraction
    if not info.get("khu_vuc"):
        loc_match = re.search(r'(Thành phố|Tỉnh|TP)[^.,\n]+', text, re.IGNORECASE)
        if loc_match:
            loc_text = loc_match.group(0).strip()
            matched_province = match_location(loc_text)
            if matched_province:
                info["khu_vuc"] = matched_province

    # Default location if none found
    if not info.get("khu_vuc"):
        info["khu_vuc"] = get_default_location()

    return info

def extract_contact_info(text):
    """Extract contact information (email, phone)"""
    info = {}

    # Email extraction
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    if email_match:
        info["email"] = email_match.group(0)

    # Phone extraction
    phone_match = re.search(r'\b(?:\+?84|0)(\d{9})\b', text.replace(' ', '').replace('-', ''))
    if phone_match:
        number = phone_match.group(0).strip()
        info["so_dien_thoai"] = number

    return info

def extract_experience_info(text):
    """Extract work experience information"""
    info = {}

    exp_match = re.search(r'(\d+)\s*(năm|year|yrs?|y)\s*(kinh\s*nghiệm|experience|exp)?\s*(?:over|trên|more\s*than|với\s*hơn|with)?', text, re.IGNORECASE)
    if exp_match:
        info["kinh_nghiem_nam"] = int(exp_match.group(1))

    return info

def extract_education_level(text: str, entities: list) -> int:
    """
    Extract and map the highest education level from text to ID.
    Returns integer ID according (1-5)
    """
    # Priority search patterns (higher education first)
    patterns = [
        (r"(thạc sĩ|tiến sĩ|master|phd|doctor)", 4),       # after_university
        (r"(đại học|đh|học viện|university|bachelor|cử nhân|kỹ sư|academy)(?!\s*(thạc sĩ|tiến sĩ))", 3),  # university
        (r"(cao đẳng|college|trung cấp|vocational)", 2),     # college
        (r"(trung học|thpt|highschool|high school)", 1)  # high_school
    ]

    # 1. Check for explicit degree mentions in text (prioritizing higher degrees)
    for pattern, degree_id in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return degree_id

    # 2. Check organization entities for school names that imply degree level
    org_entities = [e["word"] for e in entities if e["entity_group"] == "ORGANIZATION"]
    for org in org_entities:
        org_lower = org.lower()
        if any(k in org_lower for k in ["đại học", "đh", "học viện"]):
            return 3  # university
        elif any(k in org_lower for k in ["cao đẳng", "trung cấp"]):
            return 2  # college
        elif any(k in org_lower for k in ["trung học", "thpt"]):
            return 1  # high_school

    # 3. Check education section if still not found
    education_section = re.search(
        r"(học vấn|giáo dục|trình độ|bằng cấp|education|bằng)[^:]*[:]?(.*?)(?=\n\s*\n|$)",
        text,
        re.IGNORECASE | re.DOTALL
    )

    if education_section:
        edu_text = education_section.group(2)
        for pattern, degree_id in patterns:
            match = re.search(pattern, edu_text, re.IGNORECASE)
            if match:
                return degree_id

    return 5  # Default to 'other' if no degree level identified

def extract_language_info(text):
    """Detect language proficiency levels (English/Japanese) and return their label IDs."""
    text = text.lower()
    lines = text.splitlines()

    LANGUAGE_LEVELS = {
        "english": {'id': 1, 'value': 'english', 'name': 'Tiếng Anh giao tiếp'},
        "japanese": {'id': 2, 'value': 'japanese', 'name': 'Tiếng Nhật giao tiếp'},
        "basic_english": {'id': 3, 'value': 'basic_english', 'name': 'Tiếng Anh cơ bản'},
        "basic_japanese": {'id': 4, 'value': 'basic_japanese', 'name': 'Tiếng Nhật cơ bản'},
        "none": {'id': 5, 'value': 'none', 'name': 'Không có ngoại ngữ'},
    }

    level_keywords = {
        "advanced": [
            "thành thạo", "bản địa", "nâng cao", "chuyên nghiệp", "thuần thục",
            "fluency", "fluent", "native", "professional", "communicate", "advanced", "proficient"
        ],
        "basic": [
            "cơ bản", "căn bản", "đọc hiểu", "đơn giản", "phổ thông", "tốt", "ổn", "bình thường", "thường"
            "basic", "elementary", "beginner", "intermediate", "standard"
        ]
    }

    english_level = None
    japanese_level = None

    for line in lines:
        if not line.strip():
            continue

        # ----------------- English Detection -----------------
        if re.search(r"(tiếng anh|english)", line):
            # Check for IELTS
            ielts_match = re.search(r"ielts\s*(\d+(\.\d+)?)", line)
            if ielts_match:
                score = float(ielts_match.group(1))
                english_level = "english" if score >= 7.0 else "basic_english"
            else:
                # Check for TOEIC
                toeic_match = re.search(r"toeic\s*(\d+)", line)
                if toeic_match:
                    score = int(toeic_match.group(1))
                    english_level = "english" if score >= 650 else "basic_english"
                # Check for CEFR Levels
                elif re.search(r"\b(c1|c2)\b", line):
                    english_level = "english"
                elif re.search(r"\b(a1|a2|b1|b2)\b", line):
                    english_level = "basic_english"
                # Keywords for advanced and basic English
                elif any(kw in line for kw in level_keywords["advanced"]):
                    english_level = "english"
                elif any(kw in line for kw in level_keywords["basic"]):
                    english_level = "basic_english"

        # ----------------- Japanese Detection -----------------
        if re.search(r"(tiếng nhật|japanese)", line):
            # Check for Japanese proficiency levels (N1–N5)
            if re.search(r"\bn1\b|\bn2\b", line) or any(kw in line for kw in level_keywords["advanced"]):
                japanese_level = "japanese"
            elif re.search(r"\bn3\b|\bn4\b|\bn5\b", line) or any(kw in line for kw in level_keywords["basic"]):
                japanese_level = "basic_japanese"

    result_ids = None

    if english_level:
        result_ids = LANGUAGE_LEVELS[english_level]["id"]
    if japanese_level:
        result_ids = LANGUAGE_LEVELS[japanese_level]["id"]

    if not result_ids:
        result_ids = LANGUAGE_LEVELS["none"]["id"]

    return result_ids

def extract_skills_info(text):
    """Extract skills information"""
    info = match_skills_from_text(text)
    return info

def process_files(input_folder, output_file, ner_vn):
    """Process all segmented text files and extract CV data"""
    if not ner_vn:
        logging.error("Vietnamese NER pipeline not initialized")
        return

    try:
        txt_files = list(Path(input_folder).glob("*.txt"))
        if not txt_files:
            logging.warning(f"No TXT files found in {input_folder}")
            return

        cv_data = []
        for txt_file in tqdm(txt_files, desc="Processing files"):
            try:
                with open(txt_file, 'r', encoding='utf-8') as f:
                    text = f.read().strip()

                if not text or len(text) < 20:
                    logging.debug(f"Skipping small/empty file: {txt_file.name}")
                    continue

                extracted_info = extract_info(text, ner_vn)
                extracted_info["source_file"] = txt_file.name
                cv_data.append(extracted_info)

            except Exception as e:
                logging.error(f"Error processing {txt_file.name}: {str(e)}")

        # Save results
        temp_file = f"{output_file}.tmp"
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(cv_data, f, ensure_ascii=False, indent=2)
        os.replace(temp_file, output_file)

        logging.info(f"Successfully processed {len(cv_data)} files to {output_file}")

    except Exception as e:
        logging.critical(f"Fatal error in file processing: {str(e)}")

def main():
    """Main function to process CV files"""
    logging.info("Starting CV parser")

    try:
        ner_vn = load_model_vn()
        if not ner_vn:
            return

        base_dir = Path(__file__).parent
        input_folder = base_dir / "text_extract" / "vietnamese"
        output_file = base_dir / "parsed_data" / "extracted_cv_data_vn.json"

        output_file.parent.mkdir(parents=True, exist_ok=True)

        process_files(input_folder, output_file, ner_vn)

    except Exception as e:
        logging.error(f"Critical error: {str(e)}")

if __name__ == "__main__":
    main()
