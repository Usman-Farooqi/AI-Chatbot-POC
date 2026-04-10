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

import json
import os
from dataclasses import dataclass
from datetime import datetime

import requests

MCP_URL = "http://localhost:8000/mcp"


@dataclass
class DocumentBundle:
    """All documents for a single driver session."""
    vehicle_profile: dict
    driver_manual: str
    insurance_card: str
    maintenance_records: str
    warranty_info: str
    loaded_at: str  # ISO timestamp — useful for cache-busting in production

def mcp_request(payload: dict) -> dict:
    resp = requests.post(MCP_URL, json=payload, timeout=10)
    resp.raise_for_status()
    return resp.json()

def load_documents_from_mcp(driver_id: str, car_id: str) -> DocumentBundle:
    # (Optional) initialize once and cache if you want
    init_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {},
    }
    _ = mcp_request(init_payload)

    call_payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "load_vehicle_documents",
            "arguments": {
                "driver_name": driver_id,
                "car_id": car_id,
            },
        },
    }
    result = mcp_request(call_payload)
    # Result is MCP-style: content[0].json is your "document bundle"
    content = result["result"]["content"][0]
    bundle = content["json"]
    return DocumentBundle(
        vehicle_profile=bundle["vehicle_profile"],
        driver_manual=bundle["driver_manual"],
        insurance_card=bundle["insurance_card"],
        maintenance_records=bundle["maintenance_records"],
        warranty_info=bundle["warranty_info"],
        loaded_at=datetime.now().isoformat(),
    )


def load_documents(data_dir: str = "data") -> DocumentBundle:
    """
    Load all driver documents from the local data directory.

    This function signature is stable — it will not change when the body is
    replaced with Azure MCP calls. The rest of the app depends only on
    DocumentBundle, not on where the data came from.
    """
    try:
        with open(os.path.join(data_dir, "vehicle_profile.json"), "r") as f:
            vehicle_profile = json.load(f)

        with open(os.path.join(data_dir, "driver_manual.txt"), "r") as f:
            driver_manual = f.read()

        with open(os.path.join(data_dir, "insurance_card.txt"), "r") as f:
            insurance_card = f.read()

        with open(os.path.join(data_dir, "maintenance_records.txt"), "r") as f:
            maintenance_records = f.read()

        with open(os.path.join(data_dir, "warranty_info.txt"), "r") as f:
            warranty_info = f.read()

        return DocumentBundle(
            vehicle_profile=vehicle_profile,
            driver_manual=driver_manual,
            insurance_card=insurance_card,
            maintenance_records=maintenance_records,
            warranty_info=warranty_info,
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
