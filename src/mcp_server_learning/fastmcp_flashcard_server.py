#!/usr/bin/env python3
"""
FastMCP-powered Flashcard Server

A modern, streamlined implementation of the flashcard MCP server using FastMCP's
Pythonic patterns for reduced boilerplate and improved maintainability.
"""

import json
import sys
import re
import requests
import base64
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from fastmcp import FastMCP


# Initialize FastMCP instance
mcp = FastMCP("Flashcard MCP Server")


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
                raise Exception(f"Anki Connect API error: {result['error']}")
            
            return result.get("result")
        
        except requests.exceptions.ConnectionError:
            raise Exception("Cannot connect to Anki. Is Anki running with AnkiConnect addon?")
        except requests.exceptions.Timeout:
            raise Exception("Request to Anki timed out")
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

    def add_note(self, deck_name: str, model_name: str, fields: Dict[str, str], tags: List[str] = None) -> Optional[int]:
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
            formatted_notes.append({
                "deckName": note["deck_name"],
                "modelName": note["model_name"],
                "fields": note["fields"],
                "tags": note.get("tags", []),
            })
        return self._make_request("addNotes", {"notes": formatted_notes})

    def find_notes(self, query: str) -> List[int]:
        """Find notes matching the given query."""
        return self._make_request("findNotes", {"query": query})

    def notes_info(self, note_ids: List[int]) -> List[Dict[str, Any]]:
        """Get detailed information about specific notes."""
        return self._make_request("notesInfo", {"notes": note_ids})

    def update_note(self, note_id: int, fields: Dict[str, str], tags: List[str] = None) -> None:
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


class FlashcardGenerator:
    """Generates flashcards from text."""

    @staticmethod
    def convert_latex_to_display_format(text: str) -> str:
        """Convert LaTeX equations to display format for better rendering in Anki."""
        if not text:
            return text
        
        # Define patterns to convert to display format
        # Apply in order of precedence (longest patterns first)
        
        result = text
        
        # $$equation$$ -> \[equation\] (do this first to avoid conflicts with single $)
        result = re.sub(r'\$\$([^$]+?)\$\$', r'\\[\1\\]', result)
        
        # $equation$ -> \[equation\]
        result = re.sub(r'\$([^$\n]+?)\$', r'\\[\1\\]', result)
        
        # \(equation\) -> \[equation\]
        def replace_parens(match):
            content = match.group(0)[2:-2]  # Remove \( and \)
            return f'\\[{content}\\]'
        
        result = re.sub(r'\\?\\\([^)]+?\\\)', replace_parens, result)
        
        return result

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
            old_pattern = f"{re.escape(cloze_markers[0])}{re.escape(match)}{re.escape(cloze_markers[1])}"
            card_text = re.sub(old_pattern, replacement, card_text, count=1)

        return card_text

    @staticmethod
    def parse_text_to_cards(text: str, card_type: str = "front-back") -> List[Dict[str, str]]:
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
                qa_match = re.search(r"Q:\s*(.*?)\s*A:\s*(.*)", section, re.DOTALL | re.IGNORECASE)
                if qa_match:
                    front = qa_match.group(1).strip()
                    back = qa_match.group(2).strip()
                    
                    # Convert LaTeX to display format
                    front = FlashcardGenerator.convert_latex_to_display_format(front)
                    back = FlashcardGenerator.convert_latex_to_display_format(back)
                    
                    cards.append({
                        "front": front,
                        "back": back
                    })
                    continue

                # Look for question/answer separated by newline
                lines = section.split("\n")
                if len(lines) >= 2:
                    front = lines[0].strip()
                    back = "\n".join(lines[1:]).strip()
                    
                    # Convert LaTeX to display format
                    front = FlashcardGenerator.convert_latex_to_display_format(front)
                    back = FlashcardGenerator.convert_latex_to_display_format(back)
                    
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
                    # Convert LaTeX to display format
                    cloze_text = FlashcardGenerator.convert_latex_to_display_format(cloze_text)
                    cards.append({"text": cloze_text})
                except ValueError:
                    # If no cloze markers found, skip this section
                    continue

        return cards


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
            r"\{\{c\d+::(.*?)\}\}", r'<span class="cloze-blank">\1</span>', text
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
                # Handle both LaTeX format and simple dict format
                if isinstance(card_data.get("data"), dict):
                    # Handle dict format from parse_text_to_cards
                    front = card_data["data"].get("front", "No content")
                    back = card_data["data"].get("back", "")
                else:
                    # Handle string content format
                    content = card_data.get("content", card_data.get("data", ""))
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
                # Handle both LaTeX format and simple dict format
                if isinstance(card_data.get("data"), dict):
                    # Handle dict format from parse_text_to_cards
                    content = card_data["data"].get("text", "")
                else:
                    # Handle string content format
                    content = card_data.get("content", card_data.get("data", ""))
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
                content = card_data.get("content", card_data.get("data", ""))
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

    def convert_to_anki_fields(self, card_data: Dict[str, str], card_type: str, model_name: str = None) -> Dict[str, str]:
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
                field_names[1]: card_data.get("back", "") if len(field_names) > 1 else ""
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

    def upload_cards_to_anki(self, cards_data: List[Dict[str, Any]], deck_name: str) -> Dict[str, Any]:
        """Upload multiple cards to Anki."""
        try:
            # Check connection and create deck if needed
            self.anki.check_permission()
            self.anki.create_deck(deck_name)

            # Convert cards to Anki format
            anki_notes = []
            for card_data in cards_data:
                card_type = card_data.get("card_type", "front-back")
                model_name = card_data.get("model_name", self.get_default_model_for_card_type(card_type))

                fields = self.convert_to_anki_fields(card_data["data"], card_type, model_name)

                anki_notes.append({
                    "deck_name": deck_name,
                    "model_name": model_name,
                    "fields": fields,
                    "tags": card_data.get("tags", ["mcp-generated"]),
                })

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
def create_flashcards(content: str, card_type: str = "front-back") -> str:
    """Convert text into flashcards
    
    Args:
        content: Text content to convert to flashcards
        card_type: Type of flashcard - "front-back" or "cloze"
    """
    try:
        cards = FlashcardGenerator.parse_text_to_cards(content, card_type)
        
        if not cards:
            return "No flashcards could be generated from the provided content. Please check the format."
        
        result = f"Generated {len(cards)} flashcard(s):\n\n"
        for i, card in enumerate(cards, 1):
            result += f"**Card {i}:**\n"
            if card_type == "front-back":
                result += f"Front: {card['front']}\n"
                result += f"Back: {card['back']}\n"
            elif card_type == "cloze":
                result += f"Text: {card['text']}\n"
            result += "\n"
        
        return result
    
    except Exception as e:
        return f"Error generating flashcards: {str(e)}"


@mcp.tool
def upload_to_anki(content: str, deck_name: str = "MCP Generated Cards", card_type: str = "front-back", tags: List[str] = None, anki_api_key: Optional[str] = None) -> str:
    """Upload generated flashcards directly to Anki
    
    Args:
        content: Text content to convert and upload to Anki
        deck_name: Name of the Anki deck to upload to
        card_type: Type of flashcard - "front-back" or "cloze"  
        tags: Tags to add to the cards
        anki_api_key: Optional AnkiConnect API key
    """
    if tags is None:
        tags = ["mcp-generated"]
    
    try:
        # Generate flashcards from content
        cards = FlashcardGenerator.parse_text_to_cards(content, card_type)
        
        if not cards:
            return "No flashcards could be generated from the provided content"
        
        # Initialize Anki connection
        anki_connector = get_anki_connector(anki_api_key)
        card_manager = AnkiCardManager(anki_connector)
        
        # Prepare cards data for upload
        cards_data = []
        for card in cards:
            cards_data.append({
                "data": card,
                "card_type": card_type,
                "tags": tags,
            })
        
        # Upload to Anki
        result = card_manager.upload_cards_to_anki(cards_data, deck_name)
        
        if result["success"]:
            response = f"Successfully uploaded {result['successful_uploads']} cards to Anki deck '{result['deck_name']}'"
            if result["failed_uploads"] > 0:
                response += f" ({result['failed_uploads']} failed)"
            return response
        else:
            return f"Failed to upload cards to Anki: {result['error']}"
    
    except Exception as e:
        return f"Error uploading to Anki: {str(e)}"


@mcp.tool
def check_anki_connection(anki_api_key: Optional[str] = None) -> str:
    """Check connection to Anki and get available decks/models
    
    Args:
        anki_api_key: Optional AnkiConnect API key
    """
    try:
        anki_connector = get_anki_connector(anki_api_key)
        
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
        return response
    
    except Exception as e:
        return f"Failed to connect to Anki: {str(e)}\n\nMake sure Anki is running and AnkiConnect addon is installed."


@mcp.tool
def preview_cards(content: str, card_type: str = "front-back", title: str = "Flashcard Preview", tags: List[str] = None) -> str:
    """Generate HTML preview of flashcards with MathJax LaTeX rendering
    
    Args:
        content: Text content to convert to flashcards and preview
        card_type: Type of flashcard - "front-back" or "cloze"
        title: Title for the preview document
        tags: Tags to display on the cards
    """
    if tags is None:
        tags = []
        
    try:
        # Generate flashcards from content
        cards = FlashcardGenerator.parse_text_to_cards(content, card_type)
        
        if not cards:
            return "No flashcards could be generated from the provided content"
        
        # Prepare cards data for advanced rendering
        cards_data = []
        for card in cards:
            cards_data.append({
                "data": card,
                "card_type": card_type,
                "tags": tags,
            })
        
        # Generate professional HTML preview with MathJax
        html_preview = HTMLCardRenderer.render_cards_preview(cards_data, title)
        return html_preview
    
    except Exception as e:
        return f"Error generating preview: {str(e)}"


@mcp.tool
def search_anki_notes(query: str, limit: int = 20, anki_api_key: Optional[str] = None) -> str:
    """Search for notes in Anki collection
    
    Args:
        query: Search query (e.g., 'deck:Math', 'tag:chemistry', 'Python programming')
        limit: Maximum number of notes to return
        anki_api_key: Optional AnkiConnect API key
    """
    try:
        anki_connector = get_anki_connector(anki_api_key)
        note_ids = anki_connector.find_notes(query)
        
        if not note_ids:
            return f"No notes found for query: {query}"
        
        # Limit results
        limited_note_ids = note_ids[:limit]
        
        # Get note information
        notes_info = anki_connector.notes_info(limited_note_ids)
        
        response = f"Found {len(note_ids)} notes (showing first {len(limited_note_ids)}):\n\n"
        
        for i, note_info in enumerate(notes_info, 1):
            response += f"{i}. **Note ID:** {note_info['noteId']}\n"
            response += f"   **Model:** {note_info['modelName']}\n"
            response += f"   **Tags:** {', '.join(note_info.get('tags', []))}\n"
            
            # Show first few fields
            fields = note_info.get("fields", {})
            for field_name, field_value in list(fields.items())[:2]:
                preview = field_value["value"][:100] + "..." if len(field_value["value"]) > 100 else field_value["value"]
                response += f"   **{field_name}:** {preview}\n"
            response += "\n"
        
        return response
    
    except Exception as e:
        return f"Error searching Anki notes: {str(e)}"


@mcp.tool
def update_anki_note(note_id: int, fields: Dict[str, str], tags: Optional[List[str]] = None, anki_api_key: Optional[str] = None) -> str:
    """Update an existing Anki note
    
    Args:
        note_id: ID of the note to update
        fields: Fields to update (field_name: new_value)
        tags: New tags for the note (optional)
        anki_api_key: Optional AnkiConnect API key
    """
    try:
        anki_connector = get_anki_connector(anki_api_key)
        anki_connector.update_note(note_id, fields, tags)
        
        response = f"Successfully updated note {note_id}"
        if tags:
            response += f" with tags: {', '.join(tags)}"
        
        return response
    
    except Exception as e:
        return f"Error updating note: {str(e)}"


@mcp.tool
def delete_anki_notes(note_ids: List[int], anki_api_key: Optional[str] = None) -> str:
    """Delete notes from Anki collection
    
    Args:
        note_ids: List of note IDs to delete
        anki_api_key: Optional AnkiConnect API key
    """
    try:
        anki_connector = get_anki_connector(anki_api_key)
        anki_connector.delete_notes(note_ids)
        
        return f"Successfully deleted {len(note_ids)} notes"
    
    except Exception as e:
        return f"Error deleting notes: {str(e)}"


@mcp.tool
def sync_anki(anki_api_key: Optional[str] = None) -> str:
    """Synchronize Anki collection with AnkiWeb
    
    Args:
        anki_api_key: Optional AnkiConnect API key
    """
    try:
        anki_connector = get_anki_connector(anki_api_key)
        anki_connector.sync()
        
        return "Successfully synchronized Anki collection with AnkiWeb"
    
    except Exception as e:
        return f"Error syncing Anki: {str(e)}"


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