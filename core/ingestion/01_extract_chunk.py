import os
import csv
from datetime import datetime, timezone
from pathlib import Path
import re

import fitz  # pymupdf
from tqdm import tqdm

PDF_DIR = "data"
OUT_CSV = "data/processed/chunks.csv"

CHUNK_SIZE = 1200
OVERLAP = 200

def chunk_text(text: str, chunk_size: int, overlap: int):
    text = (text or "").replace("\x00", " ")
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = min(n, start + chunk_size)
        chunks.append(text[start:end])
        if end == n:
            break
        start = max(0, end - overlap)
    return chunks

def extract_pdf_pages(pdf_path: str):
    doc = fitz.open(pdf_path)
    pages = []
    for idx in range(len(doc)):
        page = doc[idx]
        txt = page.get_text("text") or ""
        pages.append((idx + 1, txt))
    return pages

def main():
    pdf_dir = Path(PDF_DIR)
    out_csv = Path(OUT_CSV)
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    if not pdf_dir.is_dir():
        raise FileNotFoundError(f"Missing folder: {PDF_DIR}")

    pdf_files = sorted([p for p in pdf_dir.iterdir() if p.suffix.lower() == ".pdf"])
    if not pdf_files:
        raise FileNotFoundError(f"No PDFs found in {PDF_DIR}")

    rows = []
    for p in pdf_files:
        pages = extract_pdf_pages(str(p))
        chunk_count = 0

        for page_num, page_text in pages:
            chunks = chunk_text(page_text, CHUNK_SIZE, OVERLAP)
            for j, ch in enumerate(chunks, start=1):
                evidence_id = f"{p.stem}#p{page_num}#c{j}"
                rows.append({
                    "evidence_id": evidence_id,
                    "doc_name": p.name,
                    "doc_source": str(p),
                    "doc_type": "pdf",
                    "page_num": page_num,
                    "chunk_id": j,
                    "chunk_text": ch,
                    "created_at": datetime.now(timezone.utc).isoformat()
                })
                chunk_count += 1

        print(f"Processed {p.name}: {len(pages)} pages → {chunk_count} chunks")

    fieldnames = ["evidence_id","doc_name","doc_source","doc_type","page_num","chunk_id","chunk_text","created_at"]
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    print(f"\nDone! Wrote {len(rows)} chunks to: {out_csv}")

if __name__ == "__main__":
    main()
