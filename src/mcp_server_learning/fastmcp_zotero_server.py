#!/usr/bin/env python3
"""
FastMCP-powered Zotero MCP Server

A modern, streamlined implementation of the Zotero MCP server using FastMCP's
Pythonic patterns for reduced boilerplate and improved maintainability.
"""

import json
import sys
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

from .zotero_server import get_zotero_server

# Initialize FastMCP instance
mcp = FastMCP("Zotero MCP Server")


@mcp.tool
def search_zotero_items(
    query: str, limit: int = 50, item_type: Optional[str] = None
) -> Dict[str, Any]:
    """Search for items in the Zotero library"""
    try:
        zotero = get_zotero_server()
        items = zotero.search_items(query, limit, item_type)

        if not items:
            return {
                "success": True,
                "data": [],
                "message": "No items found matching your search",
                "error": None,
            }

        return {
            "success": True,
            "data": items,
            "message": f"Found {len(items)} items",
            "error": None,
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": "Failed to search Zotero items",
            "error": str(e),
        }


@mcp.tool
def get_zotero_item(item_key: str) -> Dict[str, Any]:
    """Get detailed information about a specific Zotero item"""
    try:
        zotero = get_zotero_server()
        item = zotero.get_item(item_key)

        if not item:
            return {
                "success": False,
                "data": None,
                "message": f"Item with key '{item_key}' not found",
                "error": "Item not found",
            }

        return {
            "success": True,
            "data": item,
            "message": f"Retrieved item '{item.get('title', item_key)}'",
            "error": None,
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": f"Failed to get item '{item_key}'",
            "error": str(e),
        }


@mcp.tool
def get_item_notes(item_key: str) -> Dict[str, Any]:
    """Get all notes associated with a Zotero item"""
    try:
        zotero = get_zotero_server()
        notes = zotero.get_item_notes(item_key)

        if not notes:
            return {
                "success": True,
                "data": [],
                "message": f"No notes found for item '{item_key}'",
                "error": None,
            }

        return {
            "success": True,
            "data": notes,
            "message": f"Found {len(notes)} note(s) for item '{item_key}'",
            "error": None,
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": f"Failed to get notes for item '{item_key}'",
            "error": str(e),
        }


@mcp.tool
def list_zotero_collections() -> Dict[str, Any]:
    """List all collections in the Zotero library"""
    try:
        zotero = get_zotero_server()
        collections = zotero.list_collections()

        if not collections:
            return {
                "success": True,
                "data": [],
                "message": "No collections found",
                "error": None,
            }

        return {
            "success": True,
            "data": collections,
            "message": f"Found {len(collections)} collection(s)",
            "error": None,
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": "Failed to list collections",
            "error": str(e),
        }


@mcp.tool
def get_collection_items(collection_key: str, limit: int = 50) -> Dict[str, Any]:
    """Get items from a specific collection"""
    try:
        zotero = get_zotero_server()
        items = zotero.get_collection_items(collection_key, limit)

        if not items:
            return {
                "success": True,
                "data": [],
                "message": f"No items found in collection '{collection_key}'",
                "error": None,
            }

        return {
            "success": True,
            "data": items,
            "message": f"Found {len(items)} item(s) in collection",
            "error": None,
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": f"Failed to get items from collection '{collection_key}'",
            "error": str(e),
        }


@mcp.tool
def create_zotero_item(
    item_type: str,
    title: str,
    creators: Optional[List[Dict[str, Any]]] = None,
    date: str = "",
    url: str = "",
    abstract: str = "",
    tags: Optional[List[str]] = None,
    extra_fields: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a new item in the Zotero library"""
    try:
        zotero = get_zotero_server()

        # Build item data
        item_data = {
            "itemType": item_type,
            "title": title,
            "creators": creators or [],
            "date": date,
            "url": url,
            "abstractNote": abstract,
            "tags": [{"tag": tag} for tag in (tags or [])],
            **(extra_fields or {}),
        }

        result = zotero.create_item(item_data)

        return {
            "success": True,
            "data": {"item_key": result["item_key"], "title": title},
            "message": f"Successfully created item with key '{result['item_key']}'",
            "error": None,
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": f"Failed to create item '{title}'",
            "error": str(e),
        }


@mcp.tool
def create_item_note(parent_item_key: str, note_content: str) -> Dict[str, Any]:
    """Create a note attached to an existing Zotero item"""
    try:
        zotero = get_zotero_server()
        result = zotero.create_note(parent_item_key, note_content)

        return {
            "success": True,
            "data": {"note_key": result["note_key"], "parent_item_key": parent_item_key},
            "message": f"Successfully created note attached to '{parent_item_key}'",
            "error": None,
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": f"Failed to create note for item '{parent_item_key}'",
            "error": str(e),
        }


@mcp.tool
def add_item_to_collection(item_key: str, collection_key: str) -> Dict[str, Any]:
    """Add an item to a collection"""
    try:
        zotero = get_zotero_server()
        result = zotero.add_item_to_collection(item_key, collection_key)

        return {
            "success": True,
            "data": {"item_key": item_key, "collection_key": collection_key},
            "message": f"Added item '{item_key}' to collection '{collection_key}'",
            "error": None,
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": f"Failed to add item to collection",
            "error": str(e),
        }


@mcp.tool
def get_item_templates() -> Dict[str, Any]:
    """Get templates for creating new items of different types"""
    try:
        zotero = get_zotero_server()
        templates = zotero.get_item_templates()

        return {
            "success": True,
            "data": templates,
            "message": f"Retrieved {len(templates)} item templates",
            "error": None,
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": "Failed to get item templates",
            "error": str(e),
        }


def main():
    """Run the FastMCP Zotero server"""
    try:
        print("Starting Zotero MCP server...", file=sys.stderr)
        mcp.run()
    except Exception as e:
        print(f"Failed to start Zotero MCP server: {e}", file=sys.stderr)
        print(f"Error type: {type(e).__name__}", file=sys.stderr)
        import traceback

        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
