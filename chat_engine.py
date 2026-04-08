"""
chat_engine.py — Assembles the system prompt and streams Claude responses.

The system prompt injects all driver documents as XML-tagged context blocks,
then anchors Claude with the current date and mileage as grounding facts.
This structure enables multi-document reasoning (e.g., calculating oil change
due dates from mileage in the profile + service records + manual intervals).
"""

import json
import os
from datetime import date
from typing import Generator

import anthropic
from dotenv import load_dotenv

from document_loader import DocumentBundle, get_current_mileage, get_driver_name

load_dotenv()

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1024


def build_system_prompt(bundle: DocumentBundle) -> str:
    """
    Assembles the full system prompt with all documents injected as context.

    Document sections use XML tags — Claude is trained to parse these well
    and will cite sources by tag name in its responses.

    Grounding facts (date + mileage) are placed LAST so they are the most
    prominent anchors during inference.
    """
    driver_name = get_driver_name(bundle)
    current_mileage = get_current_mileage(bundle)
    today = date.today().strftime("%B %d, %Y")

    return f"""You are a personal vehicle assistant for {driver_name}. You have access to their complete vehicle documents including their driver's manual, insurance card, maintenance records, and warranty information.

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

<driver_manual>
{bundle.driver_manual}
</driver_manual>

<insurance_card>
{bundle.insurance_card}
</insurance_card>

<warranty_info>
{bundle.warranty_info}
</warranty_info>

GROUNDING FACTS (use these for all date and mileage calculations):
- Today's date: {today}
- {driver_name}'s current vehicle mileage: {current_mileage:,} miles"""


def stream_chat_response(
    messages: list[dict], bundle: DocumentBundle
) -> Generator[str, None, None]:
    """
    Streams Claude's response token by token.

    Args:
        messages: Conversation history as list of {"role": ..., "content": ...} dicts.
        bundle: The loaded DocumentBundle containing all driver documents.

    Yields:
        Text delta strings as they arrive from the API.

    Usage with Streamlit:
        response = st.write_stream(stream_chat_response(messages, bundle))
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY not found. "
            "Create a .env file with ANTHROPIC_API_KEY=your_key_here "
            "(see .env.example)."
        )

    client = anthropic.Anthropic(api_key=api_key)
    system_prompt = build_system_prompt(bundle)

    with client.messages.stream(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=system_prompt,
        messages=messages,
    ) as stream:
        for text_delta in stream.text_stream:
            yield text_delta
