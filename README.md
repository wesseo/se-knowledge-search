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
git clone git@github.com:amperity/se-knowledge-search.git
cd se-knowledge-search
./setup.sh
```

### 2. Get API Credentials

| Service | Where to Get It |
|---------|-----------------|
| **Slack** | [api.slack.com/apps](https://api.slack.com/apps) → Create App → OAuth & Permissions → Bot Token |
| **Gong** | Gong Admin → Company Settings → API → Create Key |
| **Highspot** | Highspot Admin → Integrations → API Keys |
| **Google Workspace** | Already configured via MCP connector (see below) |

### 3. Configure Environment

Copy the template and add your keys:

```bash
cp .env.template .env
# Edit .env with your actual API keys
```

### 4. Add to Claude Code

**Option A: CLI (recommended)**

```bash
# Export your env vars first (or add to shell profile)
export SLACK_BOT_TOKEN="xoxb-..."
export GONG_ACCESS_KEY="..."
export GONG_ACCESS_KEY_SECRET="..."
export HIGHSPOT_API_KEY="..."

# Add each MCP server
claude mcp add --scope user slack -- uv --directory /path/to/se-knowledge-search run slack-mcp
claude mcp add --scope user gong -- uv --directory /path/to/se-knowledge-search run gong-mcp
claude mcp add --scope user highspot -- uv --directory /path/to/se-knowledge-search run highspot-mcp
```

**Option B: Manual config**

Add to `~/.claude.json`:

```json
{
  "mcpServers": {
    "slack": {
      "command": "uv",
      "args": ["--directory", "/path/to/se-knowledge-search", "run", "slack-mcp"],
      "env": {
        "SLACK_BOT_TOKEN": "xoxb-your-token"
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

### Slack
- `slack.search_messages` - Search all accessible channels
- `slack.search_files` - Find shared files
- `slack.get_channel_history` - Browse recent channel messages
- `slack.list_channels` - List available channels
- `slack.get_thread` - Get full thread context

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

## Slack App Setup (Detailed)

### Option A: Use the Manifest (Easiest)

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click **"Create New App"** → **"From an app manifest"**
3. Select your workspace
4. Paste the contents of `slack-app-manifest.yaml` from this repo
5. Click **"Create"**
6. Click **"Install to Workspace"** and approve
7. Go to **"OAuth & Permissions"** → Copy the **Bot User OAuth Token** (starts with `xoxb-`)

### Option B: Manual Setup

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click "Create New App" → "From scratch"
3. Name it "SE Knowledge Search" and select your workspace
4. Go to "OAuth & Permissions"
5. Add these **Bot Token Scopes**:
   - `search:read` - Search messages and files
   - `channels:read` - List channels
   - `channels:history` - Read channel messages
   - `groups:read` - List private channels (optional)
   - `groups:history` - Read private channel messages (optional)
   - `users:read` - Get user names
   - `files:read` - Read shared files
6. Click "Install to Workspace"
7. Copy the **Bot User OAuth Token** (starts with `xoxb-`)

## Gong API Setup

1. You need Gong admin access
2. Go to Company Settings → API
3. Create a new API key
4. Save both the Access Key and Access Key Secret

## Troubleshooting

**"Authentication error: SLACK_BOT_TOKEN..."**
- Make sure the env var is set and exported
- Check the token starts with `xoxb-`

**"Slack error: missing_scope"**
- Your Slack app is missing required scopes
- Go back to OAuth & Permissions and add the missing scope
- Reinstall the app to your workspace

**"No messages found"**
- The bot can only search channels it has access to
- Invite the bot to relevant channels: `/invite @SE Knowledge Search`

**Gong returns empty results**
- Check date range - default is 90 days
- Verify the search terms appear in transcripts (not just call titles)

## Development

```bash
# Install dependencies
uv sync

# Run individual servers for testing
uv run slack-mcp
uv run gong-mcp
uv run highspot-mcp

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
