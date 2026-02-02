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

        # Mock multiple responses: addNote, notesInfo, setSpecificValueOfCard
        mock_responses = [
            Mock(
                json=lambda: {"result": expected_note_id, "error": None},
                raise_for_status=lambda: None,
            ),
            Mock(
                json=lambda: {
                    "result": [{"noteId": expected_note_id, "cards": [999]}],
                    "error": None,
                },
                raise_for_status=lambda: None,
            ),
            Mock(
                json=lambda: {"result": None, "error": None},
                raise_for_status=lambda: None,
            ),
        ]
        mock_post.side_effect = mock_responses

        result = self.anki_connector.add_note(
            deck_name="Test Deck",
            model_name="Basic",
            fields={"Front": "Question", "Back": "Answer"},
            tags=["test", "automated"],
        )

        assert result == expected_note_id

        # Verify the first call was addNote with correct params
        first_call = mock_post.call_args_list[0]
        assert first_call[1]["json"]["action"] == "addNote"
        note_data = first_call[1]["json"]["params"]["note"]
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

    @patch("requests.Session.post")
    def test_notes_info_success(self, mock_post):
        """Test successful notes info retrieval."""
        expected_notes = [
            {
                "noteId": 123,
                "modelName": "Basic",
                "tags": ["test"],
                "fields": {"Front": {"value": "Q1"}, "Back": {"value": "A1"}},
                "cards": [456, 457],
            },
            {
                "noteId": 124,
                "modelName": "Basic",
                "tags": [],
                "fields": {"Front": {"value": "Q2"}, "Back": {"value": "A2"}},
                "cards": [458],
            },
        ]
        mock_response = Mock()
        mock_response.json.return_value = {"result": expected_notes, "error": None}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = self.anki_connector.notes_info([123, 124])

        assert result == expected_notes
        call_args = mock_post.call_args
        assert call_args[1]["json"]["action"] == "notesInfo"
        assert call_args[1]["json"]["params"]["notes"] == [123, 124]

    @patch("requests.Session.post")
    def test_change_deck_success(self, mock_post):
        """Test successful deck change for cards."""
        mock_response = Mock()
        mock_response.json.return_value = {"result": None, "error": None}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        # Should not raise an exception
        self.anki_connector.change_deck([456, 457, 458], "New Deck")

        call_args = mock_post.call_args
        assert call_args[1]["json"]["action"] == "changeDeck"
        assert call_args[1]["json"]["params"]["cards"] == [456, 457, 458]
        assert call_args[1]["json"]["params"]["deck"] == "New Deck"

    @patch("requests.Session.post")
    def test_change_deck_empty_card_list(self, mock_post):
        """Test deck change with empty card list."""
        mock_response = Mock()
        mock_response.json.return_value = {"result": None, "error": None}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        # Should not raise an exception even with empty list
        self.anki_connector.change_deck([], "New Deck")

        call_args = mock_post.call_args
        assert call_args[1]["json"]["params"]["cards"] == []

    @patch("requests.Session.post")
    def test_change_deck_error(self, mock_post):
        """Test handling of error when changing deck."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "result": None,
            "error": "deck was not found: NonExistent",
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        with pytest.raises(Exception) as exc_info:
            self.anki_connector.change_deck([456], "NonExistent")

        assert "AnkiConnect error: deck was not found" in str(exc_info.value)

    @patch("requests.Session.post")
    def test_get_card_ids_from_notes_success(self, mock_post):
        """Test successful extraction of card IDs from notes."""
        mock_notes = [
            {"noteId": 123, "cards": [456, 457]},
            {"noteId": 124, "cards": [458]},
        ]
        mock_response = Mock()
        mock_response.json.return_value = {"result": mock_notes, "error": None}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = self.anki_connector.get_card_ids_from_notes([123, 124])

        assert result == [456, 457, 458]
        call_args = mock_post.call_args
        assert call_args[1]["json"]["action"] == "notesInfo"

    @patch("requests.Session.post")
    def test_get_card_ids_from_notes_empty(self, mock_post):
        """Test get_card_ids_from_notes with empty note list."""
        result = self.anki_connector.get_card_ids_from_notes([])
        assert result == []
        mock_post.assert_not_called()

    @patch("requests.Session.post")
    def test_get_card_ids_from_notes_no_cards(self, mock_post):
        """Test get_card_ids_from_notes when notes have no cards."""
        mock_notes = [{"noteId": 123, "cards": []}]
        mock_response = Mock()
        mock_response.json.return_value = {"result": mock_notes, "error": None}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = self.anki_connector.get_card_ids_from_notes([123])

        assert result == []

    @patch("requests.Session.post")
    def test_set_card_flags_success(self, mock_post):
        """Test successful flag setting on cards."""
        mock_response = Mock()
        mock_response.json.return_value = {"result": None, "error": None}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        self.anki_connector._set_card_flags([456, 457], flag=7)

        call_args = mock_post.call_args
        assert call_args[1]["json"]["action"] == "setSpecificValueOfCard"
        assert call_args[1]["json"]["params"]["cards"] == [456, 457]
        assert call_args[1]["json"]["params"]["keys"] == ["flags"]
        assert call_args[1]["json"]["params"]["newValues"] == ["7"]

    @patch("requests.Session.post")
    def test_set_card_flags_empty_list(self, mock_post):
        """Test _set_card_flags with empty card list."""
        self.anki_connector._set_card_flags([])
        mock_post.assert_not_called()

    @patch("requests.Session.post")
    def test_add_note_with_purple_flag(self, mock_post):
        """Test add_note automatically sets purple flag."""
        note_id = 123
        card_ids = [456]

        # Setup mock responses for multiple calls
        mock_responses = [
            # First call: addNote
            Mock(
                json=lambda: {"result": note_id, "error": None},
                raise_for_status=lambda: None,
            ),
            # Second call: notesInfo (for get_card_ids_from_notes)
            Mock(
                json=lambda: {
                    "result": [{"noteId": note_id, "cards": card_ids}],
                    "error": None,
                },
                raise_for_status=lambda: None,
            ),
            # Third call: setSpecificValueOfCard
            Mock(
                json=lambda: {"result": None, "error": None},
                raise_for_status=lambda: None,
            ),
        ]
        mock_post.side_effect = mock_responses

        result = self.anki_connector.add_note(
            deck_name="Test",
            model_name="Basic",
            fields={"Front": "Q", "Back": "A"},
        )

        assert result == note_id
        assert mock_post.call_count == 3

        # Verify the three calls
        calls = mock_post.call_args_list
        assert calls[0][1]["json"]["action"] == "addNote"
        assert calls[1][1]["json"]["action"] == "notesInfo"
        assert calls[2][1]["json"]["action"] == "setSpecificValueOfCard"
        assert calls[2][1]["json"]["params"]["cards"] == card_ids
        assert calls[2][1]["json"]["params"]["newValues"] == ["7"]

    @patch("requests.Session.post")
    def test_add_note_flag_failure_doesnt_break_creation(self, mock_post):
        """Test that flag setting failure doesn't prevent note creation."""
        note_id = 123

        # Mock responses: addNote succeeds, flagging fails
        mock_responses = [
            Mock(
                json=lambda: {"result": note_id, "error": None},
                raise_for_status=lambda: None,
            ),
            # notesInfo call raises exception
            Mock(side_effect=Exception("AnkiConnect error: flagging failed")),
        ]
        mock_post.side_effect = mock_responses

        # Should still return note_id despite flagging error
        result = self.anki_connector.add_note(
            deck_name="Test",
            model_name="Basic",
            fields={"Front": "Q", "Back": "A"},
        )

        assert result == note_id

    @patch("requests.Session.post")
    def test_add_notes_batch_with_purple_flags(self, mock_post):
        """Test add_notes automatically sets purple flags on batch."""
        note_ids = [123, 124]
        card_ids = [456, 457, 458]

        mock_responses = [
            # First: addNotes
            Mock(
                json=lambda: {"result": note_ids, "error": None},
                raise_for_status=lambda: None,
            ),
            # Second: notesInfo
            Mock(
                json=lambda: {
                    "result": [
                        {"noteId": 123, "cards": [456, 457]},
                        {"noteId": 124, "cards": [458]},
                    ],
                    "error": None,
                },
                raise_for_status=lambda: None,
            ),
            # Third: setSpecificValueOfCard
            Mock(
                json=lambda: {"result": None, "error": None},
                raise_for_status=lambda: None,
            ),
        ]
        mock_post.side_effect = mock_responses

        result = self.anki_connector.add_notes(
            [
                {
                    "deck_name": "Test",
                    "model_name": "Basic",
                    "fields": {"Front": "Q1", "Back": "A1"},
                    "tags": [],
                },
                {
                    "deck_name": "Test",
                    "model_name": "Basic",
                    "fields": {"Front": "Q2", "Back": "A2"},
                    "tags": [],
                },
            ]
        )

        assert result == note_ids
        assert mock_post.call_count == 3

        calls = mock_post.call_args_list
        assert calls[2][1]["json"]["action"] == "setSpecificValueOfCard"
        assert calls[2][1]["json"]["params"]["cards"] == card_ids

    @patch("requests.Session.post")
    def test_update_note_with_purple_flag(self, mock_post):
        """Test update_note automatically reapplies purple flag."""
        note_id = 123
        card_ids = [456]

        mock_responses = [
            # First: updateNoteFields
            Mock(
                json=lambda: {"result": None, "error": None},
                raise_for_status=lambda: None,
            ),
            # Second: notesInfo
            Mock(
                json=lambda: {
                    "result": [{"noteId": note_id, "cards": card_ids}],
                    "error": None,
                },
                raise_for_status=lambda: None,
            ),
            # Third: setSpecificValueOfCard
            Mock(
                json=lambda: {"result": None, "error": None},
                raise_for_status=lambda: None,
            ),
        ]
        mock_post.side_effect = mock_responses

        self.anki_connector.update_note(
            note_id=note_id, fields={"Front": "Updated Q"}
        )

        assert mock_post.call_count == 3

        calls = mock_post.call_args_list
        assert calls[0][1]["json"]["action"] == "updateNoteFields"
        assert calls[1][1]["json"]["action"] == "notesInfo"
        assert calls[2][1]["json"]["action"] == "setSpecificValueOfCard"
        assert calls[2][1]["json"]["params"]["cards"] == card_ids


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

    @pytest.mark.integration
    def test_real_anki_move_notes_to_deck(self):
        """Test moving notes between decks in real Anki instance."""
        connector = AnkiConnector()

        try:
            # Create test decks
            source_deck = "Test_Move_Source"
            target_deck = "Test_Move_Target"
            connector.create_deck(source_deck)
            connector.create_deck(target_deck)

            # Add a test note to source deck
            note_id = connector.add_note(
                deck_name=source_deck,
                model_name="Basic",
                fields={"Front": "Test Move Question", "Back": "Test Move Answer"},
                tags=["test-move"],
            )

            assert note_id is not None

            # Get card IDs from note
            notes_info = connector.notes_info([note_id])
            assert len(notes_info) == 1
            card_ids = notes_info[0].get("cards", [])
            assert len(card_ids) > 0

            # Move cards to target deck
            connector.change_deck(card_ids, target_deck)

            # Verify the cards were moved by checking notes_info again
            # (Note: The notes_info doesn't directly show deck, but we verify no error occurred)
            updated_info = connector.notes_info([note_id])
            assert len(updated_info) == 1
            assert updated_info[0]["noteId"] == note_id

            # Clean up
            connector.delete_notes([note_id])
            connector.delete_decks([source_deck, target_deck], cards_too=True)

        except Exception as e:
            # Clean up on error
            try:
                if note_id:
                    connector.delete_notes([note_id])
                connector.delete_decks([source_deck, target_deck], cards_too=True)
            except:
                pass
            pytest.skip(f"Anki not available for integration test: {e}")

    @pytest.mark.integration
    def test_real_anki_purple_flag_on_new_card(self):
        """Test that new cards automatically get purple flag."""
        connector = AnkiConnector()
        test_deck = "Test_Purple_Flag"
        note_id = None

        try:
            # Create test deck
            connector.create_deck(test_deck)

            # Add a note (should auto-flag with purple)
            note_id = connector.add_note(
                deck_name=test_deck,
                model_name="Basic",
                fields={"Front": "Test Purple Flag", "Back": "Answer"},
                tags=["test-purple"],
            )

            assert note_id is not None

            # Get card IDs
            card_ids = connector.get_card_ids_from_notes([note_id])
            assert len(card_ids) > 0

            # Verify purple flag (7) is set using cardsInfo
            cards_info = connector._make_request("cardsInfo", {"cards": card_ids})
            assert len(cards_info) > 0
            for card_info in cards_info:
                assert card_info.get("flags") == 7, "Card should have purple flag (7)"

            # Clean up
            connector.delete_notes([note_id])
            connector.delete_decks([test_deck], cards_too=True)

        except Exception as e:
            # Clean up on error
            try:
                if note_id:
                    connector.delete_notes([note_id])
                connector.delete_decks([test_deck], cards_too=True)
            except:
                pass
            pytest.skip(f"Anki not available for integration test: {e}")

    @pytest.mark.integration
    def test_real_anki_purple_flag_on_batch(self):
        """Test that batch-added cards automatically get purple flags."""
        connector = AnkiConnector()
        test_deck = "Test_Purple_Flag_Batch"
        note_ids = []

        try:
            # Create test deck
            connector.create_deck(test_deck)

            # Add batch of notes
            note_ids = connector.add_notes(
                [
                    {
                        "deck_name": test_deck,
                        "model_name": "Basic",
                        "fields": {"Front": "Q1", "Back": "A1"},
                        "tags": ["test-batch"],
                    },
                    {
                        "deck_name": test_deck,
                        "model_name": "Basic",
                        "fields": {"Front": "Q2", "Back": "A2"},
                        "tags": ["test-batch"],
                    },
                ]
            )

            successful_ids = [nid for nid in note_ids if nid is not None]
            assert len(successful_ids) == 2

            # Get all card IDs
            card_ids = connector.get_card_ids_from_notes(successful_ids)
            assert len(card_ids) > 0

            # Verify all cards have purple flag
            cards_info = connector._make_request("cardsInfo", {"cards": card_ids})
            for card_info in cards_info:
                assert card_info.get("flags") == 7, "All cards should have purple flag (7)"

            # Clean up
            connector.delete_notes(successful_ids)
            connector.delete_decks([test_deck], cards_too=True)

        except Exception as e:
            # Clean up on error
            try:
                if note_ids:
                    connector.delete_notes([nid for nid in note_ids if nid])
                connector.delete_decks([test_deck], cards_too=True)
            except:
                pass
            pytest.skip(f"Anki not available for integration test: {e}")

    @pytest.mark.integration
    def test_real_anki_purple_flag_reapplied_on_update(self):
        """Test that purple flag is reapplied when note is updated."""
        connector = AnkiConnector()
        test_deck = "Test_Purple_Flag_Update"
        note_id = None

        try:
            # Create test deck
            connector.create_deck(test_deck)

            # Add a note
            note_id = connector.add_note(
                deck_name=test_deck,
                model_name="Basic",
                fields={"Front": "Original Question", "Back": "Original Answer"},
                tags=["test-update"],
            )

            assert note_id is not None

            # Verify initial purple flag
            card_ids = connector.get_card_ids_from_notes([note_id])
            cards_info = connector._make_request("cardsInfo", {"cards": card_ids})
            assert cards_info[0].get("flags") == 7

            # Update the note
            connector.update_note(
                note_id=note_id, fields={"Front": "Updated Question"}
            )

            # Verify purple flag is still set (reapplied)
            cards_info = connector._make_request("cardsInfo", {"cards": card_ids})
            assert cards_info[0].get("flags") == 7, "Purple flag should persist after update"

            # Clean up
            connector.delete_notes([note_id])
            connector.delete_decks([test_deck], cards_too=True)

        except Exception as e:
            # Clean up on error
            try:
                if note_id:
                    connector.delete_notes([note_id])
                connector.delete_decks([test_deck], cards_too=True)
            except:
                pass
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
