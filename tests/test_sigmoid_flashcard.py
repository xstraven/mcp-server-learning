#!/usr/bin/env python3
"""
Simple test script to verify flashcard creation with Anki.
Tests creating a sigmoid function flashcard with LaTeX equation.
"""

import os

import pytest

from mcp_server_learning.fastmcp_flashcard_server import (
    AnkiCardManager,
    AnkiConnector,
    FlashcardGenerator,
    get_anki_connector,
)

# Path handling is done by conftest.py


@pytest.mark.usefixtures("anki_test_cleanup")
def test_sigmoid_flashcard():
    """Test creating a simple sigmoid function flashcard."""

    print("=== Sigmoid Function Flashcard Test ===\n")

    # Test content - simple Q: A: format
    test_content = """Q: What is the sigmoid function?
A: $\\sigma(x) = \\frac{1}{1 + e^{-x}}$"""

    print("1. Test Content:")
    print(f"'{test_content}'")
    print()

    # Step 1: Test flashcard parsing
    print("2. Testing flashcard parsing...")
    try:
        cards = FlashcardGenerator.parse_text_to_cards(test_content, "front-back")
        print(f"Parsed {len(cards)} card(s):")
        for i, card in enumerate(cards, 1):
            print(f"  Card {i}:")
            print(f"    Front: '{card['front']}'")
            print(f"    Back: '{card['back']}'")
        print()
    except Exception as e:
        print(f"ERROR in parsing: {e}")
        return False

    # Step 2: Test Anki connection
    print("3. Testing Anki connection...")
    try:
        anki_connector = get_anki_connector()
        permission_info = anki_connector.check_permission()
        print(f"Permission info: {permission_info}")

        # Get available decks and models
        decks = anki_connector.get_deck_names()
        models = anki_connector.get_model_names()
        print(f"Available decks: {decks[:5]}{'...' if len(decks) > 5 else ''}")
        print(f"Available models: {models}")
        print()
    except Exception as e:
        print(f"ERROR connecting to Anki: {e}")
        print("Make sure Anki is running with AnkiConnect addon installed.")
        return False

    # Step 3: Test field conversion
    print("4. Testing field conversion...")
    try:
        card_manager = AnkiCardManager(anki_connector)

        # Convert first card to Anki fields
        card_data = cards[0]
        fields = card_manager.convert_to_anki_fields(card_data, "front-back", "Basic")
        print("Converted to Anki fields:")
        for field_name, field_value in fields.items():
            print(f"  {field_name}: '{field_value}'")
        print()
    except Exception as e:
        print(f"ERROR in field conversion: {e}")
        return False

    # Step 4: Create test deck and upload card
    deck_name = "Test Deck - Sigmoid"
    print(f"5. Uploading card to deck '{deck_name}'...")
    try:
        # Prepare cards data for upload
        cards_data = []
        for card in cards:
            cards_data.append(
                {
                    "data": card,
                    "card_type": "front-back",
                    "tags": ["mcp-test-sigmoid", "mcp-test-math"],
                }
            )

        # Upload to Anki
        result = card_manager.upload_cards_to_anki(cards_data, deck_name)

        print("Upload result:")
        print(f"  Success: {result['success']}")
        if result["success"]:
            print(f"  Deck: {result['deck_name']}")
            print(f"  Total cards: {result['total_cards']}")
            print(f"  Successful uploads: {result['successful_uploads']}")
            print(f"  Failed uploads: {result['failed_uploads']}")
            print(f"  Note IDs: {result['note_ids']}")
        else:
            print(f"  Error: {result['error']}")
        print()

        return result["success"]

    except Exception as e:
        print(f"ERROR uploading to Anki: {e}")
        return False


@pytest.mark.usefixtures("anki_test_cleanup")
def test_with_mcp_tool():
    """Test using the MCP tool function directly."""
    print("=== Testing with MCP upload_to_anki function ===\n")

    test_content = """Q: What is the sigmoid function?
A: $\\sigma(x) = \\frac{1}{1 + e^{-x}}$"""

    print("Test content:")
    print(f"'{test_content}'")
    print()

    try:
        # Call the upload function directly (not as MCP tool)
        # We need to import and call the actual function logic
        from mcp_server_learning.fastmcp_flashcard_server import (
            AnkiCardManager,
            FlashcardGenerator,
            get_anki_connector,
        )

        # Generate flashcards from content
        cards = FlashcardGenerator.parse_text_to_cards(test_content, "front-back")

        if not cards:
            print("No flashcards could be generated from the provided content")
            return False

        # Initialize Anki connection
        anki_connector = get_anki_connector()
        card_manager = AnkiCardManager(anki_connector)

        # Prepare cards data for upload
        cards_data = []
        for card in cards:
            cards_data.append(
                {
                    "data": card,
                    "card_type": "front-back",
                    "tags": ["mcp-test-sigmoid", "mcp-test-mcp"],
                }
            )

        # Upload to Anki
        result = card_manager.upload_cards_to_anki(cards_data, "Test Deck - Sigmoid MCP")

        print("Function result:")
        if result["success"]:
            print(
                f"Successfully uploaded {result['successful_uploads']} cards to Anki deck '{result['deck_name']}'"
            )
            if result["failed_uploads"] > 0:
                print(f"({result['failed_uploads']} failed)")
            return True
        else:
            print(f"Failed to upload cards to Anki: {result['error']}")
            return False

    except Exception as e:
        print(f"ERROR using function: {e}")
        return False


def verify_cards_in_anki():
    """Verify that the cards were created correctly in Anki."""
    print("=== Verifying Cards in Anki ===\n")

    try:
        anki_connector = get_anki_connector()

        # Search for our test cards
        test_queries = [
            'deck:"Test Deck - Sigmoid"',
            'deck:"Test Deck - Sigmoid MCP"',
            "tag:sigmoid",
        ]

        for query in test_queries:
            print(f"Searching for: {query}")
            note_ids = anki_connector.find_notes(query)
            print(f"Found {len(note_ids)} notes")

            if note_ids:
                # Get details of first few notes
                limited_ids = note_ids[:3]  # Just first 3 for readability
                notes_info = anki_connector.notes_info(limited_ids)

                for i, note_info in enumerate(notes_info, 1):
                    print(f"  Note {i} (ID: {note_info['noteId']}):")
                    print(f"    Model: {note_info['modelName']}")
                    print(f"    Tags: {', '.join(note_info.get('tags', []))}")

                    # Show fields
                    fields = note_info.get("fields", {})
                    for field_name, field_value in fields.items():
                        content = field_value["value"]
                        print(f"    {field_name}: '{content}'")
            print()

    except Exception as e:
        print(f"ERROR verifying cards: {e}")


if __name__ == "__main__":
    print("Starting Sigmoid Function Flashcard Test\n")

    # Test 1: Direct API usage
    success1 = test_sigmoid_flashcard()

    print("\n" + "=" * 50 + "\n")

    # Test 2: Function usage
    success2 = test_with_mcp_tool()

    print("\n" + "=" * 50 + "\n")

    # Test 3: Verify cards in Anki
    verify_cards_in_anki()

    print("=" * 50)
    print("SUMMARY:")
    print(f"Direct API test: {'PASS' if success1 else 'FAIL'}")
    print(f"Function test: {'PASS' if success2 else 'FAIL'}")

    if success1 and success2:
        print("\n✅ All tests passed! Check Anki for the created cards.")
        print("The LaTeX should render as: σ(x) = 1/(1 + e^(-x))")
    else:
        print("\n❌ Some tests failed. Check the output above for details.")
