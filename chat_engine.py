"""
chat_engine.py — Streams Claude responses with on-demand MCP tool calling.

Instead of pre-loading all documents, Claude discovers available MCP tools
and selectively calls them based on what the user asks. The flow is:

1. User asks a question
2. Claude sees the available tools (get_maintenance_records, get_warranty_info, etc.)
3. Claude decides which tools to call based on the question
4. We execute those tool calls against the MCP server
5. Claude incorporates the results and responds
"""

import asyncio
import os
from datetime import date
from typing import Generator

import anthropic
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from vehicle_info import VehicleInfo

load_dotenv()

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1024
MAX_TOOL_ROUNDS = 10

MCP_URL = os.environ["MCP_URL"]

# ── MCP helpers ───────────────────────────────────────────────────────────────

def _mcp_tool_to_claude_tool(tool) -> dict:
    """Convert an MCP tool definition to Claude's tool format."""
    return {
        "name": tool.name,
        "description": tool.description or "",
        "input_schema": tool.inputSchema,
    }

async def _list_mcp_tools() -> list[dict]:
    """Connect to MCP, list available tools, return as Claude tool defs."""
    async with streamable_http_client(MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await asyncio.wait_for(session.initialize(), timeout=10)
            result = await session.list_tools()
            return [_mcp_tool_to_claude_tool(t) for t in result.tools]

async def _call_mcp_tool(name: str, arguments: dict) -> str:
    """Call a single MCP tool and return the text result."""
    async with streamable_http_client(MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await asyncio.wait_for(session.initialize(), timeout=10)
            result = await asyncio.wait_for(
                session.call_tool(name, arguments=arguments),
                timeout=30,
            )
            if result.isError:
                return f"Error: {result.content[0].text if result.content else 'Unknown'}"
            part = result.content[0]
            return part.text if hasattr(part, "text") else str(part)

# ── System prompt ─────────────────────────────────────────────────────────────

def build_system_prompt(info: VehicleInfo) -> str:
    """
    System prompt WITHOUT pre-loaded documents. Claude will fetch what it
    needs via tools. The prompt tells Claude the driver/vehicle IDs so it
    can pass them as arguments.
    """
    today = date.today().strftime("%B %d, %Y")

    return f"""You are a personal vehicle assistant for {info.driver_name}. You have access to tools that can retrieve their vehicle documents on demand.

AVAILABLE DOCUMENT TOOLS:
- get_vehicle_profile: Vehicle specs, VIN, mileage, registration info
- get_driver_manual: Maintenance schedules, operating instructions, fluid specs
- get_insurance_info: Coverage types, deductibles, limits, contacts
- get_maintenance_records: Past services, dates, mileages
- get_warranty_info: What's covered, expiration dates, terms

TOOL USAGE:
- Always use driver_id="{info.driver_id}" and car_id="{info.car_id}" when calling tools.
- Only fetch the documents you actually need to answer the question.
- For maintenance timing questions, you'll likely need BOTH maintenance_records AND driver_manual.
- For warranty coverage questions, you may need BOTH warranty_info AND vehicle_profile.
- If unsure which document has the answer, start with the most likely one.

BEHAVIORAL GUIDELINES:
- Answer questions conversationally but precisely.
- When answering maintenance timing questions, always show your math: state the last service mileage, add the interval from the manual, subtract current mileage to get miles remaining.
- Always cite which document your answer comes from (e.g., "According to your maintenance records..." or "Your insurance card shows...").
- If a question spans multiple documents, combine the information and say so.
- If the answer is "no" or "not covered," say so clearly — don't hedge.
- Keep responses concise. Use bullet points for lists of items.
- If the driver asks about something not covered in their documents, say so rather than guessing.

GROUNDING FACTS (use these for all date and mileage calculations):
- Today's date: {today}
- {info.driver_name}'s current vehicle mileage: {info.current_mileage:,} miles"""

# ── Chat streaming with tool-calling loop ─────────────────────────────────────

def stream_chat_response(
    messages: list[dict],
    info: VehicleInfo,
) -> Generator[str, None, None]:
    """
    Streams Claude's response, handling MCP tool calls in a loop.

    Flow:
    1. Send messages + tool definitions to Claude
    2. If Claude wants to call tools → execute via MCP → send results back
    3. Repeat until Claude produces a final text response
    4. Yield the final text

    Args:
        messages: Conversation history as list of {"role": ..., "content": ...} dicts.
        info:     VehicleInfo with driver/vehicle IDs, name, mileage, etc.

    Yields:
        Text chunks from Claude's final response.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY not found. "
            "Create a .env file with ANTHROPIC_API_KEY=your_key_here "
            "(see .env.example)."
        )

    client = anthropic.Anthropic(api_key=api_key)
    system_prompt = build_system_prompt(info)

    # Discover available tools from MCP server
    claude_tools = asyncio.run(_list_mcp_tools())

    current_messages = list(messages)

    # Tool-calling loop: Claude may request tools across multiple rounds
    for _ in range(MAX_TOOL_ROUNDS):
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system_prompt,
            tools=claude_tools,
            messages=current_messages,
        )

        # If Claude didn't request any tools, this is the final response
        if response.stop_reason != "tool_use":
            for block in response.content:
                if hasattr(block, "text"):
                    yield block.text
            return

        # Claude wants to use tools — add its response to the conversation
        # Serialize content blocks to dicts for the message history
        assistant_content = []
        for block in response.content:
            if block.type == "text":
                assistant_content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                assistant_content.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })

        current_messages.append({"role": "assistant", "content": assistant_content})

        # Execute each tool call via MCP
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result_text = asyncio.run(
                    _call_mcp_tool(block.name, block.input)
                )
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_text,
                })

        current_messages.append({"role": "user", "content": tool_results})

    # Safety fallback if max rounds exceeded
    yield "I'm having trouble retrieving the information. Please try again."