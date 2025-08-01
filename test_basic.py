#!/usr/bin/env python3
"""Basic test to verify the flashcard server functionality."""

from src.mcp_server_learning.flashcard_server import (
    FlashcardGenerator,
    HTMLCardRenderer
)

def test_flashcard_generation():
    """Test basic flashcard generation."""
    # Test front-back cards
    content = """Q: What is the capital of France?
A: Paris

---

What is 2 + 2?
4"""
    
    cards = FlashcardGenerator.parse_text_to_cards(content, "front-back")
    print(f"Generated {len(cards)} front-back cards")
    
    for i, card in enumerate(cards):
        print(f"\nCard {i+1}:")
        print(card)
    
    # Test cloze cards
    cloze_content = "The capital of {{France}} is {{Paris}}."
    cloze_cards = FlashcardGenerator.parse_text_to_cards(cloze_content, "cloze")
    print(f"\nGenerated {len(cloze_cards)} cloze cards")
    
    for i, card in enumerate(cloze_cards):
        print(f"\nCloze Card {i+1}:")
        print(card)
    
    # Test LaTeX document generation
    latex_doc = FlashcardGenerator.create_latex_document(cards[:1], "Test Cards")
    print(f"\nGenerated LaTeX document ({len(latex_doc)} characters)")
    print("Document starts with:", latex_doc[:100] + "...")

def test_html_preview():
    """Test HTML preview generation."""
    content = "Q: Test question?\nA: Test answer"
    cards = FlashcardGenerator.parse_text_to_cards(content)
    
    cards_data = [{
        "content": cards[0],
        "card_type": "front-back",
        "tags": ["test"]
    }]
    
    html = HTMLCardRenderer.render_cards_preview(cards_data, "Test Preview")
    print(f"\nGenerated HTML preview ({len(html)} characters)")
    print("HTML starts with:", html[:100] + "...")

if __name__ == "__main__":
    print("Testing MCP Server Learning - Flashcard Server")
    print("=" * 50)
    
    test_flashcard_generation()
    test_html_preview()
    
    print("\n" + "=" * 50)
    print("All tests completed successfully!")