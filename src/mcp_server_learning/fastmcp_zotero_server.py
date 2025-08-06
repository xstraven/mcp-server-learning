#!/usr/bin/env python3
"""
FastMCP-powered Zotero MCP Server

A modern, streamlined implementation of the Zotero MCP server using FastMCP's
Pythonic patterns for reduced boilerplate and improved maintainability.
"""

import json
import sys
from typing import Dict, List, Any, Optional
from fastmcp import FastMCP
from .zotero_server import get_zotero_server

# Initialize FastMCP instance
mcp = FastMCP("Zotero MCP Server")


@mcp.tool
def search_zotero_items(query: str, limit: int = 50, item_type: Optional[str] = None) -> str:
    """Search for items in the Zotero library"""
    zotero = get_zotero_server()
    items = zotero.search_items(query, limit, item_type)
    
    if not items:
        return "No items found matching your search."
    
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
    
    return response


@mcp.tool
def get_zotero_item(item_key: str) -> str:
    """Get detailed information about a specific Zotero item"""
    zotero = get_zotero_server()
    item = zotero.get_item(item_key)
    
    if not item:
        return f"Item with key '{item_key}' not found"
    
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
    
    return response


@mcp.tool
def get_item_notes(item_key: str) -> str:
    """Get all notes associated with a Zotero item"""
    zotero = get_zotero_server()
    notes = zotero.get_item_notes(item_key)
    
    if not notes:
        return f"No notes found for item '{item_key}'"
    
    response = f"Found {len(notes)} note(s) for item '{item_key}':\n\n"
    for i, note in enumerate(notes, 1):
        response += f"**Note {i}:**\n"
        response += f"Key: {note['key']}\n"
        response += f"Added: {note['dateAdded']}\n"
        response += f"Content:\n{note['note']}\n\n"
    
    return response


@mcp.tool
def list_zotero_collections() -> str:
    """List all collections in the Zotero library"""
    zotero = get_zotero_server()
    collections = zotero.list_collections()
    
    if not collections:
        return "No collections found"
    
    response = f"Found {len(collections)} collection(s):\n\n"
    for collection in collections:
        response += f"**{collection['name']}**\n"
        response += f"Key: {collection['key']}\n"
        if collection['parentCollection']:
            response += f"Parent: {collection['parentCollection']}\n"
        response += "\n"
    
    return response


@mcp.tool
def get_collection_items(collection_key: str, limit: int = 50) -> str:
    """Get items from a specific collection"""
    zotero = get_zotero_server()
    items = zotero.get_collection_items(collection_key, limit)
    
    if not items:
        return f"No items found in collection '{collection_key}'"
    
    response = f"Found {len(items)} item(s) in collection:\n\n"
    for item in items:
        response += f"**{item['title']}**\n"
        response += f"Key: {item['key']}\n"
        response += f"Type: {item['itemType']}\n\n"
    
    return response


@mcp.tool
def create_zotero_item(
    item_type: str,
    title: str,
    creators: Optional[List[Dict[str, Any]]] = None,
    date: str = "",
    url: str = "",
    abstract: str = "",
    tags: Optional[List[str]] = None,
    extra_fields: Optional[Dict[str, Any]] = None
) -> str:
    """Create a new item in the Zotero library"""
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
        **(extra_fields or {})
    }
    
    result = zotero.create_item(item_data)
    return f"Successfully created item!\nKey: {result['item_key']}\nTitle: {title}"


@mcp.tool
def create_item_note(parent_item_key: str, note_content: str) -> str:
    """Create a note attached to an existing Zotero item"""
    zotero = get_zotero_server()
    result = zotero.create_note(parent_item_key, note_content)
    
    return f"Successfully created note!\nNote Key: {result['note_key']}\nAttached to: {parent_item_key}"


@mcp.tool
def add_item_to_collection(item_key: str, collection_key: str) -> str:
    """Add an item to a collection"""
    zotero = get_zotero_server()
    result = zotero.add_item_to_collection(item_key, collection_key)
    
    return result['message']


@mcp.tool
def get_item_templates() -> str:
    """Get templates for creating new items of different types"""
    zotero = get_zotero_server()
    templates = zotero.get_item_templates()
    
    response = "Available item templates:\n\n"
    for item_type, template in templates.items():
        response += f"**{item_type}:**\n"
        response += f"```json\n{json.dumps(template, indent=2)}\n```\n\n"
    
    return response


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