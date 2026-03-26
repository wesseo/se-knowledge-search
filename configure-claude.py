#!/usr/bin/env python3
"""
Configure Claude Code with SE Knowledge Search MCP servers.

This script updates ~/.claude.json with the necessary MCP server configurations.
Run with: python configure-claude.py
"""

import json
import os
import sys
from pathlib import Path


def get_project_dir() -> str:
    """Get the absolute path to this project."""
    return str(Path(__file__).parent.absolute())


def load_env_file() -> dict[str, str]:
    """Load environment variables from .env file if it exists."""
    env_file = Path(__file__).parent / ".env"
    env_vars = {}

    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env_vars[key.strip()] = value.strip()

    return env_vars


def get_mcp_config(project_dir: str, env_vars: dict[str, str]) -> dict:
    """Generate MCP server configurations."""

    config = {}

    # Slack
    slack_token = env_vars.get("SLACK_BOT_TOKEN") or os.environ.get("SLACK_BOT_TOKEN")
    if slack_token:
        config["slack"] = {
            "command": "uv",
            "args": ["--directory", project_dir, "run", "slack-mcp"],
            "env": {
                "SLACK_BOT_TOKEN": slack_token
            }
        }
    else:
        print("⚠️  SLACK_BOT_TOKEN not found - skipping Slack MCP")

    # Gong
    gong_key = env_vars.get("GONG_ACCESS_KEY") or os.environ.get("GONG_ACCESS_KEY")
    gong_secret = env_vars.get("GONG_ACCESS_KEY_SECRET") or os.environ.get("GONG_ACCESS_KEY_SECRET")
    if gong_key and gong_secret:
        config["gong"] = {
            "command": "uv",
            "args": ["--directory", project_dir, "run", "gong-mcp"],
            "env": {
                "GONG_ACCESS_KEY": gong_key,
                "GONG_ACCESS_KEY_SECRET": gong_secret
            }
        }
    else:
        print("⚠️  GONG_ACCESS_KEY/SECRET not found - skipping Gong MCP")

    # Highspot
    highspot_key = env_vars.get("HIGHSPOT_API_KEY") or os.environ.get("HIGHSPOT_API_KEY")
    if highspot_key:
        config["highspot"] = {
            "command": "uv",
            "args": ["--directory", project_dir, "run", "highspot-mcp"],
            "env": {
                "HIGHSPOT_API_KEY": highspot_key
            }
        }
    else:
        print("⚠️  HIGHSPOT_API_KEY not found - skipping Highspot MCP")

    # Google Workspace (uses HTTP connector - no env vars needed)
    config["google-workspace"] = {
        "type": "http",
        "url": "https://mcp-proxy-534353623227.us-west1.run.app/mcp"
    }

    return config


def main():
    print("🔍 SE Knowledge Search - Claude Code Configuration")
    print("=" * 50)
    print()

    project_dir = get_project_dir()
    print(f"Project directory: {project_dir}")

    # Load env vars
    env_vars = load_env_file()
    if env_vars:
        print(f"Loaded {len(env_vars)} variables from .env")

    # Generate MCP config
    mcp_config = get_mcp_config(project_dir, env_vars)

    # Load existing Claude config
    claude_config_path = Path.home() / ".claude.json"

    if claude_config_path.exists():
        with open(claude_config_path) as f:
            claude_config = json.load(f)
        print(f"Loaded existing config from {claude_config_path}")
    else:
        claude_config = {}
        print(f"Creating new config at {claude_config_path}")

    # Merge MCP servers
    if "mcpServers" not in claude_config:
        claude_config["mcpServers"] = {}

    # Check for conflicts
    for name in mcp_config:
        if name in claude_config["mcpServers"]:
            print(f"⚠️  Overwriting existing '{name}' MCP server config")

    claude_config["mcpServers"].update(mcp_config)

    # Show what we're adding
    print()
    print("MCP servers to configure:")
    for name in mcp_config:
        print(f"  ✓ {name}")

    # Confirm
    print()
    response = input("Apply this configuration? [y/N] ")
    if response.lower() != "y":
        print("Cancelled.")
        sys.exit(0)

    # Write config
    with open(claude_config_path, "w") as f:
        json.dump(claude_config, f, indent=2)

    print()
    print(f"✅ Configuration written to {claude_config_path}")
    print()
    print("Next steps:")
    print("  1. Restart Claude Code")
    print("  2. Run /mcp to verify servers are loaded")
    print("  3. Try: 'Search for competitive intel on Segment'")


if __name__ == "__main__":
    main()
