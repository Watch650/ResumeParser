# file_parser_vn.py

import os
import re
import json
import logging
from pathlib import Path
from tqdm import tqdm
from models.ner_model_en import load_models, process_text_chunks, inspect_entity_outputs, combine_entities
from utils.reference_data import match_location, get_default_location, match_skills_from_text
from prototype.mapping import map_degree_to_id

def extract_info(text: str, ner_vn):
    """Extract relevant information from the CV text using NER"""
    text = re.sub(r'\s+', ' ', text.strip())

    entities = process_text_chunks(text, ner_vn)
    inspect_entity_outputs(entities)

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

    try:
        # Name
        person_entities = combine_entities(entities, "PERSON")
        info["ho_ten"] = person_entities[0] if person_entities else None

        # Fallback: Name extraction
        if not info["ho_ten"]:
            first_lines = text.split('.')[:2]
            for line in first_lines:
                upper_line = re.search(r'^([A-ZÀ-Ỵ][A-ZÀ-Ỵ\s]{2,})$', line.strip())
                if upper_line:
                    info["ho_ten"].append(upper_line.group(1).title())
                    break

        # Location
        location_entities = [e["word"] for e in entities if e["entity_group"] == "LOCATION"]
        # location_entities = combine_entities(entities, "LOCATION")
        # info["khu_vuc"] = location_entities[:2]
        org_entities = combine_entities(entities, "ORGANIZATION")
        misc_entities = combine_entities(entities, "MISCELLANEOUS")

        # Check for location matches
        for location in location_entities:
            matched_province = match_location(location)
            if matched_province:
                info["khu_vuc"] = matched_province
                break

        # Fallback: Location extraction
        if not info["khu_vuc"]:
            loc_match = re.search(r'(Thành phố|Tỉnh|TP)[^.,\n]+', text, re.IGNORECASE)
            if loc_match:
                loc_text = loc_match.group(0).strip()
                matched_province = match_location(loc_text)
                if matched_province:
                    info["khu_vuc"] = matched_province

        # If no location was found, return the default location "Tất cả địa điểm"
        if not info["khu_vuc"]:
            default_location = get_default_location()
            info["khu_vuc"] = default_location

        # Date of Birth (DOB)
        dob_match = re.search(r'\b(?:ngày\s*sinh|dob)?[:\s]*([0-3]?\d[/-][01]?\d[/-]\d{2,4})\b', text, re.IGNORECASE)
        if dob_match:
            info["ngay_sinh"] = dob_match.group(1)

        # Email
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
        if email_match:
            info["email"] = email_match.group(0)

        # Phone
        phone_match = re.search(r'(\+84|0)[1-9]\d{8}\b', text)
        if phone_match:
            info["so_dien_thoai"] = phone_match.group(0)

        # Experience extraction
        exp_match = re.search(r'(\d+)\+?\s*(năm|year)s?\s*kinh\s*nghiệm', text, re.IGNORECASE)
        if exp_match:
            info["kinh_nghiem_nam"] = int(exp_match.group(1))

        # Education extraction
        education_keywords = ["đại học", "đh", "cao học", "trường", "học viện", "cao đẳng", "trung cấp", "trung học", "thpt", "university", "academy", "college", "high school"]
        org_entities = sorted([e for e in entities if e["entity_group"] == "ORGANIZATION"], key=lambda e: e["start"])
        edu_orgs = [e["word"] for e in org_entities if any(k in e["word"].lower() for k in education_keywords)]
        if edu_orgs:
            truong_name = edu_orgs[0]
            info["trinh_do_hoc_van"]["truong"] = truong_name
            lines = text.split("\n")
            truong_lower = truong_name.lower()

            index_truong = next((i for i, line in enumerate(lines) if truong_lower in line.lower()), None)

            if index_truong is not None:
                search_range = lines[index_truong:index_truong + 6]  # check nearby lines
                for line in search_range:
                    # Extract duration
                    if not info["trinh_do_hoc_van"].get("thoi_gian"):
                        match_time = re.search(r"((?:\d{2}/)?\d{4})\s*[-–~tođến]+\s*((?:\d{2}/)?\d{4})", line)
                        if match_time:
                            info["trinh_do_hoc_van"]["thoi_gian"] = match_time.group(0).strip()

                    # Extract degree
                    if not info["trinh_do_hoc_van"].get("trinh_do"):
                        match_degree = re.search(r"(Cử nhân|Thạc sĩ|Tiến sĩ|Kỹ sư|Đại học|Cao đẳng|Học viện)", line, re.IGNORECASE)
                        if match_degree:
                            degree = match_degree.group(1).strip()
                            info["trinh_do_hoc_van"]["trinh_do"] = map_degree_to_id(degree)

                # If degree not explicitly found, infer from school name
                if not info["trinh_do_hoc_van"].get("trinh_do"):
                    if "cao đẳng" in truong_lower:
                        info["trinh_do_hoc_van"]["trinh_do"] = map_degree_to_id("Cao đẳng")
                    elif "học viện" in truong_lower:
                        info["trinh_do_hoc_van"]["trinh_do"] = map_degree_to_id("Học viện")
                    elif "đại học" in truong_lower:
                        info["trinh_do_hoc_van"]["trinh_do"] = map_degree_to_id("Đại học")
                    elif "đh" in truong_lower:
                        info["trinh_do_hoc_van"]["trinh_do"] = map_degree_to_id("Đại học")

        # If no school detected using NER, fallback to regex
        else:
            education_section_match = re.search(
                r"(học vấn|giáo dục|trình độ|bằng cấp|văn bằng)[^:]*[:\n](.*?)(?=\n\s*\n|$)",
                text, re.IGNORECASE | re.DOTALL
            )
            edu_text = education_section_match.group(2) if education_section_match else text

            edu_patterns = [
                # Multi-line format
                r"(?P<thoi_gian>\d{2}/\d{4}\s*[-–]\s*\d{2}/\d{4})\s*\n(?:Trường\s+)?(?P<truong>Đại học\s+[^\n]+)\s*\n(?:Ngành[:：]?\s*(?P<nganh>[^\n]+))?\s*\n(?:Chuyên Ngành[:：]?\s*(?P<chuyen_nganh>[^\n]+))?",

                # Degree at school
                r"(?P<trinh_do>Cử nhân|Thạc sĩ|Tiến sĩ|Kỹ sư)\s+(?P<chuyen_nganh>[^\n,.;:]+?)\s+tại\s+(?P<truong>[^\n,.;:]+)",

                # One-liner
                r"(?P<trinh_do>Cao đẳng|Đại học|Học viện)\s+(?P<truong>[^\n,.;:]+?)(?:,\s*(?P<chuyen_nganh>[^\n,.;:]+))?(?:,?\s*(?P<thoi_gian>\d{4}(?:\s*[-–]\s*\d{4})?))?",

                # Compact format with hyphen and parentheses
                r"(?P<trinh_do>Cử nhân|Thạc sĩ|Tiến sĩ|Kỹ sư|Đại học|Cao đẳng|Học viện)\s+(?P<truong>[^\-–\n]+)[\s\-–]+\s*(?P<chuyen_nganh>[^()\n]+)?\s*\(*(?P<thoi_gian>\d{4}\s*[-–]\s*\d{4})\)*"
            ]

            for pattern in edu_patterns:
                match = re.search(pattern, edu_text, re.IGNORECASE)
                if match:
                    edu = match.groupdict()
                    for k, v in edu.items():
                        if v:
                            info["trinh_do_hoc_van"][k] = v.strip()

                    # Normalize time format
                    if "thoi_gian" in info["trinh_do_hoc_van"]:
                        info["trinh_do_hoc_van"]["thoi_gian"] = info["trinh_do_hoc_van"]["thoi_gian"]

                    if "trinh_do" in info["trinh_do_hoc_van"]:
                        info["trinh_do_hoc_van"]["trinh_do"] = map_degree_to_id(info["trinh_do_hoc_van"]["trinh_do"])

                    # Infer degree if missing
                    if not info["trinh_do_hoc_van"].get("trinh_do") and "truong" in info["trinh_do_hoc_van"]:
                        truong_lower = info["trinh_do_hoc_van"]["truong"].lower()
                        if "cao đẳng" in truong_lower:
                            info["trinh_do_hoc_van"]["trinh_do"] = map_degree_to_id("Cao đẳng")
                        elif "học viện" in truong_lower:
                            info["trinh_do_hoc_van"]["trinh_do"] = map_degree_to_id("Học viện")
                        elif "đại học" in truong_lower:
                            info["trinh_do_hoc_van"]["trinh_do"] = map_degree_to_id("Đại học")
                        elif "đh" in truong_lower:
                            info["trinh_do_hoc_van"]["trinh_do"] = map_degree_to_id("Đại học")
                    break

        # Languages extraction
        japanese_basic_keywords = ["basic", "standard", "elementary", "cơ bản", "căn bản", "N1", "N2"]
        japanese_good_keywords = ["good", "master", "fluent", "advanced", "giao tiếp", "tốt", "thành thục", "nâng cao", "N3", "N4", "N5"]
        english_basic_keywords = ["basic", "standard", "elementary", "cơ bản", "căn bản"]
        english_good_keywords = ["fluent", "good", "advanced", "giao tiếp", "tốt", "thành thục", "nâng cao"]

        known_langs = ["Tiếng Anh", "English", "Japanese", "Tiếng Nhật"]
        info["ngoai_ngu"] = sorted({lang for lang in known_langs if re.search(rf'\b{re.escape(lang)}\b', text, re.IGNORECASE)})

        # Skills extraction
        skill_match = match_skills_from_text(text)
        info["ky_nang_chinh"] = skill_match

        # Summary extraction
        experience_section = ""
        exp_section_match = re.search(
            r"(kinh nghiệm làm việc|kinh nghiệm|dự án|work experience|experience)[^\n]{0,20}\n(.+?)(?=\n[A-ZĐ][^\n]{1,40}\n|\Z)",
            text,
            re.IGNORECASE | re.DOTALL
        )
        if exp_section_match:
            experience_section = exp_section_match.group(2).strip()

        # Fallback: get all lines containing job titles or companies
        if not experience_section:
            lines = text.splitlines()
            experience_lines = [line for line in lines if re.search(r"(Công ty|Company|Tập đoàn|Project|Developer|Engineer)", line, re.IGNORECASE)]
            experience_section = " ".join(experience_lines)

        if experience_section:
            # Extract role/job title
            role_match = re.search(r'(Công việc|Chức danh|Role|Position)[^\n]*[:\s]*([A-Za-z\s]+)', experience_section)
            role = role_match.group(2).strip() if role_match else "Unknown Role"

            # Extract companies
            companies = sorted(set(re.findall(r'(Công ty|Company|Tập đoàn)[^\n]+', experience_section)), key=lambda x: x.lower())

            # Construct 3-sentence summary
            sentence_1 = f"Role: {role}."
            sentence_2 = {f"Companies worked at: {', '.join(companies[:3])}."} if companies else "No companies listed."
            sentence_3 = {f"Skills: {', '.join(info['ky_nang_chinh'][:3])}."} if info["ky_nang_chinh"] else " "

            info["gioi_thieu"] = f"{sentence_1} {sentence_2} {sentence_3}"

    except Exception as e:
        logging.error(f"Error extracting info: {str(e)}")

    return info


def process_files(input_folder, output_file, ner_vn):
    """Process all segmented text files and extract CV data"""
    if not ner_vn:
        logging.error("NER pipeline not initialized")
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
        ner_vn = load_models()
        if not ner_vn:
            return

        base_dir = Path(__file__).parent
        input_folder = base_dir / "text_extract" / "vietnamese"
        output_file = base_dir / "parsed_data" / "extracted_cv_data_vn.json"

        process_files(input_folder, output_file, ner_vn)

    except Exception as e:
        logging.error(f"Critical error: {str(e)}")

if __name__ == "__main__":
    main()
