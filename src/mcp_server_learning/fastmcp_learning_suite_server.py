#!/usr/bin/env python3
"""
FastMCP Learning Suite Server

Aggregates the flashcard, Zotero, Obsidian, and math verification servers
into a single FastMCP endpoint with prefixed tool names.
"""

import os
import sys
from typing import Any

from fastmcp import FastMCP

from . import (
    fastmcp_flashcard_server,
    fastmcp_math_verification_server,
    fastmcp_obsidian_server,
    fastmcp_zotero_server,
)


def _get_env(name: str, default: str) -> str:
    value = os.getenv(name)
    return value if value is not None and value != "" else default


def _mount_suite(suite: FastMCP) -> None:
    mount = getattr(suite, "mount", None)
    if mount is None:
        raise RuntimeError(
            "FastMCP mount() not available. Upgrade fastmcp to a version that supports"
            " server composition."
        )

    mount(fastmcp_flashcard_server.mcp, prefix="flashcard")
    mount(fastmcp_zotero_server.mcp, prefix="zotero")
    mount(fastmcp_obsidian_server.mcp, prefix="obsidian")
    mount(fastmcp_math_verification_server.mcp, prefix="math")


def build_suite() -> FastMCP:
    suite = FastMCP("Learning MCP Suite")
    _mount_suite(suite)
    return suite


def _run_suite(suite: FastMCP, transport: str, host: str, port: int, path: str) -> Any:
    try:
        return suite.run(transport=transport, host=host, port=port, path=path)
    except TypeError:
        # Fallback for older FastMCP signatures without a path argument.
        return suite.run(transport=transport, host=host, port=port)


def main() -> None:
    transport = _get_env("MCP_TRANSPORT", "http")
    host = _get_env("MCP_HOST", "0.0.0.0")
    port = int(_get_env("MCP_PORT", "8000"))
    path = _get_env("MCP_PATH", "/mcp")

    try:
        print(
            f"Starting Learning MCP Suite on {transport}://{host}:{port}{path}",
            file=sys.stderr,
        )
        suite = build_suite()
        _run_suite(suite, transport=transport, host=host, port=port, path=path)
    except Exception as exc:
        print(f"Failed to start Learning MCP Suite: {exc}", file=sys.stderr)
        print(f"Error type: {type(exc).__name__}", file=sys.stderr)
        import traceback

        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
