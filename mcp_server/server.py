"""
mcp_server/server.py — FastMCP server for the AI Driver Chatbot.

Serves driver documents stored as PDFs (and vehicle_profile.json) in Azure Blob Storage.
Runs as a containerized service on Azure Container Apps.

Authentication: Managed Identity via DefaultAzureCredential (no secrets in code).
Transport: Streamable HTTP on port 8000.

Tools exposed:
  - get_driver_documents(driver_id)   — full DocumentBundle (all docs as extracted text)
  - get_vehicle_profile(driver_id)    — structured JSON profile only (lightweight)
  - update_mileage(driver_id, new_mileage) — write new mileage back to vehicle_profile.json
  - list_driver_documents(driver_id)  — metadata for all blobs (name, size, last_modified)
"""

import json
import os
from datetime import datetime, timezone

import fitz  # PyMuPDF — C-based, 5-10x faster than pdfplumber for large PDFs
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from mcp.server.fastmcp import FastMCP

# ── Config (set via Container App environment variables) ──────────────────────
# Supports both BLOB_STORAGE_URL (full URL) and STORAGE_ACCOUNT_NAME (name only)
ACCOUNT_URL = os.environ.get(
    "BLOB_STORAGE_URL",
    f"https://{os.environ.get('STORAGE_ACCOUNT_NAME', '')}.blob.core.windows.net",
)
# Supports both BLOB_CONTAINER and BLOB_CONTAINER_NAME
BLOB_CONTAINER_NAME = os.environ.get("BLOB_CONTAINER") or os.environ.get("BLOB_CONTAINER_NAME", "driver-documents")

# ── FastMCP server ────────────────────────────────────────────────────────────
mcp = FastMCP("AI Driver Documents", host="0.0.0.0", port=8000)

# ── In-memory document cache ──────────────────────────────────────────────────
# Keyed by blob name (e.g. "john_doe/driver_manual.pdf"). Survives for the
# lifetime of the container instance — avoids re-downloading and re-extracting
# the 12 MB owner's manual on every MCP call.
_DOC_CACHE: dict[str, str] = {}

# ── Embedding model singleton ─────────────────────────────────────────────────
# Loaded once per container lifetime (model is ~90MB, pre-baked into the image).
_EMBED_MODEL = None


def _get_embed_model():
    global _EMBED_MODEL
    if _EMBED_MODEL is None:
        from sentence_transformers import SentenceTransformer
        _EMBED_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return _EMBED_MODEL


# ── Helpers ───────────────────────────────────────────────────────────────────

def _blob_client() -> BlobServiceClient:
    """
    Returns a BlobServiceClient.
    Prefers AZURE_STORAGE_CONNECTION_STRING (POC / sandbox), falls back to
    Managed Identity via DefaultAzureCredential (production).
    """
    conn_str = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    if conn_str:
        return BlobServiceClient.from_connection_string(conn_str)
    return BlobServiceClient(account_url=ACCOUNT_URL, credential=DefaultAzureCredential())


def _read_blob_bytes(client: BlobServiceClient, blob_name: str) -> bytes:
    """Download a blob and return its raw bytes."""
    container = client.get_container_client(BLOB_CONTAINER_NAME)
    blob = container.get_blob_client(blob_name)
    return blob.download_blob().readall()


_PDF_KEYWORDS = {
    "oil", "maintenance", "schedule", "tire", "rotation", "brake",
    "filter", "spark plug", "transmission", "fluid", "coolant",
    "warranty", "coverage", "deductible", "roadside", "insurance",
    "registration", "inspection", "recall", "mileage",
}
_SMALL_PDF_PAGES = 50   # extract everything below this page count
_MAX_PDF_WORDS   = 8_000   # word cap for large PDFs (~10K tokens — fits rate limit)


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    """
    Extract relevant text from a PDF using PyMuPDF (fitz).

    PyMuPDF is C-based via MuPDF — typically 5-10x faster than pdfplumber
    on a constrained container CPU. Same keyword-filtering / early-stop
    logic to stay within Claude's practical context budget.

    Small PDFs (<= 50 pages): extract every page.
    Large PDFs (> 50 pages): stream page-by-page, keep only keyword-matching
    pages, and stop once 40K words have been collected.
    """
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        n_pages = len(doc)

        if n_pages <= _SMALL_PDF_PAGES:
            return "\n\n".join(page.get_text() for page in doc)

        # Large document — filter on the fly, stop early
        relevant: list[str] = []
        word_count = 0
        for page in doc:
            text = page.get_text()
            if any(kw in text.lower() for kw in _PDF_KEYWORDS):
                relevant.append(text)
                word_count += len(text.split())
                if word_count >= _MAX_PDF_WORDS:
                    break

        if relevant:
            return "\n\n".join(relevant)

        # Fallback: no keyword matches — return first 50 pages
        return "\n\n".join(doc[i].get_text() for i in range(min(50, n_pages)))


def _read_document(client: BlobServiceClient, driver_id: str, filename: str) -> str:
    """
    Read a document blob for a driver using a three-tier cache strategy:

      1. In-memory dict (_DOC_CACHE) — fastest, lives for the container's lifetime.
      2. Azure Blob text cache (.txt alongside .pdf) — survives container restarts.
         On first PDF extraction the result is written back as a .txt blob so
         subsequent calls (even on a fresh container) skip extraction entirely.
      3. Full PDF download + PyMuPDF extraction — only on first-ever access.

    Cache invalidation: delete the .txt blob to force re-extraction from PDF.
    Returns empty string if neither blob exists.
    """
    blob_name = f"{driver_id}/{filename}"

    # ── Tier 1: in-memory ────────────────────────────────────────────────────
    if blob_name in _DOC_CACHE:
        return _DOC_CACHE[blob_name]

    # ── Tier 2: blob-level text cache (PDF only) ─────────────────────────────
    if filename.endswith(".pdf"):
        txt_blob = blob_name[:-4] + ".txt"  # e.g. john_doe/driver_manual.txt
        try:
            raw_txt = _read_blob_bytes(client, txt_blob)
            text = raw_txt.decode("utf-8", errors="replace")
            _DOC_CACHE[blob_name] = text
            return text
        except Exception:
            pass  # No cache blob yet — fall through to full extraction

    # ── Tier 3: download + parse ──────────────────────────────────────────────
    try:
        raw = _read_blob_bytes(client, blob_name)
    except Exception:
        return ""

    text = _extract_pdf_text(raw) if filename.endswith(".pdf") else raw.decode("utf-8", errors="replace")
    _DOC_CACHE[blob_name] = text

    # Write extracted text back to Blob as persistent cache for future cold starts
    if filename.endswith(".pdf"):
        txt_blob = blob_name[:-4] + ".txt"
        try:
            container = client.get_container_client(BLOB_CONTAINER_NAME)
            container.get_blob_client(txt_blob).upload_blob(
                text.encode("utf-8"), overwrite=True
            )
        except Exception:
            pass  # Non-fatal — cache write failure means slower next cold start

    return text


# ── MCP Tools ─────────────────────────────────────────────────────────────────

@mcp.tool()
def get_driver_documents(driver_id: str) -> dict:
    """
    Fetch the complete document bundle for a driver.

    Returns all 5 documents as extracted text plus the structured vehicle
    profile. The Streamlit app calls this once at session start and injects
    the result into Claude's system prompt.

    Args:
        driver_id: The driver's identifier (folder prefix in Blob Storage).

    Returns:
        A dict with keys: vehicle_profile, driver_manual, insurance_card,
        maintenance_records, warranty_info, loaded_at.
    """
    client = _blob_client()

    # vehicle_profile is always JSON
    try:
        profile_bytes = _read_blob_bytes(client, f"{driver_id}/vehicle_profile.json")
        vehicle_profile = json.loads(profile_bytes.decode("utf-8"))
    except Exception as exc:
        raise ValueError(f"Could not load vehicle_profile.json for driver '{driver_id}': {exc}") from exc

    # PDF documents — try .pdf first, fall back to .txt for backwards compatibility
    def read_doc(base_name: str) -> str:
        text = _read_document(client, driver_id, f"{base_name}.pdf")
        if not text:
            text = _read_document(client, driver_id, f"{base_name}.txt")
        return text

    return {
        "vehicle_profile": vehicle_profile,
        "driver_manual": read_doc("driver_manual"),
        "insurance_card": read_doc("insurance_card"),
        "maintenance_records": read_doc("maintenance_records"),
        "warranty_info": read_doc("warranty_info"),
        "loaded_at": datetime.now(timezone.utc).isoformat(),
    }


@mcp.tool()
def get_vehicle_profile(driver_id: str) -> dict:
    """
    Fetch only the structured vehicle profile for a driver (lightweight).

    Useful for refreshing sidebar metrics (e.g., updated mileage) without
    reloading all PDF documents.

    Args:
        driver_id: The driver's identifier.

    Returns:
        The parsed vehicle_profile.json dict.
    """
    client = _blob_client()
    try:
        raw = _read_blob_bytes(client, f"{driver_id}/vehicle_profile.json")
        return json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise ValueError(f"Could not load vehicle profile for '{driver_id}': {exc}") from exc


@mcp.tool()
def update_mileage(driver_id: str, new_mileage: int) -> dict:
    """
    Update the current mileage in the driver's vehicle profile.

    Uses ETag-based optimistic concurrency to prevent overwriting concurrent
    updates. Retries once on a 412 Precondition Failed.

    Args:
        driver_id:   The driver's identifier.
        new_mileage: The new odometer reading in miles.

    Returns:
        The updated vehicle_profile dict with success: True.
    """
    client = _blob_client()
    blob_name = f"{driver_id}/vehicle_profile.json"
    container = client.get_container_client(BLOB_CONTAINER_NAME)
    blob = container.get_blob_client(blob_name)

    for attempt in range(2):
        # Read with ETag
        download = blob.download_blob()
        etag = download.properties.etag
        profile = json.loads(download.readall().decode("utf-8"))

        # Patch mileage
        profile.setdefault("vehicle", {})["current_mileage"] = new_mileage
        profile.setdefault("vehicle", {})["mileage_updated_at"] = datetime.now(timezone.utc).isoformat()

        # Write back with If-Match to catch concurrent writes
        try:
            blob.upload_blob(
                json.dumps(profile, indent=2).encode("utf-8"),
                overwrite=True,
                etag=etag,
                match_condition={"if_match": etag},
            )
            return {**profile, "success": True}
        except Exception:
            if attempt == 1:
                raise  # Give up after one retry

    raise RuntimeError("Failed to update mileage after retries.")


@mcp.tool()
def list_driver_documents(driver_id: str) -> list:
    """
    List metadata for all document blobs belonging to a driver.

    Args:
        driver_id: The driver's identifier.

    Returns:
        A list of dicts with keys: name, size_bytes, last_modified.
    """
    client = _blob_client()
    container = client.get_container_client(BLOB_CONTAINER_NAME)
    prefix = f"{driver_id}/"
    results = []
    for blob in container.list_blobs(name_starts_with=prefix):
        results.append({
            "name": blob.name.removeprefix(prefix),
            "size_bytes": blob.size,
            "last_modified": blob.last_modified.isoformat() if blob.last_modified else None,
        })
    return results


@mcp.tool()
def search_documents(driver_id: str, query: str, top_k: int = 5) -> list:
    """
    Semantic search across driver documents using the pre-built vector index.

    Loads the chunks.json index from Blob Storage (cached in memory after the
    first call), embeds the query with all-MiniLM-L6-v2, and returns the top_k
    most relevant chunks by cosine similarity.

    Args:
        driver_id: The driver's identifier (folder prefix in Blob Storage).
        query:     The search query (user question or concatenated recent messages).
        top_k:     Number of chunks to return (default 5).

    Returns:
        A list of {"text": ..., "source": ..., "score": ...} dicts ordered
        by relevance (highest score first). Returns [] if no index exists.
    """
    import numpy as np

    # ── Load chunks index (tier-1: memory, tier-2: blob) ─────────────────────
    cache_key = f"{driver_id}/__chunks__"
    if cache_key in _DOC_CACHE:
        chunks_raw = _DOC_CACHE[cache_key]
    else:
        client = _blob_client()
        try:
            raw = _read_blob_bytes(client, f"{driver_id}/chunks.json")
        except Exception:
            return []  # No index yet — caller falls back to word-cap approach
        chunks_raw = raw.decode("utf-8")
        _DOC_CACHE[cache_key] = chunks_raw

    chunks = json.loads(chunks_raw)
    if not chunks:
        return []

    # ── Embed query + cosine similarity ──────────────────────────────────────
    model = _get_embed_model()
    q_emb = model.encode(query)

    embeddings = np.array([c["embedding"] for c in chunks], dtype=np.float32)
    q_norm = q_emb / (np.linalg.norm(q_emb) + 1e-9)
    e_norms = embeddings / (np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-9)
    scores = e_norms @ q_norm

    top_idx = np.argsort(scores)[::-1][:top_k]
    return [
        {"text": chunks[i]["text"], "source": chunks[i]["source"], "score": float(scores[i])}
        for i in top_idx
    ]


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run(transport="streamable-http")
