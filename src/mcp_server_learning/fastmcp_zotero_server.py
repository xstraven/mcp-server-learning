#!/usr/bin/env python3
"""
FastMCP-powered Zotero MCP Server

A modern, streamlined implementation of the Zotero MCP server using FastMCP's
Pythonic patterns for reduced boilerplate and improved maintainability.
"""

import sys
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

from .zotero_server import get_zotero_server

# Initialize FastMCP instance
mcp = FastMCP(
    "Zotero MCP Server",
    instructions="""This server searches and manages references in a Zotero library.

Use these tools when the user wants to:
- Search for papers/books/articles (search_items)
- Get details or notes on a specific item (get_item, get_item_notes)
- Browse collections (list_collections, get_collection_items)
- Add new references (create_item, create_item_note, add_item_to_collection)
- Discover available item types (get_item_templates)

All tools return: {"success": bool, "data": Any, "message": str, "error": str|null}.

Item keys are opaque strings returned by search/create operations -- pass them
to other tools to reference specific items.

Requires: ZOTERO_API_KEY, ZOTERO_LIBRARY_ID, and ZOTERO_LIBRARY_TYPE environment variables.
""",
)


@mcp.tool
def search_items(query: str, limit: int = 50, item_type: Optional[str] = None) -> Dict[str, Any]:
    """Search for items in the Zotero library by title, author, or content.

    Args:
        query: Search text (e.g., "attention is all you need", "transformer")
        limit: Maximum results to return (default 50)
        item_type: Filter by type (e.g., "journalArticle", "book", "conferencePaper",
            "thesis", "webpage"). Omit to search all types.

    Returns {"success": bool, "data": [{"key": str, "title": str, "creators": [...],
    "date": str, "itemType": str, ...}], "message": str, "error": str|null}.
    """
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
def get_item(item_key: str) -> Dict[str, Any]:
    """Get full details for a specific Zotero item including title, abstract,
    authors, date, URL, DOI, and all metadata fields.

    Args:
        item_key: Item key from search_items results

    Returns {"success": bool, "data": {"key": str, "title": str, "abstractNote": str,
    "creators": [...], "date": str, "url": str, ...}, "message": str, "error": str|null}.
    """
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
    """Get all notes attached to a Zotero item. These are manually-created
    notes/annotations, useful for extracting study material.

    Args:
        item_key: Item key from search_items results

    Returns {"success": bool, "data": [{"key": str, "note": str, ...}],
    "message": str, "error": str|null}.
    """
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
def list_collections() -> Dict[str, Any]:
    """List all collections (folders) in the Zotero library. Use collection keys
    with get_collection_items to browse items within a collection.

    Returns {"success": bool, "data": [{"key": str, "name": str, ...}],
    "message": str, "error": str|null}.
    """
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
    """Get all items in a specific Zotero collection.

    Args:
        collection_key: Collection key from list_collections results
        limit: Maximum items to return (default 50)

    Returns {"success": bool, "data": [{"key": str, "title": str, "itemType": str, ...}],
    "message": str, "error": str|null}.
    """
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
def create_item(
    item_type: str,
    title: str,
    creators: Optional[List[Dict[str, Any]]] = None,
    date: str = "",
    url: str = "",
    abstract: str = "",
    tags: Optional[List[str]] = None,
    extra_fields: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a new bibliographic item in the Zotero library. Use get_item_templates
    to see all available item types and their fields.

    After creation, use add_item_to_collection to organize it, or
    create_item_note to attach research notes.

    Args:
        item_type: Zotero item type (e.g., "journalArticle", "book", "conferencePaper",
            "thesis", "webpage", "preprint")
        title: Item title (e.g., "Attention Is All You Need")
        creators: List of creators, each with 'creatorType' ('author'/'editor') and
            either 'firstName'+'lastName' or 'name' (for institutions).
            Example: [{"creatorType": "author", "firstName": "John", "lastName": "Smith"}]
        date: Publication date (e.g., "2023-06-15" or "2023")
        url: URL of the item
        abstract: Abstract or summary
        tags: Tags to apply (e.g., ["machine-learning", "transformers"])
        extra_fields: Additional Zotero fields (e.g., {"DOI": "10.1234/example"})

    Returns {"success": bool, "data": {"item_key": str, "title": str},
    "message": str, "error": str|null}.
    """
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
    """Create a note attached to an existing Zotero item. Notes are stored as
    HTML in Zotero.

    Args:
        parent_item_key: Item key to attach the note to (from search_items results)
        note_content: Note text (HTML or plain text)

    Returns {"success": bool, "data": {"note_key": str, "parent_item_key": str},
    "message": str, "error": str|null}.
    """
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
    """Add an existing item to a collection for organization.

    Args:
        item_key: Item key (from search_items or create_item results)
        collection_key: Collection key (from list_collections results)

    Returns {"success": bool, "data": {"item_key": str, "collection_key": str},
    "message": str, "error": str|null}.
    """
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
    """Get templates showing all available Zotero item types and their fields.
    Use this to discover valid item_type values and field names for create_item.

    Returns {"success": bool, "data": dict, "message": str, "error": str|null}.
    """
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
