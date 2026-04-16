"""
document_loader.py — Loads driver documents into a DocumentBundle.

ARCHITECTURE NOTE:
  This module is the MCP seam. Two loading paths exist:

  1. LOCAL (default, no Azure config needed):
     load_documents(data_dir="data") reads mock .txt/.json files from ./data/.
     Used for local development and testing.

  2. AZURE MCP (production):
     load_documents_from_mcp(driver_id, endpoint) connects to the FastMCP
     server running on Azure Container Apps via the official MCP Python SDK.
     Activated when AZURE_MCP_ENDPOINT is set in the environment.

  app.py checks AZURE_MCP_ENDPOINT and calls the appropriate function.
  chat_engine.py and the rest of the app are completely unchanged.
"""

import asyncio
import io
import json
import os
from dataclasses import dataclass
from datetime import datetime

import pdfplumber


# ── PDF helpers ───────────────────────────────────────────────────────────────

_PDF_KEYWORDS = {
    "oil", "maintenance", "schedule", "tire", "rotation", "brake",
    "filter", "spark plug", "transmission", "fluid", "coolant",
    "warranty", "coverage", "deductible", "roadside", "insurance",
    "registration", "inspection", "recall", "mileage",
}
_SMALL_PDF_THRESHOLD = 50    # pages — extract everything below this
_MAX_WORDS = 8_000           # word cap for large PDFs (~10K tokens — fits rate limit)


def _extract_pdf_text(path: str) -> str:
    """
    Extract relevant text from a PDF file.

    Results are cached in a sidecar `.cache` file next to the PDF so that
    subsequent loads are instant (reads ~100ms) rather than re-extracting.
    The cache is invalidated automatically if the PDF is modified.

    Small PDFs (<= 50 pages): extract every page.
    Large PDFs (> 50 pages): stream page-by-page, keep only keyword-matching
    pages, and stop once we reach 40K words.
    """
    # ── Cache check ─────────────────────────────────────────────────────────
    cache_path = path + ".cache"
    if os.path.exists(cache_path) and (
        os.path.getmtime(cache_path) >= os.path.getmtime(path)
    ):
        with open(cache_path, "r", encoding="utf-8") as f:
            return f.read()

    # ── Extract ──────────────────────────────────────────────────────────────
    with pdfplumber.open(path) as pdf:
        n_pages = len(pdf.pages)

        if n_pages <= _SMALL_PDF_THRESHOLD:
            texts = [page.extract_text() or "" for page in pdf.pages]
            result = "\n\n".join(texts)
        else:
            # Large document — filter on the fly, stop early
            relevant: list[str] = []
            word_count = 0
            for page in pdf.pages:
                text = page.extract_text() or ""
                if any(kw in text.lower() for kw in _PDF_KEYWORDS):
                    relevant.append(text)
                    word_count += len(text.split())
                    if word_count >= _MAX_WORDS:
                        break

            if relevant:
                result = "\n\n".join(relevant)
            else:
                # Fallback: no keyword matches — return first 50 pages
                texts = [pdf.pages[i].extract_text() or "" for i in range(min(50, n_pages))]
                result = "\n\n".join(texts)

    # ── Write cache ──────────────────────────────────────────────────────────
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(result)
    except OSError:
        pass  # Non-fatal: cache write failure just means slower next load

    return result


@dataclass
class DocumentBundle:
    """All documents for a single driver session."""
    vehicle_profile: dict
    driver_manual: str
    insurance_card: str
    maintenance_records: str
    warranty_info: str
    loaded_at: str  # ISO timestamp — useful for cache-busting in production


def load_documents(data_dir: str = "data") -> DocumentBundle:
    """
    Load all driver documents from the local data directory.

    Prefers PDF files (e.g. driver_manual.pdf); falls back to .txt for
    backwards compatibility. vehicle_profile.json is always loaded as JSON.

    This function signature is stable — it will not change when the body is
    replaced with Azure MCP calls. The rest of the app depends only on
    DocumentBundle, not on where the data came from.
    """
    def read_doc(base_name: str) -> str:
        """Try .pdf first, fall back to .txt."""
        pdf_path = os.path.join(data_dir, f"{base_name}.pdf")
        txt_path = os.path.join(data_dir, f"{base_name}.txt")
        if os.path.exists(pdf_path):
            return _extract_pdf_text(pdf_path)
        if os.path.exists(txt_path):
            with open(txt_path, "r") as f:
                return f.read()
        raise FileNotFoundError(
            f"No {base_name}.pdf or {base_name}.txt found in {data_dir}/"
        )

    try:
        with open(os.path.join(data_dir, "vehicle_profile.json"), "r") as f:
            vehicle_profile = json.load(f)

        return DocumentBundle(
            vehicle_profile=vehicle_profile,
            driver_manual=read_doc("driver_manual"),
            insurance_card=read_doc("insurance_card"),
            maintenance_records=read_doc("maintenance_records"),
            warranty_info=read_doc("warranty_info"),
            loaded_at=datetime.now().isoformat(),
        )

    except FileNotFoundError as e:
        raise RuntimeError(
            f"Could not load document: {e}. "
            f"Make sure you are running the app from the project root directory "
            f"and the ./data folder exists with all required files."
        ) from e


def get_vehicle_display_name(bundle: DocumentBundle) -> str:
    """Returns a formatted vehicle name string for display in the UI sidebar."""
    v = bundle.vehicle_profile.get("vehicle", {})
    return f"{v.get('year', '')} {v.get('make', '')} {v.get('model', '')} {v.get('trim', '')}".strip()


def get_driver_name(bundle: DocumentBundle) -> str:
    """Returns the driver's full name from the vehicle profile."""
    return bundle.vehicle_profile.get("driver", {}).get("name", "Driver")


def get_current_mileage(bundle: DocumentBundle) -> int:
    """Returns the vehicle's current mileage as an integer."""
    return bundle.vehicle_profile.get("vehicle", {}).get("current_mileage", 0)


def get_registration_expiry(bundle: DocumentBundle) -> str:
    """Returns the registration expiry date string (YYYY-MM-DD)."""
    return bundle.vehicle_profile.get("vehicle", {}).get("registration_expiry", "")


# ── RAG: semantic search ──────────────────────────────────────────────────────

def search_documents(
    query: str,
    driver_id: str = None,
    endpoint: str = None,
) -> list[dict]:
    """
    Semantic search across driver documents using the pre-built vector index.

    Azure path (endpoint set): calls the MCP server's search_documents tool.
    Local path (no endpoint):  searches data/john_doe_chunks.json in-memory.

    Returns a list of {"text": ..., "source": ..., "score": ...} dicts,
    ordered by relevance (highest score first). Returns [] if no index exists.
    """
    if endpoint:
        return asyncio.run(_async_search_documents(query, driver_id or "john_doe", endpoint))
    return _local_search_documents(query)


def _local_search_documents(query: str, top_k: int = 5) -> list[dict]:
    """Search the local chunks.json file using in-memory cosine similarity."""
    import numpy as np

    index_path = os.path.join("data", "john_doe_chunks.json")
    if not os.path.exists(index_path):
        return []  # Index not built yet — caller falls back to word-cap approach

    with open(index_path) as f:
        chunks = json.load(f)

    if not chunks:
        return []

    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("all-MiniLM-L6-v2")
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


async def _async_search_documents(query: str, driver_id: str, endpoint: str) -> list[dict]:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    url = _normalize_endpoint(endpoint)
    async with streamablehttp_client(url=url) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(
                "search_documents",
                {"driver_id": driver_id, "query": query, "top_k": 5},
            )

    if result.isError or not result.content:
        return []

    # FastMCP serializes a list return as multiple TextContent blocks (one per
    # item) rather than a single JSON array string.  Collect all blocks and
    # return a flat list of chunk dicts.
    chunks = []
    for content_item in result.content:
        parsed = json.loads(content_item.text)
        if isinstance(parsed, list):
            chunks.extend(parsed)   # single-block JSON array (future-proof)
        else:
            chunks.append(parsed)   # one block per item (current FastMCP behaviour)
    return chunks


# ── Azure MCP path ────────────────────────────────────────────────────────────

def load_documents_from_mcp(driver_id: str, endpoint: str) -> DocumentBundle:
    """
    Load driver documents from the Azure MCP server (Container Apps + FastMCP).

    Connects using the official MCP Python SDK over Streamable HTTP.
    This is a synchronous wrapper around the async MCP client — required
    because Streamlit's execution model is synchronous.

    Args:
        driver_id: The driver's identifier (matches the blob folder prefix).
        endpoint:  The Container App FQDN, e.g.
                   "driver-mcp-server.niceocean-abc123.eastus.azurecontainerapps.io"
                   (no trailing slash, no "https://").

    Returns:
        A DocumentBundle populated from live Azure Blob Storage data.
    """
    return asyncio.run(_async_load_documents(driver_id, endpoint))


def _normalize_endpoint(endpoint: str) -> str:
    """Ensure endpoint is a full https:// URL ending with /mcp."""
    endpoint = endpoint.rstrip("/")
    if not endpoint.startswith(("http://", "https://")):
        endpoint = f"https://{endpoint}"
    if not endpoint.endswith("/mcp"):
        endpoint = f"{endpoint}/mcp"
    return endpoint


async def _async_load_documents(driver_id: str, endpoint: str) -> DocumentBundle:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    url = _normalize_endpoint(endpoint)
    async with streamablehttp_client(url=url) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(
                "get_driver_documents",
                {"driver_id": driver_id},
            )

    # Check for server-side tool errors
    if result.isError:
        error_text = result.content[0].text if result.content else "Unknown server error"
        raise RuntimeError(f"MCP server error: {error_text}")

    if not result.content or not result.content[0].text:
        raise RuntimeError(
            "MCP server returned empty content. Check Container App logs:\n"
            "  az containerapp logs show --name driver-mcp-server "
            "--resource-group sasser-chatbot-rg --follow"
        )

    raw = result.content[0].text
    data = json.loads(raw)

    return DocumentBundle(
        vehicle_profile=data["vehicle_profile"],
        driver_manual=data.get("driver_manual", ""),
        insurance_card=data.get("insurance_card", ""),
        maintenance_records=data.get("maintenance_records", ""),
        warranty_info=data.get("warranty_info", ""),
        loaded_at=data.get("loaded_at", datetime.now().isoformat()),
    )


def update_mileage_mcp(driver_id: str, new_mileage: int, endpoint: str) -> dict:
    """
    Update the driver's current mileage via the Azure MCP server.

    Args:
        driver_id:   The driver's identifier.
        new_mileage: New odometer reading in miles.
        endpoint:    The Container App FQDN (same format as load_documents_from_mcp).

    Returns:
        The updated vehicle_profile dict returned by the server.
    """
    return asyncio.run(_async_update_mileage(driver_id, new_mileage, endpoint))


async def _async_update_mileage(driver_id: str, new_mileage: int, endpoint: str) -> dict:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    url = _normalize_endpoint(endpoint)
    async with streamablehttp_client(url=url) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(
                "update_mileage",
                {"driver_id": driver_id, "new_mileage": new_mileage},
            )

    raw = result.content[0].text
    return json.loads(raw)
