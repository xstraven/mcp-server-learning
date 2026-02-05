#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <mcp-url>" >&2
  echo "Example: $0 https://mcp.example.com/mcp/" >&2
  exit 2
fi

URL="$1"

PAYLOAD='{"jsonrpc":"2.0","id":"smoke-test","method":"tools/list","params":{}}'
RESPONSE="$(curl -sS -L --max-time 15 \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "${PAYLOAD}" \
  "${URL}" || true)"

if [[ -z "${RESPONSE}" ]]; then
  echo "No response from ${URL}" >&2
  exit 1
fi

if [[ "${RESPONSE}" == *'"jsonrpc"'* ]]; then
  echo "MCP endpoint is reachable at ${URL}"
  echo "${RESPONSE}"
  exit 0
fi

echo "Endpoint responded, but output did not look like JSON-RPC:" >&2
echo "${RESPONSE}" >&2
exit 1
