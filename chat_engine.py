"""
chat_engine.py — Assembles the system prompt and streams Claude responses.

Uses RAG (Retrieval-Augmented Generation) to build the system prompt:
  - Small documents (vehicle_profile, insurance_card, maintenance_records)
    are always injected in full — they're tiny and always relevant.
  - Large documents (driver_manual, warranty_info) are retrieved via
    semantic search: the user's question is embedded, the most relevant
    passages are returned, and only those are injected into the prompt.

This keeps the total prompt to ~3,000 tokens instead of ~15,000, which:
  1. Stays well under the 30K TPM rate limit
  2. Gives Claude precisely the relevant context, not everything at once
  3. Scales to arbitrarily large document sets
"""

import json
import os
from datetime import date
from typing import Generator

import anthropic
from dotenv import load_dotenv

from document_loader import (
    DocumentBundle,
    get_current_mileage,
    get_driver_name,
    search_documents,
)

load_dotenv()

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1024

# Fallback word cap — used only when no RAG index exists yet
_MANUAL_MAX_WORDS   = 6_000
_WARRANTY_MAX_WORDS = 5_000


def _cap_words(text: str, max_words: int) -> str:
    """Return text truncated to at most max_words words (RAG fallback)."""
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + "\n[...document excerpt — showing first portion only...]"


def _format_chunks(chunks: list[dict]) -> str:
    """Format retrieved chunks into a readable context block."""
    if not chunks:
        return "(no relevant passages retrieved)"
    parts = []
    for chunk in chunks:
        source = chunk["source"].replace("_", " ").title()
        parts.append(f"[{source}]\n{chunk['text']}")
    return "\n\n---\n\n".join(parts)


def build_system_prompt(
    bundle: DocumentBundle,
    retrieved_chunks: list[dict] | None = None,
) -> str:
    """
    Assembles the system prompt.

    If retrieved_chunks is provided (RAG mode), the large documents
    (driver_manual, warranty_info) are replaced with the retrieved passages.

    If retrieved_chunks is None or empty (fallback mode), the large documents
    are injected with a word cap — same behaviour as before RAG.
    """
    driver_name = get_driver_name(bundle)
    current_mileage = get_current_mileage(bundle)
    today = date.today().strftime("%B %d, %Y")

    base = f"""You are a personal vehicle assistant for {driver_name}. You have access to their complete vehicle documents including their driver's manual, insurance card, maintenance records, and warranty information.

BEHAVIORAL GUIDELINES:
- Answer questions conversationally but precisely.
- When answering maintenance timing questions, always show your math: state the last service mileage, add the interval from the manual, subtract current mileage to get miles remaining.
- Always cite which document your answer comes from (e.g., "According to your maintenance records..." or "Your insurance card shows...").
- If a question spans multiple documents, combine the information and say so.
- If the answer is "no" or "not covered," say so clearly — don't hedge.
- Keep responses concise. Use bullet points for lists of items.
- If the driver asks about something not covered in their documents, say so rather than guessing.

<vehicle_profile>
{json.dumps(bundle.vehicle_profile, indent=2)}
</vehicle_profile>

<maintenance_records>
{bundle.maintenance_records}
</maintenance_records>

<insurance_card>
{bundle.insurance_card}
</insurance_card>
"""

    if retrieved_chunks:
        # RAG mode — inject only the retrieved passages
        base += f"""
<retrieved_document_passages>
The following passages were retrieved from the driver's manual and warranty documents
as the most relevant sections for the current question:

{_format_chunks(retrieved_chunks)}
</retrieved_document_passages>
"""
    else:
        # Fallback — inject word-capped full documents
        base += f"""
<driver_manual>
{_cap_words(bundle.driver_manual, _MANUAL_MAX_WORDS)}
</driver_manual>

<warranty_info>
{_cap_words(bundle.warranty_info, _WARRANTY_MAX_WORDS)}
</warranty_info>
"""

    base += f"""
GROUNDING FACTS (use these for all date and mileage calculations):
- Today's date: {today}
- {driver_name}'s current vehicle mileage: {current_mileage:,} miles"""

    return base


def stream_chat_response(
    messages: list[dict],
    bundle: DocumentBundle,
    driver_id: str | None = None,
    endpoint: str | None = None,
) -> Generator[str, None, None]:
    """
    Streams Claude's response token by token using RAG context retrieval.

    Args:
        messages:  Conversation history as {"role": ..., "content": ...} dicts.
        bundle:    The loaded DocumentBundle (vehicle profile + small docs).
        driver_id: Driver identifier, used for Azure MCP search path.
        endpoint:  Azure MCP endpoint URL; if set, RAG uses the MCP server.

    Yields:
        Text delta strings as they arrive from the API.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY not found. "
            "Create a .env file with ANTHROPIC_API_KEY=your_key_here "
            "(see .env.example)."
        )

    # ── RAG retrieval ─────────────────────────────────────────────────────────
    # Build retrieval query from the last 1-2 messages for better follow-up
    # handling (e.g. "what about the filter?" has context from prior turn).
    query_parts = [
        m["content"] for m in messages[-2:]
        if m["role"] in ("user", "assistant")
    ]
    retrieval_query = " ".join(query_parts)

    chunks = search_documents(retrieval_query, driver_id=driver_id, endpoint=endpoint)

    # ── Prompt + stream ───────────────────────────────────────────────────────
    client = anthropic.Anthropic(api_key=api_key)
    system_prompt = build_system_prompt(bundle, retrieved_chunks=chunks or None)

    with client.messages.stream(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=system_prompt,
        messages=messages,
    ) as stream:
        for text_delta in stream.text_stream:
            yield text_delta
