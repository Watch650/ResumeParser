# file_parser_en.py

import re
import json
from pathlib import Path
import spacy

# Load English spaCy model
nlp = spacy.load("en_core_web_trf")

def log_spacy_entities(doc, filename: str, log_dir="logs"):
    import os
    os.makedirs(log_dir, exist_ok=True)
    log_path = Path(log_dir) / "spacy_ner_en.jsonl"

    log_entry = {
        "filename": filename,
        "text": doc.text[:200] + "..." if len(doc.text) > 200 else doc.text,
        "entities": [
            {"text": ent.text, "label": ent.label_, "start": ent.start_char, "end": ent.end_char}
            for ent in doc.ents
        ]
    }

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

def extract_info(text, filename="unknown.txt"):
    doc = nlp(text)

    # Log all NER outputs
    log_spacy_entities(doc, filename)

    info = {
        "ho_ten": None,
        "ngay_sinh": None,
        "so_dien_thoai": None,
        "email": None,
        "khu_vuc": None,
        "kinh_nghiem_nam": None,
        "trinh_do_hoc_van": {
            "truong": None,
            "trinh_do": None,
            "thoi_gian": None
        },
        "ngoai_ngu": [],
        "ky_nang_chinh": [],
        "gioi_thieu": None,
    }

    # Name extraction
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            info["ho_ten"] = ent.text
            break

    # Email
    email_match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
    if email_match:
        info["email"] = email_match.group(0)

    # Phone number
    phone_match = re.search(r"\+?\d[\d\s().-]{7,}", text)

    if phone_match:
        info["so_dien_thoai"] = phone_match.group(0)

    # Date of birth
    dob_match = re.search(r"(?:date of birth|dob)[:\s]*([\d]{1,2}[/\-\.][\d]{1,2}[/\-\.][\d]{2,4})", text, re.IGNORECASE)
    if dob_match:
        info["ngay_sinh"] = dob_match.group(1)

    # Location keywords (simplified)
    locations = ["Hanoi", "Ho Chi Minh"]
    info["khu_vuc"] = [loc for loc in locations if loc.lower() in text.lower()]

    # Years of experience
    years = re.findall(r"(\d{4})\s*[-–]\s*(\d{4}|Present)", text)
    if years:
        total_years = 0
        for y1, y2 in years:
            try:
                y1 = int(y1)
                y2 = int(y2) if y2.isdigit() else 2024
                total_years += max(0, y2 - y1)
            except:
                continue
        if total_years:
            info["kinh_nghiem_nam"] = total_years

    # Education section
    education_match = re.search(r"(education|degree)[^\n]*\n(.+?)(?=\n[A-Z][^\n]{1,40}\n|\Z)", text, re.IGNORECASE | re.DOTALL)
    if education_match:
        edu_text = education_match.group(2)
        info["trinh_do_hoc_van"]["truong"] = re.search(r"(university|college|institute).{0,50}", edu_text, re.IGNORECASE).group(0) if re.search(r"(university|college|institute)", edu_text, re.IGNORECASE) else None
        info["trinh_do_hoc_van"]["thoi_gian"] = re.search(r"\d{4}\s*[-–]\s*(\d{4}|present)", edu_text, re.IGNORECASE).group(0) if re.search(r"\d{4}\s*[-–]\s*(\d{4}|present)", edu_text, re.IGNORECASE) else None

    # Languages
    language_keywords = ["English", "French", "Chinese", "Vietnamese", "Japanese"]
    info["ngoai_ngu"] = [lang for lang in language_keywords if lang.lower() in text.lower()]

    # Skills
    skill_keywords = ["Python", "JavaScript", "React", "Node.js", "SQL", "C++", "Java", "Docker"]
    info["ky_nang_chinh"] = [skill for skill in skill_keywords if skill.lower() in text.lower()]

    # Introduction / Objective
    intro_match = re.findall(
        r"(objective|profile|summary)[^\n]{0,20}\n(.+?)(?=\n[A-Z][^\n]{1,40}\n|\Z)",
        text,
        re.IGNORECASE | re.DOTALL
    )
    if intro_match:
        info["gioi_thieu"] = intro_match[0][1].strip()

    return info

def process_files():
    base_dir = Path(__file__).parent
    input_folder = base_dir / "text_extract" / "english"
    output_file = base_dir / "parsed_data" / "extracted_cv_data_en.json"

    parsed_data = []

    for txt_file in input_folder.glob("*.txt"):
        with open(txt_file, "r", encoding="utf-8") as file:
            text = file.read()
            info = extract_info(text, filename=txt_file.name)
            info["filename"] = txt_file.name
            parsed_data.append(info)

    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(parsed_data, f, ensure_ascii=False, indent=4)

    print(f"[✓] Parsed {len(parsed_data)} CVs and saved to {output_file}")

if __name__ == "__main__":
    process_files()
