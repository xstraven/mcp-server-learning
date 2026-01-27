"""
Tests for the FastMCP Flashcard Server

Tests cover:
- Flashcard generation
- LaTeX conversion
- Anki connectivity
- Tool functions
"""

from unittest.mock import MagicMock, patch

import pytest

from mcp_server_learning import fastmcp_flashcard_server as flashcard_server
from mcp_server_learning.fastmcp_flashcard_server import (
    AnkiCardManager,
    AnkiConnector,
    FlashcardGenerator,
)


class TestFlashcardGenerator:
    """Test FlashcardGenerator functionality."""

    def test_preserve_claude_latex(self):
        """Test that LaTeX is preserved for Claude Desktop."""
        text = r"The formula is $E = mc^2$"
        result = FlashcardGenerator.preserve_claude_latex(text)
        assert "$E = mc^2$" in result

    def test_preserve_claude_latex_escaped(self):
        """Test that escaped dollar signs are unescaped."""
        text = r"Cost is \$100"
        result = FlashcardGenerator.preserve_claude_latex(text)
        assert "$100" in result

    def test_convert_to_anki_mathjax_inline(self):
        """Test inline math conversion to MathJax."""
        text = r"Inline $x^2$ math"
        result = FlashcardGenerator.convert_to_anki_mathjax(text)
        assert r"\(x^2\)" in result

    def test_convert_to_anki_mathjax_display(self):
        """Test display math conversion to MathJax."""
        text = r"Display $$x^2$$ math"
        result = FlashcardGenerator.convert_to_anki_mathjax(text)
        assert r"\[x^2\]" in result

    def test_convert_latex_to_display_format(self):
        """Test LaTeX delimiter conversion to display format."""
        text = r"Inline $x$ and display $$y$$"
        result = FlashcardGenerator.convert_latex_to_display_format(text)
        assert r"\[x\]" in result
        assert r"\[y\]" in result

    def test_parse_text_to_cards_qa_format(self):
        """Test parsing Q: A: format cards."""
        text = "Q: What is 2+2?\nA: 4"
        cards = FlashcardGenerator.parse_text_to_cards(text, "front-back")

        assert len(cards) == 1
        assert cards[0]["front"] == "What is 2+2?"
        assert cards[0]["back"] == "4"

    def test_parse_text_to_cards_multiple(self):
        """Test parsing multiple Q: A: cards."""
        text = "Q: Question 1?\nA: Answer 1\nQ: Question 2?\nA: Answer 2"
        cards = FlashcardGenerator.parse_text_to_cards(text, "front-back")

        assert len(cards) == 2

    def test_parse_text_to_cards_cloze(self):
        """Test parsing cloze deletion cards."""
        text = "The capital of {{France}} is {{Paris}}."
        cards = FlashcardGenerator.parse_text_to_cards(text, "cloze")

        assert len(cards) == 1
        assert "{{c1::France}}" in cards[0]["text"]
        assert "{{c2::Paris}}" in cards[0]["text"]

    def test_create_anki_cloze_card(self):
        """Test cloze card creation."""
        text = "The answer is {{42}}."
        result = FlashcardGenerator.create_anki_cloze_card(text)

        assert "{{c1::42}}" in result

    def test_create_anki_cloze_card_no_markers(self):
        """Test cloze card with no markers raises error."""
        with pytest.raises(ValueError, match="No cloze deletions"):
            FlashcardGenerator.create_anki_cloze_card("No markers here")


class TestAnkiConnectorMocked:
    """Test AnkiConnector with mocked requests."""

    @pytest.fixture
    def mock_connector(self):
        """Create a connector with mocked session."""
        connector = AnkiConnector()
        connector.session = MagicMock()
        return connector

    def test_make_request_success(self, mock_connector):
        """Test successful request."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": ["Deck1"], "error": None}
        mock_connector.session.post.return_value = mock_response

        result = mock_connector._make_request("deckNames")
        assert result == ["Deck1"]

    def test_make_request_error(self, mock_connector):
        """Test request with API error."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": None, "error": "Test error"}
        mock_connector.session.post.return_value = mock_response

        with pytest.raises(Exception, match="AnkiConnect error"):
            mock_connector._make_request("deckNames")

    def test_get_deck_names(self, mock_connector):
        """Test get_deck_names method."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": ["Default", "Test"], "error": None}
        mock_connector.session.post.return_value = mock_response

        result = mock_connector.get_deck_names()
        assert "Default" in result

    def test_get_model_names(self, mock_connector):
        """Test get_model_names method."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": ["Basic", "Cloze"], "error": None}
        mock_connector.session.post.return_value = mock_response

        result = mock_connector.get_model_names()
        assert "Basic" in result


class TestFlashcardMCPTools:
    """Test the MCP tool functions for flashcards."""

    def test_create_flashcards_tool(self):
        """Test create_flashcards tool function."""
        content = "Q: What is Python?\nA: A programming language"
        result = flashcard_server.create_flashcards.fn(content)

        assert result["success"] is True
        assert len(result["data"]["cards"]) == 1
        assert "Generated" in result["message"]

    def test_create_flashcards_empty(self):
        """Test create_flashcards with no valid content."""
        result = flashcard_server.create_flashcards.fn("")

        assert result["success"] is False
        assert "No flashcards" in result["message"]

    def test_create_flashcards_cloze(self):
        """Test create_flashcards with cloze type."""
        content = "The answer is {{42}}."
        result = flashcard_server.create_flashcards.fn(content, card_type="cloze")

        assert result["success"] is True
        assert len(result["data"]["cards"]) == 1
        assert result["data"]["card_type"] == "cloze"

    def test_preview_cards_tool(self):
        """Test preview_cards tool function."""
        content = "Q: Question?\nA: Answer"
        result = flashcard_server.preview_cards.fn(content)

        assert result["success"] is True
        assert len(result["data"]["cards"]) == 1
        assert result["data"]["cards"][0]["front"] == "Question?"

    def test_preview_cards_empty(self):
        """Test preview_cards with empty content."""
        result = flashcard_server.preview_cards.fn("")

        assert result["success"] is False
        assert "No flashcards" in result["message"]

    @patch.object(AnkiConnector, "_make_request")
    def test_check_anki_connection_tool(self, mock_request):
        """Test check_anki_connection tool function."""
        mock_request.side_effect = [
            {"permission": "granted", "requireApiKey": False, "version": 6},
            ["Default", "Test"],
            ["Basic", "Cloze"],
        ]

        result = flashcard_server.check_anki_connection.fn()

        assert result["success"] is True
        assert "Default" in result["data"]["decks"]
        assert "Connected" in result["message"]

    @patch.object(AnkiConnector, "_make_request")
    def test_check_anki_connection_failed(self, mock_request):
        """Test check_anki_connection when Anki not available."""
        mock_request.side_effect = Exception("connection refused")

        result = flashcard_server.check_anki_connection.fn()

        assert result["success"] is False
        assert "Failed" in result["message"]


class TestAnkiCardManager:
    """Test AnkiCardManager functionality."""

    @pytest.fixture
    def mock_manager(self):
        """Create a card manager with mocked connector."""
        connector = MagicMock()
        connector.get_model_names.return_value = ["Basic", "Cloze"]
        connector.get_model_field_names.return_value = ["Front", "Back"]
        connector.check_permission.return_value = {"permission": "granted"}
        connector.create_deck.return_value = None
        connector.add_notes.return_value = [12345]
        return AnkiCardManager(connector)

    def test_get_default_model(self, mock_manager):
        """Test getting default model for card type."""
        assert mock_manager.get_default_model_for_card_type("front-back") == "Basic"
        assert mock_manager.get_default_model_for_card_type("cloze") == "Cloze"

    def test_validate_model_exists(self, mock_manager):
        """Test model validation."""
        assert mock_manager.validate_model_exists("Basic") is True

    def test_convert_to_anki_fields_front_back(self, mock_manager):
        """Test converting front-back card to Anki fields."""
        card_data = {"front": "Question", "back": "Answer"}
        fields = mock_manager.convert_to_anki_fields(card_data, "front-back", "Basic")

        assert fields["Front"] == "Question"
        assert fields["Back"] == "Answer"

    def test_upload_cards_success(self, mock_manager):
        """Test successful card upload."""
        cards_data = [
            {
                "data": {"front": "Q", "back": "A"},
                "card_type": "front-back",
                "tags": ["test"],
            }
        ]

        result = mock_manager.upload_cards_to_anki(cards_data, "Test Deck")

        assert result["success"] is True
        assert result["successful_uploads"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
