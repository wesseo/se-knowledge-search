"""Highspot MCP Server - Search sales enablement content."""

import os

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

# Highspot API base URL
HIGHSPOT_BASE_URL = "https://api.highspot.com/v2"

server = Server("highspot")


def get_auth_headers() -> dict[str, str]:
    """Get Highspot API authentication headers."""
    api_key = os.environ.get("HIGHSPOT_API_KEY")

    if not api_key:
        raise ValueError(
            "HIGHSPOT_API_KEY environment variable required. "
            "Get this from Highspot Admin > Integrations > API Keys."
        )

    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="highspot.search",
            description="Search Highspot for sales content (pitches, slides, documents, videos). Returns matching content with titles, descriptions, and links.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search terms to find content",
                    },
                    "content_type": {
                        "type": "string",
                        "description": "Filter by type: document, video, pitch, all",
                        "enum": ["document", "video", "pitch", "all"],
                        "default": "all",
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
            name="highspot.get_item",
            description="Get details about a specific Highspot item by ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "string",
                        "description": "The Highspot item ID",
                    },
                },
                "required": ["item_id"],
            },
        ),
        Tool(
            name="highspot.list_spots",
            description="List Highspot Spots (content collections/folders).",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results to return",
                        "default": 20,
                    },
                },
            },
        ),
        Tool(
            name="highspot.get_spot_contents",
            description="Get all content items in a specific Spot.",
            inputSchema={
                "type": "object",
                "properties": {
                    "spot_id": {
                        "type": "string",
                        "description": "The Spot ID",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results to return",
                        "default": 50,
                    },
                },
                "required": ["spot_id"],
            },
        ),
        Tool(
            name="highspot.list_pitches",
            description="List recent pitches (curated content shared with prospects).",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results to return",
                        "default": 20,
                    },
                },
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
            if name == "highspot.search":
                return await search_content(client, headers, arguments)
            elif name == "highspot.get_item":
                return await get_item(client, headers, arguments)
            elif name == "highspot.list_spots":
                return await list_spots(client, headers, arguments)
            elif name == "highspot.get_spot_contents":
                return await get_spot_contents(client, headers, arguments)
            elif name == "highspot.list_pitches":
                return await list_pitches(client, headers, arguments)
            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]
        except httpx.HTTPStatusError as e:
            return [TextContent(type="text", text=f"Highspot API error: {e.response.status_code} - {e.response.text}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {e}")]


async def search_content(
    client: httpx.AsyncClient, headers: dict, arguments: dict
) -> list[TextContent]:
    """Search Highspot content."""
    query = arguments["query"]
    content_type = arguments.get("content_type", "all")
    limit = arguments.get("limit", 10)

    params = {
        "q": query,
        "limit": limit,
    }

    if content_type != "all":
        params["type"] = content_type

    resp = await client.get(
        f"{HIGHSPOT_BASE_URL}/items/search",
        headers=headers,
        params=params,
    )
    resp.raise_for_status()
    data = resp.json()

    items = data.get("items", [])

    if not items:
        return [TextContent(type="text", text=f"No content found matching '{query}'")]

    results = []
    for item in items:
        item_id = item.get("id", "unknown")
        title = item.get("title", "Untitled")
        description = item.get("description", "No description")[:200]
        item_type = item.get("type", "unknown")
        url = item.get("webUrl", "")
        owner = item.get("owner", {}).get("name", "Unknown")
        updated = item.get("updatedAt", "Unknown")

        results.append(
            f"- **{title}** ({item_type})\n"
            f"  ID: {item_id}\n"
            f"  Description: {description}\n"
            f"  Owner: {owner}, Updated: {updated}\n"
            f"  URL: {url}"
        )

    output = f"Found {len(items)} items matching '{query}':\n\n" + "\n\n".join(results)
    return [TextContent(type="text", text=output)]


async def get_item(
    client: httpx.AsyncClient, headers: dict, arguments: dict
) -> list[TextContent]:
    """Get item details."""
    item_id = arguments["item_id"]

    resp = await client.get(
        f"{HIGHSPOT_BASE_URL}/items/{item_id}",
        headers=headers,
    )
    resp.raise_for_status()
    item = resp.json()

    title = item.get("title", "Untitled")
    description = item.get("description", "No description")
    item_type = item.get("type", "unknown")
    url = item.get("webUrl", "")
    owner = item.get("owner", {}).get("name", "Unknown")
    created = item.get("createdAt", "Unknown")
    updated = item.get("updatedAt", "Unknown")
    tags = item.get("tags", [])
    spots = [s.get("name", "Unknown") for s in item.get("spots", [])]

    output = f"""**{title}**

Type: {item_type}
ID: {item_id}

**Description:**
{description}

**Metadata:**
- Owner: {owner}
- Created: {created}
- Updated: {updated}
- Tags: {', '.join(tags) if tags else 'None'}
- Spots: {', '.join(spots) if spots else 'None'}

**URL:** {url}
"""

    return [TextContent(type="text", text=output)]


async def list_spots(
    client: httpx.AsyncClient, headers: dict, arguments: dict
) -> list[TextContent]:
    """List Highspot Spots."""
    limit = arguments.get("limit", 20)

    resp = await client.get(
        f"{HIGHSPOT_BASE_URL}/spots",
        headers=headers,
        params={"limit": limit},
    )
    resp.raise_for_status()
    data = resp.json()

    spots = data.get("spots", [])

    if not spots:
        return [TextContent(type="text", text="No Spots found.")]

    results = []
    for spot in spots:
        spot_id = spot.get("id", "unknown")
        name = spot.get("name", "Unnamed")
        description = spot.get("description", "No description")[:100]
        item_count = spot.get("itemCount", 0)

        results.append(
            f"- **{name}** (ID: {spot_id})\n"
            f"  {description}\n"
            f"  Items: {item_count}"
        )

    return [TextContent(type="text", text=f"Spots:\n\n" + "\n\n".join(results))]


async def get_spot_contents(
    client: httpx.AsyncClient, headers: dict, arguments: dict
) -> list[TextContent]:
    """Get contents of a Spot."""
    spot_id = arguments["spot_id"]
    limit = arguments.get("limit", 50)

    resp = await client.get(
        f"{HIGHSPOT_BASE_URL}/spots/{spot_id}/items",
        headers=headers,
        params={"limit": limit},
    )
    resp.raise_for_status()
    data = resp.json()

    items = data.get("items", [])

    if not items:
        return [TextContent(type="text", text=f"No items found in Spot {spot_id}")]

    results = []
    for item in items:
        item_id = item.get("id", "unknown")
        title = item.get("title", "Untitled")
        item_type = item.get("type", "unknown")
        url = item.get("webUrl", "")

        results.append(f"- **{title}** ({item_type}) - ID: {item_id}\n  {url}")

    return [TextContent(type="text", text=f"Items in Spot:\n\n" + "\n".join(results))]


async def list_pitches(
    client: httpx.AsyncClient, headers: dict, arguments: dict
) -> list[TextContent]:
    """List recent pitches."""
    limit = arguments.get("limit", 20)

    resp = await client.get(
        f"{HIGHSPOT_BASE_URL}/pitches",
        headers=headers,
        params={"limit": limit},
    )
    resp.raise_for_status()
    data = resp.json()

    pitches = data.get("pitches", [])

    if not pitches:
        return [TextContent(type="text", text="No pitches found.")]

    results = []
    for pitch in pitches:
        pitch_id = pitch.get("id", "unknown")
        name = pitch.get("name", "Unnamed")
        created_by = pitch.get("createdBy", {}).get("name", "Unknown")
        created = pitch.get("createdAt", "Unknown")
        views = pitch.get("viewCount", 0)
        url = pitch.get("webUrl", "")

        results.append(
            f"- **{name}** (ID: {pitch_id})\n"
            f"  Created by: {created_by} on {created}\n"
            f"  Views: {views}\n"
            f"  URL: {url}"
        )

    return [TextContent(type="text", text=f"Recent Pitches:\n\n" + "\n\n".join(results))]


async def run():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main():
    import asyncio
    asyncio.run(run())


if __name__ == "__main__":
    main()
