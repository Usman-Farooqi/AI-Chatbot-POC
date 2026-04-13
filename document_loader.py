"""
document_loader.py — Loads driver documents into a DocumentBundle.

ARCHITECTURE NOTE:
  This module is the MCP seam. In the current POC, documents are loaded
  from local files in the ./data directory. When deploying to production
  on Azure, only this file changes — everything above it (chat_engine.py,
  app.py) stays identical.

  FUTURE: Azure MCP Integration Point
  def load_documents_from_mcp(mcp_endpoint: str, driver_token: str) -> DocumentBundle:
      # Fetch documents from Azure MCP Server using the authenticated driver's token.
      # Returns a DocumentBundle with the same structure as load_documents().
      pass
"""

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

#MCP_URL = "http://localhost:8000/mcp"  # local
MCP_URL = "https://vehicle-assistant-mcp-server.livelydune-32d815ec.westus2.azurecontainerapps.io/mcp"  # azure container app

@dataclass
class DocumentBundle:
    vehicle_profile: dict
    driver_manual: str
    insurance_card: str
    maintenance_records: str
    warranty_info: str
    loaded_at: str

async def load_documents_from_mcp_async(driver_id: str, car_id: str) -> DocumentBundle:
    print("[client] opening streamable_http_client...")
    async with streamable_http_client(MCP_URL) as (read_stream, write_stream, _notifications):
        print("[client] got streams, creating ClientSession...")
        async with ClientSession(read_stream, write_stream) as session:
            print("[client] calling session.initialize()...")
            await asyncio.wait_for(session.initialize(), timeout=10)
            print("[client] initialize() done, calling load_vehicle_documents...")

            result = await asyncio.wait_for(
                session.call_tool(
                    "load_vehicle_documents",
                    arguments={"driver_id": driver_id, "car_id": car_id},
                ),
                timeout=1000,
            )
            print("[client] call_tool() returned")

            if result.isError:
                error_text = result.content[0].text if result.content else "Unknown error"
                raise RuntimeError(f"MCP tool error: {error_text}")

            part = result.content[0]
            print("[client] content part type:", getattr(part, "type", None))
            print("[client] content part text (first 200 chars):", getattr(part, "text", "")[:200])

            # 2. Parse the JSON string
            bundle = json.loads(part.text)

            print("[client] bundle keys:", bundle.keys())

            return DocumentBundle(
                vehicle_profile=bundle["vehicle_profile"],
                driver_manual=bundle["driver_manual"],
                insurance_card=bundle["insurance_card"],
                maintenance_records=bundle["maintenance_records"],
                warranty_info=bundle["warranty_info"],
                loaded_at=datetime.now().isoformat(),
            )

def load_documents_from_mcp(driver_id: str, car_id: str) -> DocumentBundle:
    return asyncio.run(load_documents_from_mcp_async(driver_id, car_id))


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
