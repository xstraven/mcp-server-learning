#!/usr/bin/env python3
"""
Test to verify LaTeX rendering in different formats.
"""

# Path handling is done by conftest.py

from mcp_server_learning.fastmcp_flashcard_server import (
    FlashcardGenerator,
    AnkiConnector,
    AnkiCardManager,
    get_anki_connector
)


def test_different_latex_formats():
    """Test different LaTeX formats to see which renders better."""
    
    test_cases = [
        {
            "name": "Standard LaTeX",
            "content": "Q: What is the sigmoid function?\nA: $\\sigma(x) = \\frac{1}{1 + e^{-x}}$",
            "deck": "LaTeX Test - Standard"
        },
        {
            "name": "Double-escaped LaTeX",
            "content": "Q: What is the sigmoid function (double-escaped)?\nA: $$\\sigma(x) = \\frac{1}{1 + e^{-x}}$$",
            "deck": "LaTeX Test - Double"
        },
        {
            "name": "MathJax format",
            "content": "Q: What is the sigmoid function (MathJax)?\nA: \\(\\sigma(x) = \\frac{1}{1 + e^{-x}}\\)",
            "deck": "LaTeX Test - MathJax"
        },
        {
            "name": "Display math",
            "content": "Q: What is the sigmoid function (display)?\nA: \\[\\sigma(x) = \\frac{1}{1 + e^{-x}}\\]",
            "deck": "LaTeX Test - Display"
        },
        {
            "name": "Raw LaTeX",
            "content": "Q: What is the sigmoid function (raw)?\nA: \\sigma(x) = \\frac{1}{1 + e^{-x}}",
            "deck": "LaTeX Test - Raw"
        }
    ]
    
    print("Testing different LaTeX formats:\n")
    
    try:
        anki_connector = get_anki_connector()
        card_manager = AnkiCardManager(anki_connector)
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"{i}. {test_case['name']}")
            print(f"   Content: {test_case['content']}")
            
            try:
                # Parse cards
                cards = FlashcardGenerator.parse_text_to_cards(test_case['content'], "front-back")
                
                # Prepare for upload
                cards_data = [{
                    "data": card,
                    "card_type": "front-back", 
                    "tags": ["latex-test", f"format-{i}"],
                } for card in cards]
                
                # Upload
                result = card_manager.upload_cards_to_anki(cards_data, test_case['deck'])
                
                if result["success"]:
                    print(f"   ✅ Successfully uploaded to '{test_case['deck']}'")
                elif "duplicate" in result.get("error", "").lower():
                    print(f"   ⚠️  Card already exists in '{test_case['deck']}'")
                else:
                    print(f"   ❌ Failed: {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
            
            print()
            
    except Exception as e:
        print(f"ERROR: {e}")


def cleanup_test_decks():
    """Optional: Clean up test decks by finding and showing their IDs."""
    print("=== Test Deck Information ===\n")
    
    try:
        anki_connector = get_anki_connector()
        
        test_deck_patterns = [
            "Test Deck - Sigmoid",
            "LaTeX Test",
        ]
        
        for pattern in test_deck_patterns:
            query = f'deck:"{pattern}"'
            print(f"Searching for decks matching: {pattern}")
            
            try:
                note_ids = anki_connector.find_notes(query)
                print(f"Found {len(note_ids)} notes in matching decks")
                
                if note_ids:
                    # Show first few notes
                    limited_ids = note_ids[:3]
                    notes_info = anki_connector.notes_info(limited_ids)
                    
                    for note_info in notes_info:
                        print(f"  Note ID: {note_info['noteId']}, Back: {note_info['fields']['Back']['value'][:50]}...")
                        
            except Exception as e:
                print(f"  Error searching: {e}")
            print()
            
    except Exception as e:
        print(f"ERROR: {e}")


if __name__ == "__main__":
    print("LaTeX Rendering Test\n")
    test_different_latex_formats()
    
    print("\n" + "="*50 + "\n")
    cleanup_test_decks()
    
    print("\n📝 Instructions:")
    print("1. Open Anki and check the test decks")
    print("2. Review the cards to see which LaTeX format renders best")
    print("3. Standard LaTeX with single $ should work with MathJax")
    print("4. If LaTeX doesn't render, check Anki's MathJax addon settings")