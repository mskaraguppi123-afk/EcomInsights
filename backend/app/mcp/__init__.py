"""EcomInsights MCP Server package.
Provides Model Context Protocol (MCP) server endpoints and tools for Apify e-commerce crawlers.
"""

from app.mcp.server import create_mcp_server, run_server

__all__ = ["create_mcp_server", "run_server"]
