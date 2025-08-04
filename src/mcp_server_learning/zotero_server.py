#!/usr/bin/env python3

import os
from typing import Dict, List, Any, Optional
from pyzotero import zotero
import json

class ZoteroMCPServer:
    """Simplified Zotero MCP server using pyzotero with environment-based configuration."""
    
    def __init__(self):
        self.api_key = os.getenv('ZOTERO_API_KEY')
        self.library_id = os.getenv('ZOTERO_LIBRARY_ID')
        self.library_type = os.getenv('ZOTERO_LIBRARY_TYPE', 'user')
        
        if not self.api_key or not self.library_id:
            raise ValueError("ZOTERO_API_KEY and ZOTERO_LIBRARY_ID environment variables must be set")
        
        if self.library_type not in ['user', 'group']:
            raise ValueError("ZOTERO_LIBRARY_TYPE must be 'user' or 'group'")
        
        # Initialize pyzotero client
        self.zot = zotero.Zotero(self.library_id, self.library_type, self.api_key)
    
    def search_items(self, query: str, limit: int = 50, item_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for items in the Zotero library."""
        try:
            params = {'limit': limit}
            if query:
                params['q'] = query
            if item_type:
                params['itemType'] = item_type
            
            items = self.zot.items(**params)
            return [self._format_item(item) for item in items]
        except Exception as e:
            raise Exception(f"Failed to search Zotero items: {str(e)}")
    
    def get_item(self, item_key: str) -> Optional[Dict[str, Any]]:
        """Get a specific item by its key."""
        try:
            item = self.zot.item(item_key)
            return self._format_item(item)
        except Exception as e:
            raise Exception(f"Failed to get Zotero item {item_key}: {str(e)}")
    
    def get_item_notes(self, item_key: str) -> List[Dict[str, Any]]:
        """Get all notes associated with an item."""
        try:
            children = self.zot.children(item_key)
            notes = [child for child in children if child['data'].get('itemType') == 'note']
            return [self._format_note(note) for note in notes]
        except Exception as e:
            raise Exception(f"Failed to get notes for item {item_key}: {str(e)}")
    
    def list_collections(self) -> List[Dict[str, Any]]:
        """List all collections in the library."""
        try:
            collections = self.zot.collections()
            return [self._format_collection(collection) for collection in collections]
        except Exception as e:
            raise Exception(f"Failed to list collections: {str(e)}")
    
    def get_collection_items(self, collection_key: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get items from a specific collection."""
        try:
            items = self.zot.collection_items(collection_key, limit=limit)
            return [self._format_item(item) for item in items]
        except Exception as e:
            raise Exception(f"Failed to get items from collection {collection_key}: {str(e)}")
    
    def create_item(self, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new item in the library."""
        try:
            # Validate required fields based on item type
            item_type = item_data.get('itemType', 'document')
            
            # Create the item using pyzotero
            created_items = self.zot.create_items([item_data])
            
            if not created_items['successful']:
                raise Exception(f"Failed to create item: {created_items.get('failed', {})}")
            
            # Return the created item's key
            return {
                'success': True,
                'item_key': created_items['successful']['0']['key'],
                'message': 'Item created successfully'
            }
        except Exception as e:
            raise Exception(f"Failed to create Zotero item: {str(e)}")
    
    def create_note(self, parent_item_key: str, note_content: str) -> Dict[str, Any]:
        """Create a note attached to an existing item."""
        try:
            note_data = {
                'itemType': 'note',
                'parentItem': parent_item_key,
                'note': note_content
            }
            
            created_items = self.zot.create_items([note_data])
            
            if not created_items['successful']:
                raise Exception(f"Failed to create note: {created_items.get('failed', {})}")
            
            return {
                'success': True,
                'note_key': created_items['successful']['0']['key'],
                'message': 'Note created successfully'
            }
        except Exception as e:
            raise Exception(f"Failed to create note: {str(e)}")
    
    def add_item_to_collection(self, item_key: str, collection_key: str) -> Dict[str, Any]:
        """Add an item to a collection."""
        try:
            result = self.zot.addto_collection(collection_key, item_key)
            return {
                'success': True,
                'message': f'Item {item_key} added to collection {collection_key}'
            }
        except Exception as e:
            raise Exception(f"Failed to add item to collection: {str(e)}")
    
    def get_item_templates(self) -> Dict[str, Any]:
        """Get available item templates for creating new items."""
        try:
            templates = self.zot.item_template('book')  # Get a sample template
            return {
                'book': self.zot.item_template('book'),
                'journalArticle': self.zot.item_template('journalArticle'),
                'webpage': self.zot.item_template('webpage'),
                'document': self.zot.item_template('document'),
                'thesis': self.zot.item_template('thesis')
            }
        except Exception as e:
            raise Exception(f"Failed to get item templates: {str(e)}")
    
    def _format_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Format a Zotero item for consistent output."""
        data = item.get('data', {})
        return {
            'key': data.get('key', ''),
            'itemType': data.get('itemType', ''),
            'title': data.get('title', ''),
            'creators': data.get('creators', []),
            'abstractNote': data.get('abstractNote', ''),
            'date': data.get('date', ''),
            'url': data.get('url', ''),
            'tags': [tag.get('tag', '') for tag in data.get('tags', [])],
            'collections': data.get('collections', []),
            'dateAdded': data.get('dateAdded', ''),
            'dateModified': data.get('dateModified', ''),
            'extra': data.get('extra', ''),
            'publicationTitle': data.get('publicationTitle', ''),
            'volume': data.get('volume', ''),
            'issue': data.get('issue', ''),
            'pages': data.get('pages', ''),
            'publisher': data.get('publisher', ''),
            'DOI': data.get('DOI', ''),
            'ISBN': data.get('ISBN', ''),
            'language': data.get('language', ''),
            'version': item.get('version', 0)
        }
    
    def _format_note(self, note: Dict[str, Any]) -> Dict[str, Any]:
        """Format a Zotero note for consistent output."""
        data = note.get('data', {})
        return {
            'key': data.get('key', ''),
            'itemType': 'note',
            'note': data.get('note', ''),
            'parentItem': data.get('parentItem', ''),
            'dateAdded': data.get('dateAdded', ''),
            'dateModified': data.get('dateModified', ''),
            'tags': [tag.get('tag', '') for tag in data.get('tags', [])]
        }
    
    def _format_collection(self, collection: Dict[str, Any]) -> Dict[str, Any]:
        """Format a Zotero collection for consistent output."""
        data = collection.get('data', {})
        return {
            'key': data.get('key', ''),
            'name': data.get('name', ''),
            'parentCollection': data.get('parentCollection', ''),
            'relations': data.get('relations', {}),
            'version': collection.get('version', 0)
        }

# Global instance - will be initialized when first used
_zotero_server: Optional[ZoteroMCPServer] = None

def get_zotero_server() -> ZoteroMCPServer:
    """Get or create the global Zotero server instance."""
    global _zotero_server
    if _zotero_server is None:
        _zotero_server = ZoteroMCPServer()
    return _zotero_server