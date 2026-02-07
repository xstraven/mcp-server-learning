"""
Tests for the FastMCP Zotero Server

Tests cover:
- Environment variable validation
- Item search and retrieval
- Note retrieval and creation
- Collection listing and item retrieval
- Item creation
"""

from unittest.mock import MagicMock, patch

import pytest

from mcp_server_learning import fastmcp_zotero_server as zotero_server
from mcp_server_learning.zotero_server import ZoteroMCPServer, get_zotero_server


class MockZoteroClient:
    """Mock pyzotero client for testing."""

    def __init__(self):
        self.items_data = []
        self.collections_data = []
        self.notes_data = []

    def items(self, **params):
        return self.items_data

    def item(self, item_key):
        for item in self.items_data:
            if item.get("data", {}).get("key") == item_key:
                return item
        raise Exception(f"Item not found: {item_key}")

    def children(self, item_key):
        return self.notes_data

    def collections(self):
        return self.collections_data

    def collection_items(self, collection_key, limit=50):
        return self.items_data

    def create_items(self, items):
        return {
            "successful": {"0": {"key": "NEW123"}},
            "failed": {},
        }

    def addto_collection(self, collection_key, item_key):
        return True

    def item_template(self, item_type):
        return {"itemType": item_type, "title": "", "creators": []}


class TestZoteroServerConfiguration:
    """Test Zotero server environment configuration."""

    def test_missing_api_key_raises(self, monkeypatch):
        """Test that missing API key raises ValueError."""
        monkeypatch.delenv("ZOTERO_API_KEY", raising=False)
        monkeypatch.delenv("ZOTERO_LIBRARY_ID", raising=False)

        with pytest.raises(ValueError, match="ZOTERO_API_KEY"):
            ZoteroMCPServer()

    def test_missing_library_id_raises(self, monkeypatch):
        """Test that missing library ID raises ValueError."""
        monkeypatch.setenv("ZOTERO_API_KEY", "test_key")
        monkeypatch.delenv("ZOTERO_LIBRARY_ID", raising=False)

        with pytest.raises(ValueError, match="ZOTERO_LIBRARY_ID"):
            ZoteroMCPServer()

    def test_invalid_library_type_raises(self, monkeypatch):
        """Test that invalid library type raises ValueError."""
        monkeypatch.setenv("ZOTERO_API_KEY", "test_key")
        monkeypatch.setenv("ZOTERO_LIBRARY_ID", "123456")
        monkeypatch.setenv("ZOTERO_LIBRARY_TYPE", "invalid")

        with pytest.raises(ValueError, match="ZOTERO_LIBRARY_TYPE"):
            ZoteroMCPServer()


class TestSearchZoteroItems:
    """Test Zotero item search functionality."""

    @pytest.fixture
    def mock_server(self, monkeypatch):
        """Create a mock Zotero server."""
        monkeypatch.setenv("ZOTERO_API_KEY", "test_key")
        monkeypatch.setenv("ZOTERO_LIBRARY_ID", "123456")
        monkeypatch.setenv("ZOTERO_LIBRARY_TYPE", "user")

        mock_client = MockZoteroClient()
        mock_client.items_data = [
            {
                "data": {
                    "key": "ABC123",
                    "itemType": "journalArticle",
                    "title": "Test Article",
                    "creators": [{"firstName": "John", "lastName": "Doe"}],
                    "date": "2024",
                    "tags": [{"tag": "science"}],
                    "abstractNote": "An abstract",
                    "dateAdded": "2024-01-01",
                    "dateModified": "2024-01-02",
                }
            }
        ]

        with patch("mcp_server_learning.zotero_server.zotero.Zotero", return_value=mock_client):
            server = ZoteroMCPServer()
            yield server

    def test_search_returns_items(self, mock_server):
        """Test that search returns formatted items."""
        results = mock_server.search_items("test", limit=10)

        assert len(results) == 1
        assert results[0]["key"] == "ABC123"
        assert results[0]["title"] == "Test Article"
        assert results[0]["itemType"] == "journalArticle"

    def test_search_with_item_type_filter(self, mock_server):
        """Test search with item type filter."""
        results = mock_server.search_items("test", item_type="journalArticle")

        assert len(results) == 1

    def test_search_empty_results(self, mock_server):
        """Test search with no results."""
        mock_server.zot.items_data = []
        results = mock_server.search_items("nonexistent")

        assert len(results) == 0


class TestGetZoteroItem:
    """Test Zotero single item retrieval."""

    @pytest.fixture
    def mock_server(self, monkeypatch):
        """Create a mock Zotero server."""
        monkeypatch.setenv("ZOTERO_API_KEY", "test_key")
        monkeypatch.setenv("ZOTERO_LIBRARY_ID", "123456")
        monkeypatch.setenv("ZOTERO_LIBRARY_TYPE", "user")

        mock_client = MockZoteroClient()
        mock_client.items_data = [
            {
                "data": {
                    "key": "ABC123",
                    "itemType": "book",
                    "title": "Test Book",
                    "creators": [{"name": "Author Name"}],
                    "date": "2023",
                    "tags": [],
                    "abstractNote": "",
                    "dateAdded": "2023-01-01",
                    "dateModified": "2023-01-02",
                    "publisher": "Test Publisher",
                    "ISBN": "1234567890",
                }
            }
        ]

        with patch("mcp_server_learning.zotero_server.zotero.Zotero", return_value=mock_client):
            server = ZoteroMCPServer()
            yield server

    def test_get_item_returns_formatted_item(self, mock_server):
        """Test that get_item returns properly formatted item."""
        item = mock_server.get_item("ABC123")

        assert item["key"] == "ABC123"
        assert item["title"] == "Test Book"
        assert item["itemType"] == "book"
        assert item["publisher"] == "Test Publisher"

    def test_get_item_not_found_raises(self, mock_server):
        """Test that get_item raises for non-existent item."""
        with pytest.raises(Exception, match="Failed to get Zotero item"):
            mock_server.get_item("NONEXISTENT")


class TestGetItemNotes:
    """Test Zotero note retrieval."""

    @pytest.fixture
    def mock_server(self, monkeypatch):
        """Create a mock Zotero server."""
        monkeypatch.setenv("ZOTERO_API_KEY", "test_key")
        monkeypatch.setenv("ZOTERO_LIBRARY_ID", "123456")
        monkeypatch.setenv("ZOTERO_LIBRARY_TYPE", "user")

        mock_client = MockZoteroClient()
        mock_client.notes_data = [
            {
                "data": {
                    "key": "NOTE123",
                    "itemType": "note",
                    "note": "<p>This is a test note</p>",
                    "parentItem": "ABC123",
                    "dateAdded": "2024-01-01",
                    "dateModified": "2024-01-02",
                    "tags": [{"tag": "important"}],
                }
            }
        ]

        with patch("mcp_server_learning.zotero_server.zotero.Zotero", return_value=mock_client):
            server = ZoteroMCPServer()
            yield server

    def test_get_notes_returns_formatted_notes(self, mock_server):
        """Test that get_item_notes returns formatted notes."""
        notes = mock_server.get_item_notes("ABC123")

        assert len(notes) == 1
        assert notes[0]["key"] == "NOTE123"
        assert notes[0]["note"] == "<p>This is a test note</p>"
        assert notes[0]["parentItem"] == "ABC123"

    def test_get_notes_empty(self, mock_server):
        """Test get_item_notes with no notes."""
        mock_server.zot.notes_data = []
        notes = mock_server.get_item_notes("ABC123")

        assert len(notes) == 0


class TestListZoteroCollections:
    """Test Zotero collection listing."""

    @pytest.fixture
    def mock_server(self, monkeypatch):
        """Create a mock Zotero server."""
        monkeypatch.setenv("ZOTERO_API_KEY", "test_key")
        monkeypatch.setenv("ZOTERO_LIBRARY_ID", "123456")
        monkeypatch.setenv("ZOTERO_LIBRARY_TYPE", "user")

        mock_client = MockZoteroClient()
        mock_client.collections_data = [
            {
                "data": {
                    "key": "COL123",
                    "name": "Research Papers",
                    "parentCollection": None,
                    "relations": {},
                },
                "version": 1,
            },
            {
                "data": {
                    "key": "COL456",
                    "name": "Sub Collection",
                    "parentCollection": "COL123",
                    "relations": {},
                },
                "version": 2,
            },
        ]

        with patch("mcp_server_learning.zotero_server.zotero.Zotero", return_value=mock_client):
            server = ZoteroMCPServer()
            yield server

    def test_list_collections_returns_all(self, mock_server):
        """Test that list_collections returns all collections."""
        collections = mock_server.list_collections()

        assert len(collections) == 2
        assert collections[0]["name"] == "Research Papers"
        assert collections[1]["parentCollection"] == "COL123"

    def test_list_collections_empty(self, mock_server):
        """Test list_collections with no collections."""
        mock_server.zot.collections_data = []
        collections = mock_server.list_collections()

        assert len(collections) == 0


class TestGetCollectionItems:
    """Test Zotero collection item retrieval."""

    @pytest.fixture
    def mock_server(self, monkeypatch):
        """Create a mock Zotero server."""
        monkeypatch.setenv("ZOTERO_API_KEY", "test_key")
        monkeypatch.setenv("ZOTERO_LIBRARY_ID", "123456")
        monkeypatch.setenv("ZOTERO_LIBRARY_TYPE", "user")

        mock_client = MockZoteroClient()
        mock_client.items_data = [
            {
                "data": {
                    "key": "ITEM1",
                    "itemType": "document",
                    "title": "Document 1",
                    "creators": [],
                    "tags": [],
                    "date": "2024",
                    "abstractNote": "",
                    "dateAdded": "2024-01-01",
                    "dateModified": "2024-01-02",
                }
            },
            {
                "data": {
                    "key": "ITEM2",
                    "itemType": "document",
                    "title": "Document 2",
                    "creators": [],
                    "tags": [],
                    "date": "2024",
                    "abstractNote": "",
                    "dateAdded": "2024-01-01",
                    "dateModified": "2024-01-02",
                }
            },
        ]

        with patch("mcp_server_learning.zotero_server.zotero.Zotero", return_value=mock_client):
            server = ZoteroMCPServer()
            yield server

    def test_get_collection_items_returns_items(self, mock_server):
        """Test that get_collection_items returns items in collection."""
        items = mock_server.get_collection_items("COL123", limit=10)

        assert len(items) == 2
        assert items[0]["title"] == "Document 1"


class TestCreateZoteroItem:
    """Test Zotero item creation."""

    @pytest.fixture
    def mock_server(self, monkeypatch):
        """Create a mock Zotero server."""
        monkeypatch.setenv("ZOTERO_API_KEY", "test_key")
        monkeypatch.setenv("ZOTERO_LIBRARY_ID", "123456")
        monkeypatch.setenv("ZOTERO_LIBRARY_TYPE", "user")

        mock_client = MockZoteroClient()

        with patch("mcp_server_learning.zotero_server.zotero.Zotero", return_value=mock_client):
            server = ZoteroMCPServer()
            yield server

    def test_create_item_success(self, mock_server):
        """Test successful item creation."""
        item_data = {
            "itemType": "book",
            "title": "New Book",
            "creators": [{"firstName": "Jane", "lastName": "Doe"}],
        }

        result = mock_server.create_item(item_data)

        assert result["success"] is True
        assert result["item_key"] == "NEW123"

    def test_create_item_failure(self, mock_server):
        """Test item creation failure."""
        mock_server.zot.create_items = lambda x: {"successful": {}, "failed": {"0": "error"}}

        with pytest.raises(Exception, match="Failed to create"):
            mock_server.create_item({"itemType": "book", "title": "Test"})


class TestCreateItemNote:
    """Test Zotero note creation."""

    @pytest.fixture
    def mock_server(self, monkeypatch):
        """Create a mock Zotero server."""
        monkeypatch.setenv("ZOTERO_API_KEY", "test_key")
        monkeypatch.setenv("ZOTERO_LIBRARY_ID", "123456")
        monkeypatch.setenv("ZOTERO_LIBRARY_TYPE", "user")

        mock_client = MockZoteroClient()

        with patch("mcp_server_learning.zotero_server.zotero.Zotero", return_value=mock_client):
            server = ZoteroMCPServer()
            yield server

    def test_create_note_success(self, mock_server):
        """Test successful note creation."""
        result = mock_server.create_note("ABC123", "This is my note content")

        assert result["success"] is True
        assert result["note_key"] == "NEW123"


class TestAddItemToCollection:
    """Test adding items to collections."""

    @pytest.fixture
    def mock_server(self, monkeypatch):
        """Create a mock Zotero server."""
        monkeypatch.setenv("ZOTERO_API_KEY", "test_key")
        monkeypatch.setenv("ZOTERO_LIBRARY_ID", "123456")
        monkeypatch.setenv("ZOTERO_LIBRARY_TYPE", "user")

        mock_client = MockZoteroClient()

        with patch("mcp_server_learning.zotero_server.zotero.Zotero", return_value=mock_client):
            server = ZoteroMCPServer()
            yield server

    def test_add_item_to_collection_success(self, mock_server):
        """Test successfully adding item to collection."""
        result = mock_server.add_item_to_collection("ITEM123", "COL123")

        assert result["success"] is True
        assert "ITEM123" in result["message"]
        assert "COL123" in result["message"]


class TestFastMCPZoteroTools:
    """Test the FastMCP tool functions for Zotero."""

    @pytest.fixture
    def mock_zotero_server(self, monkeypatch):
        """Mock the get_zotero_server function."""
        mock_server = MagicMock()
        mock_server.search_items.return_value = [
            {
                "key": "ABC123",
                "title": "Test Item",
                "itemType": "book",
                "creators": [{"lastName": "Smith"}],
                "date": "2024",
                "tags": ["test"],
            }
        ]
        mock_server.get_item.return_value = {
            "key": "ABC123",
            "title": "Test Item",
            "itemType": "book",
            "creators": [],
            "date": "2024",
            "publicationTitle": "",
            "volume": "",
            "issue": "",
            "pages": "",
            "publisher": "Publisher",
            "url": "",
            "DOI": "",
            "ISBN": "",
            "abstractNote": "Abstract",
            "tags": [],
            "extra": "",
            "dateAdded": "2024-01-01",
            "dateModified": "2024-01-02",
        }
        mock_server.get_item_notes.return_value = [
            {
                "key": "NOTE1",
                "note": "Note content",
                "dateAdded": "2024-01-01",
            }
        ]
        mock_server.list_collections.return_value = [
            {
                "key": "COL1",
                "name": "Collection",
                "parentCollection": None,
            }
        ]
        mock_server.get_collection_items.return_value = [
            {
                "key": "ITEM1",
                "title": "Collection Item",
                "itemType": "document",
            }
        ]
        mock_server.create_item.return_value = {
            "success": True,
            "item_key": "NEW123",
        }
        mock_server.create_note.return_value = {
            "success": True,
            "note_key": "NEWNOTE",
        }
        mock_server.add_item_to_collection.return_value = {
            "success": True,
            "message": "Added",
        }
        mock_server.get_item_templates.return_value = {
            "book": {"itemType": "book"},
        }

        monkeypatch.setattr(zotero_server, "get_zotero_server", lambda: mock_server)
        yield mock_server

    def test_search_zotero_items_tool(self, mock_zotero_server):
        """Test search_zotero_items tool function."""
        result = zotero_server.search_items.fn("test query")

        assert result["success"] is True
        assert len(result["data"]) == 1
        assert result["data"][0]["title"] == "Test Item"

    def test_search_zotero_items_no_results(self, mock_zotero_server):
        """Test search with no results."""
        mock_zotero_server.search_items.return_value = []
        result = zotero_server.search_items.fn("nonexistent")

        assert result["success"] is True
        assert result["data"] == []
        assert "No items found" in result["message"]

    def test_get_zotero_item_tool(self, mock_zotero_server):
        """Test get_zotero_item tool function."""
        result = zotero_server.get_item.fn("ABC123")

        assert result["success"] is True
        assert result["data"]["title"] == "Test Item"

    def test_get_zotero_item_not_found(self, mock_zotero_server):
        """Test get_zotero_item with non-existent item."""
        mock_zotero_server.get_item.return_value = None
        result = zotero_server.get_item.fn("NONEXISTENT")

        assert result["success"] is False
        assert "not found" in result["message"]

    def test_get_item_notes_tool(self, mock_zotero_server):
        """Test get_item_notes tool function."""
        result = zotero_server.get_item_notes.fn("ABC123")

        assert result["success"] is True
        assert len(result["data"]) == 1

    def test_get_item_notes_empty(self, mock_zotero_server):
        """Test get_item_notes with no notes."""
        mock_zotero_server.get_item_notes.return_value = []
        result = zotero_server.get_item_notes.fn("ABC123")

        assert result["success"] is True
        assert result["data"] == []
        assert "No notes" in result["message"]

    def test_list_zotero_collections_tool(self, mock_zotero_server):
        """Test list_zotero_collections tool function."""
        result = zotero_server.list_collections.fn()

        assert result["success"] is True
        assert len(result["data"]) == 1
        assert result["data"][0]["name"] == "Collection"

    def test_list_zotero_collections_empty(self, mock_zotero_server):
        """Test list_zotero_collections with no collections."""
        mock_zotero_server.list_collections.return_value = []
        result = zotero_server.list_collections.fn()

        assert result["success"] is True
        assert result["data"] == []
        assert "No collections" in result["message"]

    def test_get_collection_items_tool(self, mock_zotero_server):
        """Test get_collection_items tool function."""
        result = zotero_server.get_collection_items.fn("COL1")

        assert result["success"] is True
        assert len(result["data"]) == 1

    def test_get_collection_items_empty(self, mock_zotero_server):
        """Test get_collection_items with no items."""
        mock_zotero_server.get_collection_items.return_value = []
        result = zotero_server.get_collection_items.fn("COL1")

        assert result["success"] is True
        assert result["data"] == []
        assert "No items" in result["message"]

    def test_create_zotero_item_tool(self, mock_zotero_server):
        """Test create_zotero_item tool function."""
        result = zotero_server.create_item.fn(
            item_type="book",
            title="New Book",
        )

        assert result["success"] is True
        assert result["data"]["item_key"] == "NEW123"

    def test_create_item_note_tool(self, mock_zotero_server):
        """Test create_item_note tool function."""
        result = zotero_server.create_item_note.fn("ABC123", "My note")

        assert result["success"] is True
        assert result["data"]["note_key"] == "NEWNOTE"

    def test_add_item_to_collection_tool(self, mock_zotero_server):
        """Test add_item_to_collection tool function."""
        result = zotero_server.add_item_to_collection.fn("ITEM1", "COL1")

        assert result["success"] is True
        assert result["data"]["item_key"] == "ITEM1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
