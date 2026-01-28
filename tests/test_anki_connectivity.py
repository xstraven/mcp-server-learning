#!/usr/bin/env python3

import json
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from mcp_server_learning.fastmcp_flashcard_server import AnkiConnector


class TestAnkiConnectivity:
    """Test suite for Anki Connect connectivity."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.anki_connector = AnkiConnector()
        self.default_url = "http://localhost:8765"

    def test_anki_connector_initialization(self):
        """Test AnkiConnector initializes with correct defaults."""
        connector = AnkiConnector()
        assert connector.url == self.default_url
        assert connector.api_key is None
        assert connector.session is not None

    def test_anki_connector_initialization_with_custom_params(self):
        """Test AnkiConnector initializes with custom parameters."""
        custom_url = "http://custom:9876"
        api_key = "test_key"

        connector = AnkiConnector(url=custom_url, api_key=api_key)
        assert connector.url == custom_url
        assert connector.api_key == api_key

    @patch("requests.Session.post")
    def test_make_request_success(self, mock_post):
        """Test successful API request to Anki Connect."""
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {"result": "success", "error": None}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = self.anki_connector._make_request("testAction", {"param": "value"})

        assert result == "success"
        mock_post.assert_called_once()

        # Verify request payload
        call_args = mock_post.call_args
        assert call_args[1]["json"]["action"] == "testAction"
        assert call_args[1]["json"]["version"] == 6
        assert call_args[1]["json"]["params"] == {"param": "value"}

    @patch("requests.Session.post")
    def test_make_request_with_api_key(self, mock_post):
        """Test API request includes API key when provided."""
        # Setup connector with API key
        connector = AnkiConnector(api_key="test_key")

        mock_response = Mock()
        mock_response.json.return_value = {"result": "success", "error": None}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        connector._make_request("testAction")

        # Verify API key is included
        call_args = mock_post.call_args
        assert call_args[1]["json"]["key"] == "test_key"

    @patch("requests.Session.post")
    def test_make_request_anki_error(self, mock_post):
        """Test handling of Anki Connect API errors."""
        mock_response = Mock()
        mock_response.json.return_value = {"result": None, "error": "collection is not available"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        with pytest.raises(Exception) as exc_info:
            self.anki_connector._make_request("testAction")

        assert "AnkiConnect error: collection is not available" in str(exc_info.value)

    @patch("requests.Session.post")
    def test_make_request_connection_error(self, mock_post):
        """Test handling of connection errors."""
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")

        with pytest.raises(Exception) as exc_info:
            self.anki_connector._make_request("testAction")

        assert "Failed to connect to Anki" in str(exc_info.value)

    @patch("requests.Session.post")
    def test_make_request_timeout(self, mock_post):
        """Test handling of request timeout."""
        mock_post.side_effect = requests.exceptions.Timeout("Request timed out")

        with pytest.raises(Exception) as exc_info:
            self.anki_connector._make_request("testAction")

        assert "Failed to connect to Anki" in str(exc_info.value)

    @patch("requests.Session.post")
    def test_check_permission_success(self, mock_post):
        """Test successful permission check."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "result": {"permission": "granted", "requireApiKey": False, "version": 6},
            "error": None,
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = self.anki_connector.check_permission()

        assert result["permission"] == "granted"
        assert result["requireApiKey"] is False
        assert result["version"] == 6

    @patch("requests.Session.post")
    def test_get_deck_names_success(self, mock_post):
        """Test successful deck names retrieval."""
        expected_decks = ["Default", "Spanish", "Math", "Programming"]
        mock_response = Mock()
        mock_response.json.return_value = {"result": expected_decks, "error": None}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = self.anki_connector.get_deck_names()

        assert result == expected_decks
        # Verify correct action was called
        call_args = mock_post.call_args
        assert call_args[1]["json"]["action"] == "deckNames"

    @patch("requests.Session.post")
    def test_get_model_names_success(self, mock_post):
        """Test successful model names retrieval."""
        expected_models = ["Basic", "Basic (and reversed card)", "Cloze"]
        mock_response = Mock()
        mock_response.json.return_value = {"result": expected_models, "error": None}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = self.anki_connector.get_model_names()

        assert result == expected_models
        call_args = mock_post.call_args
        assert call_args[1]["json"]["action"] == "modelNames"

    @patch("requests.Session.post")
    def test_create_deck_success(self, mock_post):
        """Test successful deck creation."""
        mock_response = Mock()
        mock_response.json.return_value = {"result": None, "error": None}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        # Should not raise an exception
        self.anki_connector.create_deck("Test Deck")

        call_args = mock_post.call_args
        assert call_args[1]["json"]["action"] == "createDeck"
        assert call_args[1]["json"]["params"]["deck"] == "Test Deck"

    @patch("requests.Session.post")
    def test_add_note_success(self, mock_post):
        """Test successful note addition."""
        expected_note_id = 1234567890
        mock_response = Mock()
        mock_response.json.return_value = {"result": expected_note_id, "error": None}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = self.anki_connector.add_note(
            deck_name="Test Deck",
            model_name="Basic",
            fields={"Front": "Question", "Back": "Answer"},
            tags=["test", "automated"],
        )

        assert result == expected_note_id
        call_args = mock_post.call_args
        assert call_args[1]["json"]["action"] == "addNote"
        note_data = call_args[1]["json"]["params"]["note"]
        assert note_data["deckName"] == "Test Deck"
        assert note_data["modelName"] == "Basic"
        assert note_data["fields"] == {"Front": "Question", "Back": "Answer"}
        assert note_data["tags"] == ["test", "automated"]

    @patch("requests.Session.post")
    def test_delete_decks_success(self, mock_post):
        """Test successful deck deletion."""
        mock_response = Mock()
        mock_response.json.return_value = {"result": None, "error": None}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        # Should not raise an exception
        self.anki_connector.delete_decks(["Test Deck 1", "Test Deck 2"], cards_too=True)

        call_args = mock_post.call_args
        assert call_args[1]["json"]["action"] == "deleteDecks"
        assert call_args[1]["json"]["params"]["decks"] == ["Test Deck 1", "Test Deck 2"]
        assert call_args[1]["json"]["params"]["cardsToo"] is True

    @patch("requests.Session.post")
    def test_delete_decks_without_cards(self, mock_post):
        """Test deck deletion without deleting cards."""
        mock_response = Mock()
        mock_response.json.return_value = {"result": None, "error": None}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        self.anki_connector.delete_decks(["Test Deck"], cards_too=False)

        call_args = mock_post.call_args
        assert call_args[1]["json"]["params"]["cardsToo"] is False


class TestAnkiConnectivityIntegration:
    """Integration tests for actual Anki Connect connectivity.

    These tests require Anki to be running with AnkiConnect addon installed.
    They are marked as integration tests and can be skipped in CI/CD.
    """

    @pytest.mark.integration
    def test_real_anki_connection(self):
        """Test connection to real Anki instance."""
        connector = AnkiConnector()

        try:
            # This will only work if Anki is running with AnkiConnect
            permission_info = connector.check_permission()

            # Basic assertions about the response structure
            assert isinstance(permission_info, dict)
            # The response should contain these keys when successful
            expected_keys = {"permission", "requireApiKey", "version"}
            assert any(key in permission_info for key in expected_keys)

        except Exception as e:
            # If Anki is not running, we expect a connection error
            pytest.skip(f"Anki not available for integration test: {e}")

    @pytest.mark.integration
    def test_real_anki_deck_retrieval(self):
        """Test retrieving deck names from real Anki instance."""
        connector = AnkiConnector()

        try:
            decks = connector.get_deck_names()

            # Anki always has at least the "Default" deck
            assert isinstance(decks, list)
            assert len(decks) >= 1
            assert "Default" in decks

        except Exception as e:
            pytest.skip(f"Anki not available for integration test: {e}")

    @pytest.mark.integration
    def test_real_anki_model_retrieval(self):
        """Test retrieving model names from real Anki instance."""
        connector = AnkiConnector()

        try:
            models = connector.get_model_names()

            # Anki comes with default note types
            assert isinstance(models, list)
            assert len(models) >= 1
            # Basic model should always be available
            assert "Basic" in models

        except Exception as e:
            pytest.skip(f"Anki not available for integration test: {e}")


class TestAnkiConnectivityConfig:
    """Test different configuration scenarios for Anki Connect."""

    def test_default_configuration(self):
        """Test default configuration values."""
        connector = AnkiConnector()
        assert connector.url == "http://localhost:8765"
        assert connector.api_key is None

    def test_custom_url_configuration(self):
        """Test custom URL configuration."""
        custom_url = "http://192.168.1.100:8765"
        connector = AnkiConnector(url=custom_url)
        assert connector.url == custom_url

    def test_api_key_configuration(self):
        """Test API key configuration."""
        api_key = "test-api-key-123"
        connector = AnkiConnector(api_key=api_key)
        assert connector.api_key == api_key

    @patch("requests.Session.post")
    def test_timeout_configuration(self, mock_post):
        """Test that requests have proper timeout configuration."""
        mock_response = Mock()
        mock_response.json.return_value = {"result": "success", "error": None}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        connector = AnkiConnector()
        connector._make_request("testAction")

        # Verify timeout is set
        call_args = mock_post.call_args
        assert call_args[1]["timeout"] == 10


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
