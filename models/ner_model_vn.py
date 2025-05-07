# ner_model_vn.py
import os
import logging
from collections import defaultdict
import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline

def configure_logging():
    """Configure consistent logging for NER operations."""
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("logs/ner_model_vn.log", encoding="utf-8"),
            logging.StreamHandler()
        ]
    )

configure_logging()

def load_model_vn(model_name="NlpHUST/ner-vietnamese-electra-base"):
    """Load the Vietnamese NER model with HuggingFace Transformers."""
    try:
        logging.info(f"Verifying availability of model: {model_name}")
        try:
            from huggingface_hub import model_info
            _ = model_info(model_name)
        except Exception as e:
            logging.warning(f"Model info unavailable: {e}. Proceeding with load.")

        tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)
        model = AutoModelForTokenClassification.from_pretrained(model_name)

        device = 0 if torch.cuda.is_available() else -1
        ner_pipeline = pipeline(
            "ner",
            model=model,
            tokenizer=tokenizer,
            aggregation_strategy="simple",
            device=device
        )

        logging.info("NER model loaded successfully.")
        return ner_pipeline
    except Exception as e:
        logging.error(f"Error loading NER model: {e}")
        return None

def process_text_chunks_vn(text, ner_pipeline, chunk_size=400, overlap=50):
    """Split text into overlapping chunks and run the NER model."""
    text = ' '.join(text.split())  # Normalize whitespace
    entities = []

    for start in range(0, len(text), chunk_size - overlap):
        chunk = text[start:start + chunk_size]
        try:
            logging.info(f"Processing chunk: {chunk[:100]}...")
            chunk_entities = ner_pipeline(chunk)
            if chunk_entities:
                entities.extend(chunk_entities)
                logging.info(f"Entities found: {chunk_entities}")
        except Exception as e:
            logging.warning(f"NER failed on chunk: {e}")

    return entities

def combine_entities_vn(entities, label):
    """Merge subwords into complete named entities by label."""
    combined = []
    current = []

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

def inspect_entity_outputs_vn(entities):
    """Print a summary of detected entities for debugging."""
    grouped = defaultdict(list)
    for e in entities:
        grouped[e['entity_group']].append(e['word'])

    for label, words in grouped.items():
        print(f"\nLabel: {label}")
        print("Examples:", ' | '.join(words[:10]))


