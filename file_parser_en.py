# file_parser_en.py

import os
import re
import json
import logging
from pathlib import Path
from tqdm import tqdm
from models.ner_model_en import load_model_en, process_text_chunks_en, inspect_entity_outputs_en, combine_entities_en
from models.ner_model_vn import load_model_vn, process_text_chunks_vn, combine_entities_vn
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

def extract_info(text: str, ner_en, ner_vn):
    """Main function to extract all information from CV text"""
    entities_en = process_text_chunks_en(text, ner_en)
    entities_vn = process_text_chunks_vn(text, ner_vn)
    inspect_entity_outputs_en(entities_en)

    info = info_structure()

    try:
        # Extract name information
        info.update(extract_name(text, entities_vn))

        # Extract dob information
        info["ngay_sinh"] = extract_dob(text)

        # Extract location information
        info.update(extract_location_info(text, entities_en))

        # Extract contact information
        info.update(extract_contact_info(text))

        # Extract experience information
        info.update(extract_experience_info(text))

        # Extract education information
        info["trinh_do_hoc_van"] = extract_education_level(text, entities_en)

        # Extract language information
        info["ngoai_ngu"] = extract_language_info(text)

        # Extract skills information
        info["ky_nang_chinh"] = extract_skills_info(text)

        # Extract summary information
        # info.update(extract_summary_info(text, info))

    except Exception as e:
        logging.error(f"Error extracting info: {str(e)}")

    return info

def extract_name(text, entities):
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
            upper_line = re.search(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)$', line.strip())
            if upper_line:
                info["ho_ten"] = upper_line.group(1).title()
                break

    return info

def extract_dob(text):
    """Extract DOB from text, handling English and Vietnamese formats with ordinal dates."""

    month_map = {
        "january": "01", "jan": "01",
        "february": "02", "feb": "02",
        "march": "03", "mar": "03",
        "april": "04", "apr": "04",
        "may": "05",
        "june": "06", "jun": "06",
        "july": "07", "jul": "07",
        "august": "08", "aug": "08",
        "september": "09", "sep": "09", "sept": "09",
        "october": "10", "oct": "10",
        "november": "11", "nov": "11",
        "december": "12", "dec": "12"
    }

    # Remove ordinal suffixes: 1st, 2nd, 3rd, 4th...
    text = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', text, flags=re.IGNORECASE)

    patterns = [
        r'\b(?:ngày\s*sinh|dob|date\s*of\s*birth)?[:\s]*([0-3]?\d[\s\/\-.]?[a-zA-Z]+[\s\/\-.]?\d{2,4})\b',  # 31 October 1978
        r'\b(?:ngày\s*sinh|dob|date\s*of\s*birth)?[:\s]*([a-zA-Z]+[\s\/\-.]?[0-3]?\d[,]?[\s\/\-.]?\d{2,4})\b'  # October 31, 1978
    ]

    for pat in patterns:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            dob = match.group(1).strip().replace(",", "")
            parts = re.split(r'[\s\/\-.]', dob.lower())
            parts = [p for p in parts if p]  # clean up

            # Format 1: DD Month YYYY
            if len(parts) == 3 and parts[1] in month_map:
                day, month, year = parts[0], month_map[parts[1]], parts[2]
            # Format 2: Month DD YYYY
            elif len(parts) == 3 and parts[0] in month_map:
                day, month, year = parts[1], month_map[parts[0]], parts[2]
            else:
                continue

            if len(year) == 2:
                year = "20" + year if int(year) < 30 else "19" + year

            return f"{day.zfill(2)}/{month.zfill(2)}/{year}"

    return None

def extract_location_info(text, entities):
    """Extract location information"""
    info = {}
    location_entities = combine_entities_en(entities, "GPE")
    # location_entities = [e["word"] for e in entities if e["entity_group"] == "LOCATION"]

    # Check for location matches
    for location in location_entities:
        matched_province = match_location(location)
        if matched_province:
            info["khu_vuc"] = matched_province

    # Fallback location extraction
    if not info.get("khu_vuc"):
        loc_match = re.search(r'(City|Province)[^.,\n]+', text, re.IGNORECASE)
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
        number = phone_match.group(0)
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
        (r"(master|phd|doctor)", 4),       # after_university
        (r"(university|uni|bachelor|academy|engineer|BS|BSc)(?!\s*(master|phd|doctor))", 3),  # university
        (r"(college|vocational)", 2),     # college
        (r"(highschool|high school)", 1)  # high_school
    ]

    # 1. Check for explicit degree mentions in text (prioritizing higher degrees)
    for pattern, degree_id in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return degree_id

    # 2. Check organization entities for school names that imply degree level
    org_entities = [e["word"] for e in entities if e["entity_group"] == "ORG"]
    for org in org_entities:
        org_lower = org.lower()
        if any(k in org_lower for k in ["university", "uni", "academy"]):
            return 3  # university
        elif any(k in org_lower for k in ["vocational", "college"]):
            return 2  # college
        elif any(k in org_lower for k in ["high school", "highschool"]):
            return 1  # high_school

    # 3. Check education section if still not found
    education_section = re.search(
        r"(major|education|degree)[^:]*[:]?(.*?)(?=\n\s*\n|$)",
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

def process_files(input_folder, output_file, ner_en, ner_vn):
    """Process all segmented text files and extract CV data"""
    if not ner_en:
        logging.error("spaCy NER pipeline not initialized")
        return
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

                extracted_info = extract_info(text, ner_en, ner_vn)
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
        ner_en = load_model_en()
        ner_vn = load_model_vn()
        if not ner_en:
            return
        if not ner_vn:
            return

        base_dir = Path(__file__).parent
        input_folder = base_dir / "text_extract" / "english"
        output_file = base_dir / "parsed_data" / "extracted_cv_data_en.json"

        output_file.parent.mkdir(parents=True, exist_ok=True)

        process_files(input_folder, output_file, ner_en, ner_vn)

    except Exception as e:
        logging.error(f"Critical error: {str(e)}")

if __name__ == "__main__":
    main()
