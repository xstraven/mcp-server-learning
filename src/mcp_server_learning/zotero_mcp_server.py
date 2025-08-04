#!/usr/bin/env python3

import asyncio
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
from .zotero_server import get_zotero_server

server = Server("zotero-mcp-server")

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available Zotero tools."""
    return [
        Tool(
            name="search_zotero_items",
            description="Search for items in the Zotero library",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for Zotero items",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 50)",
                        "default": 50,
                    },
                    "item_type": {
                        "type": "string",
                        "description": "Filter by item type (e.g., 'book', 'journalArticle', 'webpage')",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_zotero_item",
            description="Get detailed information about a specific Zotero item",
            inputSchema={
                "type": "object",
                "properties": {
                    "item_key": {
                        "type": "string",
                        "description": "The Zotero item key",
                    },
                },
                "required": ["item_key"],
            },
        ),
        Tool(
            name="get_item_notes",
            description="Get all notes associated with a Zotero item",
            inputSchema={
                "type": "object",
                "properties": {
                    "item_key": {
                        "type": "string",
                        "description": "The Zotero item key",
                    },
                },
                "required": ["item_key"],
            },
        ),
        Tool(
            name="list_zotero_collections",
            description="List all collections in the Zotero library",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="get_collection_items",
            description="Get items from a specific collection",
            inputSchema={
                "type": "object",
                "properties": {
                    "collection_key": {
                        "type": "string",
                        "description": "The collection key",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 50)",
                        "default": 50,
                    },
                },
                "required": ["collection_key"],
            },
        ),
        Tool(
            name="create_zotero_item",
            description="Create a new item in the Zotero library",
            inputSchema={
                "type": "object",
                "properties": {
                    "item_type": {
                        "type": "string",
                        "description": "Type of item to create (e.g., 'book', 'journalArticle', 'webpage')",
                    },
                    "title": {
                        "type": "string",
                        "description": "Title of the item",
                    },
                    "creators": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "creatorType": {"type": "string"},
                                "firstName": {"type": "string"},
                                "lastName": {"type": "string"},
                            },
                        },
                        "description": "List of creators (authors, editors, etc.)",
                    },
                    "date": {
                        "type": "string",
                        "description": "Publication date",
                    },
                    "url": {
                        "type": "string",
                        "description": "URL of the item",
                    },
                    "abstract": {
                        "type": "string",
                        "description": "Abstract or summary",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags to add to the item",
                    },
                    "extra_fields": {
                        "type": "object",
                        "description": "Additional fields specific to the item type",
                    },
                },
                "required": ["item_type", "title"],
            },
        ),
        Tool(
            name="create_item_note",
            description="Create a note attached to an existing Zotero item",
            inputSchema={
                "type": "object",
                "properties": {
                    "parent_item_key": {
                        "type": "string",
                        "description": "The key of the parent item to attach the note to",
                    },
                    "note_content": {
                        "type": "string",
                        "description": "The content of the note (HTML formatted)",
                    },
                },
                "required": ["parent_item_key", "note_content"],
            },
        ),
        Tool(
            name="add_item_to_collection",
            description="Add an item to a collection",
            inputSchema={
                "type": "object",
                "properties": {
                    "item_key": {
                        "type": "string",
                        "description": "The key of the item to add",
                    },
                    "collection_key": {
                        "type": "string",
                        "description": "The key of the collection",
                    },
                },
                "required": ["item_key", "collection_key"],
            },
        ),
        Tool(
            name="get_item_templates",
            description="Get templates for creating new items of different types",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool calls."""
    
    try:
        zotero = get_zotero_server()
    except Exception as e:
        return [
            types.TextContent(
                type="text",
                text=f"Error connecting to Zotero: {str(e)}\n\nPlease ensure the following environment variables are set:\n- ZOTERO_API_KEY\n- ZOTERO_LIBRARY_ID\n- ZOTERO_LIBRARY_TYPE (user or group)"
            )
        ]
    
    try:
        if name == "search_zotero_items":
            query = arguments.get("query", "")
            limit = arguments.get("limit", 50)
            item_type = arguments.get("item_type")
            
            items = zotero.search_items(query, limit, item_type)
            
            if not items:
                return [types.TextContent(type="text", text="No items found matching your search.")]
            
            response = f"Found {len(items)} items:\n\n"
            for item in items:
                creators = item.get('creators', [])
                creator_names = []
                for creator in creators[:2]:  # Show first 2 creators
                    if 'lastName' in creator:
                        creator_names.append(creator['lastName'])
                    elif 'name' in creator:
                        creator_names.append(creator['name'])
                
                creators_str = ", ".join(creator_names)
                if len(creators) > 2:
                    creators_str += f" et al."
                
                response += f"**{item['title']}**\n"
                response += f"Key: {item['key']}\n"
                response += f"Type: {item['itemType']}\n"
                if creators_str:
                    response += f"Authors: {creators_str}\n"
                if item['date']:
                    response += f"Date: {item['date']}\n"
                if item['tags']:
                    response += f"Tags: {', '.join(item['tags'])}\n"
                response += "\n"
            
            return [types.TextContent(type="text", text=response)]
        
        elif name == "get_zotero_item":
            item_key = arguments.get("item_key")
            if not item_key:
                return [types.TextContent(type="text", text="Error: item_key is required")]
            
            item = zotero.get_item(item_key)
            if not item:
                return [types.TextContent(type="text", text=f"Item with key '{item_key}' not found")]
            
            # Format detailed item information
            response = f"**{item['title']}**\n\n"
            response += f"Key: {item['key']}\n"
            response += f"Type: {item['itemType']}\n"
            
            if item['creators']:
                response += "\n**Creators:**\n"
                for creator in item['creators']:
                    creator_type = creator.get('creatorType', 'author')
                    if 'lastName' in creator:
                        name = f"{creator.get('firstName', '')} {creator['lastName']}".strip()
                    else:
                        name = creator.get('name', 'Unknown')
                    response += f"- {name} ({creator_type})\n"
            
            if item['date']:
                response += f"\n**Date:** {item['date']}\n"
            if item['publicationTitle']:
                response += f"**Publication:** {item['publicationTitle']}\n"
            if item['volume']:
                response += f"**Volume:** {item['volume']}\n"
            if item['issue']:
                response += f"**Issue:** {item['issue']}\n"
            if item['pages']:
                response += f"**Pages:** {item['pages']}\n"
            if item['publisher']:
                response += f"**Publisher:** {item['publisher']}\n"
            if item['url']:
                response += f"**URL:** {item['url']}\n"
            if item['DOI']:
                response += f"**DOI:** {item['DOI']}\n"
            if item['ISBN']:
                response += f"**ISBN:** {item['ISBN']}\n"
            
            if item['abstractNote']:
                response += f"\n**Abstract:**\n{item['abstractNote']}\n"
            
            if item['tags']:
                response += f"\n**Tags:** {', '.join(item['tags'])}\n"
            
            if item['extra']:
                response += f"\n**Extra:** {item['extra']}\n"
            
            response += f"\n**Added:** {item['dateAdded']}\n"
            response += f"**Modified:** {item['dateModified']}\n"
            
            return [types.TextContent(type="text", text=response)]
        
        elif name == "get_item_notes":
            item_key = arguments.get("item_key")
            if not item_key:
                return [types.TextContent(type="text", text="Error: item_key is required")]
            
            notes = zotero.get_item_notes(item_key)
            
            if not notes:
                return [types.TextContent(type="text", text=f"No notes found for item '{item_key}'")]
            
            response = f"Found {len(notes)} note(s) for item '{item_key}':\n\n"
            for i, note in enumerate(notes, 1):
                response += f"**Note {i}:**\n"
                response += f"Key: {note['key']}\n"
                response += f"Added: {note['dateAdded']}\n"
                response += f"Content:\n{note['note']}\n\n"
            
            return [types.TextContent(type="text", text=response)]
        
        elif name == "list_zotero_collections":
            collections = zotero.list_collections()
            
            if not collections:
                return [types.TextContent(type="text", text="No collections found")]
            
            response = f"Found {len(collections)} collection(s):\n\n"
            for collection in collections:
                response += f"**{collection['name']}**\n"
                response += f"Key: {collection['key']}\n"
                if collection['parentCollection']:
                    response += f"Parent: {collection['parentCollection']}\n"
                response += "\n"
            
            return [types.TextContent(type="text", text=response)]
        
        elif name == "get_collection_items":
            collection_key = arguments.get("collection_key")
            limit = arguments.get("limit", 50)
            
            if not collection_key:
                return [types.TextContent(type="text", text="Error: collection_key is required")]
            
            items = zotero.get_collection_items(collection_key, limit)
            
            if not items:
                return [types.TextContent(type="text", text=f"No items found in collection '{collection_key}'")]
            
            response = f"Found {len(items)} item(s) in collection:\n\n"
            for item in items:
                response += f"**{item['title']}**\n"
                response += f"Key: {item['key']}\n"
                response += f"Type: {item['itemType']}\n\n"
            
            return [types.TextContent(type="text", text=response)]
        
        elif name == "create_zotero_item":
            item_type = arguments.get("item_type")
            title = arguments.get("title")
            creators = arguments.get("creators", [])
            date = arguments.get("date", "")
            url = arguments.get("url", "")
            abstract = arguments.get("abstract", "")
            tags = arguments.get("tags", [])
            extra_fields = arguments.get("extra_fields", {})
            
            if not item_type or not title:
                return [types.TextContent(type="text", text="Error: item_type and title are required")]
            
            # Build item data
            item_data = {
                "itemType": item_type,
                "title": title,
                "creators": creators,
                "date": date,
                "url": url,
                "abstractNote": abstract,
                "tags": [{"tag": tag} for tag in tags],
                **extra_fields
            }
            
            result = zotero.create_item(item_data)
            
            return [types.TextContent(
                type="text", 
                text=f"Successfully created item!\nKey: {result['item_key']}\nTitle: {title}"
            )]
        
        elif name == "create_item_note":
            parent_item_key = arguments.get("parent_item_key")
            note_content = arguments.get("note_content")
            
            if not parent_item_key or not note_content:
                return [types.TextContent(type="text", text="Error: parent_item_key and note_content are required")]
            
            result = zotero.create_note(parent_item_key, note_content)
            
            return [types.TextContent(
                type="text",
                text=f"Successfully created note!\nNote Key: {result['note_key']}\nAttached to: {parent_item_key}"
            )]
        
        elif name == "add_item_to_collection":
            item_key = arguments.get("item_key")
            collection_key = arguments.get("collection_key")
            
            if not item_key or not collection_key:
                return [types.TextContent(type="text", text="Error: item_key and collection_key are required")]
            
            result = zotero.add_item_to_collection(item_key, collection_key)
            
            return [types.TextContent(type="text", text=result['message'])]
        
        elif name == "get_item_templates":
            templates = zotero.get_item_templates()
            
            response = "Available item templates:\n\n"
            for item_type, template in templates.items():
                response += f"**{item_type}:**\n"
                response += f"```json\n{json.dumps(template, indent=2)}\n```\n\n"
            
            return [types.TextContent(type="text", text=response)]
        
        else:
            return [types.TextContent(type="text", text=f"Unknown tool: {name}")]
    
    except Exception as e:
        return [types.TextContent(type="text", text=f"Error executing {name}: {str(e)}")]

async def main():
    """Run the Zotero MCP server."""
    from mcp.server.stdio import stdio_server
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="zotero-mcp-server",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())