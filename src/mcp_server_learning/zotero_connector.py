#!/usr/bin/env python3

import os
import sqlite3
import json
import requests
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from pathlib import Path
import re

class ZoteroWebAPI:
    """Interface for connecting to Zotero Web API."""
    
    def __init__(self, api_key: str, user_id: Optional[str] = None, group_id: Optional[str] = None):
        self.api_key = api_key
        self.user_id = user_id
        self.group_id = group_id
        self.base_url = "https://api.zotero.org"
        self.session = requests.Session()
        self.session.headers.update({
            "Zotero-API-Key": api_key,
            "User-Agent": "MCP-Learning-Server/1.0"
        })
    
    def _get_library_path(self) -> str:
        """Get the library path for API requests."""
        if self.user_id:
            return f"users/{self.user_id}"
        elif self.group_id:
            return f"groups/{self.group_id}"
        else:
            raise ValueError("Either user_id or group_id must be provided")
    
    def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make a request to the Zotero Web API."""
        if params is None:
            params = {}
        
        url = f"{self.base_url}/{self._get_library_path()}/{endpoint}"
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 5))
                raise Exception(f"Rate limited. Retry after {retry_after} seconds")
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to connect to Zotero API: {e}")
    
    def get_collections(self) -> List[Dict[str, Any]]:
        """Get all collections in the library."""
        return self._make_request("collections")
    
    def get_items(self, collection_key: str = None, limit: int = 100, start: int = 0) -> List[Dict[str, Any]]:
        """Get items from the library."""
        params = {"limit": limit, "start": start}
        
        endpoint = "items"
        if collection_key:
            endpoint = f"collections/{collection_key}/items"
        
        return self._make_request(endpoint, params)
    
    def search_items(self, query: str, item_type: str = None, tag: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Search for items in the library."""
        params = {"q": query, "limit": limit}
        
        if item_type:
            params["itemType"] = item_type
        if tag:
            params["tag"] = tag
        
        return self._make_request("items", params)
    
    def get_item_children(self, item_key: str) -> List[Dict[str, Any]]:
        """Get child items (attachments, notes) for a specific item."""
        return self._make_request(f"items/{item_key}/children")
    
    def get_tags(self) -> List[Dict[str, Any]]:
        """Get all tags in the library."""
        return self._make_request("tags")

class ZoteroLocalDB:
    """Interface for reading from local Zotero SQLite database."""
    
    def __init__(self, profile_path: str = None):
        self.profile_path = profile_path or self._find_zotero_profile()
        self.db_path = os.path.join(self.profile_path, "zotero.sqlite")
        
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Zotero database not found at {self.db_path}")
    
    def _find_zotero_profile(self) -> str:
        """Attempt to find the Zotero profile directory."""
        system = os.name
        
        if system == "nt":  # Windows
            profile_dir = os.path.expanduser("~/Zotero")
        elif system == "posix":  # macOS/Linux
            if os.path.exists(os.path.expanduser("~/Zotero")):
                profile_dir = os.path.expanduser("~/Zotero")
            else:
                profile_dir = os.path.expanduser("~/.zotero/zotero")
        else:
            raise Exception("Unsupported operating system")
        
        if not os.path.exists(profile_dir):
            raise FileNotFoundError(f"Zotero profile directory not found. Expected: {profile_dir}")
        
        return profile_dir
    
    def _execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute a SQL query and return results as dictionaries."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_items(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get items from the local database."""
        query = """
        SELECT i.itemID, i.itemTypeID, i.key, i.dateAdded, i.dateModified,
               it.typeName, f.fieldName, iv.value
        FROM items i
        LEFT JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
        LEFT JOIN itemData id ON i.itemID = id.itemID
        LEFT JOIN fields f ON id.fieldID = f.fieldID
        LEFT JOIN itemDataValues iv ON id.valueID = iv.valueID
        WHERE i.itemTypeID != 1 AND i.itemTypeID != 14  -- Exclude notes and attachments
        ORDER BY i.dateAdded DESC
        LIMIT ? OFFSET ?
        """
        
        rows = self._execute_query(query, (limit, offset))
        
        # Group by item
        items = {}
        for row in rows:
            item_id = row['itemID']
            if item_id not in items:
                items[item_id] = {
                    'itemID': item_id,
                    'key': row['key'],
                    'itemType': row['typeName'],
                    'dateAdded': row['dateAdded'],
                    'dateModified': row['dateModified'],
                    'data': {}
                }
            
            if row['fieldName'] and row['value']:
                items[item_id]['data'][row['fieldName']] = row['value']
        
        return list(items.values())
    
    def search_items(self, query: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Search items in the local database."""
        search_query = """
        SELECT DISTINCT i.itemID, i.itemTypeID, i.key, i.dateAdded, i.dateModified,
               it.typeName
        FROM items i
        LEFT JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
        LEFT JOIN itemData id ON i.itemID = id.itemID
        LEFT JOIN itemDataValues iv ON id.valueID = iv.valueID
        WHERE i.itemTypeID != 1 AND i.itemTypeID != 14
        AND (iv.value LIKE ? OR i.key LIKE ?)
        ORDER BY i.dateAdded DESC
        LIMIT ?
        """
        
        search_term = f"%{query}%"
        rows = self._execute_query(search_query, (search_term, search_term, limit))
        
        # Get full item data for search results
        result_items = []
        for row in rows:
            item_data = self.get_item_by_id(row['itemID'])
            if item_data:
                result_items.append(item_data)
        
        return result_items
    
    def get_item_by_id(self, item_id: int) -> Dict[str, Any]:
        """Get a specific item by its ID."""
        query = """
        SELECT i.itemID, i.itemTypeID, i.key, i.dateAdded, i.dateModified,
               it.typeName, f.fieldName, iv.value
        FROM items i
        LEFT JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
        LEFT JOIN itemData id ON i.itemID = id.itemID
        LEFT JOIN fields f ON id.fieldID = f.fieldID
        LEFT JOIN itemDataValues iv ON id.valueID = iv.valueID
        WHERE i.itemID = ?
        """
        
        rows = self._execute_query(query, (item_id,))
        
        if not rows:
            return None
        
        item = {
            'itemID': item_id,
            'key': rows[0]['key'],
            'itemType': rows[0]['typeName'],
            'dateAdded': rows[0]['dateAdded'],
            'dateModified': rows[0]['dateModified'],
            'data': {}
        }
        
        for row in rows:
            if row['fieldName'] and row['value']:
                item['data'][row['fieldName']] = row['value']
        
        return item
    
    def get_collections(self) -> List[Dict[str, Any]]:
        """Get all collections from the local database."""
        query = """
        SELECT collectionID, collectionName, key, dateAdded, dateModified
        FROM collections
        ORDER BY collectionName
        """
        
        return self._execute_query(query)
    
    def get_collection_items(self, collection_id: int) -> List[Dict[str, Any]]:
        """Get items in a specific collection."""
        query = """
        SELECT DISTINCT i.itemID
        FROM items i
        JOIN collectionItems ci ON i.itemID = ci.itemID
        WHERE ci.collectionID = ? AND i.itemTypeID != 1 AND i.itemTypeID != 14
        ORDER BY i.dateAdded DESC
        """
        
        rows = self._execute_query(query, (collection_id,))
        
        items = []
        for row in rows:
            item_data = self.get_item_by_id(row['itemID'])
            if item_data:
                items.append(item_data)
        
        return items
    
    def get_item_tags(self, item_id: int) -> List[str]:
        """Get tags for a specific item."""
        query = """
        SELECT t.name
        FROM tags t
        JOIN itemTags it ON t.tagID = it.tagID
        WHERE it.itemID = ?
        ORDER BY t.name
        """
        
        rows = self._execute_query(query, (item_id,))
        return [row['name'] for row in rows]
    
    def get_item_notes(self, item_id: int) -> List[Dict[str, Any]]:
        """Get notes for a specific item."""
        query = """
        SELECT i.itemID, i.key, n.title, n.note
        FROM items i
        JOIN itemNotes n ON i.itemID = n.itemID
        WHERE n.parentItemID = ?
        ORDER BY i.dateAdded DESC
        """
        
        return self._execute_query(query, (item_id,))

class ZoteroCitationFormatter:
    """Formats Zotero items into various citation styles."""
    
    @staticmethod
    def format_apa(item_data: Dict[str, Any]) -> str:
        """Format item in APA style."""
        data = item_data.get('data', {})
        item_type = item_data.get('itemType', '')
        
        if item_type == 'book':
            return ZoteroCitationFormatter._format_book_apa(data)
        elif item_type == 'journalArticle':
            return ZoteroCitationFormatter._format_article_apa(data)
        elif item_type == 'webpage':
            return ZoteroCitationFormatter._format_webpage_apa(data)
        else:
            return ZoteroCitationFormatter._format_generic_apa(data)
    
    @staticmethod
    def _format_book_apa(data: Dict[str, Any]) -> str:
        """Format book in APA style."""
        author = data.get('author', 'Unknown Author')
        title = data.get('title', 'Unknown Title')
        publisher = data.get('publisher', '')
        date = data.get('date', '')
        
        year = ZoteroCitationFormatter._extract_year(date)
        
        citation = f"{author} ({year}). *{title}*"
        if publisher:
            citation += f". {publisher}"
        
        return citation + "."
    
    @staticmethod
    def _format_article_apa(data: Dict[str, Any]) -> str:
        """Format journal article in APA style."""
        author = data.get('author', 'Unknown Author')
        title = data.get('title', 'Unknown Title')
        journal = data.get('publicationTitle', '')
        volume = data.get('volume', '')
        issue = data.get('issue', '')
        pages = data.get('pages', '')
        date = data.get('date', '')
        
        year = ZoteroCitationFormatter._extract_year(date)
        
        citation = f"{author} ({year}). {title}. *{journal}*"
        
        if volume:
            citation += f", {volume}"
        if issue:
            citation += f"({issue})"
        if pages:
            citation += f", {pages}"
        
        return citation + "."
    
    @staticmethod
    def _format_webpage_apa(data: Dict[str, Any]) -> str:
        """Format webpage in APA style."""
        author = data.get('author', data.get('websiteTitle', 'Unknown Author'))
        title = data.get('title', 'Unknown Title')
        url = data.get('url', '')
        date = data.get('date', '')
        access_date = data.get('accessDate', '')
        
        year = ZoteroCitationFormatter._extract_year(date)
        
        citation = f"{author} ({year}). {title}"
        if url:
            citation += f". Retrieved from {url}"
        
        return citation
    
    @staticmethod
    def _format_generic_apa(data: Dict[str, Any]) -> str:
        """Format generic item in APA style."""
        author = data.get('author', 'Unknown Author')
        title = data.get('title', 'Unknown Title')
        date = data.get('date', '')
        
        year = ZoteroCitationFormatter._extract_year(date)
        
        return f"{author} ({year}). {title}."
    
    @staticmethod
    def _extract_year(date_string: str) -> str:
        """Extract year from date string."""
        if not date_string:
            return "n.d."
        
        year_match = re.search(r'\b(19|20)\d{2}\b', date_string)
        return year_match.group(0) if year_match else "n.d."

class ZoteroConnector:
    """Main connector class that provides unified access to Zotero data."""
    
    def __init__(self, api_key: str = None, user_id: str = None, group_id: str = None, 
                 local_profile_path: str = None, prefer_local: bool = True):
        self.prefer_local = prefer_local
        self.web_api = None
        self.local_db = None
        
        # Initialize Web API if credentials provided
        if api_key and (user_id or group_id):
            self.web_api = ZoteroWebAPI(api_key, user_id, group_id)
        
        # Initialize local database if available
        try:
            self.local_db = ZoteroLocalDB(local_profile_path)
        except (FileNotFoundError, Exception):
            self.local_db = None
        
        if not self.web_api and not self.local_db:
            raise Exception("No Zotero access method available. Provide API credentials or ensure local Zotero installation.")
    
    def get_items(self, limit: int = 100, offset: int = 0, collection_key: str = None) -> List[Dict[str, Any]]:
        """Get items using preferred method."""
        if self.prefer_local and self.local_db:
            return self.local_db.get_items(limit, offset)
        elif self.web_api:
            return self.web_api.get_items(collection_key, limit, offset)
        elif self.local_db:
            return self.local_db.get_items(limit, offset)
        else:
            raise Exception("No Zotero access method available")
    
    def search_items(self, query: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Search items using preferred method."""
        if self.prefer_local and self.local_db:
            return self.local_db.search_items(query, limit)
        elif self.web_api:
            return self.web_api.search_items(query, limit=limit)
        elif self.local_db:
            return self.local_db.search_items(query, limit)
        else:
            raise Exception("No Zotero access method available")
    
    def get_collections(self) -> List[Dict[str, Any]]:
        """Get collections using preferred method."""
        if self.prefer_local and self.local_db:
            return self.local_db.get_collections()
        elif self.web_api:
            return self.web_api.get_collections()
        elif self.local_db:
            return self.local_db.get_collections()
        else:
            raise Exception("No Zotero access method available")
    
    def format_citation(self, item_data: Dict[str, Any], style: str = "apa") -> str:
        """Format an item as a citation."""
        if style.lower() == "apa":
            return ZoteroCitationFormatter.format_apa(item_data)
        else:
            raise ValueError(f"Unsupported citation style: {style}")
    
    def get_item_metadata(self, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract structured metadata from an item."""
        data = item_data.get('data', {})
        
        metadata = {
            'title': data.get('title', 'Unknown Title'),
            'authors': data.get('author', 'Unknown Author'),
            'year': ZoteroCitationFormatter._extract_year(data.get('date', '')),
            'item_type': item_data.get('itemType', 'unknown'),
            'abstract': data.get('abstractNote', ''),
            'tags': [],
            'url': data.get('url', ''),
            'doi': data.get('DOI', ''),
            'key': item_data.get('key', ''),
            'date_added': item_data.get('dateAdded', ''),
            'date_modified': item_data.get('dateModified', '')
        }
        
        # Get tags if using local database
        if self.local_db and 'itemID' in item_data:
            metadata['tags'] = self.local_db.get_item_tags(item_data['itemID'])
        
        return metadata
    
    def is_available(self) -> Dict[str, bool]:
        """Check which access methods are available."""
        return {
            'web_api': self.web_api is not None,
            'local_db': self.local_db is not None
        }