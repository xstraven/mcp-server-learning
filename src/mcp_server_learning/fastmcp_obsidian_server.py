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


def get_vault_stats() -> str:
    """Get statistics about the Obsidian vault"""
    obsidian = _get_connector()
    stats = obsidian.get_vault_stats()

    response = "**Obsidian Vault Statistics**\n\n"
    response += f"📍 **Vault Path:** {stats['vault_path']}\n"
    response += f"📄 **Total Notes:** {stats['total_notes']}\n"
    response += f"💾 **Total Size:** {stats['total_size_bytes']:,} bytes\n"
    response += f"🏷️ **Total Tags:** {stats['total_tags']}\n\n"

    if stats["note_types"]:
        response += "**Note Types:**\n"
        for note_type, count in stats["note_types"].items():
            response += f"- {note_type}: {count}\n"
        response += "\n"

    if stats["all_tags"]:
        response += f"**Popular Tags:** {', '.join(stats['all_tags'][:10])}"
        if len(stats["all_tags"]) > 10:
            response += f" (and {len(stats['all_tags']) - 10} more)"
        response += "\n"

    return response


def list_vault_notes(
    limit: Optional[int] = None,
    offset: int = 0,
    refresh_cache: bool = False,
) -> str:
    """List all notes in the vault with optional pagination"""
    obsidian = _get_connector()
    notes = obsidian.get_notes(limit=limit, offset=offset, refresh_cache=refresh_cache)

    if not notes:
        return "No notes found in vault"

    response = f"Found {len(notes)} note(s):\n\n"
    for note in notes:
        response += f"**{note['title']}**\n"
        response += f"Path: {note['path']}\n"
        response += f"Modified: {note['modified']}\n"
        if note["tags"]:
            response += f"Tags: {', '.join(note['tags'])}\n"
        response += "\n"
    return response


def search_obsidian_notes(
    query: str,
    search_in: Optional[List[str]] = None,
    limit: Optional[int] = None,
) -> str:
    """Search for notes in the vault by content, title, or tags"""
    obsidian = _get_connector()
    search_in = search_in or ["content", "title", "tags"]
    results = obsidian.search_notes(query, search_in, limit)

    if not results:
        return f"No notes found matching '{query}'"

    response = f"Found {len(results)} note(s) matching '{query}':\n\n"
    for note in results:
        response += f"**{note['title']}**\n"
        response += f"Path: {note['path']}\n"
        response += f"Modified: {note['modified']}\n"
        if note["tags"]:
            response += f"Tags: {', '.join(note['tags'])}\n"

        content_lower = note["content"].lower()
        query_lower = query.lower()
        if query_lower in content_lower:
            idx = content_lower.find(query_lower)
            start = max(0, idx - 50)
            end = min(len(note["content"]), idx + len(query) + 50)
            snippet = note["content"][start:end]
            if start > 0:
                snippet = "..." + snippet
            if end < len(note["content"]):
                snippet = snippet + "..."
            response += f"Snippet: {snippet}\n"

        response += "\n"
    return response


def get_obsidian_note(note_name: str) -> str:
    """Get detailed information about a specific note"""
    obsidian = _get_connector()
    note = obsidian.get_note_by_name(note_name)
    if not note:
        return f"Note '{note_name}' not found"

    response = f"**{note['title']}**\n\n"
    response += f"**Path:** {note['path']}\n"
    response += f"**Created:** {note['created']}\n"
    response += f"**Modified:** {note['modified']}\n"
    response += f"**Size:** {note['size']} bytes\n"

    if note["tags"]:
        response += f"**Tags:** {', '.join(note['tags'])}\n"

    if note["frontmatter"]:
        import json as _json

        response += f"\n**Frontmatter:**\n```yaml\n{_json.dumps(note['frontmatter'], indent=2)}\n```\n"

    if note["wikilinks"]:
        response += f"\n**Links ({len(note['wikilinks'])}):**\n"
        for link in note["wikilinks"][:10]:
            response += f"- [[{link['target']}]]"
            if link["header"]:
                response += f"#{link['header']}"
            if link["display"] != link["target"]:
                response += f" (displayed as: {link['display']})"
            response += "\n"
        if len(note["wikilinks"]) > 10:
            response += f"... and {len(note['wikilinks']) - 10} more links\n"

    if note["headers"]:
        response += f"\n**Headers ({len(note['headers'])}):**\n"
        for header in note["headers"]:
            indent = "  " * (header["level"] - 1)
            response += f"{indent}- {header['text']} (H{header['level']})\n"

    response += f"\n**Content:**\n{note['content']}"
    return response


def get_notes_by_tag(tag: str) -> str:
    """Get all notes that have a specific tag"""
    obsidian = _get_connector()
    notes = obsidian.get_notes_by_tag(tag)

    if not notes:
        return f"No notes found with tag '{tag}'"

    response = f"Found {len(notes)} note(s) with tag '{tag}':\n\n"
    for note in notes:
        response += f"**{note['title']}**\n"
        response += f"Path: {note['path']}\n"
        response += f"Modified: {note['modified']}\n"
        if note["tags"]:
            response += f"All tags: {', '.join(note['tags'])}\n"
        response += "\n"
    return response


def get_note_backlinks(note_name: str) -> str:
    """Find all notes that link to a specific note"""
    obsidian = _get_connector()
    backlinks = obsidian.scanner.get_backlinks(note_name)

    if not backlinks:
        return f"No backlinks found for note '{note_name}'"

    response = f"Found {len(backlinks)} backlink(s) to '{note_name}':\n\n"
    for backlink in backlinks:
        response += f"**{backlink['source_note']}**\n"
        response += f"Path: {backlink['source_path']}\n"
        response += f"Link text: {backlink['link_text']}\n"
        if backlink["header"]:
            response += f"Linked to header: {backlink['header']}\n"
        response += "\n"
    return response


def get_orphaned_notes() -> str:
    """Find notes that have no incoming or outgoing links"""
    obsidian = _get_connector()
    orphaned = obsidian.scanner.get_orphaned_notes()

    if not orphaned:
        return "No orphaned notes found - all notes have links!"

    response = f"Found {len(orphaned)} orphaned note(s) (no incoming or outgoing links):\n\n"
    for note in orphaned:
        response += f"**{note['title']}**\n"
        response += f"Path: {note['path']}\n"
        response += f"Modified: {note['modified']}\n"
        response += f"Size: {note['size']} bytes\n\n"
    return response


def get_note_links(note_name: str) -> str:
    """Get all wikilinks from a specific note"""
    obsidian = _get_connector()
    note = obsidian.get_note_by_name(note_name)
    if not note:
        return f"Note '{note_name}' not found"

    links = note["wikilinks"]
    if not links:
        return f"No links found in note '{note_name}'"

    response = f"Found {len(links)} link(s) in '{note_name}':\n\n"
    for link in links:
        response += f"**[[{link['target']}]]**\n"
        if link["header"]:
            response += f"Header: #{link['header']}\n"
        if link["display"] != link["target"]:
            response += f"Display text: {link['display']}\n"
        response += "\n"
    return response


def extract_note_headers(note_name: str) -> str:
    """Extract structured headers from a note"""
    obsidian = _get_connector()
    note = obsidian.get_note_by_name(note_name)
    if not note:
        return f"Note '{note_name}' not found"

    headers = note["headers"]
    if not headers:
        return f"No headers found in note '{note_name}'"

    response = f"Found {len(headers)} header(s) in '{note_name}':\n\n"
    for header in headers:
        indent = "  " * (header["level"] - 1)
        response += f"{indent}**H{header['level']}:** {header['text']}\n"
        response += f"{indent}Line: {header['line_number']}\n"
        response += f"{indent}Anchor: #{header['anchor']}\n\n"
    return response


def extract_note_blocks(note_name: str, block_types: Optional[List[str]] = None) -> str:
    """Extract content blocks (paragraphs, lists, quotes, code, headers) from a note"""
    obsidian = _get_connector()
    note = obsidian.get_note_by_name(note_name)
    if not note:
        return f"Note '{note_name}' not found"

    blocks = note["blocks"]
    if block_types:
        blocks = [block for block in blocks if block["type"] in block_types]

    if not blocks:
        filter_msg = f" of type(s) {', '.join(block_types)}" if block_types else ""
        return f"No blocks{filter_msg} found in note '{note_name}'"

    response = f"Found {len(blocks)} block(s) in '{note_name}':\n\n"
    for i, block in enumerate(blocks, 1):
        response += f"**Block {i} ({block['type']})**\n"
        response += f"Lines {block['start_line']}-{block['end_line']}:\n"
        if block["type"] == "code" and "language" in block:
            response += f"Language: {block['language']}\n"
        response += f"```\n{block['content']}\n```\n\n"
    return response


def get_notes_for_flashcards(
    note_names: Optional[List[str]] = None,
    tag_filter: Optional[str] = None,
    content_types: Optional[List[str]] = None,
) -> str:
    """Extract content from notes suitable for flashcard generation"""
    obsidian = _get_connector()
    content_types = content_types or ["headers", "definitions", "lists", "quotes"]

    if tag_filter:
        notes_to_process = obsidian.get_notes_by_tag(tag_filter)
    elif note_names:
        notes_to_process = []
        for name in note_names:
            note = obsidian.get_note_by_name(name)
            if note:
                notes_to_process.append(note)
    else:
        return "Error: Either note_names or tag_filter must be provided"

    if not notes_to_process:
        return "No notes found to process"

    all_flashcard_content: List[Dict[str, Any]] = []
    for note in notes_to_process:
        content = obsidian.extract_content_for_flashcards(note, content_types)
        all_flashcard_content.extend(content)

    if not all_flashcard_content:
        return "No suitable content found for flashcards"

    response = (
        f"Extracted {len(all_flashcard_content)} potential flashcard(s) from {len(notes_to_process)} note(s):\n\n"
    )
    for i, content in enumerate(all_flashcard_content[:20], 1):
        response += f"**Flashcard {i} ({content['type']})**\n"
        response += f"Source: {content['source_note']}"
        if "source_line" in content:
            response += f" (line {content['source_line']})"
        response += "\n"

        if content["type"] == "header":
            response += f"Q: {content['question']}\n"
            response += f"Context: {content['context']}\n"
        elif "content" in content:
            response += f"Content: {content['content']}\n"

        if "context" in content and content["type"] != "header":
            response += f"Context: {content['context']}\n"

        response += "\n"

    if len(all_flashcard_content) > 20:
        response += f"... and {len(all_flashcard_content) - 20} more potential flashcards\n"

    return response

# Register tools with FastMCP while keeping functions directly callable for tests
mcp.tool(get_vault_stats)
mcp.tool(list_vault_notes)
mcp.tool(search_obsidian_notes)
mcp.tool(get_obsidian_note)
mcp.tool(get_notes_by_tag)
mcp.tool(get_note_backlinks)
mcp.tool(get_orphaned_notes)
mcp.tool(get_note_links)
mcp.tool(extract_note_headers)
mcp.tool(extract_note_blocks)
mcp.tool(get_notes_for_flashcards)


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
