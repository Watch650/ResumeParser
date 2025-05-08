# ner_model_en.py
import os
import logging
import spacy
from collections import defaultdict

def configure_logging():
    """Configure consistent logging for NER operations."""
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("logs/ner_model_en.log", encoding="utf-8"),
            logging.StreamHandler()
        ]
    )

configure_logging()

def load_model_en(model_name="en_core_web_trf"):
    """Load the spaCy model for Named Entity Recognition (NER)."""
    try:
        logging.info(f"Loading spaCy model: {model_name}")
        nlp = spacy.load(model_name)
        logging.info("spaCy model loaded successfully.")
        return nlp
    except Exception as e:
        logging.error(f"Error loading spaCy model: {e}")
        return None

def process_text_chunks_en(text, nlp, chunk_size=400, overlap=50):
    """Split text into overlapping chunks and run the NER model."""
    text = ' '.join(text.split())  # Normalize whitespace
    entities = []

    for start in range(0, len(text), chunk_size - overlap):
        chunk = text[start:start + chunk_size]
        try:
            logging.info(f"Processing chunk: {chunk[:100]}...")
            doc = nlp(chunk)
            chunk_entities = [
                {
                    "word": ent.text,
                    "entity_group": ent.label_,
                    "start": ent.start_char,
                    "end": ent.end_char
                }
                for ent in doc.ents
            ]
            if chunk_entities:
                entities.extend(chunk_entities)
                logging.info(f"Entities found: {chunk_entities}")
        except Exception as e:
            logging.warning(f"NER failed on chunk: {e}")

    return entities

def combine_entities_en(entities, label):
    """Merge subwords into complete named entities by label."""
    combined = []
    current = []

    # Sort the entities by their start position in the text
    sorted_entities = sorted(entities, key=lambda e: e['start'])

    for e in sorted_entities:
        logging.debug(f"Raw entity: {e}")
        if e["entity_group"] == label:
            word = e["word"].replace("##", "").strip()
            if current and not word.startswith(" "):
                current.append(word)
            else:
                if current:
                    combined.append(" ".join(current).strip())
                current = [word]
        else:
            if current:
                combined.append(" ".join(current).strip())
                current = []

    if current:
        combined.append(" ".join(current).strip())

    result = sorted({c for c in combined if len(c) > 1})
    logging.info(f"Combined {label} entities: {result}")
    return result

def inspect_entity_outputs_en(entities):
    """Print a summary of detected entities for debugging."""
    grouped = defaultdict(list)
    for e in entities:
        grouped[e['entity_group']].append(e['word'])

    for label, words in grouped.items():
        print(f"\nLabel: {label}")
        print("Examples:", ' | '.join(words[:10]))

