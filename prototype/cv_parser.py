import spacy
import re
from pyvi import ViTokenizer
import langdetect
import os
import json


# Load SpaCy model
nlp = spacy.load("en_core_web_sm")

# List of known skills (extend as needed)
SKILL_KEYWORDS = [
    # Frontend
    "html", "css", "javascript", "typescript", "react", "vue", "angular", "bootstrap", "tailwind",
    # Backend
    "node", "express", "django", "flask", "laravel", "php", "java", "spring", "c#", ".net", "ruby", "c", "c++", "react"
    # Databases
    "mysql", "postgresql", "mongodb", "sqlite", "redis",
    # DevOps & Tools
    "docker", "kubernetes", "git", "github", "gitlab", "jenkins", "aws", "azure", "gcp", "nginx",
    # Data Science / AI
    "python", "r", "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch", "matplotlib", "seaborn",
    # Extras
    "jira", "confluence", "firebase", "graphql", "rest", "api", "socket.io"
]
SKILL_KEYWORDS += ["kỹ năng giao tiếp", "phân tích dữ liệu", "python", "học máy"]

DEGREE_KEYWORDS = [
    "bachelor", "master", "phd", "b.sc", "m.sc", "btech", "mtech", "mba", "bs", "ms"
]
DEGREE_KEYWORDS += ["cử nhân", "thạc sĩ", "tiến sĩ", "kỹ sư", "đại học"]

# Date patterns like "Jan 2020 – Mar 2023", "2019 - Present", "01/2020 - 03/2023"
DATE_RANGE_PATTERN = re.compile(
    r"((Jan(uary)?|Feb(ruary)?|Mar(ch)?|Apr(il)?|May|Jun(e)?|Jul(y)?|Aug(ust)?|"
    r"Sep(tember)?|Oct(ober)?|Nov(ember)?|Dec(ember)?)[ \t.,-]?\d{4}|"
    r"\d{1,2}/\d{4}|\d{4})\s*[-–]\s*(Present|\d{1,2}/\d{4}|\d{4}|"
    r"(Jan(uary)?|Feb(ruary)?|Mar(ch)?|Apr(il)?|May|Jun(e)?|Jul(y)?|Aug(ust)?|"
    r"Sep(tember)?|Oct(ober)?|Nov(ember)?|Dec(ember)?)[ \t.,-]?\d{4})"
)

def detect_language(text):
    try:
        return langdetect.detect(text)
    except:
        return "en"

def tokenize_text(text):
    lang = detect_language(text)
    if lang == "vi":
        print("Detected Vietnamese text. Using PyVi tokenizer.")
        return ViTokenizer.tokenize(text)
    else:
        print("Detected English text. Using SpaCy tokenizer.")
        return text

def extract_info(text):
    tokenized_text = tokenize_text(text)
    doc = nlp(tokenized_text)

    # Name
    name = next((ent.text for ent in doc.ents if ent.label_ == "PERSON"), None)

    if not name:
        # Fallback: look for common labels or capitalized lines
        lines = text.split("\n")
        for line in lines:
            if re.search(r"(họ tên|tên đầy đủ|name)", line, re.IGNORECASE):
                name_match = re.search(r"(họ tên|tên đầy đủ|name)[:\-]?\s*(.*)", line, re.IGNORECASE)
                if name_match:
                    name = name_match.group(2).strip()
                    break
        if not name:
            # Try finding first line with 2-4 capitalized words (heuristic for full name)
            for line in lines[:10]:
                words = line.strip().split()
                if 1 < len(words) <= 4 and all(word.istitle() or word.isupper() for word in words):
                    name = line.strip()
                    break


    # Email
    email_match = re.search(r"\b[\w\.-]+@[\w\.-]+\.\w+\b", text)
    email = email_match.group(0) if email_match else None

    # Phone number
    phone_match = re.search(r"(\+?\d{1,3}[\s-]?)?(\(?\d{2,4}\)?[\s-]?)?\d{3,4}[\s-]?\d{3,4}", text)
    phone = phone_match.group(0) if phone_match else None

    # Birth year
    birth_match = re.search(r"(sinh năm|born in)[^\d]*(\d{4})", text, re.IGNORECASE)
    birth_year = birth_match.group(2) if birth_match else None

    # Location (rough extraction using known keywords)
    city_match = re.search(r"(Hà Nội|Hanoi|HCM|Hồ Chí Minh|Da Nang|Đà Nẵng|Vietnam)", text, re.IGNORECASE)
    location = city_match.group(0) if city_match else None

    # Skills
    skills_found = []
    for token in doc:
        if token.text.lower() in SKILL_KEYWORDS:
            skills_found.append(token.text)

    # Education
    education_block = ""
    school_match = re.search(r"(?:trường|academy|university|college)[^\n]{0,80}", text, re.IGNORECASE)
    if school_match:
        education_block = school_match.group(0)
    school = school_match.group(0) if school_match else None

    major_match = re.search(r"(software|computer|công nghệ thông tin|information technology|engineering)[^\n]{0,30}", text, re.IGNORECASE)
    major = major_match.group(0).strip() if major_match else None

    edu_date_range = re.search(DATE_RANGE_PATTERN, education_block)
    edu_time = edu_date_range.group(0) if edu_date_range else None

    # Experience duration estimate
    experience_ranges = [match.group(0) for match in re.finditer(DATE_RANGE_PATTERN, text)]
    experience_years = 0
    for match in experience_ranges:
        years = re.findall(r"\d{4}", match)
        if len(years) == 2:
            diff = int(years[1]) - int(years[0])
            if diff > 0:
                experience_years += diff
        elif len(years) == 1 and "present" in match.lower():
            diff = 2025 - int(years[0])
            experience_years += diff

    # Language skill (look for common phrases)
    language_match = re.search(r"(IELTS|TOEIC|TOEFL|Giao tiếp|English)", text, re.IGNORECASE)
    language = language_match.group(0) if language_match else None

    # Introduction (first paragraph or 2-3 lines)
    paragraphs = text.split("\n")
    summary_lines = []
    for line in paragraphs:
        if len(line.strip()) > 20:
            summary_lines.append(line.strip())
        if len(summary_lines) >= 2:
            break
    introduction = " ".join(summary_lines)

    return {
        "ho_ten": name,
        "ngay_sinh": birth_year,
        "so_dien_thoai": phone,
        "email": email,
        "khu_vuc": location,
        "kinh_nghiem_nam": experience_years if experience_years > 0 else None,
        "trinh_do_hoc_van": {
            "truong": school,
            "thoi_gian": edu_time,
            "chuyen_nganh": major
        },
        "ngoai_ngu": language,
        "ky_nang_chinh": list(set(skills_found)),
        "gioi_thieu": introduction
    }



def process_files(input_dir, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for filename in os.listdir(input_dir):
        if filename.endswith(".txt"):
            input_path = os.path.join(input_dir, filename)
            output_filename = os.path.splitext(filename)[0] + "_parsed.json"
            output_path = os.path.join(output_dir, output_filename)

            print(f"Processing file: {filename}")

            try:
                with open(input_path, "r", encoding="utf-8") as file:
                    resume_text = file.read()

                extracted = extract_info(resume_text)

                with open(output_path, "w", encoding="utf-8") as outfile:
                    json.dump(extracted, outfile, indent=2, ensure_ascii=False)

                print(f"Successfully processed and saved: {output_filename}")
            except Exception as e:
                print(f"Error processing file {filename}: {str(e)}")

if __name__ == "__main__":
    input_dir = "text_extract"
    output_dir = "info_parse"

    process_files(input_dir, output_dir)
    print("Processing completed.")

