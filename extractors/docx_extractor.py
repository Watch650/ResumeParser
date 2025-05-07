# extractors/docx_extractor.py
import docx
import logging
from utils.table_formatter import format_table

def extract_docx_text(path: str) -> str:
    try:
        doc = docx.Document(path)
        output = []

        for element in doc.element.body:
            if element.tag.endswith('p'):
                para = docx.text.paragraph.Paragraph(element, doc)
                text = para.text.strip()
                if text:
                    output.append(text)

            elif element.tag.endswith('tbl'):
                table = docx.table.Table(element, doc)
                rows = [
                    [" ".join(p.text.strip() for p in cell.paragraphs if p.text.strip())
                     for cell in row.cells]
                    for row in table.rows
                ]
                if rows:
                    output.append(format_table(rows))

        return "\n".join(output).strip()

    except Exception as e:
        logging.error(f"DOCX extraction failed: {e}")
        return ""
