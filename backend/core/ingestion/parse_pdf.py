from unstructured.partition.pdf import partition_pdf
import json
from pathlib import Path

def parse_spvc(pdf_path: str, output_path: str):
    """
    Parses the Sport or Pleasure Vessel Code PDF into structured elements, preserving
    section headers, page numbers, and table structure.
    """
    print(f"Parsing {pdf_path}... this can take a few minutes for 281 pages.")

    elements = partition_pdf(
        filename=pdf_path,
        strategy="hi_res",          # uses layout detection — needed for tables
        infer_table_structure=True, # keeps tables as structured data, not flattened text
    )

    structured_output = []
    for el in elements:
        structured_output.append({
            "text": str(el),
            "category": el.category,        # e.g. "Title", "NarrativeText", "Table"
            "page_number": el.metadata.page_number,
        })

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(structured_output, f, indent=2)

    print(f"Done. {len(structured_output)} elements extracted → {output_path}")

if __name__ == "__main__":
    parse_spvc(
        pdf_path="data/raw/spvc_2025.pdf",
        output_path="data/processed/spvc_2025_parsed.json",
    )