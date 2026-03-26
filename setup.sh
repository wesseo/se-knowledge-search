#!/bin/bash
# SE Knowledge Search - Setup Script
# Run this to configure MCP servers for Claude Code

set -e

echo "🔍 SE Knowledge Search - Setup"
echo "=============================="
echo ""

# Check for uv
if ! command -v uv &> /dev/null; then
    echo "❌ 'uv' package manager not found. Install it first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Get the directory where this script lives
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "📦 Installing dependencies..."
cd "$SCRIPT_DIR"
uv sync

echo ""
echo "🔑 API Credentials Required"
echo "==========================="
echo ""
echo "You'll need API keys for each service. Here's how to get them:"
echo ""
echo "1. SLACK_BOT_TOKEN"
echo "   → Create app at https://api.slack.com/apps"
echo "   → Add scopes: search:read, channels:read, channels:history, users:read"
echo "   → Install to workspace and copy Bot Token"
echo ""
echo "2. GONG_ACCESS_KEY and GONG_ACCESS_KEY_SECRET"
echo "   → Gong Admin → Company Settings → API"
echo "   → Create new API key"
echo ""
echo "3. HIGHSPOT_API_KEY"
echo "   → Highspot Admin → Integrations → API Keys"
echo "   → Generate new key"
echo ""
echo "4. GOOGLE_WORKSPACE (already configured via MCP connector)"
echo "   → Should work if you have google-workspace MCP set up"
echo ""

# Create env template
cat > "$SCRIPT_DIR/.env.template" << 'EOF'
# SE Knowledge Search - Environment Variables
# Copy this to .env and fill in your values

# Slack Bot Token (starts with xoxb-)
SLACK_BOT_TOKEN=xoxb-your-token-here

# Gong API credentials
GONG_ACCESS_KEY=your-access-key
GONG_ACCESS_KEY_SECRET=your-secret-key

# Highspot API key
HIGHSPOT_API_KEY=your-api-key
EOF

echo "📝 Created .env.template - copy to .env and add your keys"
echo ""

# Generate Claude Code MCP config
echo "🔧 Generating Claude Code configuration..."
echo ""

cat << EOF

Add this to your ~/.claude.json under "mcpServers":

{
  "mcpServers": {
    "slack": {
      "command": "uv",
      "args": ["--directory", "$SCRIPT_DIR", "run", "slack-mcp"],
      "env": {
        "SLACK_BOT_TOKEN": "\$SLACK_BOT_TOKEN"
      }
    },
    "gong": {
      "command": "uv",
      "args": ["--directory", "$SCRIPT_DIR", "run", "gong-mcp"],
      "env": {
        "GONG_ACCESS_KEY": "\$GONG_ACCESS_KEY",
        "GONG_ACCESS_KEY_SECRET": "\$GONG_ACCESS_KEY_SECRET"
      }
    },
    "highspot": {
      "command": "uv",
      "args": ["--directory", "$SCRIPT_DIR", "run", "highspot-mcp"],
      "env": {
        "HIGHSPOT_API_KEY": "\$HIGHSPOT_API_KEY"
      }
    },
    "google-workspace": {
      "type": "http",
      "url": "https://mcp-proxy-534353623227.us-west1.run.app/mcp"
    }
  }
}

EOF

echo ""
echo "Or run these commands to add them via CLI:"
echo ""
echo "claude mcp add --scope user slack -- uv --directory $SCRIPT_DIR run slack-mcp"
echo "claude mcp add --scope user gong -- uv --directory $SCRIPT_DIR run gong-mcp"
echo "claude mcp add --scope user highspot -- uv --directory $SCRIPT_DIR run highspot-mcp"
echo ""
echo "✅ Setup complete! Next steps:"
echo "   1. Copy .env.template to .env and add your API keys"
echo "   2. Add the MCP servers to your Claude config"
echo "   3. Restart Claude Code"
echo "   4. Try: 'Search for competitive intel on Segment'"
