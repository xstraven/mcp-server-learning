#!/usr/bin/env python3
"""
FastMCP-powered Obsidian MCP Server

Re-implements the existing Obsidian MCP tools using FastMCP for
consistency with other servers in this project.
"""

import os
import sys
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

from .obsidian_connector import ObsidianConnector

# Initialize FastMCP instance
mcp = FastMCP("Obsidian MCP Server")


def _get_connector() -> ObsidianConnector:
    vault_path = os.getenv("OBSIDIAN_VAULT_PATH")
    if not vault_path:
        raise RuntimeError(
            "OBSIDIAN_VAULT_PATH environment variable must be set to your Obsidian vault path"
        )
    return ObsidianConnector(vault_path)


@mcp.tool
def get_vault_stats() -> Dict[str, Any]:
    """Get statistics about the Obsidian vault"""
    try:
        obsidian = _get_connector()
        stats = obsidian.get_vault_stats()

        return {
            "success": True,
            "data": stats,
            "message": f"Retrieved stats for {stats['total_notes']} notes in vault",
            "error": None,
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": "Failed to get vault stats",
            "error": str(e),
        }


@mcp.tool
def list_vault_notes(
    limit: Optional[int] = None,
    offset: int = 0,
    refresh_cache: bool = False,
) -> Dict[str, Any]:
    """List all notes in the vault with optional pagination"""
    try:
        obsidian = _get_connector()
        notes = obsidian.get_notes(limit=limit, offset=offset, refresh_cache=refresh_cache)

        if not notes:
            return {
                "success": True,
                "data": [],
                "message": "No notes found in vault",
                "error": None,
            }

        return {
            "success": True,
            "data": notes,
            "message": f"Found {len(notes)} note(s)",
            "error": None,
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": "Failed to list vault notes",
            "error": str(e),
        }


@mcp.tool
def search_obsidian_notes(
    query: str,
    search_in: Optional[List[str]] = None,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """Search for notes in the vault by content, title, or tags"""
    try:
        obsidian = _get_connector()
        search_in = search_in or ["content", "title", "tags"]
        results = obsidian.search_notes(query, search_in, limit)

        if not results:
            return {
                "success": True,
                "data": [],
                "message": f"No notes found matching '{query}'",
                "error": None,
            }

        return {
            "success": True,
            "data": results,
            "message": f"Found {len(results)} note(s) matching '{query}'",
            "error": None,
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": f"Failed to search for '{query}'",
            "error": str(e),
        }


@mcp.tool
def get_obsidian_note(note_name: str) -> Dict[str, Any]:
    """Get detailed information about a specific note"""
    try:
        obsidian = _get_connector()
        note = obsidian.get_note_by_name(note_name)

        if not note:
            return {
                "success": False,
                "data": None,
                "message": f"Note '{note_name}' not found",
                "error": "Note not found",
            }

        return {
            "success": True,
            "data": note,
            "message": f"Retrieved note '{note['title']}'",
            "error": None,
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": f"Failed to get note '{note_name}'",
            "error": str(e),
        }


@mcp.tool
def get_notes_by_tag(tag: str) -> Dict[str, Any]:
    """Get all notes that have a specific tag"""
    try:
        obsidian = _get_connector()
        notes = obsidian.get_notes_by_tag(tag)

        if not notes:
            return {
                "success": True,
                "data": [],
                "message": f"No notes found with tag '{tag}'",
                "error": None,
            }

        return {
            "success": True,
            "data": notes,
            "message": f"Found {len(notes)} note(s) with tag '{tag}'",
            "error": None,
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": f"Failed to get notes with tag '{tag}'",
            "error": str(e),
        }


@mcp.tool
def get_note_backlinks(note_name: str) -> Dict[str, Any]:
    """Find all notes that link to a specific note"""
    try:
        obsidian = _get_connector()
        backlinks = obsidian.scanner.get_backlinks(note_name)

        if not backlinks:
            return {
                "success": True,
                "data": [],
                "message": f"No backlinks found for note '{note_name}'",
                "error": None,
            }

        return {
            "success": True,
            "data": backlinks,
            "message": f"Found {len(backlinks)} backlink(s) to '{note_name}'",
            "error": None,
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": f"Failed to get backlinks for '{note_name}'",
            "error": str(e),
        }


@mcp.tool
def get_orphaned_notes() -> Dict[str, Any]:
    """Find notes that have no incoming or outgoing links"""
    try:
        obsidian = _get_connector()
        orphaned = obsidian.scanner.get_orphaned_notes()

        if not orphaned:
            return {
                "success": True,
                "data": [],
                "message": "No orphaned notes found - all notes have links!",
                "error": None,
            }

        return {
            "success": True,
            "data": orphaned,
            "message": f"Found {len(orphaned)} orphaned note(s)",
            "error": None,
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": "Failed to get orphaned notes",
            "error": str(e),
        }


@mcp.tool
def get_note_links(note_name: str) -> Dict[str, Any]:
    """Get all wikilinks from a specific note"""
    try:
        obsidian = _get_connector()
        note = obsidian.get_note_by_name(note_name)

        if not note:
            return {
                "success": False,
                "data": None,
                "message": f"Note '{note_name}' not found",
                "error": "Note not found",
            }

        links = note["wikilinks"]
        if not links:
            return {
                "success": True,
                "data": [],
                "message": f"No links found in note '{note_name}'",
                "error": None,
            }

        return {
            "success": True,
            "data": links,
            "message": f"Found {len(links)} link(s) in '{note_name}'",
            "error": None,
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": f"Failed to get links from '{note_name}'",
            "error": str(e),
        }


@mcp.tool
def extract_note_headers(note_name: str) -> Dict[str, Any]:
    """Extract structured headers from a note"""
    try:
        obsidian = _get_connector()
        note = obsidian.get_note_by_name(note_name)

        if not note:
            return {
                "success": False,
                "data": None,
                "message": f"Note '{note_name}' not found",
                "error": "Note not found",
            }

        headers = note["headers"]
        if not headers:
            return {
                "success": True,
                "data": [],
                "message": f"No headers found in note '{note_name}'",
                "error": None,
            }

        return {
            "success": True,
            "data": headers,
            "message": f"Found {len(headers)} header(s) in '{note_name}'",
            "error": None,
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": f"Failed to extract headers from '{note_name}'",
            "error": str(e),
        }


@mcp.tool
def extract_note_blocks(note_name: str, block_types: Optional[List[str]] = None) -> Dict[str, Any]:
    """Extract content blocks (paragraphs, lists, quotes, code, headers) from a note"""
    try:
        obsidian = _get_connector()
        note = obsidian.get_note_by_name(note_name)

        if not note:
            return {
                "success": False,
                "data": None,
                "message": f"Note '{note_name}' not found",
                "error": "Note not found",
            }

        blocks = note["blocks"]
        if block_types:
            blocks = [block for block in blocks if block["type"] in block_types]

        if not blocks:
            filter_msg = f" of type(s) {', '.join(block_types)}" if block_types else ""
            return {
                "success": True,
                "data": [],
                "message": f"No blocks{filter_msg} found in note '{note_name}'",
                "error": None,
            }

        return {
            "success": True,
            "data": blocks,
            "message": f"Found {len(blocks)} block(s) in '{note_name}'",
            "error": None,
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": f"Failed to extract blocks from '{note_name}'",
            "error": str(e),
        }


@mcp.tool
def get_notes_for_flashcards(
    note_names: Optional[List[str]] = None,
    tag_filter: Optional[str] = None,
    content_types: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Extract content from notes suitable for flashcard generation"""
    try:
        if not note_names and not tag_filter:
            return {
                "success": False,
                "data": None,
                "message": "Error: Either note_names or tag_filter must be provided",
                "error": "Missing required parameter",
            }

        obsidian = _get_connector()
        content_types = content_types or ["headers", "definitions", "lists", "quotes"]

        if tag_filter:
            notes_to_process = obsidian.get_notes_by_tag(tag_filter)
        else:
            notes_to_process = []
            for name in note_names:
                note = obsidian.get_note_by_name(name)
                if note:
                    notes_to_process.append(note)

        if not notes_to_process:
            return {
                "success": True,
                "data": [],
                "message": "No notes found to process",
                "error": None,
            }

        all_flashcard_content: List[Dict[str, Any]] = []
        for note in notes_to_process:
            content = obsidian.extract_content_for_flashcards(note, content_types)
            all_flashcard_content.extend(content)

        if not all_flashcard_content:
            return {
                "success": True,
                "data": [],
                "message": "No suitable content found for flashcards",
                "error": None,
            }

        return {
            "success": True,
            "data": all_flashcard_content,
            "message": f"Extracted {len(all_flashcard_content)} potential flashcard(s) from {len(notes_to_process)} note(s)",
            "error": None,
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": "Failed to extract flashcard content",
            "error": str(e),
        }


def main():
    """Run the FastMCP Obsidian server"""
    try:
        print("Starting Obsidian MCP server...", file=sys.stderr)
        mcp.run()
    except Exception as e:
        print(f"Failed to start Obsidian MCP server: {e}", file=sys.stderr)
        print(f"Error type: {type(e).__name__}", file=sys.stderr)
        import traceback

        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
