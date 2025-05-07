# utils/reference_data.py

import os
import re
import requests
from functools import lru_cache
from rapidfuzz import process
import logging

PROVINCES_API = "https://api-v2.devwork.vn/common/provinces"
SKILLS_API = "https://api-v2.devwork.vn/skills"

# Create logs directory if it doesn't exist
if not os.path.exists("logs"):
    os.makedirs("logs")

# Configure the logger to log to a file in the 'logs' folder
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/match_location.log")
    ]
)

logger = logging.getLogger(__name__)

@lru_cache(maxsize=1)
def fetch_locations():
    """Fetch locations from the external API."""
    try:
        response = requests.get(PROVINCES_API, timeout=10)
        response.raise_for_status()
        data = response.json()  # Parse JSON response
        return data["data"]
    except Exception as e:
        print(f"Error fetching locations: {e}")
        return []

@lru_cache(maxsize=1)
def fetch_skills():
    """Fetch skills from the external API."""
    try:
        response = requests.get(SKILLS_API, timeout=10)
        response.raise_for_status()
        data = response.json()  # Parse JSON response
        return data["data"]
    except Exception as e:
        print(f"Error fetching skills: {e}")
        return []

def get_default_location():
    """Fetch the default location from the API by ID"""
    try:
        locations = fetch_locations()
        for location in locations:
            if location["id"] == 99:
                return location["id"]
    except Exception as e:
        print(f"Error fetching default location: {e}")



def match_location(extracted, threshold=90):
    """Match a given location to a province in the API list, using fuzzy matching with common abbreviations."""
    # Fetch locations from the external API
    provinces = fetch_locations()
    match = None
    highest_score = 0

    # Common abbreviations mapping
    COMMON_ABBREVIATIONS = {
        "tp.hcm": "Hồ Chí Minh",
        "tp. hcm": "Hồ Chí Minh",
        "hcm": "Hồ Chí Minh",
        "hcmc": "Hồ Chí Minh",
        "ho chi minh": "Hồ Chí Minh",
        "tphcm": "Hồ Chí Minh",
        "tp hcm": "Hồ Chí Minh",
        "hà nội": "Hà Nội",
        "hn": "Hà Nội",
        "tp.hn": "Hà Nội",
        "tp. hn": "Hà Nội",
        "hanoi": "Hà Nội",
        "ha noi": "Hà Nội",
        "đà nẵng": "Đà Nẵng",
        "dn": "Đà Nẵng",
        "danang": "Đà Nẵng",
        "da nang": "Đà Nẵng"
    }

    # Normalize the input
    normalized_input = extracted.lower().strip()
    logger.info(f"Normalized input: {normalized_input}")

    # Check if the normalized location is in the common abbreviations list
    if normalized_input in COMMON_ABBREVIATIONS:
        # Return the matched province ID based on the common abbreviation
        official_name = COMMON_ABBREVIATIONS[normalized_input]
        logger.info(f"Match found in common abbreviations: {official_name}")
        for province in provinces:
            if province["name"] == official_name:
                logger.info(f"Matched province: {province['name']} with ID {province['id']}")
                return province["id"]

    # Try matching with the provinces list using fuzzy matching
    logger.info(f"Attempting fuzzy match with provinces list")
    for province in provinces:
        match_result = process.extractOne(extracted, [province["name"]], score_cutoff=threshold)
        if match_result and match_result[1] > highest_score:
            highest_score = match_result[1]
            match = province["id"]
            logger.info(f"Fuzzy match found: {province['name']} (Score: {match_result[1]})")

    # If no match found with the full name, try removing "TP." prefix and matching again
    if "tp." in normalized_input or "tp " in normalized_input:
        cleaned_input = re.sub(r'tp[\.\s]*', '', normalized_input).strip()
        logger.info(f"Cleaned input after removing 'TP.' prefix: {cleaned_input}")
        for province in provinces:
            match_result = process.extractOne(cleaned_input, [province["name"]], score_cutoff=threshold)
            if match_result and match_result[1] > highest_score:
                highest_score = match_result[1]
                match = province["id"]
                logger.info(f"Fuzzy match found after cleaning 'TP.' prefix: {province['name']} (Score: {match_result[1]})")

    if match:
        logger.info(f"Final matched province ID: {match}")
    else:
        logger.info("No match found")

    return match

def match_skills_from_text(text):
    """Match all possible skills from a text by comparing with the 'name' field."""
    skills = fetch_skills()  # Fetch skills from the API
    matched_skills = []
    norm_text = re.sub(r'[^\w\s/#+.-]', ' ', text.lower())  # Normalize the input text

    skill_patterns = {
        skill["id"]: re.compile(rf'(?<!\w){re.escape(skill["name"].lower())}(?!\w)', re.IGNORECASE)
        for skill in skills if isinstance(skill, dict) and "name" in skill
    }

    for skill_id, pattern in skill_patterns.items():
        if pattern.search(norm_text):  # <- FIXED: match against norm_text
            matched_skills.append(skill_id)
            logger.info(f"Matched skill ID {skill_id}: {pattern.pattern}")

    if matched_skills:
        logger.info(f"Matched skills: {matched_skills}")
    else:
        logger.info("No skills matched.")

    return matched_skills