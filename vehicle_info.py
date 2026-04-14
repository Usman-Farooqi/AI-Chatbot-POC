import asyncio 
import json 
from dataclasses import dataclass

from mcp import ClientSession 
from mcp.client.streamable_http import streamable_http_client

import os
from dotenv import load_dotenv

load_dotenv()

MCP_URL = os.environ["MCP_URL"]

@dataclass 
class VehicleInfo: # Lightweight summary pulled from the vehicle profile resource.
    driver_id: str
    car_id: str
    driver_name: str 
    vehicle_name: str 
    current_mileage: int 
    registration_expiry: str # "YYYY-MM-DD"

async def _fetch_vehicle_profile(driver_id: str, car_id: str) -> dict:
    """Call the get_vehicle_profile tool on the MCP server."""
    async with streamable_http_client(MCP_URL) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await asyncio.wait_for(session.initialize(), timeout=100)

            result = await asyncio.wait_for(
                session.call_tool(
                    "get_vehicle_profile",
                    arguments={"driver_id": driver_id, "car_id": car_id},
                ),
                timeout=300,
            )

            if result.isError:
                error_text = result.content[0].text if result.content else "Unknown error"
                raise RuntimeError(f"MCP tool error: {error_text}")

            part = result.content[0]
            text = part.text if hasattr(part, "text") else str(part)
            return json.loads(text)

def _build_vehicle_name(profile: dict) -> str:
    vehicle = profile.get("vehicle", {})
    year = vehicle.get("year", "")
    make = vehicle.get("make", "")
    model = vehicle.get("model", "")
    trim = vehicle.get("trim", "")
    return f"{year} {make} {model} {trim}".strip()

def get_vehicle_info(driver_id: str, car_id: str) -> VehicleInfo:
    """Synchronous wrapper — call from Streamlit."""
    profile = asyncio.run(_fetch_vehicle_profile(driver_id, car_id))

    driver = profile.get("driver", {})
    vehicle = profile.get("vehicle", {})

    return VehicleInfo(
        driver_id=driver_id,
        car_id=car_id,
        driver_name=driver.get("name", "Unknown Driver"),
        vehicle_name=_build_vehicle_name(profile),
        current_mileage=vehicle.get("current_mileage", 0),
        registration_expiry=vehicle.get("registration_expiry", ""),
    )


