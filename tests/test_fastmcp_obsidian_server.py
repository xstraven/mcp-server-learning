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
    out = obs_server.list_vault_notes(limit=1)
    assert "Found 1 note" in out


def test_get_obsidian_note_not_found(monkeypatch):
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "/tmp/vault")
    monkeypatch.setattr(obs_server, "_get_connector", lambda: DummyConnector())
    out = obs_server.get_obsidian_note("nope")
    assert "not found" in out

