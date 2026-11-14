@echo off
setlocal
title EcomInsights MCP Server (Apify Crawlers)

echo ========================================================
echo   EcomInsights - MCP Server (Apify Crawlers)
echo ========================================================
echo.
echo Starting Model Context Protocol (MCP) server for Amazon ^& Flipkart crawlers...
echo Stdio transport active. Listening for JSON-RPC messages from MCP clients.
echo Press Ctrl+C to terminate.
echo.

cd /d "%~dp0"
python run_mcp_server.py

pause
