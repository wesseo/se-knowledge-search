"""Gong MCP Server - Search call transcripts and recordings."""

import os
from datetime import datetime, timedelta

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

GONG_BASE_URL = "https://api.gong.io/v2"

server = Server("gong")


def get_auth_headers() -> dict[str, str]:
    """Get Gong API authentication headers."""
    access_key = os.environ.get("GONG_ACCESS_KEY")
    access_secret = os.environ.get("GONG_ACCESS_KEY_SECRET")

    if not access_key or not access_secret:
        raise ValueError(
            "GONG_ACCESS_KEY and GONG_ACCESS_KEY_SECRET environment variables required. "
            "Get these from Gong Admin > Company Settings > API."
        )

    import base64

    credentials = base64.b64encode(f"{access_key}:{access_secret}".encode()).decode()
    return {
        "Authorization": f"Basic {credentials}",
        "Content-Type": "application/json",
    }


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="gong.search_calls",
            description="Search Gong call transcripts for keywords or topics. Returns calls where the search terms appear in the transcript.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search terms to find in call transcripts",
                    },
                    "from_date": {
                        "type": "string",
                        "description": "Start date (ISO format, e.g., 2024-01-01). Defaults to 90 days ago.",
                    },
                    "to_date": {
                        "type": "string",
                        "description": "End date (ISO format). Defaults to today.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results to return",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="gong.get_call_transcript",
            description="Get the full transcript for a specific Gong call by ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "call_id": {
                        "type": "string",
                        "description": "The Gong call ID",
                    },
                },
                "required": ["call_id"],
            },
        ),
        Tool(
            name="gong.list_recent_calls",
            description="List recent Gong calls, optionally filtered by participant email.",
            inputSchema={
                "type": "object",
                "properties": {
                    "participant_email": {
                        "type": "string",
                        "description": "Filter to calls with this participant",
                    },
                    "days_back": {
                        "type": "integer",
                        "description": "Number of days to look back",
                        "default": 30,
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results to return",
                        "default": 20,
                    },
                },
            },
        ),
        Tool(
            name="gong.get_call_highlights",
            description="Get AI-generated highlights and key points from a call.",
            inputSchema={
                "type": "object",
                "properties": {
                    "call_id": {
                        "type": "string",
                        "description": "The Gong call ID",
                    },
                },
                "required": ["call_id"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        headers = get_auth_headers()
    except ValueError as e:
        return [TextContent(type="text", text=f"Authentication error: {e}")]

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            if name == "gong.search_calls":
                return await search_calls(client, headers, arguments)
            elif name == "gong.get_call_transcript":
                return await get_call_transcript(client, headers, arguments)
            elif name == "gong.list_recent_calls":
                return await list_recent_calls(client, headers, arguments)
            elif name == "gong.get_call_highlights":
                return await get_call_highlights(client, headers, arguments)
            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]
        except httpx.HTTPStatusError as e:
            return [TextContent(type="text", text=f"Gong API error: {e.response.status_code} - {e.response.text}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {e}")]


async def search_calls(
    client: httpx.AsyncClient, headers: dict, arguments: dict
) -> list[TextContent]:
    """Search call transcripts for keywords."""
    query = arguments["query"]
    limit = arguments.get("limit", 10)

    # Calculate date range
    to_date = arguments.get("to_date") or datetime.now().strftime("%Y-%m-%dT23:59:59Z")
    if arguments.get("from_date"):
        from_date = arguments["from_date"]
        if "T" not in from_date:
            from_date = f"{from_date}T00:00:00Z"
    else:
        from_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%dT00:00:00Z")

    if "T" not in to_date:
        to_date = f"{to_date}T23:59:59Z"

    # Search transcripts using Gong's content search API
    payload = {
        "filter": {
            "fromDateTime": from_date,
            "toDateTime": to_date,
        },
        "contentSelector": {
            "exposedFields": {
                "content": {
                    "trackers": [query]
                }
            }
        },
    }

    resp = await client.post(
        f"{GONG_BASE_URL}/calls/transcript",
        headers=headers,
        json=payload,
    )
    resp.raise_for_status()
    data = resp.json()

    calls = data.get("callTranscripts", [])[:limit]

    if not calls:
        return [TextContent(type="text", text=f"No calls found matching '{query}' in the specified date range.")]

    results = []
    for call in calls:
        call_id = call.get("callId", "unknown")
        # Get call metadata
        meta_resp = await client.post(
            f"{GONG_BASE_URL}/calls/extensive",
            headers=headers,
            json={"filter": {"callIds": [call_id]}},
        )
        if meta_resp.status_code == 200:
            meta_data = meta_resp.json()
            call_meta = meta_data.get("calls", [{}])[0] if meta_data.get("calls") else {}
            title = call_meta.get("title", "Untitled Call")
            started = call_meta.get("started", "Unknown date")
            participants = [p.get("name", p.get("emailAddress", "Unknown")) for p in call_meta.get("participants", [])]
        else:
            title = "Untitled Call"
            started = "Unknown date"
            participants = []

        # Extract relevant transcript snippets
        transcript = call.get("transcript", [])
        snippets = []
        for segment in transcript:
            text = segment.get("text", "")
            if query.lower() in text.lower():
                speaker = segment.get("speakerName", "Unknown")
                snippets.append(f"  [{speaker}]: {text[:200]}...")

        results.append(
            f"**{title}** (ID: {call_id})\n"
            f"  Date: {started}\n"
            f"  Participants: {', '.join(participants[:5])}\n"
            f"  Matching excerpts:\n" + "\n".join(snippets[:3])
        )

    output = f"Found {len(calls)} calls matching '{query}':\n\n" + "\n\n".join(results)
    return [TextContent(type="text", text=output)]


async def get_call_transcript(
    client: httpx.AsyncClient, headers: dict, arguments: dict
) -> list[TextContent]:
    """Get full transcript for a call."""
    call_id = arguments["call_id"]

    resp = await client.post(
        f"{GONG_BASE_URL}/calls/transcript",
        headers=headers,
        json={"filter": {"callIds": [call_id]}},
    )
    resp.raise_for_status()
    data = resp.json()

    calls = data.get("callTranscripts", [])
    if not calls:
        return [TextContent(type="text", text=f"No transcript found for call {call_id}")]

    transcript = calls[0].get("transcript", [])
    lines = []
    for segment in transcript:
        speaker = segment.get("speakerName", "Unknown")
        text = segment.get("text", "")
        lines.append(f"[{speaker}]: {text}")

    return [TextContent(type="text", text="\n".join(lines))]


async def list_recent_calls(
    client: httpx.AsyncClient, headers: dict, arguments: dict
) -> list[TextContent]:
    """List recent calls."""
    days_back = arguments.get("days_back", 30)
    limit = arguments.get("limit", 20)
    participant_email = arguments.get("participant_email")

    from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%dT00:00:00Z")
    to_date = datetime.now().strftime("%Y-%m-%dT23:59:59Z")

    payload = {
        "filter": {
            "fromDateTime": from_date,
            "toDateTime": to_date,
        }
    }

    resp = await client.post(
        f"{GONG_BASE_URL}/calls/extensive",
        headers=headers,
        json=payload,
    )
    resp.raise_for_status()
    data = resp.json()

    calls = data.get("calls", [])

    # Filter by participant if specified
    if participant_email:
        calls = [
            c for c in calls
            if any(
                p.get("emailAddress", "").lower() == participant_email.lower()
                for p in c.get("participants", [])
            )
        ]

    calls = calls[:limit]

    if not calls:
        return [TextContent(type="text", text="No calls found in the specified range.")]

    results = []
    for call in calls:
        call_id = call.get("id", "unknown")
        title = call.get("title", "Untitled")
        started = call.get("started", "Unknown")
        duration = call.get("duration", 0)
        participants = [
            p.get("name", p.get("emailAddress", "Unknown"))
            for p in call.get("participants", [])
        ]

        results.append(
            f"- **{title}** (ID: {call_id})\n"
            f"  Date: {started}, Duration: {duration // 60} min\n"
            f"  Participants: {', '.join(participants[:5])}"
        )

    return [TextContent(type="text", text=f"Recent calls:\n\n" + "\n\n".join(results))]


async def get_call_highlights(
    client: httpx.AsyncClient, headers: dict, arguments: dict
) -> list[TextContent]:
    """Get call highlights and key points."""
    call_id = arguments["call_id"]

    # Get call details with key points
    resp = await client.post(
        f"{GONG_BASE_URL}/calls/extensive",
        headers=headers,
        json={
            "filter": {"callIds": [call_id]},
            "contentSelector": {
                "exposedFields": {
                    "keyPoints": True,
                    "outline": True,
                    "highlights": True,
                    "trackers": True,
                }
            },
        },
    )
    resp.raise_for_status()
    data = resp.json()

    calls = data.get("calls", [])
    if not calls:
        return [TextContent(type="text", text=f"No call found with ID {call_id}")]

    call = calls[0]
    title = call.get("title", "Untitled")

    # Format highlights
    output_parts = [f"**{title}**\n"]

    key_points = call.get("keyPoints", [])
    if key_points:
        output_parts.append("\n**Key Points:**")
        for kp in key_points:
            output_parts.append(f"- {kp.get('text', '')}")

    outline = call.get("outline", [])
    if outline:
        output_parts.append("\n**Outline:**")
        for item in outline:
            output_parts.append(f"- {item.get('text', '')}")

    trackers = call.get("trackers", [])
    if trackers:
        output_parts.append("\n**Topics Detected:**")
        for tracker in trackers:
            output_parts.append(f"- {tracker.get('name', '')}: {tracker.get('count', 0)} mentions")

    return [TextContent(type="text", text="\n".join(output_parts))]


async def run():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main():
    import asyncio
    asyncio.run(run())


if __name__ == "__main__":
    main()
