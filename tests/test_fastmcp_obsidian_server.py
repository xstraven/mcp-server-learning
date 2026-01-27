import os
import types

import pytest

# Import the tool functions to call directly
from mcp_server_learning import fastmcp_obsidian_server as obs_server


class DummyConnector:
    def __init__(self):
        self.scanner = types.SimpleNamespace(
            get_backlinks=lambda note: [
                {
                    "source_note": "NoteA",
                    "source_path": "A.md",
                    "link_text": "A -> B",
                    "header": None,
                }
            ],
            get_orphaned_notes=lambda: [
                {
                    "title": "Lonely",
                    "path": "Lonely.md",
                    "modified": "2024-01-01T00:00:00",
                    "size": 10,
                }
            ],
        )

    def get_vault_stats(self):
        return {
            "vault_path": "/tmp/vault",
            "total_notes": 2,
            "total_size_bytes": 123,
            "total_tags": 1,
            "all_tags": ["tag1", "tag2"],
            "note_types": {"note": 2},
        }

    def get_notes(self, limit=None, offset=0, refresh_cache=False):
        return [
            {
                "title": "Test",
                "path": "Test.md",
                "modified": "2024-01-01T00:00:00",
                "tags": ["tag1"],
            }
        ]

    def search_notes(self, query, search_in=None, limit=None):
        return [
            {
                "title": "Test",
                "path": "Test.md",
                "modified": "2024-01-01T00:00:00",
                "tags": ["tag1"],
                "content": f"... {query} ...",
            }
        ]

    def get_note_by_name(self, name):
        if name == "exists":
            return {
                "title": "exists",
                "path": "exists.md",
                "created": "2024-01-01T00:00:00",
                "modified": "2024-01-01T00:00:00",
                "size": 1,
                "tags": [],
                "frontmatter": {"k": "v"},
                "wikilinks": [],
                "headers": [],
                "content": "body",
                "blocks": [
                    {
                        "type": "paragraph",
                        "content": "para",
                        "start_line": 1,
                        "end_line": 1,
                    }
                ],
            }
        return None

    def get_notes_by_tag(self, tag):
        return [
            {
                "title": "Tagged",
                "path": "Tagged.md",
                "modified": "2024-01-01T00:00:00",
                "tags": [tag],
            }
        ]

    def extract_content_for_flashcards(self, note, content_types=None):
        return [
            {
                "type": "header",
                "question": "What?",
                "context": "Header",
                "source_note": note.get("title", "exists"),
                "source_line": 1,
            }
        ]


def test_missing_env_raises(monkeypatch):
    # Ensure env var is missing and _get_connector raises
    monkeypatch.delenv("OBSIDIAN_VAULT_PATH", raising=False)
    with pytest.raises(RuntimeError):
        obs_server._get_connector()


def test_list_vault_notes(monkeypatch):
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "/tmp/vault")
    monkeypatch.setattr(obs_server, "_get_connector", lambda: DummyConnector())
    result = obs_server.list_vault_notes.fn(limit=1)

    assert result["success"] is True
    assert len(result["data"]) == 1
    assert "Found 1 note" in result["message"]


def test_get_obsidian_note_not_found(monkeypatch):
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "/tmp/vault")
    monkeypatch.setattr(obs_server, "_get_connector", lambda: DummyConnector())
    result = obs_server.get_obsidian_note.fn("nope")

    assert result["success"] is False
    assert "not found" in result["message"]


def test_get_vault_stats(monkeypatch):
    """Test get_vault_stats returns formatted stats."""
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "/tmp/vault")
    monkeypatch.setattr(obs_server, "_get_connector", lambda: DummyConnector())
    result = obs_server.get_vault_stats.fn()

    assert result["success"] is True
    assert result["data"]["total_notes"] == 2
    assert "2 notes" in result["message"]


def test_search_obsidian_notes(monkeypatch):
    """Test search_obsidian_notes returns matching notes."""
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "/tmp/vault")
    monkeypatch.setattr(obs_server, "_get_connector", lambda: DummyConnector())
    result = obs_server.search_obsidian_notes.fn("test")

    assert result["success"] is True
    assert len(result["data"]) == 1
    assert "Found 1 note" in result["message"]


def test_search_obsidian_notes_no_results(monkeypatch):
    """Test search_obsidian_notes with no matches."""
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "/tmp/vault")

    class EmptySearchConnector(DummyConnector):
        def search_notes(self, query, search_in=None, limit=None):
            return []

    monkeypatch.setattr(obs_server, "_get_connector", lambda: EmptySearchConnector())
    result = obs_server.search_obsidian_notes.fn("nonexistent")

    assert result["success"] is True
    assert result["data"] == []
    assert "No notes found" in result["message"]


def test_get_notes_by_tag(monkeypatch):
    """Test get_notes_by_tag returns tagged notes."""
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "/tmp/vault")
    monkeypatch.setattr(obs_server, "_get_connector", lambda: DummyConnector())
    result = obs_server.get_notes_by_tag.fn("tag1")

    assert result["success"] is True
    assert len(result["data"]) == 1
    assert "tag1" in result["message"]


def test_get_notes_by_tag_no_results(monkeypatch):
    """Test get_notes_by_tag with no matching tag."""
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "/tmp/vault")

    class NoTagsConnector(DummyConnector):
        def get_notes_by_tag(self, tag):
            return []

    monkeypatch.setattr(obs_server, "_get_connector", lambda: NoTagsConnector())
    result = obs_server.get_notes_by_tag.fn("nonexistent")

    assert result["success"] is True
    assert result["data"] == []
    assert "No notes found" in result["message"]


def test_get_note_backlinks(monkeypatch):
    """Test get_note_backlinks returns backlinks."""
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "/tmp/vault")
    monkeypatch.setattr(obs_server, "_get_connector", lambda: DummyConnector())
    result = obs_server.get_note_backlinks.fn("NoteB")

    assert result["success"] is True
    assert len(result["data"]) == 1
    assert result["data"][0]["source_note"] == "NoteA"


def test_get_note_backlinks_no_results(monkeypatch):
    """Test get_note_backlinks with no backlinks."""
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "/tmp/vault")

    class NoBacklinksConnector(DummyConnector):
        def __init__(self):
            self.scanner = types.SimpleNamespace(
                get_backlinks=lambda note: [],
                get_orphaned_notes=lambda: [],
            )

    monkeypatch.setattr(obs_server, "_get_connector", lambda: NoBacklinksConnector())
    result = obs_server.get_note_backlinks.fn("NoteB")

    assert result["success"] is True
    assert result["data"] == []
    assert "No backlinks" in result["message"]


def test_get_orphaned_notes(monkeypatch):
    """Test get_orphaned_notes returns orphaned notes."""
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "/tmp/vault")
    monkeypatch.setattr(obs_server, "_get_connector", lambda: DummyConnector())
    result = obs_server.get_orphaned_notes.fn()

    assert result["success"] is True
    assert len(result["data"]) == 1
    assert result["data"][0]["title"] == "Lonely"


def test_get_orphaned_notes_none(monkeypatch):
    """Test get_orphaned_notes with no orphans."""
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "/tmp/vault")

    class NoOrphansConnector(DummyConnector):
        def __init__(self):
            self.scanner = types.SimpleNamespace(
                get_backlinks=lambda note: [],
                get_orphaned_notes=lambda: [],
            )

    monkeypatch.setattr(obs_server, "_get_connector", lambda: NoOrphansConnector())
    result = obs_server.get_orphaned_notes.fn()

    assert result["success"] is True
    assert result["data"] == []
    assert "No orphaned notes" in result["message"]


def test_get_note_links(monkeypatch):
    """Test get_note_links returns wikilinks from a note."""
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "/tmp/vault")

    class LinksConnector(DummyConnector):
        def get_note_by_name(self, name):
            if name == "exists":
                return {
                    "title": "exists",
                    "path": "exists.md",
                    "created": "2024-01-01T00:00:00",
                    "modified": "2024-01-01T00:00:00",
                    "size": 100,
                    "tags": [],
                    "frontmatter": {},
                    "wikilinks": [
                        {"target": "OtherNote", "header": None, "display": "OtherNote"},
                        {"target": "Another", "header": "Section", "display": "Another"},
                    ],
                    "headers": [],
                    "content": "body",
                    "blocks": [],
                }
            return None

    monkeypatch.setattr(obs_server, "_get_connector", lambda: LinksConnector())
    result = obs_server.get_note_links.fn("exists")

    assert result["success"] is True
    assert len(result["data"]) == 2
    assert "Found 2 link" in result["message"]


def test_get_note_links_not_found(monkeypatch):
    """Test get_note_links with non-existent note."""
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "/tmp/vault")
    monkeypatch.setattr(obs_server, "_get_connector", lambda: DummyConnector())
    result = obs_server.get_note_links.fn("nonexistent")

    assert result["success"] is False
    assert "not found" in result["message"]


def test_get_note_links_no_links(monkeypatch):
    """Test get_note_links with note that has no links."""
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "/tmp/vault")
    monkeypatch.setattr(obs_server, "_get_connector", lambda: DummyConnector())
    result = obs_server.get_note_links.fn("exists")

    assert result["success"] is True
    assert result["data"] == []
    assert "No links found" in result["message"]


def test_extract_note_headers(monkeypatch):
    """Test extract_note_headers returns headers."""
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "/tmp/vault")

    class HeadersConnector(DummyConnector):
        def get_note_by_name(self, name):
            if name == "exists":
                return {
                    "title": "exists",
                    "path": "exists.md",
                    "created": "2024-01-01T00:00:00",
                    "modified": "2024-01-01T00:00:00",
                    "size": 100,
                    "tags": [],
                    "frontmatter": {},
                    "wikilinks": [],
                    "headers": [
                        {
                            "level": 1,
                            "text": "Main Header",
                            "line_number": 1,
                            "anchor": "main-header",
                        },
                        {
                            "level": 2,
                            "text": "Sub Header",
                            "line_number": 5,
                            "anchor": "sub-header",
                        },
                    ],
                    "content": "body",
                    "blocks": [],
                }
            return None

    monkeypatch.setattr(obs_server, "_get_connector", lambda: HeadersConnector())
    result = obs_server.extract_note_headers.fn("exists")

    assert result["success"] is True
    assert len(result["data"]) == 2
    assert "Found 2 header" in result["message"]


def test_extract_note_headers_not_found(monkeypatch):
    """Test extract_note_headers with non-existent note."""
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "/tmp/vault")
    monkeypatch.setattr(obs_server, "_get_connector", lambda: DummyConnector())
    result = obs_server.extract_note_headers.fn("nonexistent")

    assert result["success"] is False
    assert "not found" in result["message"]


def test_extract_note_headers_no_headers(monkeypatch):
    """Test extract_note_headers with note that has no headers."""
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "/tmp/vault")
    monkeypatch.setattr(obs_server, "_get_connector", lambda: DummyConnector())
    result = obs_server.extract_note_headers.fn("exists")

    assert result["success"] is True
    assert result["data"] == []
    assert "No headers found" in result["message"]


def test_extract_note_blocks(monkeypatch):
    """Test extract_note_blocks returns content blocks."""
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "/tmp/vault")
    monkeypatch.setattr(obs_server, "_get_connector", lambda: DummyConnector())
    result = obs_server.extract_note_blocks.fn("exists")

    assert result["success"] is True
    assert len(result["data"]) == 1
    assert result["data"][0]["type"] == "paragraph"


def test_extract_note_blocks_not_found(monkeypatch):
    """Test extract_note_blocks with non-existent note."""
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "/tmp/vault")
    monkeypatch.setattr(obs_server, "_get_connector", lambda: DummyConnector())
    result = obs_server.extract_note_blocks.fn("nonexistent")

    assert result["success"] is False
    assert "not found" in result["message"]


def test_extract_note_blocks_with_filter(monkeypatch):
    """Test extract_note_blocks with block type filter."""
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "/tmp/vault")

    class BlocksConnector(DummyConnector):
        def get_note_by_name(self, name):
            if name == "exists":
                return {
                    "title": "exists",
                    "path": "exists.md",
                    "created": "2024-01-01T00:00:00",
                    "modified": "2024-01-01T00:00:00",
                    "size": 100,
                    "tags": [],
                    "frontmatter": {},
                    "wikilinks": [],
                    "headers": [],
                    "content": "body",
                    "blocks": [
                        {"type": "paragraph", "content": "text", "start_line": 1, "end_line": 1},
                        {
                            "type": "code",
                            "content": "print()",
                            "start_line": 3,
                            "end_line": 3,
                            "language": "python",
                        },
                    ],
                }
            return None

    monkeypatch.setattr(obs_server, "_get_connector", lambda: BlocksConnector())
    result = obs_server.extract_note_blocks.fn("exists", block_types=["code"])

    assert result["success"] is True
    assert len(result["data"]) == 1
    assert result["data"][0]["type"] == "code"


def test_get_obsidian_note_found(monkeypatch):
    """Test get_obsidian_note returns note details."""
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "/tmp/vault")
    monkeypatch.setattr(obs_server, "_get_connector", lambda: DummyConnector())
    result = obs_server.get_obsidian_note.fn("exists")

    assert result["success"] is True
    assert result["data"]["title"] == "exists"
    assert result["data"]["content"] == "body"


def test_get_notes_for_flashcards(monkeypatch):
    """Test get_notes_for_flashcards returns flashcard content."""
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "/tmp/vault")
    monkeypatch.setattr(obs_server, "_get_connector", lambda: DummyConnector())
    result = obs_server.get_notes_for_flashcards.fn(tag_filter="tag1")

    assert result["success"] is True
    assert len(result["data"]) >= 1
    assert "Extracted" in result["message"]


def test_get_notes_for_flashcards_by_names(monkeypatch):
    """Test get_notes_for_flashcards with note names."""
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "/tmp/vault")
    monkeypatch.setattr(obs_server, "_get_connector", lambda: DummyConnector())
    result = obs_server.get_notes_for_flashcards.fn(note_names=["exists"])

    assert result["success"] is True
    assert len(result["data"]) >= 1


def test_get_notes_for_flashcards_missing_params(monkeypatch):
    """Test get_notes_for_flashcards requires note_names or tag_filter."""
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "/tmp/vault")
    monkeypatch.setattr(obs_server, "_get_connector", lambda: DummyConnector())
    result = obs_server.get_notes_for_flashcards.fn()

    assert result["success"] is False
    assert "must be provided" in result["message"]
