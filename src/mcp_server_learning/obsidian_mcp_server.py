#!/usr/bin/env python3

import asyncio
import os
import json
from typing import Dict, List, Any, Optional
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.types import (
    Tool,
    TextContent,
    LoggingLevel,
)
import mcp.types as types
from .obsidian_connector import ObsidianConnector

server = Server("obsidian-mcp-server")

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available Obsidian tools."""
    return [
        Tool(
            name="get_vault_stats",
            description="Get statistics about the Obsidian vault",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="list_vault_notes",
            description="List all notes in the vault with optional pagination",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of notes to return",
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Number of notes to skip (for pagination)",
                        "default": 0,
                    },
                    "refresh_cache": {
                        "type": "boolean",
                        "description": "Whether to refresh the note cache",
                        "default": False,
                    },
                },
            },
        ),
        Tool(
            name="search_obsidian_notes",
            description="Search for notes in the vault by content, title, or tags",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query",
                    },
                    "search_in": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["content", "title", "tags"]
                        },
                        "description": "Fields to search in (default: all)",
                        "default": ["content", "title", "tags"],
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_obsidian_note",
            description="Get detailed information about a specific note",
            inputSchema={
                "type": "object",
                "properties": {
                    "note_name": {
                        "type": "string",
                        "description": "Name of the note (without .md extension)",
                    },
                },
                "required": ["note_name"],
            },
        ),
        Tool(
            name="get_notes_by_tag",
            description="Get all notes that have a specific tag",
            inputSchema={
                "type": "object",
                "properties": {
                    "tag": {
                        "type": "string",
                        "description": "Tag to search for",
                    },
                },
                "required": ["tag"],
            },
        ),
        Tool(
            name="get_note_backlinks",
            description="Find all notes that link to a specific note",
            inputSchema={
                "type": "object",
                "properties": {
                    "note_name": {
                        "type": "string",
                        "description": "Name of the note to find backlinks for",
                    },
                },
                "required": ["note_name"],
            },
        ),
        Tool(
            name="get_orphaned_notes",
            description="Find notes that have no incoming or outgoing links",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="get_note_links",
            description="Get all wikilinks from a specific note",
            inputSchema={
                "type": "object",
                "properties": {
                    "note_name": {
                        "type": "string",
                        "description": "Name of the note to get links from",
                    },
                },
                "required": ["note_name"],
            },
        ),
        Tool(
            name="extract_note_headers",
            description="Extract structured headers from a note",
            inputSchema={
                "type": "object",
                "properties": {
                    "note_name": {
                        "type": "string",
                        "description": "Name of the note to extract headers from",
                    },
                },
                "required": ["note_name"],
            },
        ),
        Tool(
            name="extract_note_blocks",
            description="Extract content blocks (paragraphs, lists, quotes, code) from a note",
            inputSchema={
                "type": "object",
                "properties": {
                    "note_name": {
                        "type": "string",
                        "description": "Name of the note to extract blocks from",
                    },
                    "block_types": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["paragraph", "list", "numbered_list", "quote", "code", "header"]
                        },
                        "description": "Types of blocks to extract (default: all)",
                    },
                },
                "required": ["note_name"],
            },
        ),
        Tool(
            name="get_notes_for_flashcards",
            description="Extract content from notes that is suitable for flashcard generation",
            inputSchema={
                "type": "object",
                "properties": {
                    "note_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Names of notes to extract content from",
                    },
                    "tag_filter": {
                        "type": "string",
                        "description": "Only process notes with this tag",
                    },
                    "content_types": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["headers", "definitions", "lists", "quotes"]
                        },
                        "description": "Types of content to extract (default: all)",
                        "default": ["headers", "definitions", "lists", "quotes"],
                    },
                },
            },
        ),
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool calls."""
    
    vault_path = os.getenv('OBSIDIAN_VAULT_PATH')
    if not vault_path:
        return [
            types.TextContent(
                type="text",
                text="Error: OBSIDIAN_VAULT_PATH environment variable must be set"
            )
        ]
    
    try:
        obsidian = ObsidianConnector(vault_path)
    except Exception as e:
        return [
            types.TextContent(
                type="text",
                text=f"Error connecting to Obsidian vault at '{vault_path}': {str(e)}"
            )
        ]
    
    try:
        if name == "get_vault_stats":
            stats = obsidian.get_vault_stats()
            
            response = f"**Obsidian Vault Statistics**\n\n"
            response += f"📍 **Vault Path:** {stats['vault_path']}\n"
            response += f"📄 **Total Notes:** {stats['total_notes']}\n"
            response += f"💾 **Total Size:** {stats['total_size_bytes']:,} bytes\n"
            response += f"🏷️ **Total Tags:** {stats['total_tags']}\n\n"
            
            if stats['note_types']:
                response += "**Note Types:**\n"
                for note_type, count in stats['note_types'].items():
                    response += f"- {note_type}: {count}\n"
                response += "\n"
            
            if stats['all_tags']:
                response += f"**Popular Tags:** {', '.join(stats['all_tags'][:10])}"
                if len(stats['all_tags']) > 10:
                    response += f" (and {len(stats['all_tags']) - 10} more)"
                response += "\n"
            
            return [types.TextContent(type="text", text=response)]
        
        elif name == "list_vault_notes":
            limit = arguments.get("limit")
            offset = arguments.get("offset", 0)
            refresh_cache = arguments.get("refresh_cache", False)
            
            notes = obsidian.get_notes(limit=limit, offset=offset, refresh_cache=refresh_cache)
            
            if not notes:
                return [types.TextContent(type="text", text="No notes found in vault")]
            
            response = f"Found {len(notes)} note(s):\n\n"
            for note in notes:
                response += f"**{note['title']}**\n"
                response += f"Path: {note['path']}\n"
                response += f"Modified: {note['modified']}\n"
                if note['tags']:
                    response += f"Tags: {', '.join(note['tags'])}\n"
                response += "\n"
            
            return [types.TextContent(type="text", text=response)]
        
        elif name == "search_obsidian_notes":
            query = arguments.get("query")
            search_in = arguments.get("search_in", ["content", "title", "tags"])
            limit = arguments.get("limit")
            
            results = obsidian.search_notes(query, search_in, limit)
            
            if not results:
                return [types.TextContent(type="text", text=f"No notes found matching '{query}'")]
            
            response = f"Found {len(results)} note(s) matching '{query}':\n\n"
            for note in results:
                response += f"**{note['title']}**\n"
                response += f"Path: {note['path']}\n"
                response += f"Modified: {note['modified']}\n"
                if note['tags']:
                    response += f"Tags: {', '.join(note['tags'])}\n"
                
                # Show a snippet of content where the query was found
                content_lower = note['content'].lower()
                query_lower = query.lower()
                if query_lower in content_lower:
                    idx = content_lower.find(query_lower)
                    start = max(0, idx - 50)
                    end = min(len(note['content']), idx + len(query) + 50)
                    snippet = note['content'][start:end]
                    if start > 0:
                        snippet = "..." + snippet
                    if end < len(note['content']):
                        snippet = snippet + "..."
                    response += f"Snippet: {snippet}\n"
                
                response += "\n"
            
            return [types.TextContent(type="text", text=response)]
        
        elif name == "get_obsidian_note":
            note_name = arguments.get("note_name")
            if not note_name:
                return [types.TextContent(type="text", text="Error: note_name is required")]
            
            note = obsidian.get_note_by_name(note_name)
            if not note:
                return [types.TextContent(type="text", text=f"Note '{note_name}' not found")]
            
            response = f"**{note['title']}**\n\n"
            response += f"**Path:** {note['path']}\n"
            response += f"**Created:** {note['created']}\n"
            response += f"**Modified:** {note['modified']}\n"
            response += f"**Size:** {note['size']} bytes\n"
            
            if note['tags']:
                response += f"**Tags:** {', '.join(note['tags'])}\n"
            
            if note['frontmatter']:
                response += f"\n**Frontmatter:**\n```yaml\n{json.dumps(note['frontmatter'], indent=2)}\n```\n"
            
            if note['wikilinks']:
                response += f"\n**Links ({len(note['wikilinks'])}):**\n"
                for link in note['wikilinks'][:10]:  # Show first 10 links
                    response += f"- [[{link['target']}]]"
                    if link['header']:
                        response += f"#{link['header']}"
                    if link['display'] != link['target']:
                        response += f" (displayed as: {link['display']})"
                    response += "\n"
                if len(note['wikilinks']) > 10:
                    response += f"... and {len(note['wikilinks']) - 10} more links\n"
            
            if note['headers']:
                response += f"\n**Headers ({len(note['headers'])}):**\n"
                for header in note['headers']:
                    indent = "  " * (header['level'] - 1)
                    response += f"{indent}- {header['text']} (H{header['level']})\n"
            
            response += f"\n**Content:**\n{note['content']}"
            
            return [types.TextContent(type="text", text=response)]
        
        elif name == "get_notes_by_tag":
            tag = arguments.get("tag")
            if not tag:
                return [types.TextContent(type="text", text="Error: tag is required")]
            
            notes = obsidian.get_notes_by_tag(tag)
            
            if not notes:
                return [types.TextContent(type="text", text=f"No notes found with tag '{tag}'")]
            
            response = f"Found {len(notes)} note(s) with tag '{tag}':\n\n"
            for note in notes:
                response += f"**{note['title']}**\n"
                response += f"Path: {note['path']}\n"
                response += f"Modified: {note['modified']}\n"
                if note['tags']:
                    response += f"All tags: {', '.join(note['tags'])}\n"
                response += "\n"
            
            return [types.TextContent(type="text", text=response)]
        
        elif name == "get_note_backlinks":
            note_name = arguments.get("note_name")
            if not note_name:
                return [types.TextContent(type="text", text="Error: note_name is required")]
            
            backlinks = obsidian.scanner.get_backlinks(note_name)
            
            if not backlinks:
                return [types.TextContent(type="text", text=f"No backlinks found for note '{note_name}'")]
            
            response = f"Found {len(backlinks)} backlink(s) to '{note_name}':\n\n"
            for backlink in backlinks:
                response += f"**{backlink['source_note']}**\n"
                response += f"Path: {backlink['source_path']}\n"
                response += f"Link text: {backlink['link_text']}\n"
                if backlink['header']:
                    response += f"Linked to header: {backlink['header']}\n"
                response += "\n"
            
            return [types.TextContent(type="text", text=response)]
        
        elif name == "get_orphaned_notes":
            orphaned = obsidian.scanner.get_orphaned_notes()
            
            if not orphaned:
                return [types.TextContent(type="text", text="No orphaned notes found - all notes have links!")]
            
            response = f"Found {len(orphaned)} orphaned note(s) (no incoming or outgoing links):\n\n"
            for note in orphaned:
                response += f"**{note['title']}**\n"
                response += f"Path: {note['path']}\n"
                response += f"Modified: {note['modified']}\n"
                response += f"Size: {note['size']} bytes\n"
                response += "\n"
            
            return [types.TextContent(type="text", text=response)]
        
        elif name == "get_note_links":
            note_name = arguments.get("note_name")
            if not note_name:
                return [types.TextContent(type="text", text="Error: note_name is required")]
            
            note = obsidian.get_note_by_name(note_name)
            if not note:
                return [types.TextContent(type="text", text=f"Note '{note_name}' not found")]
            
            links = note['wikilinks']
            
            if not links:
                return [types.TextContent(type="text", text=f"No links found in note '{note_name}'")]
            
            response = f"Found {len(links)} link(s) in '{note_name}':\n\n"
            for link in links:
                response += f"**[[{link['target']}]]**\n"
                if link['header']:
                    response += f"Header: #{link['header']}\n"
                if link['display'] != link['target']:
                    response += f"Display text: {link['display']}\n"
                response += "\n"
            
            return [types.TextContent(type="text", text=response)]
        
        elif name == "extract_note_headers":
            note_name = arguments.get("note_name")
            if not note_name:
                return [types.TextContent(type="text", text="Error: note_name is required")]
            
            note = obsidian.get_note_by_name(note_name)
            if not note:
                return [types.TextContent(type="text", text=f"Note '{note_name}' not found")]
            
            headers = note['headers']
            
            if not headers:
                return [types.TextContent(type="text", text=f"No headers found in note '{note_name}'")]
            
            response = f"Found {len(headers)} header(s) in '{note_name}':\n\n"
            for header in headers:
                indent = "  " * (header['level'] - 1)
                response += f"{indent}**H{header['level']}:** {header['text']}\n"
                response += f"{indent}Line: {header['line_number']}\n"
                response += f"{indent}Anchor: #{header['anchor']}\n\n"
            
            return [types.TextContent(type="text", text=response)]
        
        elif name == "extract_note_blocks":
            note_name = arguments.get("note_name")
            block_types = arguments.get("block_types")
            
            if not note_name:
                return [types.TextContent(type="text", text="Error: note_name is required")]
            
            note = obsidian.get_note_by_name(note_name)
            if not note:
                return [types.TextContent(type="text", text=f"Note '{note_name}' not found")]
            
            blocks = note['blocks']
            
            if block_types:
                blocks = [block for block in blocks if block['type'] in block_types]
            
            if not blocks:
                filter_msg = f" of type(s) {', '.join(block_types)}" if block_types else ""
                return [types.TextContent(type="text", text=f"No blocks{filter_msg} found in note '{note_name}'")]
            
            response = f"Found {len(blocks)} block(s) in '{note_name}':\n\n"
            for i, block in enumerate(blocks, 1):
                response += f"**Block {i} ({block['type']})**\n"
                response += f"Lines {block['start_line']}-{block['end_line']}:\n"
                if block['type'] == 'code' and 'language' in block:
                    response += f"Language: {block['language']}\n"
                response += f"```\n{block['content']}\n```\n\n"
            
            return [types.TextContent(type="text", text=response)]
        
        elif name == "get_notes_for_flashcards":
            note_names = arguments.get("note_names", [])
            tag_filter = arguments.get("tag_filter")
            content_types = arguments.get("content_types", ["headers", "definitions", "lists", "quotes"])
            
            # Get notes to process
            if tag_filter:
                notes_to_process = obsidian.get_notes_by_tag(tag_filter)
            elif note_names:
                notes_to_process = []
                for name in note_names:
                    note = obsidian.get_note_by_name(name)
                    if note:
                        notes_to_process.append(note)
            else:
                return [types.TextContent(type="text", text="Error: Either note_names or tag_filter must be provided")]
            
            if not notes_to_process:
                return [types.TextContent(type="text", text="No notes found to process")]
            
            all_flashcard_content = []
            for note in notes_to_process:
                flashcard_content = obsidian.extract_content_for_flashcards(note, content_types)
                all_flashcard_content.extend(flashcard_content)
            
            if not all_flashcard_content:
                return [types.TextContent(type="text", text="No suitable content found for flashcards")]
            
            response = f"Extracted {len(all_flashcard_content)} potential flashcard(s) from {len(notes_to_process)} note(s):\n\n"
            
            for i, content in enumerate(all_flashcard_content[:20], 1):  # Show first 20
                response += f"**Flashcard {i} ({content['type']})**\n"
                response += f"Source: {content['source_note']}"
                if 'source_line' in content:
                    response += f" (line {content['source_line']})"
                response += "\n"
                
                if content['type'] == 'header':
                    response += f"Q: {content['question']}\n"
                    response += f"Context: {content['context']}\n"
                elif 'content' in content:
                    response += f"Content: {content['content']}\n"
                
                if 'context' in content and content['type'] != 'header':
                    response += f"Context: {content['context']}\n"
                
                response += "\n"
            
            if len(all_flashcard_content) > 20:
                response += f"... and {len(all_flashcard_content) - 20} more potential flashcards\n"
            
            return [types.TextContent(type="text", text=response)]
        
        else:
            return [types.TextContent(type="text", text=f"Unknown tool: {name}")]
    
    except Exception as e:
        return [types.TextContent(type="text", text=f"Error executing {name}: {str(e)}")]

async def main():
    """Run the Obsidian MCP server."""
    from mcp.server.stdio import stdio_server
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="obsidian-mcp-server",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())