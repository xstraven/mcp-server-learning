#!/usr/bin/env bash
set -euo pipefail

MCP_TRANSPORT="${MCP_TRANSPORT:-http}"
MCP_HOST="${MCP_HOST:-127.0.0.1}"
MCP_PORT="${MCP_PORT:-8000}"
MCP_PATH="${MCP_PATH:-/mcp}"

echo "Starting Learning MCP Suite on ${MCP_TRANSPORT}://${MCP_HOST}:${MCP_PORT}${MCP_PATH}" >&2

exec env \
  MCP_TRANSPORT="${MCP_TRANSPORT}" \
  MCP_HOST="${MCP_HOST}" \
  MCP_PORT="${MCP_PORT}" \
  MCP_PATH="${MCP_PATH}" \
  uv run fastmcp-learning-suite
