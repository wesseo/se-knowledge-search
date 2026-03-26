"""Slack MCP Server - Search messages and channels.

This is a simplified Slack MCP server focused on search use cases.
For a full-featured Slack MCP, see: https://github.com/modelcontextprotocol/servers/tree/main/src/slack
"""

import os

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

SLACK_BASE_URL = "https://slack.com/api"

server = Server("slack")


def get_auth_headers() -> dict[str, str]:
    """Get Slack API authentication headers."""
    token = os.environ.get("SLACK_BOT_TOKEN")

    if not token:
        raise ValueError(
            "SLACK_BOT_TOKEN environment variable required. "
            "Create a Slack app at api.slack.com/apps with these scopes: "
            "search:read, channels:read, channels:history, users:read"
        )

    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="slack.search_messages",
            description="Search Slack messages across all accessible channels. Use this to find discussions, Q&A, and tribal knowledge.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query. Supports Slack search syntax: 'from:@user', 'in:#channel', 'has:link', etc.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results to return",
                        "default": 20,
                    },
                    "sort": {
                        "type": "string",
                        "description": "Sort by 'score' (relevance) or 'timestamp' (recent first)",
                        "enum": ["score", "timestamp"],
                        "default": "score",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="slack.search_files",
            description="Search for files shared in Slack (docs, images, PDFs, etc.).",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for files",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results to return",
                        "default": 20,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="slack.get_channel_history",
            description="Get recent messages from a specific channel.",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel": {
                        "type": "string",
                        "description": "Channel name (without #) or channel ID",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of messages to retrieve",
                        "default": 50,
                    },
                },
                "required": ["channel"],
            },
        ),
        Tool(
            name="slack.list_channels",
            description="List public Slack channels.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results to return",
                        "default": 100,
                    },
                },
            },
        ),
        Tool(
            name="slack.get_thread",
            description="Get all replies in a thread given the channel and thread timestamp.",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel": {
                        "type": "string",
                        "description": "Channel ID",
                    },
                    "thread_ts": {
                        "type": "string",
                        "description": "Thread timestamp (ts of the parent message)",
                    },
                },
                "required": ["channel", "thread_ts"],
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
            if name == "slack.search_messages":
                return await search_messages(client, headers, arguments)
            elif name == "slack.search_files":
                return await search_files(client, headers, arguments)
            elif name == "slack.get_channel_history":
                return await get_channel_history(client, headers, arguments)
            elif name == "slack.list_channels":
                return await list_channels(client, headers, arguments)
            elif name == "slack.get_thread":
                return await get_thread(client, headers, arguments)
            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]
        except httpx.HTTPStatusError as e:
            return [TextContent(type="text", text=f"Slack API error: {e.response.status_code} - {e.response.text}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {e}")]


async def search_messages(
    client: httpx.AsyncClient, headers: dict, arguments: dict
) -> list[TextContent]:
    """Search Slack messages."""
    query = arguments["query"]
    limit = arguments.get("limit", 20)
    sort = arguments.get("sort", "score")

    resp = await client.get(
        f"{SLACK_BASE_URL}/search.messages",
        headers=headers,
        params={
            "query": query,
            "count": limit,
            "sort": sort,
            "sort_dir": "desc",
        },
    )
    resp.raise_for_status()
    data = resp.json()

    if not data.get("ok"):
        return [TextContent(type="text", text=f"Slack error: {data.get('error', 'Unknown error')}")]

    messages = data.get("messages", {}).get("matches", [])

    if not messages:
        return [TextContent(type="text", text=f"No messages found matching '{query}'")]

    # Cache for user names
    user_cache = {}

    async def get_user_name(user_id: str) -> str:
        if user_id in user_cache:
            return user_cache[user_id]
        try:
            user_resp = await client.get(
                f"{SLACK_BASE_URL}/users.info",
                headers=headers,
                params={"user": user_id},
            )
            if user_resp.status_code == 200:
                user_data = user_resp.json()
                if user_data.get("ok"):
                    name = user_data["user"].get("real_name", user_data["user"].get("name", user_id))
                    user_cache[user_id] = name
                    return name
        except Exception:
            pass
        return user_id

    results = []
    for msg in messages:
        channel_name = msg.get("channel", {}).get("name", "unknown")
        user_id = msg.get("user", "unknown")
        user_name = await get_user_name(user_id) if user_id != "unknown" else "Unknown"
        text = msg.get("text", "")[:500]
        ts = msg.get("ts", "")
        permalink = msg.get("permalink", "")

        # Format timestamp
        from datetime import datetime
        try:
            dt = datetime.fromtimestamp(float(ts))
            date_str = dt.strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            date_str = "Unknown date"

        results.append(
            f"**#{channel_name}** - {user_name} ({date_str})\n"
            f"{text}\n"
            f"[View in Slack]({permalink})"
        )

    output = f"Found {len(messages)} messages matching '{query}':\n\n" + "\n\n---\n\n".join(results)
    return [TextContent(type="text", text=output)]


async def search_files(
    client: httpx.AsyncClient, headers: dict, arguments: dict
) -> list[TextContent]:
    """Search Slack files."""
    query = arguments["query"]
    limit = arguments.get("limit", 20)

    resp = await client.get(
        f"{SLACK_BASE_URL}/search.files",
        headers=headers,
        params={
            "query": query,
            "count": limit,
        },
    )
    resp.raise_for_status()
    data = resp.json()

    if not data.get("ok"):
        return [TextContent(type="text", text=f"Slack error: {data.get('error', 'Unknown error')}")]

    files = data.get("files", {}).get("matches", [])

    if not files:
        return [TextContent(type="text", text=f"No files found matching '{query}'")]

    results = []
    for f in files:
        name = f.get("name", "Untitled")
        title = f.get("title", name)
        filetype = f.get("filetype", "unknown")
        url = f.get("permalink", "")
        user = f.get("user", "Unknown")
        created = f.get("created", 0)

        from datetime import datetime
        try:
            date_str = datetime.fromtimestamp(created).strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            date_str = "Unknown date"

        results.append(
            f"- **{title}** ({filetype})\n"
            f"  Shared by: {user} on {date_str}\n"
            f"  [View file]({url})"
        )

    output = f"Found {len(files)} files matching '{query}':\n\n" + "\n\n".join(results)
    return [TextContent(type="text", text=output)]


async def get_channel_history(
    client: httpx.AsyncClient, headers: dict, arguments: dict
) -> list[TextContent]:
    """Get channel message history."""
    channel = arguments["channel"]
    limit = arguments.get("limit", 50)

    # If channel is a name, look up the ID
    if not channel.startswith("C"):
        channels_resp = await client.get(
            f"{SLACK_BASE_URL}/conversations.list",
            headers=headers,
            params={"types": "public_channel,private_channel", "limit": 1000},
        )
        if channels_resp.status_code == 200:
            channels_data = channels_resp.json()
            if channels_data.get("ok"):
                for ch in channels_data.get("channels", []):
                    if ch.get("name") == channel.lstrip("#"):
                        channel = ch["id"]
                        break

    resp = await client.get(
        f"{SLACK_BASE_URL}/conversations.history",
        headers=headers,
        params={
            "channel": channel,
            "limit": limit,
        },
    )
    resp.raise_for_status()
    data = resp.json()

    if not data.get("ok"):
        return [TextContent(type="text", text=f"Slack error: {data.get('error', 'Unknown error')}")]

    messages = data.get("messages", [])

    if not messages:
        return [TextContent(type="text", text=f"No messages found in channel")]

    results = []
    for msg in messages:
        user = msg.get("user", "Unknown")
        text = msg.get("text", "")[:500]
        ts = msg.get("ts", "")
        thread_ts = msg.get("thread_ts")
        reply_count = msg.get("reply_count", 0)

        from datetime import datetime
        try:
            dt = datetime.fromtimestamp(float(ts))
            date_str = dt.strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            date_str = "Unknown"

        thread_info = f" ({reply_count} replies)" if reply_count > 0 else ""
        results.append(f"[{date_str}] {user}: {text}{thread_info}")

    return [TextContent(type="text", text="\n\n".join(results))]


async def list_channels(
    client: httpx.AsyncClient, headers: dict, arguments: dict
) -> list[TextContent]:
    """List Slack channels."""
    limit = arguments.get("limit", 100)

    resp = await client.get(
        f"{SLACK_BASE_URL}/conversations.list",
        headers=headers,
        params={
            "types": "public_channel",
            "limit": limit,
            "exclude_archived": True,
        },
    )
    resp.raise_for_status()
    data = resp.json()

    if not data.get("ok"):
        return [TextContent(type="text", text=f"Slack error: {data.get('error', 'Unknown error')}")]

    channels = data.get("channels", [])

    if not channels:
        return [TextContent(type="text", text="No channels found")]

    results = []
    for ch in channels:
        name = ch.get("name", "unknown")
        purpose = ch.get("purpose", {}).get("value", "")[:100]
        member_count = ch.get("num_members", 0)
        channel_id = ch.get("id", "")

        results.append(f"- **#{name}** (ID: {channel_id}) - {member_count} members\n  {purpose}")

    return [TextContent(type="text", text=f"Channels:\n\n" + "\n\n".join(results))]


async def get_thread(
    client: httpx.AsyncClient, headers: dict, arguments: dict
) -> list[TextContent]:
    """Get thread replies."""
    channel = arguments["channel"]
    thread_ts = arguments["thread_ts"]

    resp = await client.get(
        f"{SLACK_BASE_URL}/conversations.replies",
        headers=headers,
        params={
            "channel": channel,
            "ts": thread_ts,
        },
    )
    resp.raise_for_status()
    data = resp.json()

    if not data.get("ok"):
        return [TextContent(type="text", text=f"Slack error: {data.get('error', 'Unknown error')}")]

    messages = data.get("messages", [])

    if not messages:
        return [TextContent(type="text", text="No messages found in thread")]

    results = []
    for msg in messages:
        user = msg.get("user", "Unknown")
        text = msg.get("text", "")
        ts = msg.get("ts", "")

        from datetime import datetime
        try:
            dt = datetime.fromtimestamp(float(ts))
            date_str = dt.strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            date_str = "Unknown"

        results.append(f"[{date_str}] {user}:\n{text}")

    return [TextContent(type="text", text="\n\n---\n\n".join(results))]


async def run():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main():
    import asyncio
    asyncio.run(run())


if __name__ == "__main__":
    main()
