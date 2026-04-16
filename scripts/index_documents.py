"""
scripts/index_documents.py — Build the RAG vector index for driver documents.

Run this once (or whenever a document is replaced) to:
  1. Extract full text from all 4 PDF documents (no word limit)
  2. Split into ~300-word chunks with 50-word overlap
  3. Embed each chunk with sentence-transformers (all-MiniLM-L6-v2)
  4. Save locally as data/john_doe_chunks.json
  5. Upload to Azure Blob Storage as john_doe/chunks.json

Usage:
    cd "<project root>"
    python scripts/index_documents.py

The resulting chunks.json is used by:
  - document_loader._local_search_documents()  (local Streamlit dev path)
  - mcp_server search_documents tool           (Azure MCP path)
"""

import json
import os
import sys
import time

import numpy as np
import pdfplumber

# ── Config ────────────────────────────────────────────────────────────────────

DRIVER_ID   = "john_doe"
DATA_DIR    = "data"
OUTPUT_FILE = os.path.join(DATA_DIR, f"{DRIVER_ID}_chunks.json")

DOCUMENTS = {
    "driver_manual":      os.path.join(DATA_DIR, "driver_manual.pdf"),
    "warranty_info":      os.path.join(DATA_DIR, "warranty_info.pdf"),
    "insurance_card":     os.path.join(DATA_DIR, "insurance_card.pdf"),
    "maintenance_records": os.path.join(DATA_DIR, "maintenance_records.pdf"),
}

CHUNK_WORDS   = 300   # target words per chunk
OVERLAP_WORDS = 50    # overlap between consecutive chunks
MODEL_NAME    = "all-MiniLM-L6-v2"

CONN_STR = os.environ.get("AZURE_STORAGE_CONNECTION_STRING", "")
BLOB_CONTAINER = "driver-documents"


# ── Text extraction ───────────────────────────────────────────────────────────

def extract_full_text(pdf_path: str) -> str:
    """Extract all text from a PDF with no word limit."""
    with pdfplumber.open(pdf_path) as pdf:
        pages = [page.extract_text() or "" for page in pdf.pages]
    return "\n\n".join(pages)


# ── Chunking ──────────────────────────────────────────────────────────────────

def chunk_text(text: str, chunk_words: int = CHUNK_WORDS, overlap: int = OVERLAP_WORDS) -> list[str]:
    """
    Split text into overlapping fixed-size word chunks.
    Overlap ensures context isn't lost at chunk boundaries.
    """
    words = text.split()
    if not words:
        return []

    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_words, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start += chunk_words - overlap
    return chunks


# ── Embedding ─────────────────────────────────────────────────────────────────

def embed_chunks(chunks: list[str], model) -> np.ndarray:
    """Embed a list of text chunks. Returns (N, D) float32 array."""
    return model.encode(chunks, show_progress_bar=True, convert_to_numpy=True)


# ── Azure upload ──────────────────────────────────────────────────────────────

def upload_to_blob(local_path: str, blob_name: str) -> bool:
    """Upload a local file to Azure Blob Storage. Returns True on success."""
    if not CONN_STR:
        print("  ⚠  AZURE_STORAGE_CONNECTION_STRING not set — skipping Azure upload.")
        return False
    try:
        from azure.storage.blob import BlobServiceClient
        client = BlobServiceClient.from_connection_string(CONN_STR)
        container = client.get_container_client(BLOB_CONTAINER)
        with open(local_path, "rb") as f:
            container.get_blob_client(blob_name).upload_blob(f, overwrite=True)
        return True
    except Exception as exc:
        print(f"  ✗ Azure upload failed: {exc}")
        return False


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("RAG Index Builder")
    print("=" * 60)

    # Load embedding model (downloads ~22MB on first run, then cached)
    print(f"\nLoading embedding model: {MODEL_NAME} ...")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(MODEL_NAME)
    print("  ✓ Model ready")

    all_chunks = []

    for source, pdf_path in DOCUMENTS.items():
        if not os.path.exists(pdf_path):
            print(f"\n⚠  Skipping {source} — file not found: {pdf_path}")
            continue

        print(f"\n── {source} ({os.path.basename(pdf_path)}) ──")

        # Extract full text
        t0 = time.time()
        text = extract_full_text(pdf_path)
        print(f"  Extracted {len(text.split()):,} words in {time.time()-t0:.1f}s")

        # Chunk
        chunks = chunk_text(text)
        print(f"  Split into {len(chunks)} chunks ({CHUNK_WORDS}w / {OVERLAP_WORDS}w overlap)")

        # Embed
        print(f"  Embedding {len(chunks)} chunks...")
        embeddings = embed_chunks(chunks, model)

        # Collect
        for i, (chunk_text_, emb) in enumerate(zip(chunks, embeddings)):
            all_chunks.append({
                "source":    source,
                "chunk_id":  i,
                "text":      chunk_text_,
                "embedding": emb.tolist(),
            })

    print(f"\n{'='*60}")
    print(f"Total chunks: {len(all_chunks)}")

    # Save locally
    with open(OUTPUT_FILE, "w") as f:
        json.dump(all_chunks, f)
    size_mb = os.path.getsize(OUTPUT_FILE) / 1_000_000
    print(f"Saved locally: {OUTPUT_FILE} ({size_mb:.1f} MB)")

    # Upload to Azure
    blob_name = f"{DRIVER_ID}/chunks.json"
    print(f"\nUploading to Azure Blob: {blob_name} ...")
    if upload_to_blob(OUTPUT_FILE, blob_name):
        print(f"  ✓ Uploaded to blob storage")
    else:
        print("  (Upload skipped — will use local file for dev)")

    print("\n✓ Index build complete.")
    print("  The app will now use RAG for document queries.")


if __name__ == "__main__":
    # Ensure we're running from the project root
    if not os.path.isdir(DATA_DIR):
        print(f"ERROR: Run this script from the project root (expected to find ./{DATA_DIR}/)")
        sys.exit(1)

    # Load .env for AZURE_STORAGE_CONNECTION_STRING
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    main()
