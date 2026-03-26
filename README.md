# SE Knowledge Search

Unified search across Slack, Gong, Google Workspace, and Highspot for SE teams.

**Stop asking "Has anyone worked on X?" in Slack.** Search all your knowledge sources at once.

## What It Does

| Source | What You Can Find |
|--------|-------------------|
| **Slack** | Past discussions, Q&A threads, tribal knowledge |
| **Gong** | Customer call transcripts, objection handling, demo examples |
| **Google Workspace** | Docs, slides, sheets shared across the team |
| **Highspot** | Curated sales content, battle cards, pitch decks |

## Quick Start

### 1. Clone and Install

```bash
git clone git@github.com:wesseo/se-knowledge-search.git
cd se-knowledge-search
./setup.sh
```

### 2. Get API Credentials

| Service | Where to Get It |
|---------|-----------------|
| **Slack** | Extract `xoxc-` and `xoxd-` tokens from browser (see [Slack Setup](#slack-setup-detailed)) |
| **Gong** | Gong Admin → Company Settings → API → Create Key |
| **Highspot** | Highspot Admin → Integrations → API Keys |
| **Google Workspace** | Already configured via MCP connector |

### 3. Configure Environment

Copy the template and add your keys:

```bash
cp .env.template .env
# Edit .env with your actual API keys
```

### 4. Add to Claude Code

**Option A: Use the config script (recommended)**

```bash
# Edit .env with your credentials first
python configure-claude.py
```

**Option B: Manual config**

Add to `~/.claude.json`:

```json
{
  "mcpServers": {
    "slack": {
      "command": "npx",
      "args": ["-y", "@korotovsky/slack-mcp-server"],
      "env": {
        "SLACK_MCP_XOXC_TOKEN": "xoxc-...",
        "SLACK_MCP_XOXD_TOKEN": "xoxd-..."
      }
    },
    "gong": {
      "command": "uv",
      "args": ["--directory", "/path/to/se-knowledge-search", "run", "gong-mcp"],
      "env": {
        "GONG_ACCESS_KEY": "your-key",
        "GONG_ACCESS_KEY_SECRET": "your-secret"
      }
    },
    "highspot": {
      "command": "uv",
      "args": ["--directory", "/path/to/se-knowledge-search", "run", "highspot-mcp"],
      "env": {
        "HIGHSPOT_API_KEY": "your-key"
      }
    },
    "google-workspace": {
      "type": "http",
      "url": "https://mcp-proxy-534353623227.us-west1.run.app/mcp"
    }
  }
}
```

### 5. Restart Claude Code

```bash
# Verify MCPs are loaded
/mcp
```

## Usage

Just ask natural questions:

```
"Has anyone worked on a Snowflake integration?"

"Find me slides about our competitive positioning vs Segment"

"How do we usually handle the 'too expensive' objection?"

"Any docs on setting up SSO for enterprise customers?"

"What did we discuss with Acme Corp about their data warehouse?"
```

The search skill will automatically query the relevant sources and synthesize results.

## Available Tools

### Slack (via [@korotovsky/slack-mcp-server](https://github.com/korotovsky/slack-mcp-server))
- Search messages across channels
- Read DMs and group DMs
- Get unread messages
- Browse channel history
- Post messages (optional)

### Gong
- `gong.search_calls` - Search call transcripts by keyword
- `gong.get_call_transcript` - Get full transcript
- `gong.list_recent_calls` - Browse recent calls
- `gong.get_call_highlights` - Get AI-generated highlights

### Highspot
- `highspot.search` - Search all content
- `highspot.get_item` - Get item details
- `highspot.list_spots` - List content collections
- `highspot.get_spot_contents` - Browse a Spot
- `highspot.list_pitches` - List shared pitches

### Google Workspace
Uses the existing Google Workspace MCP connector for:
- Drive search
- Docs/Sheets/Slides access

## Slack Setup (Detailed)

Uses [@korotovsky/slack-mcp-server](https://github.com/korotovsky/slack-mcp-server) - the most feature-rich Slack MCP with DMs, search, unread messages, and no bot installation required.

### Extract Tokens from Browser

1. Open [slack.com](https://app.slack.com) in Chrome and log into your workspace
2. Open DevTools (F12) → **Application** tab → **Cookies**
3. Find and copy these two cookies:
   - `d` → This is your `SLACK_MCP_XOXD_TOKEN` (starts with `xoxd-`)
   - `ds` → ignore this one
4. Go to **Network** tab, filter by `api`, refresh the page
5. Click any `api.slack.com` request → **Headers** → find `token=xoxc-...` in the request
   - This is your `SLACK_MCP_XOXC_TOKEN`

### Add to .env

```bash
SLACK_MCP_XOXC_TOKEN=xoxc-your-token-here
SLACK_MCP_XOXD_TOKEN=xoxd-your-token-here
```

> **Note:** These are your personal user tokens. They give access to everything you can see in Slack. Keep them secure and don't share them.

For detailed instructions with screenshots, see: [github.com/korotovsky/slack-mcp-server](https://github.com/korotovsky/slack-mcp-server)

## Gong API Setup

1. You need Gong admin access
2. Go to Company Settings → API
3. Create a new API key
4. Save both the Access Key and Access Key Secret

## Troubleshooting

**Slack: "Invalid token" or authentication errors**
- Tokens expire when you log out of Slack in browser - re-extract them
- Make sure you copied the full token including the `xoxc-` or `xoxd-` prefix
- Check you're logged into the right workspace

**Gong returns empty results**
- Check date range - default is 90 days
- Verify the search terms appear in transcripts (not just call titles)
- You need Gong API access (admin must enable)

**Highspot: 401/403 errors**
- API key may have expired - generate a new one
- Check the key has read permissions

## Development

```bash
# Install dependencies
uv sync

# Run individual servers for testing
uv run gong-mcp
uv run highspot-mcp

# Test Slack MCP
npx @korotovsky/slack-mcp-server

# Lint
uv run ruff check src/
uv run ruff format src/
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       Claude Code                            │
│                  (with search skill)                         │
└──────────────────────────┬──────────────────────────────────┘
                           │ MCP Protocol
    ┌──────────┬───────────┼───────────┬───────────┐
    ▼          ▼           ▼           ▼           ▼
┌────────┐ ┌────────┐ ┌──────────┐ ┌──────────┐
│ Slack  │ │  Gong  │ │  Google  │ │ Highspot │
│  MCP   │ │  MCP   │ │Workspace │ │   MCP    │
│        │ │        │ │   MCP    │ │          │
└────────┘ └────────┘ └──────────┘ └──────────┘
```

## License

Internal use only.
