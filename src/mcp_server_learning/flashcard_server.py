#!/usr/bin/env python3

import asyncio
import json
import re
import requests
import base64
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel,
)
import mcp.types as types


server = Server("mcp-server-learning-flashcards")


# Custom exceptions for Anki Connect
class AnkiConnectError(Exception):
    """Base exception for Anki Connect errors."""

    pass


class AnkiConnectionError(AnkiConnectError):
    """Raised when unable to connect to Anki."""

    pass


class AnkiPermissionError(AnkiConnectError):
    """Raised when permission is denied."""

    pass


class AnkiAPIError(AnkiConnectError):
    """Raised when Anki Connect API returns an error."""

    pass


class AnkiDuplicateError(AnkiConnectError):
    """Raised when trying to add duplicate notes."""

    pass


# # Global connectors - will be initialized when first used
# zotero_connector: Optional[ZoteroConnector] = None
# obsidian_connector: Optional[ObsidianConnector] = None


class AnkiConnector:
    """Interface for connecting to Anki via AnkiConnect addon."""

    def __init__(
        self, url: str = "http://localhost:8765", api_key: Optional[str] = None
    ):
        self.url = url
        self.api_key = api_key
        self.session = requests.Session()

    def _make_request(
        self, action: str, params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Make a request to AnkiConnect API."""
        if params is None:
            params = {}

        payload = {"action": action, "version": 6, "params": params}

        if self.api_key:
            payload["key"] = self.api_key

        try:
            response = self.session.post(self.url, json=payload, timeout=10)
            response.raise_for_status()

            result = response.json()
            if result.get("error"):
                error_msg = result["error"]

                # Handle specific error types
                if "permission" in error_msg.lower():
                    raise AnkiPermissionError(f"Permission denied: {error_msg}")
                elif (
                    "collection" in error_msg.lower()
                    and "not available" in error_msg.lower()
                ):
                    raise AnkiConnectionError(
                        f"Collection not available: {error_msg}"
                    )
                elif "duplicate" in error_msg.lower():
                    raise AnkiDuplicateError(f"Duplicate note: {error_msg}")
                else:
                    raise AnkiAPIError(f"Anki Connect API error: {error_msg}")

            return result.get("result")

        except requests.exceptions.ConnectionError as e:
            raise AnkiConnectionError(
                f"Cannot connect to Anki. Is Anki running with AnkiConnect addon? {e}"
            )
        except requests.exceptions.Timeout as e:
            raise AnkiConnectionError(f"Request to Anki timed out: {e}")
        except requests.exceptions.HTTPError as e:
            raise AnkiConnectionError(
                f"HTTP error when connecting to Anki: {e}"
            )
        except requests.exceptions.RequestException as e:
            raise AnkiConnectionError(f"Request failed: {e}")
        except ValueError as e:
            raise AnkiAPIError(f"Invalid JSON response from Anki: {e}")

    def check_permission(self) -> Dict[str, Any]:
        """Check if AnkiConnect is available and get permission info."""
        try:
            result = self._make_request("requestPermission")
            return result
        except AnkiPermissionError:
            # If permission is explicitly denied, we still want to return the info
            # but let the caller know permission was denied
            raise
        except AnkiConnectionError:
            # Re-raise connection errors as they indicate Anki is not available
            raise

    def ensure_permission(self) -> bool:
        """Ensure we have permission to access Anki. Returns True if permission granted."""
        try:
            permission_info = self.check_permission()
            permission = permission_info.get("permission", "denied")
            return permission == "granted"
        except AnkiPermissionError:
            return False

    def get_deck_names(self) -> List[str]:
        """Get list of available deck names."""
        return self._make_request("deckNames")

    def get_model_names(self) -> List[str]:
        """Get list of available note type names."""
        return self._make_request("modelNames")

    def get_model_field_names(self, model_name: str) -> List[str]:
        """Get field names for a specific note type."""
        return self._make_request("modelFieldNames", {"modelName": model_name})

    def create_deck(self, deck_name: str) -> None:
        """Create a new deck if it doesn't exist."""
        self._make_request("createDeck", {"deck": deck_name})

    def add_note(
        self,
        deck_name: str,
        model_name: str,
        fields: Dict[str, str],
        tags: List[str] = None,
    ) -> Optional[int]:
        """Add a single note to Anki."""
        if tags is None:
            tags = []

        note = {
            "deckName": deck_name,
            "modelName": model_name,
            "fields": fields,
            "tags": tags,
        }

        return self._make_request("addNote", {"note": note})

    def add_notes(self, notes: List[Dict[str, Any]]) -> List[Optional[int]]:
        """Add multiple notes to Anki."""
        formatted_notes = []
        for note in notes:
            formatted_notes.append(
                {
                    "deckName": note["deck_name"],
                    "modelName": note["model_name"],
                    "fields": note["fields"],
                    "tags": note.get("tags", []),
                }
            )

        return self._make_request("addNotes", {"notes": formatted_notes})

    def can_add_notes(self, notes: List[Dict[str, Any]]) -> List[bool]:
        """Check if notes can be added without creating duplicates."""
        formatted_notes = []
        for note in notes:
            formatted_notes.append(
                {
                    "deckName": note["deck_name"],
                    "modelName": note["model_name"],
                    "fields": note["fields"],
                    "tags": note.get("tags", []),
                }
            )

        return self._make_request("canAddNotes", {"notes": formatted_notes})

    def find_notes(self, query: str) -> List[int]:
        """Find notes matching the given query."""
        return self._make_request("findNotes", {"query": query})

    def notes_info(self, note_ids: List[int]) -> List[Dict[str, Any]]:
        """Get detailed information about specific notes."""
        return self._make_request("notesInfo", {"notes": note_ids})

    def update_note(
        self, note_id: int, fields: Dict[str, str], tags: List[str] = None
    ) -> None:
        """Update an existing note."""
        params = {"note": {"id": note_id, "fields": fields}}
        if tags is not None:
            params["note"]["tags"] = tags

        self._make_request("updateNoteFields", params)

    def delete_notes(self, note_ids: List[int]) -> None:
        """Delete notes by their IDs."""
        self._make_request("deleteNotes", {"notes": note_ids})

    def sync(self) -> None:
        """Synchronize collection with AnkiWeb."""
        self._make_request("sync")

    def get_deck_stats(
        self, deck_names: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """Get statistics for specified decks."""
        return self._make_request("getDeckStats", {"decks": deck_names})

    def find_cards(self, query: str) -> List[int]:
        """Find cards matching the given query."""
        return self._make_request("findCards", {"query": query})

    def cards_info(self, card_ids: List[int]) -> List[Dict[str, Any]]:
        """Get detailed information about specific cards."""
        return self._make_request("cardsInfo", {"cards": card_ids})

    def store_media_file(self, filename: str, data: str) -> str:
        """Store a media file in Anki's media collection.

        Args:
            filename: Name of the file to store
            data: Base64 encoded file data

        Returns:
            The filename as stored in Anki's media collection
        """
        return self._make_request(
            "storeMediaFile", {"filename": filename, "data": data}
        )

    def retrieve_media_file(self, filename: str) -> str:
        """Retrieve a media file from Anki's media collection.

        Args:
            filename: Name of the file to retrieve

        Returns:
            Base64 encoded file data
        """
        return self._make_request("retrieveMediaFile", {"filename": filename})

    def delete_media_file(self, filename: str) -> None:
        """Delete a media file from Anki's media collection."""
        self._make_request("deleteMediaFile", {"filename": filename})

    def add_note_with_media(
        self,
        deck_name: str,
        model_name: str,
        fields: Dict[str, str],
        tags: List[str] = None,
        media_files: List[Dict[str, Any]] = None,
    ) -> Optional[int]:
        """Add a note with media files.

        Args:
            deck_name: Name of the deck
            model_name: Name of the note type
            fields: Field values for the note
            tags: Tags to add to the note
            media_files: List of media file dictionaries with 'filename', 'data', and optional 'fields'
        """
        if tags is None:
            tags = []
        if media_files is None:
            media_files = []

        note = {
            "deckName": deck_name,
            "modelName": model_name,
            "fields": fields,
            "tags": tags,
        }

        # Add media files to the note
        if media_files:
            note["audio"] = []
            note["video"] = []
            note["picture"] = []

            for media_file in media_files:
                media_entry = {
                    "url": media_file.get("url", ""),
                    "filename": media_file["filename"],
                    "fields": media_file.get("fields", []),
                }

                # Add data if provided (for base64 encoded files)
                if "data" in media_file:
                    media_entry["data"] = media_file["data"]

                # Categorize by file type
                filename_lower = media_file["filename"].lower()
                if any(
                    filename_lower.endswith(ext)
                    for ext in [".mp3", ".wav", ".m4a", ".ogg"]
                ):
                    note["audio"].append(media_entry)
                elif any(
                    filename_lower.endswith(ext)
                    for ext in [".mp4", ".webm", ".ogv"]
                ):
                    note["video"].append(media_entry)
                elif any(
                    filename_lower.endswith(ext)
                    for ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg"]
                ):
                    note["picture"].append(media_entry)

        return self._make_request("addNote", {"note": note})

    @staticmethod
    def encode_file_to_base64(file_path: str) -> str:
        """Encode a file to base64 string for Anki media storage.

        Args:
            file_path: Path to the file to encode

        Returns:
            Base64 encoded string of the file contents
        """
        try:
            with open(file_path, "rb") as file:
                file_data = file.read()
                return base64.b64encode(file_data).decode("utf-8")
        except Exception as e:
            raise AnkiAPIError(f"Failed to encode file {file_path}: {e}")

    @staticmethod
    def decode_base64_to_file(base64_data: str, output_path: str) -> None:
        """Decode base64 data to a file.

        Args:
            base64_data: Base64 encoded file data
            output_path: Path where to save the decoded file
        """
        try:
            file_data = base64.b64decode(base64_data)
            with open(output_path, "wb") as file:
                file.write(file_data)
        except Exception as e:
            raise AnkiAPIError(
                f"Failed to decode base64 data to {output_path}: {e}"
            )


class FlashcardGenerator:
    """Generates LaTeX flashcards from text and diagrams."""

    @staticmethod
    def escape_latex(text: str) -> str:
        """Escape special LaTeX characters."""
        latex_special_chars = {
            "&": r"\&",
            "%": r"\%",
            "$": r"\$",
            "#": r"\#",
            "^": r"\textasciicircum{}",
            "_": r"\_",
            "{": r"\{",
            "}": r"\}",
            "~": r"\textasciitilde{}",
            "\\": r"\textbackslash{}",
        }

        for char, escaped in latex_special_chars.items():
            text = text.replace(char, escaped)
        return text

    @staticmethod
    def create_front_back_card(front: str, back: str) -> str:
        """Create a front-back flashcard in LaTeX format."""
        front_escaped = FlashcardGenerator.escape_latex(front)
        back_escaped = FlashcardGenerator.escape_latex(back)

        return f"""\\begin{{flashcard}}{{{front_escaped}}}
{back_escaped}
\\end{{flashcard}}"""

    @staticmethod
    def create_cloze_deletion_card(
        text: str, cloze_markers: List[str] = None
    ) -> str:
        """Create a cloze deletion card in LaTeX format with support for multiple deletions."""
        if cloze_markers is None:
            cloze_markers = ["{{", "}}"]

        # Find text within cloze markers
        pattern = (
            f"{re.escape(cloze_markers[0])}(.*?){re.escape(cloze_markers[1])}"
        )
        matches = re.findall(pattern, text)

        if not matches:
            raise ValueError("No cloze deletions found in text")

        # Create the card with numbered cloze deletions for multiple clozes
        card_text = text
        for i, match in enumerate(matches, 1):
            replacement = f"\\\\cloze{{{match}}}"
            # Replace each occurrence with a unique cloze number
            old_pattern = f"{re.escape(cloze_markers[0])}{re.escape(match)}{re.escape(cloze_markers[1])}"
            card_text = re.sub(old_pattern, replacement, card_text, count=1)

        escaped_text = FlashcardGenerator.escape_latex(card_text)

        return f"""\\begin{{clozecard}}
{escaped_text}
\\end{{clozecard}}"""

    @staticmethod
    def create_anki_cloze_card(
        text: str, cloze_markers: List[str] = None
    ) -> str:
        """Create a cloze deletion card in Anki format with support for multiple deletions."""
        if cloze_markers is None:
            cloze_markers = ["{{", "}}"]

        # Find text within cloze markers
        pattern = (
            f"{re.escape(cloze_markers[0])}(.*?){re.escape(cloze_markers[1])}"
        )
        matches = re.findall(pattern, text)

        if not matches:
            raise ValueError("No cloze deletions found in text")

        # Create the card with numbered cloze deletions for Anki format
        card_text = text
        for i, match in enumerate(matches, 1):
            replacement = f"{{{{c{i}::{match}}}}}"
            # Replace each occurrence with a unique cloze number
            old_pattern = f"{re.escape(cloze_markers[0])}{re.escape(match)}{re.escape(cloze_markers[1])}"
            card_text = re.sub(old_pattern, replacement, card_text, count=1)

        return card_text

    @staticmethod
    def parse_text_to_cards(
        text: str, card_type: str = "front-back"
    ) -> List[str]:
        """Parse text into multiple flashcards."""
        cards = []

        if card_type == "front-back":
            # Split by double newlines or specific separators
            sections = re.split(r"\n\s*\n|---", text.strip())

            for section in sections:
                section = section.strip()
                if not section:
                    continue

                # Look for Q: A: pattern
                qa_match = re.search(
                    r"Q:\s*(.*?)\s*A:\s*(.*)",
                    section,
                    re.DOTALL | re.IGNORECASE,
                )
                if qa_match:
                    cards.append(
                        FlashcardGenerator.create_front_back_card(
                            qa_match.group(1).strip(), qa_match.group(2).strip()
                        )
                    )
                    continue

                # Look for question/answer separated by newline
                lines = section.split("\n")
                if len(lines) >= 2:
                    front = lines[0].strip()
                    back = "\n".join(lines[1:]).strip()
                    cards.append(
                        FlashcardGenerator.create_front_back_card(front, back)
                    )

        elif card_type == "cloze":
            # Split by double newlines for multiple cloze cards
            sections = re.split(r"\n\s*\n", text.strip())

            for section in sections:
                section = section.strip()
                if not section:
                    continue

                try:
                    cards.append(
                        FlashcardGenerator.create_cloze_deletion_card(section)
                    )
                except ValueError:
                    # If no cloze markers found, skip this section
                    continue

        return cards

    @staticmethod
    def process_diagram(diagram_text: str, diagram_type: str = "ascii") -> str:
        """Process diagrams and convert them to LaTeX format."""
        if diagram_type == "ascii":
            # Wrap ASCII diagrams in verbatim environment
            return f"\\begin{{verbatim}}\n{diagram_text}\n\\end{{verbatim}}"
        elif diagram_type == "tikz":
            # If it's already TikZ code, wrap it properly
            if "\\begin{tikzpicture}" not in diagram_text:
                return f"\\begin{{tikzpicture}}\n{diagram_text}\n\\end{{tikzpicture}}"
            return diagram_text
        elif diagram_type == "flowchart":
            # Convert simple flowchart notation to TikZ
            return FlashcardGenerator._convert_flowchart_to_tikz(diagram_text)
        else:
            # Default to verbatim for unknown types
            return f"\\begin{{verbatim}}\n{diagram_text}\n\\end{{verbatim}}"

    @staticmethod
    def _convert_flowchart_to_tikz(flowchart: str) -> str:
        """Convert simple flowchart notation to TikZ."""
        # This is a basic implementation - could be expanded
        lines = flowchart.strip().split("\n")
        tikz_code = "\\begin{tikzpicture}[node distance=2cm]\n"

        # Simple parsing for basic flowchart elements
        for i, line in enumerate(lines):
            line = line.strip()
            if "-->" in line:
                parts = line.split("-->")
                if len(parts) == 2:
                    from_node = parts[0].strip().replace(" ", "_")
                    to_node = parts[1].strip().replace(" ", "_")
                    tikz_code += f"\\draw[->] ({from_node}) -- ({to_node});\n"
            elif line:
                # Create a node
                node_name = line.replace(" ", "_")
                tikz_code += f"\\node ({node_name}) {{{line}}};\n"

        tikz_code += "\\end{tikzpicture}"
        return tikz_code

    @staticmethod
    def create_diagram_card(
        diagram: str, explanation: str, diagram_type: str = "ascii"
    ) -> str:
        """Create a flashcard with a diagram and explanation."""
        processed_diagram = FlashcardGenerator.process_diagram(
            diagram, diagram_type
        )
        escaped_explanation = FlashcardGenerator.escape_latex(explanation)

        return f"""\\begin{{flashcard}}{{Diagram}}
{processed_diagram}

\\vspace{{1em}}

{escaped_explanation}
\\end{{flashcard}}"""

    @staticmethod
    def create_latex_document(
        cards: List[str], title: str = "Flashcards"
    ) -> str:
        """Wrap flashcards in a complete LaTeX document."""
        escaped_title = FlashcardGenerator.escape_latex(title)

        header = f"""\\documentclass{{article}}
\\usepackage[utf8]{{inputenc}}
\\usepackage{{flashcards}}
\\usepackage{{amsmath}}
\\usepackage{{amsfonts}}
\\usepackage{{amssymb}}
\\usepackage{{tikz}}
\\usepackage{{verbatim}}
\\usetikzlibrary{{shapes,arrows,positioning}}

\\title{{{escaped_title}}}
\\author{{Generated by MCP Learning Server}}
\\date{{\\today}}

\\begin{{document}}

\\maketitle

"""

        footer = """
\\end{document}
"""

        cards_content = "\n\n".join(cards)

        return header + cards_content + footer


class AnkiCardManager:
    """Manages conversion from generated flashcards to Anki cards."""

    def __init__(self, anki_connector: AnkiConnector):
        self.anki = anki_connector

    def get_default_model_for_card_type(self, card_type: str) -> str:
        """Get the appropriate Anki model for a flashcard type."""
        model_mapping = {
            "front-back": "Basic",
            "cloze": "Cloze",
            "diagram": "Basic",
        }
        return model_mapping.get(card_type, "Basic")

    def validate_model_exists(self, model_name: str) -> bool:
        """Check if a note type (model) exists in Anki."""
        try:
            models = self.anki.get_model_names()
            return model_name in models
        except Exception:
            return False

    def get_model_fields(self, model_name: str) -> List[str]:
        """Get field names for a model with error handling."""
        try:
            return self.anki.get_model_field_names(model_name)
        except Exception as e:
            raise AnkiAPIError(
                f"Failed to get fields for model '{model_name}': {e}"
            )

    def validate_fields_for_model(
        self, fields: Dict[str, str], model_name: str
    ) -> Dict[str, Any]:
        """Validate that all required fields are provided for a model.

        Returns:
            Dictionary with validation results including missing fields and warnings
        """
        try:
            model_fields = self.get_model_fields(model_name)
            provided_fields = set(fields.keys())
            required_fields = set(model_fields)

            missing_fields = required_fields - provided_fields
            extra_fields = provided_fields - required_fields

            return {
                "valid": len(missing_fields) == 0,
                "missing_fields": list(missing_fields),
                "extra_fields": list(extra_fields),
                "model_fields": model_fields,
            }
        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
                "missing_fields": [],
                "extra_fields": [],
                "model_fields": [],
            }

    def convert_to_anki_fields(
        self, card_content: str, card_type: str, model_name: str = None
    ) -> Dict[str, str]:
        """Convert generated flashcard content to Anki field format with validation."""
        if model_name is None:
            model_name = self.get_default_model_for_card_type(card_type)

        # Validate model exists
        if not self.validate_model_exists(model_name):
            # Try to fallback to a basic model
            fallback_model = self.get_default_model_for_card_type(card_type)
            if fallback_model != model_name and self.validate_model_exists(
                fallback_model
            ):
                model_name = fallback_model
            else:
                raise AnkiAPIError(
                    f"Model '{model_name}' not found and no valid fallback available"
                )

        try:
            field_names = self.get_model_fields(model_name)
        except Exception:
            # Last resort fallback
            field_names = (
                ["Front", "Back"] if card_type != "cloze" else ["Text"]
            )

        # Parse content based on card type
        if card_type == "front-back":
            fields = self._parse_front_back_card(card_content, field_names)
        elif card_type == "cloze":
            fields = self._parse_cloze_card(card_content, field_names)
        elif card_type == "diagram":
            fields = self._parse_diagram_card(card_content, field_names)
        else:
            # Default fallback
            fields = {field_names[0]: card_content}

        # Validate fields
        validation = self.validate_fields_for_model(fields, model_name)
        if not validation["valid"] and validation.get("missing_fields"):
            # Fill missing fields with empty strings
            for field in validation["missing_fields"]:
                fields[field] = ""

        return fields

    def _parse_front_back_card(
        self, content: str, field_names: List[str]
    ) -> Dict[str, str]:
        """Parse front-back card content for Anki fields."""
        # Remove LaTeX flashcard environment
        content = re.sub(r"\\begin\{flashcard\}.*?\n", "", content)
        content = re.sub(r"\\end\{flashcard\}.*", "", content)

        # Try to split into front and back
        parts = content.strip().split("\n", 1)

        fields = {}
        if len(parts) >= 2:
            fields[field_names[0]] = parts[0].strip()
            fields[field_names[1]] = parts[1].strip()
        else:
            fields[field_names[0]] = content.strip()
            if len(field_names) > 1:
                fields[field_names[1]] = ""

        return fields

    def _parse_cloze_card(
        self, content: str, field_names: List[str]
    ) -> Dict[str, str]:
        """Parse cloze card content for Anki fields with proper numbering."""
        # Remove LaTeX cloze environment
        content = re.sub(r"\\begin\{clozecard\}.*?\n", "", content)
        content = re.sub(r"\\end\{clozecard\}.*", "", content)

        # Convert LaTeX cloze format to Anki cloze format with proper numbering
        # Find all cloze deletions and number them sequentially
        cloze_pattern = r"\\\\cloze\{([^}]+)\}"
        matches = re.findall(cloze_pattern, content)

        # Replace each cloze with proper numbering
        for i, match in enumerate(matches, 1):
            old_pattern = r"\\\\cloze\{" + re.escape(match) + r"\}"
            replacement = f"{{{{c{i}::{match}}}}}"
            content = re.sub(old_pattern, replacement, content, count=1)

        fields = {field_names[0]: content.strip()}
        return fields

    def _parse_diagram_card(
        self, content: str, field_names: List[str]
    ) -> Dict[str, str]:
        """Parse diagram card content for Anki fields."""
        # Remove LaTeX flashcard environment
        content = re.sub(r"\\begin\{flashcard\}.*?\n", "", content)
        content = re.sub(r"\\end\{flashcard\}.*", "", content)

        # Split diagram and explanation
        parts = content.split("\\vspace{1em}")

        fields = {}
        if len(parts) >= 2:
            fields[field_names[0]] = parts[0].strip()
            if len(field_names) > 1:
                fields[field_names[1]] = parts[1].strip()
        else:
            fields[field_names[0]] = content.strip()
            if len(field_names) > 1:
                fields[field_names[1]] = ""

        return fields

    def upload_cards_to_anki(
        self,
        cards_data: List[Dict[str, Any]],
        deck_name: str,
        check_duplicates: bool = True,
        duplicate_policy: str = "skip",
        batch_size: int = 100,
    ) -> Dict[str, Any]:
        """Upload multiple cards to Anki with duplicate detection and batch processing.

        Args:
            cards_data: List of card data dictionaries
            deck_name: Name of the target Anki deck
            check_duplicates: Whether to check for duplicates before adding
            duplicate_policy: How to handle duplicates ("skip", "add_anyway", "update")
            batch_size: Number of cards to process in each batch
        """
        try:
            # Check connection and create deck if needed
            permission_info = self.anki.check_permission()
            self.anki.create_deck(deck_name)

            # Track processing results
            total_results = {
                "total_cards": len(cards_data),
                "successful_uploads": 0,
                "failed_uploads": 0,
                "skipped_duplicates": 0,
                "added_duplicates": 0,
                "processing_errors": [],
                "note_ids": [],
                "batches_processed": 0,
            }

            # Process cards in batches
            for i in range(0, len(cards_data), batch_size):
                batch = cards_data[i : i + batch_size]
                batch_num = (i // batch_size) + 1

                try:
                    # Convert batch to Anki format
                    anki_notes = []
                    conversion_errors = []

                    for j, card_data in enumerate(batch):
                        try:
                            card_type = card_data.get("card_type", "front-back")
                            model_name = card_data.get(
                                "model_name",
                                self.get_default_model_for_card_type(card_type),
                            )

                            fields = self.convert_to_anki_fields(
                                card_data["content"], card_type, model_name
                            )

                            anki_notes.append(
                                {
                                    "deck_name": deck_name,
                                    "model_name": model_name,
                                    "fields": fields,
                                    "tags": card_data.get(
                                        "tags", ["mcp-generated"]
                                    ),
                                }
                            )
                        except Exception as e:
                            conversion_errors.append(
                                {
                                    "batch": batch_num,
                                    "card_index": i + j,
                                    "error": str(e),
                                }
                            )

                    # Add conversion errors to total results
                    total_results["processing_errors"].extend(conversion_errors)
                    total_results["failed_uploads"] += len(conversion_errors)

                    if not anki_notes:
                        continue

                    # Check for duplicates if requested
                    duplicates_info = {
                        "can_add": [],
                        "skipped": 0,
                        "added_anyway": 0,
                    }
                    if check_duplicates:
                        try:
                            duplicates_info["can_add"] = (
                                self.anki.can_add_notes(anki_notes)
                            )

                            if duplicate_policy == "skip":
                                # Filter out duplicates
                                filtered_notes = []
                                for note, can_add in zip(
                                    anki_notes, duplicates_info["can_add"]
                                ):
                                    if can_add:
                                        filtered_notes.append(note)
                                    else:
                                        duplicates_info["skipped"] += 1
                                anki_notes = filtered_notes
                            elif duplicate_policy == "add_anyway":
                                # Count duplicates but add them anyway
                                duplicates_info["added_anyway"] = sum(
                                    1
                                    for can_add in duplicates_info["can_add"]
                                    if not can_add
                                )
                        except Exception as e:
                            total_results["processing_errors"].append(
                                {
                                    "batch": batch_num,
                                    "error": f"Duplicate check failed: {e}",
                                }
                            )

                    # Upload notes in batch
                    if anki_notes:
                        try:
                            note_ids = self.anki.add_notes(anki_notes)

                            # Count results
                            batch_success = sum(
                                1 for note_id in note_ids if note_id is not None
                            )
                            batch_failed = len(note_ids) - batch_success

                            total_results["successful_uploads"] += batch_success
                            total_results["failed_uploads"] += batch_failed
                            total_results[
                                "skipped_duplicates"
                            ] += duplicates_info["skipped"]
                            total_results[
                                "added_duplicates"
                            ] += duplicates_info["added_anyway"]
                            total_results["note_ids"].extend(note_ids)

                        except Exception as e:
                            total_results["processing_errors"].append(
                                {
                                    "batch": batch_num,
                                    "error": f"Upload failed: {e}",
                                }
                            )
                            total_results["failed_uploads"] += len(anki_notes)

                    total_results["batches_processed"] += 1

                except Exception as e:
                    total_results["processing_errors"].append(
                        {
                            "batch": batch_num,
                            "error": f"Batch processing failed: {e}",
                        }
                    )
                    total_results["failed_uploads"] += len(batch)

            return {
                "success": total_results["successful_uploads"] > 0,
                "deck_name": deck_name,
                **total_results,
            }

        except AnkiDuplicateError as e:
            return {
                "success": False,
                "error": f"Duplicate detection error: {str(e)}",
                "total_cards": len(cards_data),
            }
        except (AnkiConnectionError, AnkiPermissionError, AnkiAPIError) as e:
            return {
                "success": False,
                "error": str(e),
                "total_cards": len(cards_data),
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "total_cards": len(cards_data),
            }


class HTMLCardRenderer:
    """Renders flashcards as HTML for preview purposes."""

    @staticmethod
    def get_base_css() -> str:
        """Get base CSS styles for flashcard rendering."""
        return """
        <style>
        .flashcard-container {
            max-width: 600px;
            margin: 20px auto;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        .flashcard {
            border: 2px solid #e0e0e0;
            border-radius: 12px;
            margin: 16px 0;
            background: white;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .card-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 20px;
            font-weight: 600;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .card-front, .card-back {
            padding: 24px;
            min-height: 60px;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
        }
        .card-front {
            background: #f8f9fa;
            border-bottom: 1px solid #e0e0e0;
            font-size: 18px;
            font-weight: 500;
            color: #2c3e50;
        }
        .card-back {
            background: white;
            font-size: 16px;
            line-height: 1.6;
            color: #34495e;
        }
        .cloze-card {
            padding: 24px;
            background: white;
            font-size: 16px;
            line-height: 1.6;
            color: #2c3e50;
        }
        .cloze-blank {
            background: #3498db;
            color: white;
            padding: 2px 8px;
            border-radius: 4px;
            font-weight: 500;
        }
        .diagram-container {
            background: #f8f9fa;
            padding: 20px;
            margin: 16px 0;
            border-radius: 8px;
            border: 1px solid #dee2e6;
        }
        .diagram-code {
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            background: #2c3e50;
            color: #ecf0f1;
            padding: 16px;
            border-radius: 6px;
            white-space: pre-wrap;
            overflow-x: auto;
            font-size: 14px;
            line-height: 1.4;
        }
        .math {
            font-style: italic;
            color: #8e44ad;
        }
        .tag {
            display: inline-block;
            background: #e8f4f8;
            color: #2980b9;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 12px;
            margin: 2px;
            font-weight: 500;
        }
        .tags-container {
            padding: 12px 20px;
            background: #f8f9fa;
            border-top: 1px solid #e0e0e0;
        }
        .preview-header {
            text-align: center;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            margin-bottom: 0;
        }
        .preview-header h1 {
            margin: 0;
            font-size: 24px;
            font-weight: 600;
        }
        .preview-header p {
            margin: 8px 0 0 0;
            opacity: 0.9;
            font-size: 14px;
        }
        </style>
        """

    @staticmethod
    def get_mathjax_script() -> str:
        """Get MathJax configuration script for LaTeX rendering."""
        return """
        <script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>
        <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
        <script>
        window.MathJax = {
            tex: {
                inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
                displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']],
                processEscapes: true,
                processEnvironments: true
            },
            options: {
                ignoreHtmlClass: 'tex2jax_ignore',
                processHtmlClass: 'tex2jax_process'
            }
        };
        </script>
        """

    @staticmethod
    def convert_latex_to_mathjax(text: str) -> str:
        """Convert LaTeX syntax to MathJax-compatible format."""
        # Convert display math
        text = re.sub(
            r"\\begin\{equation\}(.*?)\\end\{equation\}",
            r"$$\1$$",
            text,
            flags=re.DOTALL,
        )
        text = re.sub(
            r"\\begin\{align\}(.*?)\\end\{align\}",
            r"$$\\begin{align}\1\\end{align}$$",
            text,
            flags=re.DOTALL,
        )

        # Convert inline math (be careful not to double-convert)
        text = re.sub(r"(?<!\\)\$(?!\$)(.*?)(?<!\\)\$(?!\$)", r"$\1$", text)

        # Convert common LaTeX commands
        text = text.replace("\\LaTeX", "$\\LaTeX$")
        text = text.replace("\\TeX", "$\\TeX$")

        # Clean up escaped characters for HTML
        text = text.replace("\\&", "&")
        text = text.replace("\\%", "%")
        text = text.replace("\\$", "$")
        text = text.replace("\\#", "#")
        text = text.replace("\\_", "_")
        text = text.replace("\\{", "{")
        text = text.replace("\\}", "}")

        return text

    @staticmethod
    def render_front_back_card(
        front: str, back: str, tags: List[str] = None
    ) -> str:
        """Render a front-back card as HTML."""
        if tags is None:
            tags = []

        front_html = HTMLCardRenderer.convert_latex_to_mathjax(front)
        back_html = HTMLCardRenderer.convert_latex_to_mathjax(back)

        tags_html = ""
        if tags:
            tags_html = f"""
            <div class="tags-container">
                {''.join(f'<span class="tag">{tag}</span>' for tag in tags)}
            </div>
            """

        return f"""
        <div class="flashcard">
            <div class="card-header">Front-Back Card</div>
            <div class="card-front">{front_html}</div>
            <div class="card-back">{back_html}</div>
            {tags_html}
        </div>
        """

    @staticmethod
    def render_cloze_card(text: str, tags: List[str] = None) -> str:
        """Render a cloze deletion card as HTML."""
        if tags is None:
            tags = []

        # Convert cloze deletions to HTML
        cloze_html = re.sub(
            r"\{\{c1::(.*?)\}\}", r'<span class="cloze-blank">\1</span>', text
        )
        cloze_html = HTMLCardRenderer.convert_latex_to_mathjax(cloze_html)

        tags_html = ""
        if tags:
            tags_html = f"""
            <div class="tags-container">
                {''.join(f'<span class="tag">{tag}</span>' for tag in tags)}
            </div>
            """

        return f"""
        <div class="flashcard">
            <div class="card-header">Cloze Deletion Card</div>
            <div class="cloze-card">{cloze_html}</div>
            {tags_html}
        </div>
        """

    @staticmethod
    def render_diagram_card(
        diagram: str,
        explanation: str,
        diagram_type: str = "ascii",
        tags: List[str] = None,
    ) -> str:
        """Render a diagram card as HTML."""
        if tags is None:
            tags = []

        # Process diagram based on type
        if diagram_type == "ascii":
            diagram_html = f'<div class="diagram-code">{diagram}</div>'
        elif diagram_type == "tikz":
            # For TikZ, show the code for now (could be enhanced with TikZ to SVG conversion)
            diagram_html = f'<div class="diagram-code">{diagram}</div><p><em>TikZ Diagram Code</em></p>'
        else:
            diagram_html = f'<div class="diagram-code">{diagram}</div>'

        explanation_html = HTMLCardRenderer.convert_latex_to_mathjax(
            explanation
        )

        tags_html = ""
        if tags:
            tags_html = f"""
            <div class="tags-container">
                {''.join(f'<span class="tag">{tag}</span>' for tag in tags)}
            </div>
            """

        return f"""
        <div class="flashcard">
            <div class="card-header">Diagram Card</div>
            <div class="card-front">
                <div class="diagram-container">
                    {diagram_html}
                </div>
            </div>
            <div class="card-back">{explanation_html}</div>
            {tags_html}
        </div>
        """

    @staticmethod
    def render_cards_preview(
        cards_data: List[Dict[str, Any]], title: str = "Flashcard Preview"
    ) -> str:
        """Render multiple cards as a complete HTML document."""
        cards_html = []

        for card_data in cards_data:
            card_type = card_data.get("card_type", "front-back")
            tags = card_data.get("tags", [])

            if card_type == "front-back":
                # Extract front and back from content
                content = card_data["content"]
                # Simple parsing - could be enhanced
                parts = (
                    content.replace("\\begin{flashcard}", "")
                    .replace("\\end{flashcard}", "")
                    .strip()
                    .split("\n", 1)
                )
                front = parts[0].strip() if parts else "No content"
                back = parts[1].strip() if len(parts) > 1 else ""

                cards_html.append(
                    HTMLCardRenderer.render_front_back_card(front, back, tags)
                )

            elif card_type == "cloze":
                content = card_data["content"]
                # Clean up cloze content
                content = (
                    content.replace("\\begin{clozecard}", "")
                    .replace("\\end{clozecard}", "")
                    .strip()
                )
                # Convert LaTeX cloze to standard format
                content = re.sub(
                    r"\\\\cloze\{([^}]+)\}", r"{{c1::\1}}", content
                )

                cards_html.append(
                    HTMLCardRenderer.render_cloze_card(content, tags)
                )

            elif card_type == "diagram":
                # Extract diagram and explanation
                content = card_data["content"]
                content = (
                    content.replace("\\begin{flashcard}{Diagram}", "")
                    .replace("\\end{flashcard}", "")
                    .strip()
                )

                # Split by vspace
                parts = content.split("\\vspace{1em}")
                diagram = parts[0].strip() if parts else "No diagram"
                explanation = (
                    parts[1].strip() if len(parts) > 1 else "No explanation"
                )

                # Detect diagram type
                diagram_type = "tikz" if "tikzpicture" in diagram else "ascii"

                cards_html.append(
                    HTMLCardRenderer.render_diagram_card(
                        diagram, explanation, diagram_type, tags
                    )
                )

        full_html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title}</title>
            {HTMLCardRenderer.get_base_css()}
            {HTMLCardRenderer.get_mathjax_script()}
        </head>
        <body>
            <div class="preview-header">
                <h1>{title}</h1>
                <p>{len(cards_data)} card{"s" if len(cards_data) != 1 else ""} generated</p>
            </div>
            <div class="flashcard-container">
                {''.join(cards_html)}
            </div>
        </body>
        </html>
        """

        return full_html


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="create_flashcards",
            description="Convert text or diagrams into LaTeX flashcards for Anki",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Text or diagram content to convert to flashcards",
                    },
                    "card_type": {
                        "type": "string",
                        "enum": ["front-back", "cloze"],
                        "description": "Type of flashcard to create",
                        "default": "front-back",
                    },
                    "title": {
                        "type": "string",
                        "description": "Title for the flashcard deck",
                        "default": "Flashcards",
                    },
                    "full_document": {
                        "type": "boolean",
                        "description": "Whether to return a complete LaTeX document or just the cards",
                        "default": True,
                    },
                },
                "required": ["content"],
            },
        ),
        Tool(
            name="create_diagram_card",
            description="Create a flashcard with a diagram and explanation",
            inputSchema={
                "type": "object",
                "properties": {
                    "diagram": {
                        "type": "string",
                        "description": "The diagram content (ASCII art, TikZ code, or flowchart notation)",
                    },
                    "explanation": {
                        "type": "string",
                        "description": "Explanation or description of the diagram",
                    },
                    "diagram_type": {
                        "type": "string",
                        "enum": ["ascii", "tikz", "flowchart"],
                        "description": "Type of diagram",
                        "default": "ascii",
                    },
                },
                "required": ["diagram", "explanation"],
            },
        ),
        Tool(
            name="create_single_card",
            description="Create a single LaTeX flashcard",
            inputSchema={
                "type": "object",
                "properties": {
                    "front": {
                        "type": "string",
                        "description": "Front of the card (for front-back cards)",
                    },
                    "back": {
                        "type": "string",
                        "description": "Back of the card (for front-back cards)",
                    },
                    "cloze_text": {
                        "type": "string",
                        "description": "Text with cloze deletions marked by {{ }} (for cloze cards)",
                    },
                    "card_type": {
                        "type": "string",
                        "enum": ["front-back", "cloze"],
                        "description": "Type of flashcard to create",
                        "default": "front-back",
                    },
                },
                "anyOf": [
                    {"required": ["front", "back"]},
                    {"required": ["cloze_text"]},
                ],
            },
        ),
        Tool(
            name="upload_to_anki",
            description="Upload generated flashcards directly to Anki",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Text content to convert and upload to Anki",
                    },
                    "card_type": {
                        "type": "string",
                        "enum": ["front-back", "cloze"],
                        "description": "Type of flashcard to create",
                        "default": "front-back",
                    },
                    "deck_name": {
                        "type": "string",
                        "description": "Name of the Anki deck to upload to",
                        "default": "MCP Generated Cards",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags to add to the cards",
                        "default": ["mcp-generated"],
                    },
                    "anki_api_key": {
                        "type": "string",
                        "description": "Optional AnkiConnect API key if authentication is enabled",
                    },
                },
                "required": ["content"],
            },
        ),
        Tool(
            name="check_anki_connection",
            description="Check connection to Anki and get available decks/models",
            inputSchema={
                "type": "object",
                "properties": {
                    "anki_api_key": {
                        "type": "string",
                        "description": "Optional AnkiConnect API key if authentication is enabled",
                    }
                },
            },
        ),
        Tool(
            name="preview_cards",
            description="Generate HTML preview of flashcards for easy visualization",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Text content to convert to flashcards and preview",
                    },
                    "card_type": {
                        "type": "string",
                        "enum": ["front-back", "cloze"],
                        "description": "Type of flashcard to create",
                        "default": "front-back",
                    },
                    "title": {
                        "type": "string",
                        "description": "Title for the preview document",
                        "default": "Flashcard Preview",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags to display on the cards",
                        "default": [],
                    },
                },
                "required": ["content"],
            },
        ),
        Tool(
            name="search_anki_notes",
            description="Search for notes in Anki collection",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (e.g., 'deck:Math', 'tag:chemistry', 'Python programming')",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of notes to return",
                        "default": 20,
                    },
                    "anki_api_key": {
                        "type": "string",
                        "description": "Optional AnkiConnect API key if authentication is enabled",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_note_info",
            description="Get detailed information about specific Anki notes",
            inputSchema={
                "type": "object",
                "properties": {
                    "note_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "List of note IDs to get information about",
                    },
                    "anki_api_key": {
                        "type": "string",
                        "description": "Optional AnkiConnect API key if authentication is enabled",
                    },
                },
                "required": ["note_ids"],
            },
        ),
        Tool(
            name="update_anki_note",
            description="Update an existing Anki note",
            inputSchema={
                "type": "object",
                "properties": {
                    "note_id": {
                        "type": "integer",
                        "description": "ID of the note to update",
                    },
                    "fields": {
                        "type": "object",
                        "description": "Fields to update (field_name: new_value)",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "New tags for the note (optional)",
                    },
                    "anki_api_key": {
                        "type": "string",
                        "description": "Optional AnkiConnect API key if authentication is enabled",
                    },
                },
                "required": ["note_id", "fields"],
            },
        ),
        Tool(
            name="delete_anki_notes",
            description="Delete notes from Anki collection",
            inputSchema={
                "type": "object",
                "properties": {
                    "note_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "List of note IDs to delete",
                    },
                    "anki_api_key": {
                        "type": "string",
                        "description": "Optional AnkiConnect API key if authentication is enabled",
                    },
                },
                "required": ["note_ids"],
            },
        ),
        Tool(
            name="sync_anki",
            description="Synchronize Anki collection with AnkiWeb",
            inputSchema={
                "type": "object",
                "properties": {
                    "anki_api_key": {
                        "type": "string",
                        "description": "Optional AnkiConnect API key if authentication is enabled",
                    }
                },
            },
        ),
        Tool(
            name="add_media_to_anki",
            description="Add media files to Anki collection",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the media file to add",
                    },
                    "filename": {
                        "type": "string",
                        "description": "Name to use for the file in Anki's media collection",
                    },
                    "anki_api_key": {
                        "type": "string",
                        "description": "Optional AnkiConnect API key if authentication is enabled",
                    },
                },
                "required": ["file_path", "filename"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool calls."""
    if name == "create_flashcards":
        content = arguments.get("content", "")
        card_type = arguments.get("card_type", "front-back")
        title = arguments.get("title", "Flashcards")
        full_document = arguments.get("full_document", True)

        try:
            cards = FlashcardGenerator.parse_text_to_cards(content, card_type)

            if not cards:
                return [
                    types.TextContent(
                        type="text",
                        text="No flashcards could be generated from the provided content. Please check the format.",
                    )
                ]

            if full_document:
                result = FlashcardGenerator.create_latex_document(cards, title)
            else:
                result = "\n\n".join(cards)

            return [types.TextContent(type="text", text=result)]

        except Exception as e:
            return [
                types.TextContent(
                    type="text", text=f"Error generating flashcards: {str(e)}"
                )
            ]

    elif name == "create_diagram_card":
        diagram = arguments.get("diagram", "")
        explanation = arguments.get("explanation", "")
        diagram_type = arguments.get("diagram_type", "ascii")

        if not diagram or not explanation:
            return [
                types.TextContent(
                    type="text",
                    text="Both diagram and explanation are required",
                )
            ]

        try:
            result = FlashcardGenerator.create_diagram_card(
                diagram, explanation, diagram_type
            )
            return [types.TextContent(type="text", text=result)]
        except Exception as e:
            return [
                types.TextContent(
                    type="text", text=f"Error creating diagram card: {str(e)}"
                )
            ]

    elif name == "create_single_card":
        card_type = arguments.get("card_type", "front-back")

        try:
            if card_type == "front-back":
                front = arguments.get("front", "")
                back = arguments.get("back", "")
                if not front or not back:
                    return [
                        types.TextContent(
                            type="text",
                            text="Both front and back are required for front-back cards",
                        )
                    ]

                result = FlashcardGenerator.create_front_back_card(front, back)

            elif card_type == "cloze":
                cloze_text = arguments.get("cloze_text", "")
                if not cloze_text:
                    return [
                        types.TextContent(
                            type="text",
                            text="Cloze text is required for cloze cards",
                        )
                    ]

                result = FlashcardGenerator.create_cloze_deletion_card(
                    cloze_text
                )

            return [types.TextContent(type="text", text=result)]

        except Exception as e:
            return [
                types.TextContent(
                    type="text", text=f"Error creating flashcard: {str(e)}"
                )
            ]

    elif name == "upload_to_anki":
        content = arguments.get("content", "")
        card_type = arguments.get("card_type", "front-back")
        deck_name = arguments.get("deck_name", "MCP Generated Cards")
        tags = arguments.get("tags", ["mcp-generated"])
        anki_api_key = arguments.get("anki_api_key")

        if not content:
            return [
                types.TextContent(
                    type="text",
                    text="Content is required for uploading to Anki",
                )
            ]

        try:
            # Generate flashcards from content
            cards = FlashcardGenerator.parse_text_to_cards(content, card_type)

            if not cards:
                return [
                    types.TextContent(
                        type="text",
                        text="No flashcards could be generated from the provided content",
                    )
                ]

            # Initialize Anki connection
            anki_connector = AnkiConnector(api_key=anki_api_key)
            card_manager = AnkiCardManager(anki_connector)

            # Prepare cards data for upload
            cards_data = []
            for card_content in cards:
                cards_data.append(
                    {
                        "content": card_content,
                        "card_type": card_type,
                        "tags": tags,
                    }
                )

            # Upload to Anki
            result = card_manager.upload_cards_to_anki(cards_data, deck_name)

            if result["success"]:
                response = f"Successfully uploaded {result['successful_uploads']} cards to Anki deck '{result['deck_name']}'"
                if result["failed_uploads"] > 0:
                    response += f" ({result['failed_uploads']} failed)"
                return [types.TextContent(type="text", text=response)]
            else:
                return [
                    types.TextContent(
                        type="text",
                        text=f"Failed to upload cards to Anki: {result['error']}",
                    )
                ]

        except Exception as e:
            return [
                types.TextContent(
                    type="text", text=f"Error uploading to Anki: {str(e)}"
                )
            ]

    elif name == "check_anki_connection":
        anki_api_key = arguments.get("anki_api_key")

        try:
            anki_connector = AnkiConnector(api_key=anki_api_key)

            # Check connection and permissions
            permission_info = anki_connector.check_permission()

            # Get available decks and models
            decks = anki_connector.get_deck_names()
            models = anki_connector.get_model_names()

            response = f"""Anki Connection Status: ✓ Connected
            
Permission: {permission_info.get('permission', 'unknown')}
API Key Required: {permission_info.get('requireApiKey', False)}
Version: {permission_info.get('version', 'unknown')}

Available Decks ({len(decks)}):
{', '.join(decks[:10])}{'...' if len(decks) > 10 else ''}

Available Note Types ({len(models)}):
{', '.join(models[:10])}{'...' if len(models) > 10 else ''}
"""

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            return [
                types.TextContent(
                    type="text",
                    text=f"Failed to connect to Anki: {str(e)}\n\nMake sure Anki is running and AnkiConnect addon is installed.",
                )
            ]

    elif name == "preview_cards":
        content = arguments.get("content", "")
        card_type = arguments.get("card_type", "front-back")
        title = arguments.get("title", "Flashcard Preview")
        tags = arguments.get("tags", [])

        if not content:
            return [
                types.TextContent(
                    type="text", text="Content is required for previewing cards"
                )
            ]

        try:
            # Generate flashcards from content
            cards = FlashcardGenerator.parse_text_to_cards(content, card_type)

            if not cards:
                return [
                    types.TextContent(
                        type="text",
                        text="No flashcards could be generated from the provided content",
                    )
                ]

            # Prepare cards data for rendering
            cards_data = []
            for card_content in cards:
                cards_data.append(
                    {
                        "content": card_content,
                        "card_type": card_type,
                        "tags": tags,
                    }
                )

            # Generate HTML preview
            html_preview = HTMLCardRenderer.render_cards_preview(
                cards_data, title
            )

            return [types.TextContent(type="text", text=html_preview)]

        except Exception as e:
            return [
                types.TextContent(
                    type="text", text=f"Error generating preview: {str(e)}"
                )
            ]


    elif name == "search_anki_notes":
        query = arguments.get("query", "")
        limit = arguments.get("limit", 20)
        anki_api_key = arguments.get("anki_api_key")

        if not query:
            return [
                types.TextContent(type="text", text="Search query is required")
            ]

        try:
            anki_connector = AnkiConnector(api_key=anki_api_key)
            note_ids = anki_connector.find_notes(query)

            if not note_ids:
                return [
                    types.TextContent(
                        type="text", text=f"No notes found for query: {query}"
                    )
                ]

            # Limit results
            limited_note_ids = note_ids[:limit]

            # Get note information
            notes_info = anki_connector.notes_info(limited_note_ids)

            response = f"Found {len(note_ids)} notes (showing first {len(limited_note_ids)}):\n\n"

            for i, note_info in enumerate(notes_info, 1):
                response += f"{i}. **Note ID:** {note_info['noteId']}\n"
                response += f"   **Model:** {note_info['modelName']}\n"
                response += (
                    f"   **Tags:** {', '.join(note_info.get('tags', []))}\n"
                )

                # Show first few fields
                fields = note_info.get("fields", {})
                for field_name, field_value in list(fields.items())[:2]:
                    preview = (
                        field_value["value"][:100] + "..."
                        if len(field_value["value"]) > 100
                        else field_value["value"]
                    )
                    response += f"   **{field_name}:** {preview}\n"
                response += "\n"

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            return [
                types.TextContent(
                    type="text", text=f"Error searching Anki notes: {str(e)}"
                )
            ]

    elif name == "get_note_info":
        note_ids = arguments.get("note_ids", [])
        anki_api_key = arguments.get("anki_api_key")

        if not note_ids:
            return [
                types.TextContent(type="text", text="Note IDs are required")
            ]

        try:
            anki_connector = AnkiConnector(api_key=anki_api_key)
            notes_info = anki_connector.notes_info(note_ids)

            response = f"Information for {len(notes_info)} notes:\n\n"

            for note_info in notes_info:
                response += f"**Note ID:** {note_info['noteId']}\n"
                response += f"**Model:** {note_info['modelName']}\n"
                response += (
                    f"**Tags:** {', '.join(note_info.get('tags', []))}\n"
                )
                response += f"**Fields:**\n"

                fields = note_info.get("fields", {})
                for field_name, field_value in fields.items():
                    response += f"  - {field_name}: {field_value['value']}\n"
                response += "\n"

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            return [
                types.TextContent(
                    type="text", text=f"Error getting note info: {str(e)}"
                )
            ]

    elif name == "update_anki_note":
        note_id = arguments.get("note_id")
        fields = arguments.get("fields", {})
        tags = arguments.get("tags")
        anki_api_key = arguments.get("anki_api_key")

        if not note_id or not fields:
            return [
                types.TextContent(
                    type="text", text="Note ID and fields are required"
                )
            ]

        try:
            anki_connector = AnkiConnector(api_key=anki_api_key)
            anki_connector.update_note(note_id, fields, tags)

            response = f"Successfully updated note {note_id}"
            if tags:
                response += f" with tags: {', '.join(tags)}"

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            return [
                types.TextContent(
                    type="text", text=f"Error updating note: {str(e)}"
                )
            ]

    elif name == "delete_anki_notes":
        note_ids = arguments.get("note_ids", [])
        anki_api_key = arguments.get("anki_api_key")

        if not note_ids:
            return [
                types.TextContent(type="text", text="Note IDs are required")
            ]

        try:
            anki_connector = AnkiConnector(api_key=anki_api_key)
            anki_connector.delete_notes(note_ids)

            response = f"Successfully deleted {len(note_ids)} notes"

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            return [
                types.TextContent(
                    type="text", text=f"Error deleting notes: {str(e)}"
                )
            ]

    elif name == "sync_anki":
        anki_api_key = arguments.get("anki_api_key")

        try:
            anki_connector = AnkiConnector(api_key=anki_api_key)
            anki_connector.sync()

            response = "Successfully synchronized Anki collection with AnkiWeb"

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            return [
                types.TextContent(
                    type="text", text=f"Error syncing Anki: {str(e)}"
                )
            ]

    elif name == "add_media_to_anki":
        file_path = arguments.get("file_path", "")
        filename = arguments.get("filename", "")
        anki_api_key = arguments.get("anki_api_key")

        if not file_path or not filename:
            return [
                types.TextContent(
                    type="text", text="File path and filename are required"
                )
            ]

        try:
            # Check if file exists
            if not Path(file_path).exists():
                return [
                    types.TextContent(
                        type="text", text=f"File not found: {file_path}"
                    )
                ]

            anki_connector = AnkiConnector(api_key=anki_api_key)

            # Encode file to base64
            base64_data = anki_connector.encode_file_to_base64(file_path)

            # Store in Anki
            stored_filename = anki_connector.store_media_file(
                filename, base64_data
            )

            response = f"Successfully added media file '{stored_filename}' to Anki collection"

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            return [
                types.TextContent(
                    type="text", text=f"Error adding media to Anki: {str(e)}"
                )
            ]

    else:
        raise ValueError(f"Unknown tool: {name}")


async def main():
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="mcp-server-learning-flashcards",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
