#!/usr/bin/env python3
"""
FastMCP-powered Flashcard Server

A modern, streamlined implementation of the flashcard MCP server using FastMCP's
Pythonic patterns for reduced boilerplate and improved maintainability.
"""

import re
import sys
from typing import Any, Dict, List, Optional

import requests
from fastmcp import FastMCP

# Initialize FastMCP instance
mcp = FastMCP(
    "Flashcard MCP Server",
    instructions="""This server creates spaced-repetition flashcards and manages Anki integration.

Use these tools when the user wants to:
- Create flashcards from study material (create_cards)
- Upload flashcards to their Anki deck (upload_cards)
- Search, update, or delete existing Anki cards (search_notes, update_note, delete_notes)
- Move cards between decks or sync with AnkiWeb (move_to_deck, sync)
- Check Anki connectivity (check_connection)

All tools return: {"success": bool, "data": Any, "message": str, "error": str|null}. Check "success" first.

LaTeX math is supported: $...$ for inline, $$...$$ for display math.
For Anki upload, LaTeX is automatically converted to MathJax format.

Requires: Anki desktop running with AnkiConnect addon (port 8765).

FLASHCARD QUALITY RULES - follow these when generating card content:
1. ATOMICITY: Each card tests exactly ONE fact. If a card can be split, split it.
2. BREVITY: Front 5-20 words (max 30). Back 1-15 words (max 30).
3. NO LISTS: Never put a list as the answer. Make separate cards per item.
4. PRECISE: Every question must have exactly one correct answer.
5. NO YES/NO: Rephrase to test the underlying knowledge directly.
6. CONTEXT PREFIX: Start fronts with a topic label (e.g., "Linear Algebra:").
7. MATH: Use cloze to blank one variable at a time. Test when/why, not computation.
8. CLOZE vs Q&A: Use cloze for facts/formulas/terms. Use front-back for conceptual understanding.
""",
)


class AnkiConnector:
    """Interface for connecting to Anki via AnkiConnect addon."""

    def __init__(self, url: str = "http://localhost:8765", api_key: Optional[str] = None):
        self.url = url
        self.api_key = api_key
        self.session = requests.Session()

    def _make_request(self, action: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
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
                # Match project test expectations
                raise Exception(f"AnkiConnect error: {result['error']}")

            return result.get("result")

        except requests.exceptions.ConnectionError:
            # Include expected substring for tests
            raise Exception("Failed to connect to Anki: connection refused")
        except requests.exceptions.Timeout:
            # Include expected substring for tests
            raise Exception("Failed to connect to Anki: request timed out")
        except Exception as e:
            if "Anki Connect API error" in str(e):
                raise
            raise Exception(f"Request failed: {e}")

    def check_permission(self) -> Dict[str, Any]:
        """Check if AnkiConnect is available and get permission info."""
        return self._make_request("requestPermission")

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
        note_id = self._make_request("addNote", {"note": note})

        # Auto-flag with purple (best-effort, don't fail if flagging errors)
        try:
            if note_id:
                card_ids = self.get_card_ids_from_notes([note_id])
                if card_ids:
                    self._set_card_flags(card_ids)
        except Exception:
            # Flag setting is enhancement, don't break note creation
            pass

        return note_id

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
        note_ids = self._make_request("addNotes", {"notes": formatted_notes})

        # Auto-flag with purple (best-effort, don't fail if flagging errors)
        try:
            successful_ids = [nid for nid in note_ids if nid is not None]
            if successful_ids:
                card_ids = self.get_card_ids_from_notes(successful_ids)
                if card_ids:
                    self._set_card_flags(card_ids)
        except Exception:
            # Flag setting is enhancement, don't break batch creation
            pass

        return note_ids

    def find_notes(self, query: str) -> List[int]:
        """Find notes matching the given query."""
        return self._make_request("findNotes", {"query": query})

    def notes_info(self, note_ids: List[int]) -> List[Dict[str, Any]]:
        """Get detailed information about specific notes."""
        return self._make_request("notesInfo", {"notes": note_ids})

    def get_card_ids_from_notes(self, note_ids: List[int]) -> List[int]:
        """Get all card IDs associated with note IDs.

        Args:
            note_ids: List of note IDs to get cards from.

        Returns:
            List of card IDs (may be multiple cards per note).
        """
        if not note_ids:
            return []

        notes_data = self.notes_info(note_ids)
        card_ids = []
        for note in notes_data:
            card_ids.extend(note.get("cards", []))
        return card_ids

    def update_note(self, note_id: int, fields: Dict[str, str], tags: List[str] = None) -> None:
        """Update an existing note."""
        params = {"note": {"id": note_id, "fields": fields}}
        if tags is not None:
            params["note"]["tags"] = tags
        self._make_request("updateNoteFields", params)

        # Auto-flag with purple (best-effort, don't fail if flagging errors)
        try:
            card_ids = self.get_card_ids_from_notes([note_id])
            if card_ids:
                self._set_card_flags(card_ids)
        except Exception:
            # Flag setting is enhancement, don't break note update
            pass

    def delete_notes(self, note_ids: List[int]) -> None:
        """Delete notes by their IDs."""
        self._make_request("deleteNotes", {"notes": note_ids})

    def delete_decks(self, deck_names: List[str], cards_too: bool = True) -> None:
        """Delete decks and optionally their cards.

        Args:
            deck_names: List of deck names to delete.
            cards_too: If True, also delete all cards in those decks. Defaults to True.
        """
        self._make_request("deleteDecks", {"decks": deck_names, "cardsToo": cards_too})

    def sync(self) -> None:
        """Synchronize collection with AnkiWeb."""
        self._make_request("sync")

    def change_deck(self, card_ids: List[int], deck: str) -> None:
        """Move cards to a different deck.

        Args:
            card_ids: List of card IDs to move.
            deck: Target deck name.
        """
        self._make_request("changeDeck", {"cards": card_ids, "deck": deck})

    def _set_card_flags(self, card_ids: List[int], flag: int = 7) -> None:
        """Set flags on cards (purple=7 by default).

        Args:
            card_ids: List of card IDs to flag.
            flag: Flag value (0=none, 1=red, 2=orange, 3=green, 4=blue, 5=pink, 6=turquoise, 7=purple).
        """
        if not card_ids:
            return

        self._make_request(
            "setSpecificValueOfCard",
            {"cards": card_ids, "keys": ["flags"], "newValues": [str(flag)]},
        )


class FlashcardGenerator:
    """Generates flashcards from text with proper LaTeX math formatting.

    Math Rendering:
    - Claude Desktop: Uses standard LaTeX ($...$ and $$...$$) - renders natively
    - Anki: Converts to MathJax format (\\(...\\) and \\[...\\]) - works with Anki's MathJax

    LaTeX Examples:
    - Inline math: $E = mc^2$
    - Display math: $$P(X \\geq a) \\leq \\frac{E[X]}{a}$$
    - Greek letters: $\\sigma$, $\\alpha$, $\\beta$
    - Fractions: $\\frac{1}{1 + e^{-x}}$
    - Subscripts/superscripts: $x_i^2$, $e^{-x}$
    """

    @staticmethod
    def preserve_claude_latex(text: str) -> str:
        """Keep standard LaTeX format for Claude Desktop (native LaTeX rendering)."""
        if not text:
            return text

        # Claude Desktop supports standard LaTeX natively
        # Just clean up any escaping issues
        result = text.replace("\\$", "$")  # Unescape dollar signs
        return result

    @staticmethod
    def convert_to_anki_mathjax(text: str) -> str:
        """Convert standard LaTeX to Anki MathJax format."""
        if not text:
            return text

        result = text

        # Convert standard LaTeX delimiters to Anki MathJax format
        # $$display math$$ -> \[display math\]
        result = re.sub(r"\$\$([^$]+?)\$\$", r"\\[\1\\]", result)

        # $inline math$ -> \(inline math\)
        result = re.sub(r"\$([^$\n]+?)\$", r"\\(\1\\)", result)

        return result

    @staticmethod
    def convert_latex_to_display_format(text: str) -> str:
        """Convert various LaTeX math delimiters to unified display format \\[...\\].

        - $...$ -> \\[...\\]
        - $$...$$ -> \\[...\\]
        - \\(...\\) -> \\[...\\]
        - Existing \\[...\\] is preserved.
        """
        if not text:
            return text

        s = text

        # Protect existing display math \[...\]
        placeholders: list[str] = []

        def _protect(match):
            placeholders.append(match.group(0))
            return f"__MJX_DISPLAY_{len(placeholders)-1}__"

        s = re.sub(r"\\\[[\s\S]*?\\\]", _protect, s)

        # Convert \(...\) -> \[...\]
        s = re.sub(r"\\\(([^)]*?)\\\)", r"\\[\1\\]", s)

        # Convert $$...$$ -> \[...\]
        s = re.sub(r"\$\$([\s\S]*?)\$\$", r"\\[\1\\]", s)

        # Convert inline $...$ -> \[...\] (avoid $$ handled above)
        s = re.sub(r"(?<!\$)\$([^\n$]+?)\$(?!\$)", r"\\[\1\\]", s)

        # Restore protected \[...\]
        for i, ph in enumerate(placeholders):
            s = s.replace(f"__MJX_DISPLAY_{i}__", ph)

        return s

    @staticmethod
    def create_anki_cloze_card(text: str, cloze_markers: List[str] = None) -> str:
        """Create a cloze deletion card in Anki format."""
        if cloze_markers is None:
            cloze_markers = ["{{", "}}"]

        # Find text within cloze markers
        pattern = f"{re.escape(cloze_markers[0])}(.*?){re.escape(cloze_markers[1])}"
        matches = re.findall(pattern, text)

        if not matches:
            raise ValueError("No cloze deletions found in text")

        # Create the card with numbered cloze deletions
        card_text = text
        for i, match in enumerate(matches, 1):
            replacement = f"{{{{c{i}::{match}}}}}"
            old_pattern = (
                f"{re.escape(cloze_markers[0])}{re.escape(match)}{re.escape(cloze_markers[1])}"
            )
            card_text = re.sub(old_pattern, replacement, card_text, count=1)

        return card_text

    @staticmethod
    def parse_text_to_cards(text: str, card_type: str = "front-back") -> List[Dict[str, str]]:
        """Parse text into multiple flashcards (preserves LaTeX for Claude Desktop)."""
        cards = []

        if card_type == "front-back":
            # First, try to find Q: A: patterns in the entire text (not split by newlines)
            qa_matches = list(
                re.finditer(
                    r"Q:\s*(.*?)\s*A:\s*(.*?)(?=Q:|$)",
                    text.strip(),
                    re.DOTALL | re.IGNORECASE,
                )
            )

            if qa_matches:
                # Process Q: A: patterns found
                for qa_match in qa_matches:
                    front = qa_match.group(1).strip()
                    back = qa_match.group(2).strip()

                    # Keep LaTeX as-is for Claude Desktop display
                    front = FlashcardGenerator.preserve_claude_latex(front)
                    back = FlashcardGenerator.preserve_claude_latex(back)

                    cards.append({"front": front, "back": back})
            else:
                # Fallback: Split by double newlines or specific separators
                sections = re.split(r"\n\s*\n|---", text.strip())

                for section in sections:
                    section = section.strip()
                    if not section:
                        continue

                    # Look for question/answer separated by newline
                    lines = section.split("\n")
                    if len(lines) >= 2:
                        front = lines[0].strip()
                        back = "\n".join(lines[1:]).strip()

                        # Keep LaTeX as-is for Claude Desktop display
                        front = FlashcardGenerator.preserve_claude_latex(front)
                        back = FlashcardGenerator.preserve_claude_latex(back)

                        cards.append({"front": front, "back": back})

        elif card_type == "cloze":
            # Split by double newlines for multiple cloze cards
            sections = re.split(r"\n\s*\n", text.strip())

            for section in sections:
                section = section.strip()
                if not section:
                    continue

                try:
                    cloze_text = FlashcardGenerator.create_anki_cloze_card(section)
                    # Keep LaTeX as-is for Claude Desktop display
                    cloze_text = FlashcardGenerator.preserve_claude_latex(cloze_text)
                    cards.append({"text": cloze_text})
                except ValueError:
                    # If no cloze markers found, skip this section
                    continue

        return cards


class AnkiCardManager:
    """Manages conversion and upload of flashcards to Anki."""

    def __init__(self, anki_connector: AnkiConnector):
        self.anki = anki_connector

    def get_default_model_for_card_type(self, card_type: str) -> str:
        """Get the appropriate Anki model for a flashcard type."""
        model_mapping = {
            "front-back": "Basic",
            "cloze": "Cloze",
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
        """Get field names for a model."""
        try:
            return self.anki.get_model_field_names(model_name)
        except Exception as e:
            raise Exception(f"Failed to get fields for model '{model_name}': {e}")

    def convert_to_anki_fields(
        self, card_data: Dict[str, str], card_type: str, model_name: str = None
    ) -> Dict[str, str]:
        """Convert flashcard data to Anki field format."""
        if model_name is None:
            model_name = self.get_default_model_for_card_type(card_type)

        # Validate model exists
        if not self.validate_model_exists(model_name):
            fallback_model = self.get_default_model_for_card_type(card_type)
            if fallback_model != model_name and self.validate_model_exists(fallback_model):
                model_name = fallback_model
            else:
                raise Exception(f"Model '{model_name}' not found and no valid fallback available")

        try:
            field_names = self.get_model_fields(model_name)
        except Exception:
            # Fallback field names
            field_names = ["Front", "Back"] if card_type != "cloze" else ["Text"]

        # Convert based on card type
        if card_type == "front-back":
            fields = {
                field_names[0]: card_data.get("front", ""),
                field_names[1]: (card_data.get("back", "") if len(field_names) > 1 else ""),
            }
        elif card_type == "cloze":
            fields = {field_names[0]: card_data.get("text", "")}
        else:
            fields = {field_names[0]: str(card_data)}

        # Fill missing fields with empty strings
        for field_name in field_names:
            if field_name not in fields:
                fields[field_name] = ""

        return fields

    def upload_cards_to_anki(
        self, cards_data: List[Dict[str, Any]], deck_name: str
    ) -> Dict[str, Any]:
        """Upload multiple cards to Anki."""
        try:
            # Check connection and create deck if needed
            self.anki.check_permission()
            self.anki.create_deck(deck_name)

            # Convert cards to Anki format
            anki_notes = []
            for card_data in cards_data:
                card_type = card_data.get("card_type", "front-back")
                model_name = card_data.get(
                    "model_name",
                    self.get_default_model_for_card_type(card_type),
                )

                fields = self.convert_to_anki_fields(card_data["data"], card_type, model_name)

                anki_notes.append(
                    {
                        "deck_name": deck_name,
                        "model_name": model_name,
                        "fields": fields,
                        "tags": card_data.get("tags", ["mcp-generated"]),
                    }
                )

            # Upload to Anki
            if anki_notes:
                note_ids = self.anki.add_notes(anki_notes)
                successful = sum(1 for note_id in note_ids if note_id is not None)
                failed = len(note_ids) - successful

                return {
                    "success": True,
                    "deck_name": deck_name,
                    "total_cards": len(cards_data),
                    "successful_uploads": successful,
                    "failed_uploads": failed,
                    "note_ids": note_ids,
                }
            else:
                return {
                    "success": False,
                    "error": "No valid cards to upload",
                    "total_cards": len(cards_data),
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "total_cards": len(cards_data),
            }


def get_anki_connector(api_key: Optional[str] = None) -> AnkiConnector:
    """Get Anki connector instance."""
    return AnkiConnector(api_key=api_key)


@mcp.tool
def create_cards(
    content: str,
    card_type: str = "front-back",
    title: str = "",
    tags: List[str] = None,
) -> Dict[str, Any]:
    """Create flashcards from text content IN MEMORY (does not upload to Anki).
    Use upload_cards to send cards to Anki after reviewing them.

    Accepts Q:/A: format for front-back cards or {{cloze markers}} for cloze cards.
    LaTeX math supported: $inline$ and $$display$$.

    CARD QUALITY GUIDELINES - follow these strictly:
    - Each card must test exactly ONE atomic fact (split multi-fact cards)
    - Front: 5-20 words ideal, 30 max. Back: 1-15 words ideal, 30 max
    - Start each front with a topic prefix (e.g., "Calculus:", "Cell Bio:")
    - No lists as answers -- make one card per item instead
    - No yes/no answers -- rephrase to test the knowledge directly
    - For math formulas: use cloze, blank ONE variable at a time
    - For concepts/explanations: use front-back Q&A
    - For definitions/terms/facts: use cloze deletions

    Args:
        content: Card content in Q:/A: format (front-back) or with {{cloze}} markers.
            Example front-back: "Q: Calculus: What is the derivative of $x^n$? A: $nx^{n-1}$ (power rule)"
            Example cloze: "The derivative of $x^n$ is ${{nx^{n-1}}}$ by the power rule"
        card_type: "front-back" for Q&A pairs, "cloze" for fill-in-the-blank
        title: Optional title for this card set
        tags: Optional tags for categorization

    Returns {"success": bool, "data": {"cards": [{"front": str, "back": str}], "card_type": str,
    "title": str, "tags": [str]}, "message": str, "error": str|null}.
    """
    if tags is None:
        tags = []

    try:
        cards = FlashcardGenerator.parse_text_to_cards(content, card_type)

        if not cards:
            return {
                "success": False,
                "data": None,
                "message": "No flashcards could be generated from the provided content",
                "error": "Invalid content format",
            }

        return {
            "success": True,
            "data": {
                "cards": cards,
                "card_type": card_type,
                "title": title,
                "tags": tags,
            },
            "message": f"Generated {len(cards)} flashcard(s)",
            "error": None,
        }

    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": "Error generating flashcards",
            "error": str(e),
        }


@mcp.tool
def upload_cards(
    content: str,
    deck_name: str = "MCP Generated Cards",
    card_type: str = "front-back",
    tags: List[str] = None,
    anki_api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Parse text into flashcards and upload directly to Anki. LaTeX ($...$) is
    automatically converted to MathJax format for Anki rendering.

    Creates the deck if it doesn't exist. Cards are auto-flagged purple for easy identification.
    Requires Anki running with AnkiConnect addon on port 8765.

    CARD QUALITY GUIDELINES - follow these strictly:
    - Each card must test exactly ONE atomic fact (split multi-fact cards)
    - Front: 5-20 words ideal, 30 max. Back: 1-15 words ideal, 30 max
    - Start each front with a topic prefix (e.g., "Calculus:", "Cell Bio:")
    - No lists as answers -- make one card per item instead
    - No yes/no answers -- rephrase to test the knowledge directly
    - For math formulas: use cloze, blank ONE variable at a time
    - For concepts/explanations: use front-back Q&A

    Args:
        content: Card content in Q:/A: format or with {{cloze}} markers.
            Example: "Q: Topology: What is a homeomorphism? A: A continuous bijection with continuous inverse"
        deck_name: Target Anki deck name (created if it doesn't exist)
        card_type: "front-back" for Q&A pairs, "cloze" for fill-in-the-blank
        tags: Tags for the cards (default: ["mcp-generated"])
        anki_api_key: AnkiConnect API key (only if authentication is configured)

    Returns {"success": bool, "data": {"deck_name": str, "successful_uploads": int,
    "failed_uploads": int, "note_ids": [int]}, "message": str, "error": str|null}.
    """
    if tags is None:
        tags = ["mcp-generated"]

    try:
        # Generate flashcards from content (preserves LaTeX initially)
        cards = FlashcardGenerator.parse_text_to_cards(content, card_type)

        # Convert LaTeX to Anki MathJax format for each card
        for card in cards:
            if "front" in card:
                card["front"] = FlashcardGenerator.convert_to_anki_mathjax(card["front"])
                card["back"] = FlashcardGenerator.convert_to_anki_mathjax(card["back"])
            elif "text" in card:
                card["text"] = FlashcardGenerator.convert_to_anki_mathjax(card["text"])

        if not cards:
            return {
                "success": False,
                "data": None,
                "message": "No flashcards could be generated from the provided content",
                "error": "Invalid content format",
            }

        # Initialize Anki connection
        anki_connector = get_anki_connector(anki_api_key)
        card_manager = AnkiCardManager(anki_connector)

        # Prepare cards data for upload
        cards_data = []
        for card in cards:
            cards_data.append(
                {
                    "data": card,
                    "card_type": card_type,
                    "tags": tags,
                }
            )

        # Upload to Anki
        result = card_manager.upload_cards_to_anki(cards_data, deck_name)

        if result["success"]:
            return {
                "success": True,
                "data": result,
                "message": f"Successfully uploaded {result['successful_uploads']} cards to Anki deck '{result['deck_name']}'",
                "error": None,
            }
        else:
            return {
                "success": False,
                "data": result,
                "message": "Failed to upload cards to Anki",
                "error": result.get("error"),
            }

    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": "Error uploading to Anki",
            "error": str(e),
        }


@mcp.tool
def check_connection(anki_api_key: Optional[str] = None) -> Dict[str, Any]:
    """Check if Anki is running and accessible via AnkiConnect. Returns available decks
    and note models. Use this as a diagnostic before upload_cards, or to discover deck names.

    Args:
        anki_api_key: AnkiConnect API key (only if authentication is configured)

    Returns {"success": bool, "data": {"permission": dict, "decks": [str], "models": [str]},
    "message": str, "error": str|null}.
    """
    try:
        anki_connector = get_anki_connector(anki_api_key)

        # Check connection and permissions
        permission_info = anki_connector.check_permission()

        # Get available decks and models
        decks = anki_connector.get_deck_names()
        models = anki_connector.get_model_names()

        return {
            "success": True,
            "data": {
                "permission": permission_info,
                "decks": decks,
                "models": models,
            },
            "message": f"Connected to Anki - {len(decks)} deck(s), {len(models)} model(s) available",
            "error": None,
        }

    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": "Failed to connect to Anki",
            "error": str(e),
        }


@mcp.tool
def search_notes(query: str, limit: int = 20, anki_api_key: Optional[str] = None) -> Dict[str, Any]:
    """Search for notes in the Anki collection using Anki's query syntax.

    Use this to find note IDs needed by update_note, delete_notes, or move_to_deck.

    Args:
        query: Anki search query. Supports: 'deck:DeckName', 'tag:tagname',
            'front:*keyword*', 'added:7' (last 7 days), or free text.
        limit: Maximum notes to return (1-100)
        anki_api_key: AnkiConnect API key (only if authentication is configured)

    Returns {"success": bool, "data": {"notes": [{"noteId": int, "fields": dict,
    "tags": [str], "modelName": str, "cards": [int]}], "total_found": int,
    "returned": int, "query": str}, "message": str, "error": str|null}.
    """
    try:
        anki_connector = get_anki_connector(anki_api_key)
        note_ids = anki_connector.find_notes(query)

        if not note_ids:
            return {
                "success": True,
                "data": {"notes": [], "total_found": 0, "query": query},
                "message": f"No notes found for query: {query}",
                "error": None,
            }

        # Limit results
        limited_note_ids = note_ids[:limit]

        # Get note information
        notes_info = anki_connector.notes_info(limited_note_ids)

        return {
            "success": True,
            "data": {
                "notes": notes_info,
                "total_found": len(note_ids),
                "returned": len(limited_note_ids),
                "query": query,
            },
            "message": f"Found {len(note_ids)} notes (showing {len(limited_note_ids)})",
            "error": None,
        }

    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": "Error searching Anki notes",
            "error": str(e),
        }


@mcp.tool
def update_note(
    note_id: int,
    fields: Dict[str, str],
    tags: Optional[List[str]] = None,
    anki_api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Update fields and/or tags on an existing Anki note. Updated cards are
    automatically re-flagged purple.

    To find a note_id, use search_notes first (e.g., search_notes("deck:MyDeck")).

    Args:
        note_id: Note ID from search_notes results
        fields: Fields to update, e.g. {"Front": "new question", "Back": "new answer"}
        tags: Replace all tags on this note (omit to keep existing tags)
        anki_api_key: AnkiConnect API key (only if authentication is configured)

    Returns {"success": bool, "data": {"note_id": int, "fields": dict, "tags": list},
    "message": str, "error": str|null}.
    """
    try:
        anki_connector = get_anki_connector(anki_api_key)
        anki_connector.update_note(note_id, fields, tags)

        return {
            "success": True,
            "data": {"note_id": note_id, "fields": fields, "tags": tags},
            "message": f"Successfully updated note {note_id}",
            "error": None,
        }

    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": f"Error updating note {note_id}",
            "error": str(e),
        }


@mcp.tool
def delete_notes(note_ids: List[int], anki_api_key: Optional[str] = None) -> Dict[str, Any]:
    """Permanently delete notes and their cards from Anki. This is destructive
    and cannot be undone.

    To find note_ids, use search_notes first.

    Args:
        note_ids: List of note IDs to delete (from search_notes results)
        anki_api_key: AnkiConnect API key (only if authentication is configured)

    Returns {"success": bool, "data": {"deleted_note_ids": [int], "count": int},
    "message": str, "error": str|null}.
    """
    try:
        anki_connector = get_anki_connector(anki_api_key)
        anki_connector.delete_notes(note_ids)

        return {
            "success": True,
            "data": {"deleted_note_ids": note_ids, "count": len(note_ids)},
            "message": f"Successfully deleted {len(note_ids)} notes",
            "error": None,
        }

    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": "Error deleting notes",
            "error": str(e),
        }


@mcp.tool
def sync(anki_api_key: Optional[str] = None) -> Dict[str, Any]:
    """Synchronize the local Anki collection with AnkiWeb. Requires an AnkiWeb
    account configured in Anki. Use after uploading or modifying cards.

    Args:
        anki_api_key: AnkiConnect API key (only if authentication is configured)

    Returns {"success": bool, "data": null, "message": str, "error": str|null}.
    """
    try:
        anki_connector = get_anki_connector(anki_api_key)
        anki_connector.sync()

        return {
            "success": True,
            "data": None,
            "message": "Successfully synchronized Anki collection with AnkiWeb",
            "error": None,
        }

    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": "Error syncing Anki",
            "error": str(e),
        }


@mcp.tool
def move_to_deck(
    note_ids: List[int], deck_name: str, anki_api_key: Optional[str] = None
) -> Dict[str, Any]:
    """Move notes (and their cards) to a different Anki deck. The target deck
    is created if it doesn't exist.

    To find note_ids, use search_notes first.

    Args:
        note_ids: List of note IDs to move (from search_notes results)
        deck_name: Target deck name (e.g., "Physics::Thermodynamics")
        anki_api_key: AnkiConnect API key (only if authentication is configured)

    Returns {"success": bool, "data": {"note_ids": [int], "card_ids": [int],
    "deck_name": str}, "message": str, "error": str|null}.
    """
    try:
        anki_connector = get_anki_connector(anki_api_key)

        # Get card IDs from note IDs
        notes_info = anki_connector.notes_info(note_ids)
        card_ids = []
        for note in notes_info:
            card_ids.extend(note.get("cards", []))

        if not card_ids:
            return {
                "success": False,
                "data": None,
                "message": "No cards found for the given note IDs",
                "error": "No cards to move",
            }

        # Move cards to target deck
        anki_connector.change_deck(card_ids, deck_name)

        return {
            "success": True,
            "data": {
                "note_ids": note_ids,
                "card_ids": card_ids,
                "deck_name": deck_name,
            },
            "message": f"Successfully moved {len(card_ids)} card(s) to '{deck_name}'",
            "error": None,
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": "Error moving notes to deck",
            "error": str(e),
        }


@mcp.prompt
def study_from_notes(note_names: str, deck_name: str = "Study Cards") -> str:
    """Generate flashcards from Obsidian notes and upload to Anki."""
    return f"""Help me study by creating flashcards from my Obsidian notes.

Notes to process: {note_names}
Target Anki deck: {deck_name}

Steps:
1. Use obsidian_get_flashcard_content to extract key concepts from these notes
2. For each concept, create an atomic flashcard (one fact per card):
   - Definitions/terms/formulas -> cloze deletions
   - Concepts/explanations -> front-back Q&A
   - Math formulas -> cloze blanking ONE variable at a time
3. Keep fronts under 20 words with a topic prefix. Keep backs under 15 words.
4. If any cards contain math, verify expressions using math_verify_equivalence
5. Show me the cards for review before uploading
6. After I approve, upload to Anki using flashcard_upload_cards"""


@mcp.prompt
def study_from_paper(item_key: str, deck_name: str = "Paper Notes") -> str:
    """Generate flashcards from a Zotero paper and upload to Anki."""
    return f"""Help me study a paper from my Zotero library.

Zotero item key: {item_key}
Target Anki deck: {deck_name}

Steps:
1. Use zotero_get_item to retrieve the paper details (title, abstract, etc.)
2. Use zotero_get_item_notes to get any annotations or notes
3. Extract key concepts, definitions, theorems, and results
4. Create atomic flashcards:
   - One fact per card, topic prefix on each front
   - Fronts: 5-20 words. Backs: 1-15 words.
   - Use cloze for formulas (blank one variable at a time)
   - Use front-back for conceptual understanding
5. Show me the cards for review
6. After approval, upload using flashcard_upload_cards"""


@mcp.prompt
def review_deck(deck_name: str) -> str:
    """Review an Anki deck for card quality issues."""
    return f"""Review the flashcard quality in my Anki deck '{deck_name}'.

Steps:
1. Use flashcard_search_notes with query 'deck:{deck_name}' to get all cards
2. Analyze each card against these quality criteria:
   - Is it atomic? (tests exactly one fact)
   - Is the front under 30 words? Is the back under 30 words?
   - Does it avoid lists, yes/no answers, and vague questions?
   - Does it have a topic prefix on the front?
   - Is the answer precise and unambiguous?
3. Report: total cards, cards needing improvement, specific suggestions
4. For cards that need fixes, offer to update them using flashcard_update_note"""


def main():
    """Run the FastMCP Flashcard server"""
    try:
        print("Starting Flashcard MCP server...", file=sys.stderr)
        mcp.run()
    except Exception as e:
        print(f"Failed to start Flashcard MCP server: {e}", file=sys.stderr)
        print(f"Error type: {type(e).__name__}", file=sys.stderr)
        import traceback

        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
