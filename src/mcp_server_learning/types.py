"""
Shared type definitions for MCP Server Learning.

This module provides standard response types for tool return values,
ensuring consistency across all servers.
"""

from typing import Any, List, Optional, TypedDict


class ToolResponse(TypedDict, total=False):
    """Standard response type for MCP tools.

    All tools should return this structure for consistency.

    Attributes:
        success: Whether the operation completed successfully
        data: The actual data returned by the tool (type varies by tool)
        message: Human-readable summary of what happened
        error: Error message if success is False, None otherwise
    """

    success: bool
    data: Any
    message: str
    error: Optional[str]


class NoteInfo(TypedDict, total=False):
    """Information about an Obsidian note."""

    title: str
    path: str
    created: str
    modified: str
    size: int
    tags: List[str]
    frontmatter: dict
    wikilinks: List[dict]
    headers: List[dict]
    content: str
    blocks: List[dict]


class VaultStats(TypedDict, total=False):
    """Statistics about an Obsidian vault."""

    vault_path: str
    total_notes: int
    total_size_bytes: int
    total_tags: int
    note_types: dict
    all_tags: List[str]


class BacklinkInfo(TypedDict, total=False):
    """Information about a backlink."""

    source_note: str
    source_path: str
    link_text: str
    header: Optional[str]


class ZoteroItem(TypedDict, total=False):
    """Information about a Zotero item."""

    key: str
    itemType: str
    title: str
    creators: List[dict]
    abstractNote: str
    date: str
    url: str
    tags: List[str]
    collections: List[str]
    dateAdded: str
    dateModified: str


class FlashcardData(TypedDict, total=False):
    """Flashcard data structure."""

    front: str
    back: str
    text: str  # For cloze cards


class VerificationResult(TypedDict, total=False):
    """Result of a mathematical verification."""

    is_valid: bool
    expr1: str
    expr2: str
    difference: str
    simplified_difference: str
    explanation: str
    error: Optional[str]
