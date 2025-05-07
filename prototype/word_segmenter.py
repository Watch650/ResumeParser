import os
import sys
import logging
from pathlib import Path
import py_vncorenlp
from tqdm import tqdm

def configure_logging(log_dir: Path):
    """Configure logging to use specified directory"""
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "word_segmentation.log"

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def initialize_vncorenlp(models_dir: Path):
    """Initialize VnCoreNLP with your specific model path"""
    try:
        # Use the exact path you provided
        vncorenlp_path = Path(r"C:\Users\Asus\Downloads\Hachinet\PDFtoJSON\vncorenlp")

        # Verify the directory exists
        if not vncorenlp_path.exists():
            logging.error(f"VnCoreNLP directory not found at: {vncorenlp_path}")
            return None

        logging.info(f"Initializing VnCoreNLP with models at: {vncorenlp_path}")

        rdrsegmenter = py_vncorenlp.VnCoreNLP(
            annotators=["wseg"],
            save_dir=str(vncorenlp_path)  # Convert to string for compatibility
        )
        logging.info("VnCoreNLP initialized successfully")
        return rdrsegmenter
    except Exception as e:
        logging.error(f"Failed to initialize VnCoreNLP: {e}")
        return None

def process_file(txt_file: Path, output_dir: Path, rdrsegmenter) -> bool:
    """Process a single Vietnamese text file"""
    try:
        # Read with encoding fallback
        try:
            with open(txt_file, "r", encoding='utf-8') as f:
                text = f.read().strip()
        except UnicodeDecodeError:
            with open(txt_file, "r", encoding='latin-1') as f:
                text = f.read().strip()

        if not text:
            logging.warning(f"Empty file skipped: {txt_file.name}")
            return False

        # Segment text
        segmented = rdrsegmenter.word_segment(text)
        segmented_text = "\n".join(segmented)

        # Create output file
        output_path = output_dir / f"{txt_file.stem}_segmented.txt"

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(segmented_text)

        return True

    except Exception as e:
        logging.error(f"Error processing {txt_file.name}: {str(e)}")
        return False

def main():
    # Configure paths
    base_dir = Path(__file__).parent
    input_dir = base_dir / "text_extract" / "vietnamese"
    output_dir = base_dir / "output_segmented"
    log_dir = base_dir / "logs"

    # Setup logging
    configure_logging(log_dir)
    logging.info(f"Starting Vietnamese word segmentation from: {input_dir}")

    # Initialize VnCoreNLP with your specific path
    rdrsegmenter = initialize_vncorenlp(Path(r"C:\Users\Asus\Downloads\Hachinet\PDFtoJSON\vncorenlp"))
    if not rdrsegmenter:
        sys.exit(1)

    # Get all text files
    txt_files = list(input_dir.glob("*.txt"))
    if not txt_files:
        logging.error("No Vietnamese text files found in input directory!")
        sys.exit(1)

    # Prepare output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Process files
    results = {'success': 0, 'error': 0}
    for txt_file in tqdm(txt_files, desc="Segmenting Vietnamese files"):
        if process_file(txt_file, output_dir, rdrsegmenter):
            results['success'] += 1
        else:
            results['error'] += 1

    # Print summary
    logging.info("Processing Summary:")
    logging.info(f"├── Total files processed: {len(txt_files)}")
    logging.info(f"├── Successfully segmented: {results['success']}")
    logging.info(f"└── Failed: {results['error']}")
    logging.info(f"Output directory: {output_dir}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Process interrupted by user")
        sys.exit(0)
    except Exception as e:
        logging.critical(f"Unexpected error: {str(e)}")
        sys.exit(1)