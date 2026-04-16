import asyncio
import json
from dataclasses import dataclass

import anthropic
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

import os
from dotenv import load_dotenv

load_dotenv()

MCP_URL = os.environ["MCP_URL"]

@dataclass
class VehicleInfo:  # Lightweight summary pulled from vehicle documents.
    driver_id: str
    car_id: str
    driver_name: str
    vehicle_name: str
    current_mileage: int
    registration_expiry: str  # "YYYY-MM-DD"
    oil_change_due: str       # display string e.g. "49,100 mi"
    insurance_expiry: str     # display string e.g. "Dec 2026"

async def _call_mcp_tool(tool_name: str, driver_id: str, car_id: str) -> str:
    """Call any MCP tool by name and return the raw text result."""
    async with streamable_http_client(MCP_URL) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await asyncio.wait_for(session.initialize(), timeout=100)

            result = await asyncio.wait_for(
                session.call_tool(
                    tool_name,
                    arguments={"driver_id": driver_id, "car_id": car_id},
                ),
                timeout=300,
            )

            if result.isError:
                error_text = result.content[0].text if result.content else "Unknown error"
                raise RuntimeError(f"MCP tool error: {error_text}")

            part = result.content[0]
            return part.text if hasattr(part, "text") else str(part)

async def _fetch_all_docs(driver_id: str, car_id: str) -> tuple[str, str, str]:
    """Fetch vehicle profile, maintenance records, and insurance info in parallel."""
    profile_raw, maintenance_raw, insurance_raw = await asyncio.gather(
        _call_mcp_tool("get_vehicle_profile", driver_id, car_id),
        _call_mcp_tool("get_maintenance_records", driver_id, car_id),
        _call_mcp_tool("get_insurance_info", driver_id, car_id),
    )
    return profile_raw, maintenance_raw, insurance_raw

def _extract_with_llm(raw_text: str, question: str, api_key: str) -> str:
    """
    Use Claude Haiku to extract a single display value from raw document text.

    Asking a model instead of parsing specific fields means the extraction stays
    correct even when the underlying document format changes.
    """
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=20,
        messages=[{
            "role": "user",
            "content": (
                f"{question}\n\n"
                f"Document:\n{raw_text}\n\n"
                "Respond with ONLY the value, no explanation or punctuation."
            ),
        }],
    )
    return response.content[0].text.strip()

def _build_vehicle_name(profile: dict) -> str:
    vehicle = profile.get("vehicle", {})
    year = vehicle.get("year", "")
    make = vehicle.get("make", "")
    model = vehicle.get("model", "")
    trim = vehicle.get("trim", "")
    return f"{year} {make} {model} {trim}".strip()

def get_vehicle_info(driver_id: str, car_id: str) -> VehicleInfo:
    """Synchronous wrapper — call from Streamlit."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "")

    profile_raw, maintenance_raw, insurance_raw = asyncio.run(
        _fetch_all_docs(driver_id, car_id)
    )

    profile = json.loads(profile_raw)
    driver = profile.get("driver", {})
    vehicle = profile.get("vehicle", {})

    oil_change_due = _extract_with_llm(
        maintenance_raw,
        "What is the next scheduled oil change due mileage? "
        "Format as a number with comma separator and 'mi' suffix, e.g. '49,100 mi'.",
        api_key,
    )

    insurance_expiry = _extract_with_llm(
        insurance_raw,
        "When does the insurance policy expire? "
        "Format as abbreviated month and year only, e.g. 'Dec 2026'.",
        api_key,
    )

    return VehicleInfo(
        driver_id=driver_id,
        car_id=car_id,
        driver_name=driver.get("name", "Unknown Driver"),
        vehicle_name=_build_vehicle_name(profile),
        current_mileage=vehicle.get("current_mileage", 0),
        registration_expiry=vehicle.get("registration_expiry", ""),
        oil_change_due=oil_change_due,
        insurance_expiry=insurance_expiry,
    )


