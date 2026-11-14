"""Entrypoint to launch the EcomInsights Apify Crawlers MCP Server.

Run directly in terminal:
    python run_mcp_server.py

Or register in your Claude Desktop / Cursor / Antigravity MCP config:
    {
      "mcpServers": {
        "ecominsights": {
          "command": "python",
          "args": ["run_mcp_server.py"]
        }
      }
    }
"""

import os
import sys

_root = os.path.dirname(os.path.abspath(__file__))
_backend = os.path.join(_root, "backend")
if _backend not in sys.path:
    sys.path.insert(0, _backend)

from app.mcp.server import run_server

if __name__ == "__main__":
    run_server()
